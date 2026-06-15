"""
engine/core_v2.py
=================
Motor matemático puro V2.0 del modelo Mundell-Fleming extendido.

Principios V2.0:
  - Funciones PURAS: dado el mismo input → mismo output. Sin efectos laterales.
  - Impuesto PROPORCIONAL `t`: multiplicador = 1/(1 - c₁·(1-t) + m₁).
  - Movilidad IMPERFECTA de capitales: r_BP = r* + ΔEₑ - NX/f.
  - Pass-through cambiario: P_local = α_PT·E·P* + (1-α_PT)·P_NT.
  - Tipo de cambio REAL: q = E·P*/P_local.
  - Condición Marshall-Lerner integrada + efecto J-curve.
  - Tres regímenes: fixed | flexible | crawling_peg.
  - Salter-Swan DINÁMICO: pendientes derivadas del modelo, no hardcodeadas.

Jerarquía de módulos:
  config/parameters_v2.py → engine/core_v2.py → engine/dynamics_v2.py

Este módulo NO importa de ui/, streamlit, ni config/parameters_v2 directamente.
Los tipos TypedDict se importan de config/parameters_v2.py.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

import numpy as np
from scipy.optimize import fsolve

_log = logging.getLogger(__name__)

from config.parameters_v2 import (
    EquilibriumV2,
    PolicyInstruments,
    SalterSwanResult,
    StructuralParams,
)
from engine.monetary_rule import apply_taylor_rule, compute_implied_M


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 2: FUNCIONES DE COMPONENTES (PURAS)
# ─────────────────────────────────────────────────────────────────────────────

def compute_multiplier(c1: float, t_c: float = None, m1: float = 0.0, tau: float = 0.0, *, t: float = None) -> float:
    """
    Multiplicador keynesiano con impuesto proporcional y arancel.

    k_m = 1 / (1 - c₁·(1-t_c) + m₁·(1-τ))

    Retrocompatibilidad: el parámetro 't' es un alias de 't_c'. Si se pasa
    'tau=0.0' reproduce el multiplicador V2.0 exactamente.

    Parameters
    ----------
    c1  : float  Propensión marginal a consumir.
    t_c : float  Tasa impositiva proporcional al consumo/ingreso ∈ (0, 1).
    m1  : float  Propensión marginal a importar.
    tau : float  Arancel a importaciones ∈ [0, 1); default 0.0.
    t   : float  Alias de t_c (retrocompatibilidad).

    Returns
    -------
    float : Multiplicador keynesiano V2.1.

    Raises
    ------
    ValueError
        Si el denominador ≤ 0 (modelo inestable / parámetros inválidos).
    """
    # Retrocompatibilidad: aceptar 't' como alias de 't_c'
    if t_c is None and t is not None:
        t_c = t
    elif t_c is None:
        raise TypeError("compute_multiplier() requiere 't_c' (o el alias 't')")

    denominator = 1.0 - c1 * (1.0 - t_c) + m1 * (1.0 - tau)
    if denominator <= 0.0:
        raise ValueError(
            f"Multiplicador indefinido: 1 - c1·(1-t_c) + m1·(1-τ) = {denominator:.6f}. "
            f"Parámetros: c1={c1}, t_c={t_c}, m1={m1}, tau={tau}. "
            "El modelo requiere denominador > 0."
        )
    return 1.0 / denominator


def compute_autonomous_demand(
    c0: float,
    I0: float,
    G_total: float,
    NX0: float,
    r: float,
    b: float,
    Tr: float = 0.0,
    c1: float = 0.75,
    t_k: float = 0.0,
    rho_k: float = 0.0,
) -> float:
    """
    Demanda autónoma agregada (A) con instrumentos V2.1.

    A = c0 + c1·Tr + I0 - ρ_k·t_k - b·r + G_total + NX0

    Componentes:
      - c0           : Consumo autónomo puro.
      - c1·Tr        : Efecto de transferencias: el gobierno transfiere Tr a
                       los hogares, que consumen la fracción c1 de ellas.
      - I0 - ρ_k·t_k : Inversión autónoma neta del efecto del impuesto
                       corporativo (t_k sube → I_inv baja vía ρ_k).
      - G_total      : Gasto público total (G_c + I_g).
      - NX0          : Exportaciones netas autónomas de base.
      - -b·r         : Componente sensible a la tasa de interés (separado
                       para la resolución del sistema lineal IS-BP).

    Nota: t_c (tasa al consumo) no aparece aquí porque su efecto es
    capturado endógenamente por el multiplicador k_m (reduce Yd = Y·(1-t_c)).

    Parameters
    ----------
    c0      : Consumo autónomo
    I0      : Inversión autónoma
    G_total : Gasto público total (G_c + I_g)
    NX0     : Exportaciones netas autónomas
    r       : Tasa de interés (para el componente -b·r)
    b       : Sensibilidad inversión–tasa de interés
    Tr      : Transferencias del gobierno a hogares (default 0.0)
    c1      : PMgC (para escalar el efecto de Tr; default 0.75)
    t_k     : Tasa impositiva corporativa (default 0.0)
    rho_k   : Sensibilidad de inversión a t_k (default 0.0)

    Returns
    -------
    float : Demanda autónoma A (excluido el término -b·r para el solver)
    """
    return c0 + c1 * Tr + I0 - rho_k * t_k - b * r + G_total + NX0


# ─────────────────────────────────────────────────────────────────────────────
# REFORMA 1B: PASS-THROUGH CAMBIARIO GRADUAL (V3.0)
# ─────────────────────────────────────────────────────────────────────────────

def compute_passthrough_E(
    E_t: float,
    E_t1: float,
    E_t2: float,
    weights: tuple[float, float, float] = (0.40, 0.35, 0.25),
) -> float:
    """
    Tipo de cambio efectivo para el pass-through a precios (media ponderada).

    E_efectivo = w0*E_t + w1*E_{t-1} + w2*E_{t-2}

    Modela la inercia del traspaso cambiario: los importadores agotan
    inventarios viejos antes de actualizar sus listas de precios.
    Retrasa la transmisión completa del shock cambiario en ~2 períodos.

    Pesos calibrados por la literatura empírica de pass-through en emergentes
    (Campa & Goldberg, 2002):
      w0 = 0.40 — efecto del período actual (40%)
      w1 = 0.35 — efecto del período anterior (35%)
      w2 = 0.25 — efecto de dos períodos atrás (25%)

    Parameters
    ----------
    E_t  : Tipo de cambio nominal actual
    E_t1 : Tipo de cambio del período anterior (t-1)
    E_t2 : Tipo de cambio de dos períodos atrás (t-2)
    weights : Pesos de la media ponderada (suman 1.0)

    Returns
    -------
    float : Tipo de cambio efectivo para el cálculo de P_T y P_local
    """
    w0, w1, w2 = weights
    return w0 * E_t + w1 * E_t1 + w2 * E_t2


def compute_price_level(
    E: float,
    P_star: float,
    P_NT: float,
    alpha_PT: float,
    tau: float = 0.0,
    E_eff: Optional[float] = None,
) -> float:
    """
    Nivel de precios doméstico general (ponderación de transables y no transables).

    P_T = E_eff · P* · (1 + τ)        [usa E_eff para pass-through gradual]
    P_local = α_PT · P_T + (1 - α_PT) · P_NT

    V3.0 [Reforma 1B]: acepta E_eff (tipo de cambio efectivo promediado).
    Si E_eff is None, usa E (comportamiento V2.0 exacto).
    El TCR siempre se calcula con E nominal real, no con E_eff.

    Parameters
    ----------
    E       : Tipo de cambio nominal real (para referencia)
    P_star  : Nivel de precios externo (base = 1.0)
    P_NT    : Precio de bienes no-transables (variable de estado)
    alpha_PT: Peso bienes transables en la canasta de precios ∈ [0,1]
    tau     : Arancel a importaciones ∈ [0,1); default 0.0
    E_eff   : Tipo de cambio efectivo pass-through (V3.0); None = usa E (V2.0)

    Returns
    -------
    float : Nivel de precios doméstico P_local
    """
    if not (0.0 <= alpha_PT <= 1.0):
        raise ValueError(f"alpha_PT debe estar en [0,1], recibido: {alpha_PT}")
    E_for_prices = E_eff if E_eff is not None else E
    P_T = E_for_prices * P_star * (1.0 + tau)
    return alpha_PT * P_T + (1.0 - alpha_PT) * P_NT


def compute_real_exchange_rate(
    E: float,
    P_star: float,
    P_local: float,
) -> float:
    """
    Tipo de cambio real (q).

    q = (E · P*) / P_local

    q > 1 → depreciación real (mejora competitividad).
    q < 1 → apreciación real (pérdida de competitividad).

    Parameters
    ----------
    E       : Tipo de cambio nominal
    P_star  : Nivel de precios externo
    P_local : Nivel de precios doméstico

    Returns
    -------
    float : Tipo de cambio real q

    Raises
    ------
    ValueError
        Si P_local ≤ 0.
    """
    if P_local <= 0.0:
        raise ValueError(f"P_local debe ser positivo, recibido: {P_local}")
    return (E * P_star) / P_local


def compute_sectoral_composition(
    Y: float,
    P_T: float,
    P_NT: float,
    alpha_PT: float,
) -> tuple[float, float, float]:
    """
    Calcula la composición sectorial del PIB entre Transables (Y_T) y No-Transables (Y_NT).
    Ponderado estrictamente para que, a q_int = 1.0 (estado estacionario t=0), el sector
    transable sea exactamente el 40% y el no transable sea el 60% del producto.
    """
    alpha_PT = 0.40
    q_int = P_T / P_NT if P_NT > 0.0 else 0.0
    share_T = max(0.05, min(0.95, alpha_PT * q_int))
    Y_T = Y * share_T
    Y_NT = Y * (1.0 - share_T)
    return q_int, Y_T, Y_NT


def compute_NX(
    NX0: float,
    epsilon_x: float,
    epsilon_m: float,
    q: float,
    m1: float,
    Y: float,
    j_curve_active: bool = False,
    epsilon_x_short: float = 0.10,
    epsilon_m_short: float = 0.05,
    # V2.1 sector externo desagregado
    x0: float = 0.0,
    x1: float = 0.0,
    Y_star: float = 0.0,
    m0: float = 0.0,
    tau: float = 0.0,
    s_x: float = 0.0,
) -> tuple[float, float, float]:
    """
    Exportaciones brutas, importaciones brutas y exportaciones netas.

    Sector externo desagregado (V2.1):
    ───────────────────────────────────
    X     = x0 + x1·Y_star + ε_x_eff · q · (1 + s_x)
    M_imp = m0 + m1·(1-τ)·Y - ε_m_eff · q
    NX    = X - M_imp

    Condición Marshall-Lerner: una devaluación mejora NX si y solo si
    ε_x + ε_m > 1. Si no se cumple, el coeficiente de q en X es negativo
    (usando el epsilon efectivo negativo ya establecido en V2.0).

    Efecto J-curve: en el primer turno post-devaluación, las exportaciones
    responden lentamente (ε_x_short) y las importaciones caen poco
    (ε_m_short), causando una caída inicial de NX.

    Retrocompatibilidad: cuando x0=x1=Y_star=m0=tau=s_x=0.0, la función
    reproduce exactamente el NX de V2.0 (NX = NX0 + eps_eff·q - m1·Y).

    Parameters
    ----------
    NX0            : Exportaciones netas autónomas (V2.0 legacy; se usa si x0=m0=0)
    epsilon_x      : Elasticidad precio de exportaciones
    epsilon_m      : Elasticidad precio de importaciones
    q              : Tipo de cambio real
    m1             : Propensión marginal a importar
    Y              : Ingreso
    j_curve_active : True → primer turno post-devaluación (efecto J)
    epsilon_x_short: Elasticidad de corto plazo en X para el efecto J
    epsilon_m_short: Elasticidad de corto plazo en M_imp para el efecto J
    x0             : Exportaciones autónomas (nivel base)
    x1             : Sensibilidad de X a Y_star
    Y_star         : PIB mundial (variable exógena)
    m0             : Importaciones autónomas (nivel base)
    tau            : Arancel a importaciones ∈ [0, 1)
    s_x            : Subsidio a exportaciones ∈ [0, 1)

    Returns
    -------
    tuple[float, float, float]
        (NX, X, M_imp) — exportaciones netas, brutas e importaciones brutas.
    """
    ml_satisfied = (epsilon_x + epsilon_m) > 1.0

    # Elasticidad efectiva de exportaciones según M-L y J-curve
    if j_curve_active:
        eps_x_eff = epsilon_x_short
        eps_m_eff = epsilon_m_short
    elif ml_satisfied:
        eps_x_eff = epsilon_x
        eps_m_eff = epsilon_m
    else:
        # M-L no cumplida: devaluación EMPEORA NX
        # eps_x efectivo negativo; eps_m aún positivo pero dominado
        eps_x_eff = -(epsilon_m - epsilon_x)
        eps_m_eff = epsilon_m

    # Modo V2.1 desagregado vs. modo V2.0 legacy
    use_disaggregated = (x0 != 0.0 or m0 != 0.0 or x1 != 0.0 or Y_star != 0.0)

    if use_disaggregated:
        X     = x0 + x1 * Y_star + eps_x_eff * q * (1.0 + s_x)
        M_imp = m0 + m1 * (1.0 - tau) * Y - eps_m_eff * q
    else:
        # Modo legacy V2.0: NX0 es el término autónomo neto
        # X = NX0_positivo + eps_x_eff * q * (1 + s_x)
        # M_imp = m1*(1-tau)*Y
        X     = NX0 + eps_x_eff * q * (1.0 + s_x)
        M_imp = m1 * (1.0 - tau) * Y

    # Cota inferior de importaciones (no negatividad)
    M_imp = max(0.0, M_imp)

    NX = X - M_imp
    return NX, X, M_imp


def compute_bp_curve(
    r_star: float,
    delta_E_expected: float,
    NX: float,
    f: float,
    rho: float = 0.0,
) -> float:
    """
    Curva BP: UIP + Prima de Riesgo + Corrección por Movilidad Imperfecta.

    Fundamento teórico (V2.1):
    ──────────────────────────
    El núcleo es la Paridad Descubierta de Intereses (UIP):

        r_BP_UIP = r* + ΔEₑ + ρ

    donde ρ es la prima de riesgo-país (= 0.0 hasta Fase 3, cuando se
    conectará a la razón Deuda/PIB).

    La corrección por movilidad imperfecta de capitales (f finito) proviene
    de la condición de equilibrio de Balanza de Pagos:

        CA + KA = 0  →  NX + f·(r - r* - ΔEₑ - ρ) = 0
        →  r_BP = r* + ΔEₑ + ρ - NX/f

    El parámetro `f` controla la *pendiente* de la curva BP:
    - f → ∞ (movilidad perfecta): corrección → 0  →  r_BP = r* + ΔEₑ + ρ  (horizontal)
    - f pequeño (movilidad baja): corrección grande  →  BP más empinada

    La prima ρ es el único componente que desplaza el nivel de la BP de forma
    exógena; NX/f ajusta la pendiente endógenamente.

    Parameters
    ----------
    r_star           : Tasa de interés internacional
    delta_E_expected : Depreciación esperada del TC (positivo = deprecia)
    NX               : Exportaciones netas de equilibrio (CA simplificada)
    f                : Parámetro de movilidad de capitales (f > 0)
    rho              : Prima de riesgo-país (Fase 3: ρ = ρ(B/Y)); default 0.0

    Returns
    -------
    float : Tasa de interés de equilibrio externo r_BP

    Raises
    ------
    ValueError
        Si f ≤ 0.
    """
    if f <= 0.0:
        raise ValueError(f"Parámetro f debe ser positivo, recibido: {f}")
    slope_correction = NX / f
    return r_star + delta_E_expected + rho * 100.0 - slope_correction


def is_curve_v2(
    Y: float,
    c1: float,
    t: float,
    m1: float,
    b: float,
    A: float,
    epsilon_x: float,
    q: float,
) -> float:
    """
    Curva IS V2.0 con impuesto proporcional y tipo de cambio real.

    r_IS = (A + ε_x·q - Y·(1 - c₁·(1-t) + m₁)) / b

    Derivada de la condición de equilibrio del mercado de bienes:
    Y = k_m · (A + ε_x·q - b·r)

    Parameters
    ----------
    Y         : Nivel de ingreso
    c1        : Propensión marginal a consumir
    t         : Tasa impositiva proporcional
    m1        : Propensión marginal a importar
    b         : Sensibilidad inversión–tasa de interés
    A         : Demanda autónoma (sin el componente ε_x·q)
    epsilon_x : Elasticidad-precio exportaciones
    q         : Tipo de cambio real

    Returns
    -------
    float : Tasa de interés sobre la curva IS
    """
    if b <= 0.0:
        raise ValueError(f"Parámetro b debe ser positivo, recibido: {b}")
    slope_term = 1.0 - c1 * (1.0 - t) + m1
    return (A + epsilon_x * q - Y * slope_term) / b


def lm_curve_v2(Y: float, k: float, M_real: float, h: float) -> float:
    """
    Curva LM V2.0 con saldos reales.

    r_LM = (k·Y - M_real) / h

    M_real = M / P_local (calculado externamente antes de llamar esta función)

    Parameters
    ----------
    Y      : Nivel de ingreso
    k      : Sensibilidad demanda de dinero al ingreso
    M_real : Saldos monetarios reales (M / P_local)
    h      : Sensibilidad demanda de dinero a la tasa de interés

    Returns
    -------
    float : Tasa de interés sobre la curva LM
    """
    if h <= 0.0:
        raise ValueError(f"Parámetro h debe ser positivo, recibido: {h}")
    return (k * Y - M_real) / h


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 3: SOLVERS DE EQUILIBRIO
# ─────────────────────────────────────────────────────────────────────────────

def eq_fixed_v2(
    sp: StructuralParams,
    pi: PolicyInstruments,
    Y_pot: float,
    P_NT: float,
    delta_E_expected: float = 0.0,
    j_curve_active: bool = False,
    rho: float = 0.0,  # FASE 3.1
    velocity_penalty: float = 1.0,
    pi_e: float = 0.03,  # V3.5: expectativa de inflación previa para tasa real
    r_prev: Optional[float] = None, # V3.6
    Y_prev: Optional[float] = None, # V3.8
) -> EquilibriumV2:
    """
    Equilibrio IS-LM-BP bajo Tipo de Cambio FIJO (V2.1).

    Bajo TC fijo:
    - E es exógeno (instrumento del banco central).
    - M se acomoda endógenamente para mantener r = r_BP.
    - La condición externa determina r.

    V2.1 incorpora: G_c+I_g=G_total, Tr, t_c, t_k, rho_k, tau, s_x, k_c.

    Pasos:
    1. Extraer instrumentos V2.1 con retrocompatibilidad.
    2. Calcular P_local y q.
    3. Resolver sistema 2×2 IS-BP para (Y, r).
    4. Calcular M_endo (LM).
    5. Calcular variables derivadas (C, I_inv, X, M_imp, NX, A_dom).
    6. Verificar identidad macroeconómica.

    Parameters
    ----------
    sp               : Parámetros estructurales
    pi               : Instrumentos de política
    Y_pot            : PIB potencial actual
    P_NT             : Precio de bienes no-transables (estado)
    delta_E_expected : Variación esperada del TC (= 0 bajo TC fijo creíble)
    j_curve_active   : Flag de efecto J-curve activo
    rho              : Prima de riesgo país (Fase 3: de la Deuda Soberana)

    Returns
    -------
    EquilibriumV2
    """
    E      = pi["E"]
    r_star = pi["r_star"]
    P_star = sp["P_star"]

    # ── 1. Extraer instrumentos V2.1 con retrocompatibilidad ──────────────────
    G_c   = pi.get("G_c",  pi.get("G", 20.0))
    I_g   = pi.get("I_g",  0.0)
    Tr    = pi.get("Tr",   0.0)
    t_c   = pi.get("t_c",  sp.get("t", 0.20))  # retrocompat: usa sp["t"] si no hay t_c
    t_k   = pi.get("t_k",  0.0)
    tau   = pi.get("tau",  0.0)
    s_x   = pi.get("s_x",  0.0)
    k_c   = pi.get("k_c",  0.0)
    rho_k = sp.get("rho_k", 0.0)

    G_total = G_c + I_g
    # Sincronizar G en pi para retrocompatibilidad (snapshots, scoring, etc.)
    pi = dict(pi)  # copia local
    pi["G"] = G_total

    # ── 2. Nivel de precios local y TCR ───────────────────────────────────────
    P_local = compute_price_level(E, P_star, P_NT, sp["alpha_PT"], tau=tau)
    q = compute_real_exchange_rate(E, P_star, P_local)

    # ── Multiplicador con tau y t_c ───────────────────────────────────────────
    k_m = compute_multiplier(sp["c1"], t_c, sp["m1"], tau)
    slope = 1.0 - sp["c1"] * (1.0 - t_c) + sp["m1"] * (1.0 - tau)  # = 1/k_m

    # Movilidad de capitales efectiva inicial (asumiendo entrada neta de capitales: sin cepo)
    f_inflow = max(sp["f"], 1e-4)

    # Componente autónomo y elasticidad efectiva según modo desagregado vs legacy
    x0 = sp.get("x0", 0.0)
    x1 = sp.get("x1", 0.0)
    Y_star = sp.get("Y_star", 0.0)
    m0 = sp.get("m0", 0.0)
    use_disaggregated = (x0 != 0.0 or m0 != 0.0 or x1 != 0.0 or Y_star != 0.0)

    if use_disaggregated:
        NX0_eff = x0 + x1 * Y_star - m0
        ml_ok = (sp["epsilon_x"] + sp["epsilon_m"]) > 1.0
        if j_curve_active:
            eps_x_eff = 0.10
            eps_m_eff = 0.10
        elif ml_ok:
            eps_x_eff = sp["epsilon_x"]
            eps_m_eff = sp["epsilon_m"]
        else:
            eps_x_eff = -(sp["epsilon_m"] - sp["epsilon_x"])
            eps_m_eff = sp["epsilon_m"]
        eps_eff_sx = eps_x_eff * (1.0 + s_x) + eps_m_eff
    else:
        NX0_eff = sp["NX0"]
        ml_ok = (sp["epsilon_x"] + sp["epsilon_m"]) > 1.0
        if j_curve_active:
            eps_eff = 0.10
        elif ml_ok:
            eps_eff = sp["epsilon_x"]
        else:
            eps_eff = -(sp["epsilon_m"] - sp["epsilon_x"])
        eps_eff_sx = eps_eff * (1.0 + s_x)

    # Componente autónomo (sin término de r; se separa para el sistema lineal)
    # V3.0 Reforma 4B: si lambda_h > 0, aplicar inercia del consumo a c0
    lambda_h = sp.get("lambda_h", 0.0)
    C_prev   = pi.get("_C_prev", 0.0)  # Pasado internamente por state_manager
    c0_eff   = lambda_h * C_prev + (1.0 - lambda_h) * sp["c0"] if (lambda_h > 0 and C_prev > 0) else sp["c0"]

    # V3.0 Reforma 4A: crowding-in/out ya calculado externamente como delta_I0
    delta_I0 = pi.get("_delta_I0", 0.0)

    # V3.5: Suavizar la tasa real esperada acotando la deflación esperada a un piso de -2%
    pi_e_clamped = max(-0.02, pi_e)

    A_auto = sp["c0"] + sp["c1"] * Tr + sp["I0"] - rho_k * t_k + G_total + NX0_eff
    # Sumamos sp["b"] * pi_e_clamped * 100.0 para reflejar el canal de tasa real en la inversión privada
    A_autonomo_neto = (A_auto - sp["c0"]) + c0_eff + delta_I0 + sp.get("b", 1.0) * pi_e_clamped * 100.0

    # ── 3. Sistema 2×2: IS y BP simultáneas (Y, r) ───────────────────────────
    m1_eff = sp["m1"] * (1.0 - tau)  # propensión marginal a importar efectiva
    rhs_bp_inflow = (
        r_star + delta_E_expected * 100.0 + rho * 100.0
        - NX0_eff / f_inflow
        - eps_eff_sx * q / f_inflow
    )

    A_mat_inflow = np.array([
        [1.0,              sp["b"] * k_m],
        [-m1_eff / f_inflow,  1.0          ],
    ])
    b_vec_inflow = np.array([
        k_m * (A_autonomo_neto + eps_eff_sx * q),
        rhs_bp_inflow,
    ])

    f_eff = f_inflow
    try:
        sol = np.linalg.solve(A_mat_inflow, b_vec_inflow)
        Y, r = float(sol[0]), float(sol[1])
        
        # Evaluar el signo del flujo neto de capitales financieros
        parity = r_star + delta_E_expected * 100.0 + rho * 100.0
        if r < parity:
            # Flujo negativo (salida/fuga de dólares): se activa el cepo (1.0 - k_c)
            f_outflow = max(sp["f"] * (1.0 - k_c), 1e-4)
            f_eff = f_outflow
            A_mat_outflow = np.array([
                [1.0,                    sp["b"] * k_m],
                [-m1_eff / f_outflow,   1.0          ],
            ])
            rhs_bp_outflow = (
                r_star + delta_E_expected * 100.0 + rho * 100.0
                - NX0_eff / f_outflow
                - eps_eff_sx * q / f_outflow
            )
            b_vec_outflow = np.array([
                k_m * (A_autonomo_neto + eps_eff_sx * q),
                rhs_bp_outflow,
            ])
            sol_outflow = np.linalg.solve(A_mat_outflow, b_vec_outflow)
            Y, r = float(sol_outflow[0]), float(sol_outflow[1])
    except np.linalg.LinAlgError:
        # Sistema singular: recurrir a solución simplificada r = r* + ΔEₑ + ρ
        r = r_star + delta_E_expected * 100.0 + rho * 100.0
        Y = k_m * (A_autonomo_neto + eps_eff_sx * q - sp["b"] * r)

    # Suavizado intertemporal de la tasa de interés de mercado (V3.6)
    if r_prev is not None:
        r_unconstrained = r
        # Damping fuerte: 70% inercia, 30% nuevo equilibrio para evitar saltos bruscos
        r = 0.70 * r_prev + 0.30 * r_unconstrained
        # Recalcular Y con la tasa suavizada para mantener la identidad macroeconómica
        Y = k_m * (A_autonomo_neto + eps_eff_sx * q - sp["b"] * r)

    Y_solved = Y
    # Suavizado intertemporal del PIB real (inercia industrial V4.2)
    # 75% valor resuelto, 25% turno anterior → convergencia más rápida con amortiguación suficiente
    if Y_prev is not None:
        Y = 0.75 * Y + 0.25 * Y_prev
    Y = max(10.0, Y)

    # ── 4. M endógena (LM) con esterilización V3.0 (Reforma 2B) ──────────────
    M_real_eq = (sp["k"] * Y - sp["h"] * r) / velocity_penalty
    # psi_s = 0 (default): sin esterilización → M_endo es la solución LM directa.
    # psi_s > 0: el BC emite bonos para esterilizar las compras de divisas,
    #   reduciendo el multiplicador monetario efectivo proporcionalmente.
    psi_s = pi.get("psi_s", 0.0)
    if psi_s > 0.0:
        M_real_eq = M_real_eq * (1.0 - 0.5 * psi_s)
    M_real_eq = max(1e-6, M_real_eq)
    M_endo = max(1e-4, M_real_eq * P_local)


    # ── 5. Variables derivadas ────────────────────────────────────────────────
    NX, X, M_imp = compute_NX(
        sp["NX0"], sp["epsilon_x"], sp["epsilon_m"],
        q, sp["m1"], Y, j_curve_active,
        x0=sp.get("x0", 0.0), x1=sp.get("x1", 0.0),
        Y_star=sp.get("Y_star", 0.0), m0=sp.get("m0", 0.0),
        tau=tau, s_x=s_x,
    )
    NX_prev = pi.get("_NX_prev")
    if NX_prev is not None:
        NX = 0.70 * NX + 0.30 * NX_prev
    C     = c0_eff + sp["c1"] * (Y * (1.0 - t_c) + Tr)
    # V3.8: Si hay inercia en Y o se aplicó floor, forzar consistencia de la identidad macroeconómica en la inversión
    if Y_prev is not None or abs(Y - Y_solved) > 1e-6:
        I_inv = Y - C - G_total - NX
    else:
        I_inv = sp["I0"] + delta_I0 - sp["b"] * (r - pi_e_clamped * 100.0) - rho_k * t_k
    mult  = k_m
    gap   = (Y - Y_pot) / Y_pot if Y_pot > 0 else 0.0
    A_dom = C + I_inv + G_total   # Absorción doméstica (SIN NX)

    # Economía Dual (FASE 3.1)
    P_T = E * P_star * (1.0 + tau)
    q_int, Y_T, Y_NT = compute_sectoral_composition(Y, P_T, P_NT, sp["alpha_PT"])

    # ── FIX F-01: Verificación de identidad macroeconómica Y = C+I+G+NX ─────
    _identity_gap = abs(Y - (A_dom + NX))
    if _identity_gap > 1e-3:
        _log.warning(
            "[eq_fixed_v2] Identidad Y = C+I+G+NX violada. "
            "Y=%.6f, C+I+G+NX=%.6f, brecha=%.6f. "
            "Revisar calibración de eps_eff o parámetros del escenario.",
            Y, A_dom + NX, _identity_gap,
        )

    return EquilibriumV2(
        Y=round(Y, 6),
        r=round(r, 6),
        E_endo=float("nan"),        # E es exógeno bajo TC fijo
        M_endo=round(M_endo, 6),
        NX=round(NX, 6),
        X=round(X, 6),
        M_imp=round(M_imp, 6),
        G_total=round(G_total, 6),
        C=round(C, 6),
        I_inv=round(I_inv, 6),
        mult=round(mult, 6),
        P_local=round(P_local, 6),
        q_real=round(q, 6),
        M_real=round(M_real_eq, 6),
        gap=round(gap, 6),
        A_domestic=round(A_dom, 6),
        P_T=round(P_T, 6),
        q_int=round(q_int, 6),
        Y_T=round(Y_T, 6),
        Y_NT=round(Y_NT, 6),
        FX_intervention=0.0,  # Fijo: sin intervención cambiaria endógena
    )


def eq_flexible_v2(
    sp: StructuralParams,
    pi: PolicyInstruments,
    Y_pot: float,
    P_NT: float,
    E_prev: float,
    Y_prev: Optional[float] = None,
    r_prev: Optional[float] = None,
    E_guess: Optional[float] = None,
    j_curve_active: bool = False,
    delta_E_external: float = 0.0,
    max_iter: int = 200,
    tol: float = 1e-6,
    rho: float = 0.0,
    velocity_penalty: float = 1.0,
    # V3.0 Reforma 1B: pass-through gradual
    E_eff: Optional[float] = None,
    # V3.0 Reforma 1A: bandas dinámicas PPP
    pi_local_prev: float = 0.0,
    pi_star: float = 0.03,
) -> EquilibriumV2:
    """
    Equilibrio IS-LM-BP bajo Tipo de Cambio FLEXIBLE (V3.0).

    V3.0 incorpora:
    - Reforma 2A: Modo rate_targeting (LM horizontal en r = r_ref).
    - Reforma 1A: Bandas cambiarias dinámicas basadas en PPP e UIP.
    - Reforma 1B: Pass-through gradual con E_eff ponderado.
    - Reforma 4A/4B: inercia del consumo y crowding effects.

    Parameters
    ----------
    sp               : Parámetros estructurales
    pi               : Instrumentos de política
    Y_pot            : PIB potencial actual
    P_NT             : Precio de no-transables
    E_prev           : Tipo de cambio del período anterior
    Y_prev, r_prev   : Puntos iniciales opcionales
    E_guess          : Estimación inicial de E_endo
    j_curve_active   : Flag de efecto J-curve
    delta_E_external : Prima de devaluación exógena
    max_iter, tol    : Parámetros de convergencia
    rho              : Prima de riesgo soberano
    E_eff            : TC efectivo pass-through (V3.0 Reforma 1B)
    pi_local_prev    : Inflación local previa para banda PPP (V3.0 Reforma 1A)
    pi_star          : Inflación externa de referencia (V3.0 Reforma 1A)

    Returns
    -------
    EquilibriumV2
    """
    monetary_mode = pi.get("monetary_mode", "quantity")
    M      = pi["M"]
    r_star = pi["r_star"]
    P_star = sp["P_star"]

    # ── 1. Extraer instrumentos V2.1 con retrocompatibilidad ──────────────────
    G_c   = pi.get("G_c",  pi.get("G", 20.0))
    I_g   = pi.get("I_g",  0.0)
    Tr    = pi.get("Tr",   0.0)
    t_c   = pi.get("t_c",  sp.get("t", 0.20))
    t_k   = pi.get("t_k",  0.0)
    tau   = pi.get("tau",  0.0)
    s_x   = pi.get("s_x",  0.0)
    k_c   = pi.get("k_c",  0.0)
    rho_k = sp.get("rho_k", 0.0)

    G_total = G_c + I_g
    pi = dict(pi)
    pi["G"] = G_total

    # ── Parámetros efectivos ──────────────────────────────────────────────────
    k_m   = compute_multiplier(sp["c1"], t_c, sp["m1"], tau)
    m1_eff = sp["m1"] * (1.0 - tau)
    f_eff  = max(sp["f"] * (1.0 - k_c), 1e-4)

    # Componente autónomo y elasticidad efectiva según modo desagregado vs legacy
    x0 = sp.get("x0", 0.0)
    x1 = sp.get("x1", 0.0)
    Y_star = sp.get("Y_star", 0.0)
    m0 = sp.get("m0", 0.0)
    use_disaggregated = (x0 != 0.0 or m0 != 0.0 or x1 != 0.0 or Y_star != 0.0)

    if use_disaggregated:
        NX0_eff = x0 + x1 * Y_star - m0
        ml_ok = (sp["epsilon_x"] + sp["epsilon_m"]) > 1.0
        if j_curve_active:
            eps_x_eff = 0.10
            eps_m_eff = 0.10
        elif ml_ok:
            eps_x_eff = sp["epsilon_x"]
            eps_m_eff = sp["epsilon_m"]
        else:
            eps_x_eff = -(sp["epsilon_m"] - sp["epsilon_x"])
            eps_m_eff = sp["epsilon_m"]
        eps_eff_sx = eps_x_eff * (1.0 + s_x) + eps_m_eff
    else:
        NX0_eff = sp["NX0"]
        ml_ok = (sp["epsilon_x"] + sp["epsilon_m"]) > 1.0
        if j_curve_active:
            eps_eff = 0.10
        elif ml_ok:
            eps_eff = sp["epsilon_x"]
        else:
            eps_eff = -(sp["epsilon_m"] - sp["epsilon_x"])
        eps_eff_sx = eps_eff * (1.0 + s_x)

    # V3.0 Reforma 4B/4A: inercia del consumo y crowding effects
    lambda_h = sp.get("lambda_h", 0.0)
    C_prev_flex = pi.get("_C_prev", 0.0)
    c0_eff_flex = (lambda_h * C_prev_flex + (1.0 - lambda_h) * sp["c0"]
                   if (lambda_h > 0 and C_prev_flex > 0) else sp["c0"])
    delta_I0_flex = pi.get("_delta_I0", 0.0)

    # V3.5: Suavizar la tasa real esperada acotando la deflación esperada a un piso de -2%
    pi_e_clamped = max(-0.02, pi_local_prev)

    # Demanda autónoma base estática (sin el término -b*r, contiene sp["c0"])
    A_auto_base = sp["c0"] + sp["c1"] * Tr + sp["I0"] - rho_k * t_k + G_total + NX0_eff

    # El término autónomo real neto remueve el c0 viejo para evitar la doble contabilidad
    # Sumamos sp["b"] * pi_e_clamped * 100.0 para reflejar la tasa de interés real
    A_autonomo_neto = (A_auto_base - sp["c0"]) + c0_eff_flex + delta_I0_flex + sp.get("b", 1.0) * pi_e_clamped * 100.0

    # Punto inicial de E
    E_current = E_guess if E_guess is not None else E_prev

    # Loop de convergencia externo (circular E ↔ P_local)
    for _ in range(max_iter):
        P_local = compute_price_level(E_current, P_star, P_NT, sp["alpha_PT"], tau=tau)
        M_real  = (M / P_local) / velocity_penalty
        q       = compute_real_exchange_rate(E_current, P_star, P_local)

        # Expectativas cambiarias: variación desde período anterior
        delta_E_expected = (E_current - E_prev) / max(E_prev, 1e-9)

        # Puntos iniciales para fsolve
        Y0 = Y_prev if Y_prev is not None else (M_real + sp["h"] * r_star) / sp["k"]
        r0 = r_prev if r_prev is not None else r_star
        E0 = E_current

        def system(vars: np.ndarray) -> list[float]:
            Y_s, r_s, E_s = float(vars[0]), float(vars[1]), float(vars[2])
            E_s_safe = max(1e-4, E_s)
            P_loc_s = compute_price_level(E_s_safe, P_star, P_NT, sp["alpha_PT"], tau=tau)
            P_loc_s = max(1e-4, P_loc_s)
            q_s      = compute_real_exchange_rate(E_s_safe, P_star, P_loc_s)
            M_real_s = M / P_loc_s

            # NX_s: usamos la versión escalar (NX, X, M_imp)[0]
            NX_s, _, _ = compute_NX(
                sp["NX0"], sp["epsilon_x"], sp["epsilon_m"],
                q_s, sp["m1"], Y_s, j_curve_active,
                x0=sp.get("x0", 0.0), x1=sp.get("x1", 0.0),
                Y_star=sp.get("Y_star", 0.0), m0=sp.get("m0", 0.0),
                tau=tau, s_x=s_x,
            )

            # Convertir delta_E_e a puntos porcentuales para que sea consistente con r_star y rho
            delta_E_e_pct = ((E_s_safe - E_prev) / max(E_prev, 1e-9)) * 100.0 + (delta_E_external * 100.0)

            # IS: Y = k_m · (A_autonomo_neto - b·r + eps_eff_sx·q)
            eq_IS = Y_s - k_m * (A_autonomo_neto - sp["b"] * r_s + eps_eff_sx * q_s)
            # LM: r = r_ref under rate_targeting, otherwise r = (k·Y - M_real / velocity_penalty) / h
            if monetary_mode == "rate_targeting":
                r_ref_val = pi.get("r_ref", r_star)
                eq_LM = r_s - r_ref_val
            else:
                eq_LM = r_s - (sp["k"] * Y_s - M_real_s / velocity_penalty) / sp["h"]
            # Evaluar asimetría de cepo: si r_s < parity (salida/fuga), aplicar (1 - k_c), si no 1.0 (entrada libre)
            parity = r_star + delta_E_e_pct + rho * 100.0
            if r_s < parity:
                f_s = max(sp["f"] * (1.0 - k_c), 1e-4)
            else:
                f_s = max(sp["f"], 1e-4)
            # BP: r = r* + ΔEₑ + ρ - NX/f_s
            eq_BP = r_s - compute_bp_curve(r_star, delta_E_e_pct, NX_s, f_s, rho=rho)
            return [eq_IS, eq_LM, eq_BP]

        from scipy.optimize import least_squares
        lower_bounds = [10.0, 0.1, 0.1]
        upper_bounds = [300.0, 100.0, 100.0]
        try:
            sol = least_squares(
                system, 
                x0=[Y0, r0, E0], 
                bounds=(lower_bounds, upper_bounds), 
                ftol=1e-7, xtol=1e-7
            )
            Y_new, r_new, E_new = float(sol.x[0]), float(sol.x[1]), float(sol.x[2])
        except Exception:
            # Fallback a fsolve si falla
            sol_f = fsolve(system, [Y0, r0, E0])
            Y_new = max(10.0, min(300.0, float(sol_f[0])))
            r_new = max(0.1, min(100.0, float(sol_f[1])))
            E_new = max(1e-4, min(100.0, float(sol_f[2])))

        if r_prev is not None:
            max_jump = 4.0 # 400 puntos básicos máximo por turno
            r_new = r_prev + max(-max_jump, min(max_jump, r_new - r_prev))

        # ── REFORMA 1A V3.0: Bandas dinámicas basadas en PPP + UIP ──────────────
        # PPP: el TC fundamental ajusta por diferencial de inflación
        E_ppp = E_prev * (1.0 + pi_local_prev - pi_star)
        # UIP: ajuste por diferencial de tasas
        r_prev_safe = r_prev if r_prev is not None else r_star
        E_uip = E_prev * (1.0 + (r_prev_safe - r_star) / 100.0)
        E_fundamental = 0.6 * E_ppp + 0.4 * E_uip
        # Banda: ±20% alrededor del fundamental (vs ±50%/100% estático previo)
        band_lo = max(0.5 * E_prev, E_fundamental * 0.80)
        band_hi = min(2.0 * E_prev, E_fundamental * 1.20)

        E_new_bounded = max(band_lo, min(band_hi, E_new))

        # Intervención cambiaria esterilizada (Reforma 1A)
        fx_intervention_this_iter = max(0.0, E_prev - E_new) * 0.5 if E_new < band_lo else 0.0

        # Damping: mover solo 40% hacia la nueva solución (suaviza la convergencia circular)
        damping = 0.4
        E_next = E_current + damping * (E_new_bounded - E_current)
        
        # Criterio de convergencia
        if abs(E_next - E_current) < tol:
            E_current = E_next
            break
        E_current = E_next

    # Calcular valores finales con E convergido
    # V3.0 Reforma 1B: usar E_eff para pass-through si está disponible
    P_local_f = compute_price_level(E_current, P_star, P_NT, sp["alpha_PT"], tau=tau, E_eff=E_eff)
    q_f       = compute_real_exchange_rate(E_current, P_star, P_local_f)
    M_real_f  = (M / P_local_f) / velocity_penalty

    Y_new_solved = Y_new
    # Suavizado intertemporal del PIB real (inercia industrial V3.8)
    if Y_prev is not None:
        Y_new = 0.75 * Y_new + 0.25 * Y_prev  # V4.2: 75/25 amortiguador
    Y_new = max(10.0, Y_new)

    NX, X, M_imp = compute_NX(
        sp["NX0"], sp["epsilon_x"], sp["epsilon_m"],
        q_f, sp["m1"], Y_new, j_curve_active,
        x0=sp.get("x0", 0.0), x1=sp.get("x1", 0.0),
        Y_star=sp.get("Y_star", 0.0), m0=sp.get("m0", 0.0),
        tau=tau, s_x=s_x,
    )
    NX_prev = pi.get("_NX_prev")
    if NX_prev is not None:
        NX = 0.70 * NX + 0.30 * NX_prev

    # V3.0 Reforma 2A: bajo rate_targeting, M_endo es la M implícita
    if monetary_mode == "rate_targeting":
        r_ref_val = pi.get("r_ref") or r_new
        M_snap_final = compute_implied_M(r_ref_val, Y_new, sp["k"], sp["h"], P_local_f, velocity_penalty)
        M_snap_final = max(1e-4, M_snap_final)
    else:
        M_snap_final = float("nan")  # M es exógena bajo quantity mode

    C     = c0_eff_flex + sp["c1"] * (Y_new * (1.0 - t_c) + Tr)
    # V3.8: Si hay inercia en Y o se aplicó floor, forzar consistencia de la identidad macroeconómica en la inversión
    if Y_prev is not None or abs(Y_new - Y_new_solved) > 1e-6:
        I_inv = Y_new - C - G_total - NX
    else:
        I_inv = sp["I0"] + delta_I0_flex - sp["b"] * (r_new - pi_e_clamped * 100.0) - rho_k * t_k
    gap   = (Y_new - Y_pot) / Y_pot if Y_pot > 0 else 0.0
    A_dom = C + I_inv + G_total

    P_T = E_current * P_star * (1.0 + tau)
    q_int, Y_T, Y_NT = compute_sectoral_composition(Y_new, P_T, P_NT, sp["alpha_PT"])

    _identity_gap = abs(Y_new - (A_dom + NX))
    if _identity_gap > 1e-3:
        _log.warning(
            "[eq_flexible_v2] Identidad Y = C+I+G+NX violada. "
            "Y=%.6f, C+I+G+NX=%.6f, brecha=%.6f.",
            Y_new, A_dom + NX, _identity_gap,
        )

    return EquilibriumV2(
        Y=round(Y_new, 6),
        r=round(r_new, 6),
        E_endo=round(E_current, 6),
        M_endo=round(M_snap_final, 6),
        NX=round(NX, 6),
        X=round(X, 6),
        M_imp=round(M_imp, 6),
        G_total=round(G_total, 6),
        C=round(C, 6),
        I_inv=round(I_inv, 6),
        mult=round(k_m, 6),
        P_local=round(P_local_f, 6),
        q_real=round(q_f, 6),
        M_real=round(M_real_f, 6),
        gap=round(gap, 6),
        A_domestic=round(A_dom, 6),
        P_T=round(P_T, 6),
        q_int=round(q_int, 6),
        Y_T=round(Y_T, 6),
        Y_NT=round(Y_NT, 6),
        FX_intervention=round(fx_intervention_this_iter, 6),
    )


def eq_crawling_peg_v2(
    sp: StructuralParams,
    pi: PolicyInstruments,
    Y_pot: float,
    P_NT: float,
    E_prev: float,
    crawl_rate: float,
    j_curve_active: bool = False,
    rho: float = 0.0,  # FASE 3.1
    velocity_penalty: float = 1.0,
    pi_e: float = 0.03,  # V3.5: expectativa de inflación
    r_prev: Optional[float] = None,
    Y_prev: Optional[float] = None,
) -> EquilibriumV2:
    """
    Equilibrio IS-LM-BP bajo Crawling Peg (deslizamiento cambiario programado).

    E_t = E_{t-1} · (1 + crawl_rate)
    delta_E_expected = crawl_rate (las expectativas se anclan al crawl)

    Luego resuelve como TC Fijo con el nuevo E_t.

    Parameters
    ----------
    sp             : Parámetros estructurales
    pi             : Instrumentos de política (pi["E"] = E_{t-1})
    Y_pot          : PIB potencial actual
    P_NT           : Precio de no-transables
    E_prev         : Tipo de cambio del período anterior
    crawl_rate     : Tasa de deslizamiento programado
    j_curve_active : Flag de efecto J-curve
    rho            : Prima de riesgo soberano (riesgo país)

    Returns
    -------
    EquilibriumV2
    """
    # Nuevo tipo de cambio nominal según el crawl programado
    E_new = E_prev * (1.0 + crawl_rate)

    # Crear copia de instrumentos con E actualizado
    pi_crawl: PolicyInstruments = dict(pi)  # type: ignore[assignment]
    pi_crawl["E"] = E_new

    # Las expectativas se anclan al ritmo del crawl
    delta_E_expected = crawl_rate

    # Resolver como TC Fijo con el nuevo E
    result = eq_fixed_v2(
        sp=sp,
        pi=pi_crawl,
        Y_pot=Y_pot,
        P_NT=P_NT,
        delta_E_expected=delta_E_expected,
        j_curve_active=j_curve_active,
        rho=rho,  # FASE 3.1
        velocity_penalty=velocity_penalty,
        pi_e=pi_e,
        r_prev=r_prev,
        Y_prev=Y_prev,
    )

    # Sobreescribir E_endo con el valor del crawl (para registro)
    result_dict = dict(result)
    result_dict["E_endo"] = round(E_new, 6)  # informativo

    return EquilibriumV2(**result_dict)  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 4: SALTER-SWAN DINÁMICO
# ─────────────────────────────────────────────────────────────────────────────

# Mapa de zona → (diagnóstico, política recomendada)
_ZONE_MAP: dict[str, tuple[str, str]] = {
    "I": (
        "Superávit de cuenta corriente + Sobreempleo (presiones inflacionarias). "
        "La economía está por encima del pleno empleo con saldo externo positivo.",
        "Apreciar el tipo de cambio real (revaluar E) y/o contraer la absorción "
        "(política fiscal contractiva). Objetivo: enfriar demanda sin comprometer externo.",
    ),
    "II": (
        "Superávit de cuenta corriente + Desempleo (capacidad ociosa). "
        "La economía tiene exceso de oferta con saldo externo favorable.",
        "Expandir la absorción doméstica (política fiscal expansiva) y mantener "
        "o apreciar moderadamente el tipo de cambio. Objetivo: estimular demanda interna.",
    ),
    "III": (
        "Déficit de cuenta corriente + Desempleo (el peor escenario). "
        "Presión simultánea sobre reservas y empleo — dilema de política.",
        "Depreciar el tipo de cambio real (devaluar E) para mejorar competitividad, "
        "con contención fiscal moderada. PRECAUCIÓN: riesgo de espiral inflacionaria.",
    ),
    "IV": (
        "Déficit de cuenta corriente + Sobreempleo (economía recalentada). "
        "Alta demanda presiona precios e importaciones simultáneamente.",
        "Contraer absorción (política fiscal restrictiva) y depreciar el tipo de "
        "cambio real para reequilibrar la cuenta corriente. Política dual necesaria.",
    ),
}


def compute_salter_swan(
    eq_result: EquilibriumV2,
    sp: StructuralParams,
    G: float,
    A_ref: float = 100.0,
    q_ref: float = 1.0,
    pi: Optional[PolicyInstruments] = None,
) -> SalterSwanResult:
    """
    Análisis Salter-Swan dinámico con pendientes derivadas del modelo.

    En lugar de pendientes hardcodeadas (V1.0), las curvas IB y EB se
    derivan de los parámetros estructurales del modelo IS-LM-BP:

    Pendiente IB (Balance Interno — pleno empleo):
        dq/dA|_IB = -(1 - c₁·(1-t) + m₁) / (ε_x · Δq)   [negativa]

    Pendiente EB (Balance Externo — equilibrio cuenta corriente):
        dq/dA|_EB = m₁ / (ε_x · Δq)                       [positiva]

    La absorción doméstica se deriva del equilibrio IS-LM: A = C + I + G.
    El TCR se toma directamente del equilibrio calculado.

    Clasificación de zona:
        I  : q > q_IB(A) y q > q_EB(A)  → Superávit + Sobreempleo
        II : q < q_IB(A) y q > q_EB(A)  → Superávit + Desempleo
        III: q < q_IB(A) y q < q_EB(A)  → Déficit + Desempleo
        IV : q > q_IB(A) y q < q_EB(A)  → Déficit + Sobreempleo

    Parameters
    ----------
    eq_result : Resultado del equilibrio IS-LM-BP del período
    sp        : Parámetros estructurales
    G         : Gasto público del período
    A_ref     : Absorción de referencia para el equilibrio de largo plazo
    q_ref     : TCR de referencia (= 1.0 implica paridad)
    pi        : Instrumentos de política

    Returns
    -------
    SalterSwanResult
    """
    A_actual = eq_result["A_domestic"]
    q_actual = eq_result["q_real"]

    # Condición Marshall-Lerner
    ml_satisfied = (sp["epsilon_x"] + sp["epsilon_m"]) > 1.0

    if pi is None:
        pi = {}

    t_c = pi.get("t_c", sp.get("t", 0.20))
    tau = pi.get("tau", 0.0)
    m1_eff = sp.get("m1", 0.15) * (1.0 - tau)

    slope_numerator_IB = 1.0 - sp.get("c1", 0.75) * (1.0 - t_c) + m1_eff
    slope_denominator  = max(sp.get("epsilon_x", 0.8), 1e-6)

    # Normalización de escala
    scale_factor = q_ref / max(A_ref, 1.0)
    slope_IB = (-slope_numerator_IB / slope_denominator) * scale_factor
    slope_EB = (m1_eff / slope_denominator) * scale_factor

    # Curvas IB y EB en el nivel de A actual
    # Las curvas pasan por el punto (A_ref, q_ref) de equilibrio de largo plazo
    q_IB_at_A = q_ref + slope_IB * (A_actual - A_ref)
    q_EB_at_A = q_ref + slope_EB * (A_actual - A_ref)

    # Clasificación de zona
    above_IB = q_actual > q_IB_at_A
    above_EB = q_actual > q_EB_at_A

    if above_IB and above_EB:
        zone = "I"
    elif (not above_IB) and above_EB:
        zone = "II"
    elif (not above_IB) and (not above_EB):
        zone = "III"
    else:
        zone = "IV"

    diagnosis, policy = _ZONE_MAP[zone]

    return SalterSwanResult(
        zone=zone,
        diagnosis=diagnosis,
        policy=policy,
        q_actual=round(q_actual, 6),
        A_actual=round(A_actual, 6),
        q_IB_at_A=round(q_IB_at_A, 6),
        q_EB_at_A=round(q_EB_at_A, 6),
        slope_IB=round(slope_IB, 6),
        slope_EB=round(slope_EB, 6),
        ml_satisfied=ml_satisfied,
    )


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCHER PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def solve_equilibrium_v2(
    sp: StructuralParams,
    pi: PolicyInstruments,
    Y_pot: float,
    P_NT: float,
    E_prev: float,
    Y_prev: Optional[float] = None,
    r_prev: Optional[float] = None,
    j_curve_active: bool = False,
    delta_E_expected: float = 0.0,
    rho: float = 0.0,
    prev_velocity_penalty: float = 1.0,
    # V3.0 Reforma 1B: pass-through gradual
    E_eff: Optional[float] = None,
    # V3.0 Reforma 1A: bandas dinámicas PPP
    pi_local_prev: float = 0.0,
    pi_star: float = 0.03,
) -> EquilibriumV2:
    """
    Dispatcher: selecciona el solver según el régimen cambiario.

    Parameters
    ----------
    sp                : Parámetros estructurales
    pi                : Instrumentos de política (incluye pi["regime"])
    Y_pot             : PIB potencial actual
    P_NT              : Precio de no-transables (estado)
    E_prev            : Tipo de cambio del período anterior
    Y_prev            : Y del período anterior (para punto inicial en flexible)
    r_prev            : r del período anterior (para punto inicial en flexible)
    j_curve_active    : Flag de efecto J-curve
    delta_E_expected  : Prima de devaluación exógena (crisis de credibilidad).
                        Bajo régimen fijo: se suma a r_BP.
                        Bajo flexible: se añade al delta_E endógeno en BP.
                        Bajo crawling peg: ignorado (usa crawl_rate).
    rho               : Prima de riesgo soberano en puntos porcentuales (coherente con r_star).
                        Calculado una sola vez por compute_sovereign_risk y escalado por el caller.
    prev_velocity_penalty : Penalización de velocidad de dinero previa

    Returns
    -------
    EquilibriumV2

    Raises
    ------
    ValueError
         Si el régimen no es reconocido.
    """
    # ── INYECCIÓN DE GASTO FORZOSO POR DESASTRE NATURAL (F-18 FIX) ──────────
    G_needed = sp.get("G_needed", 0.0)
    if G_needed > 0.0:
        pi = dict(pi)  # copia defensiva para no mutar el original
        pi["G_c"] = pi.get("G_c", pi.get("G", 20.0)) + G_needed
        pi["G"] = pi["G_c"] + pi.get("I_g", 0.0)

    # ── PENALIZACIÓN DE VELOCIDAD MONETARIA (única de este módulo) ───────────
    M_val = pi.get("M", 40.0)
    new_velocity_penalty_shock = 0.0
    if M_val > 120.0:
        new_velocity_penalty_shock += 0.05 * (math.exp(0.25 * (M_val - 120.0)) - 1.0)
    elif M_val < 15.0:
        new_velocity_penalty_shock += 0.05 * (math.exp(0.4 * (15.0 - M_val)) - 1.0)

    velocity_penalty = 0.6 * prev_velocity_penalty + 0.4 * (1.0 + new_velocity_penalty_shock)

    # rho se usa directamente — ya contiene la prima de riesgo completa
    # calculada por compute_sovereign_risk (fuente única de verdad).

    regime = pi.get("regime", "fixed")

    if regime == "fixed":
        eq = eq_fixed_v2(
            sp=sp, pi=pi,
            Y_pot=Y_pot, P_NT=P_NT,
            delta_E_expected=delta_E_expected,
            j_curve_active=j_curve_active,
            rho=rho,  # FASE 3.1
            velocity_penalty=velocity_penalty,
            pi_e=pi_local_prev, # V3.5
            r_prev=r_prev, # V3.6
            Y_prev=Y_prev, # V3.8
        )

    elif regime == "flexible":
        # En crisis de credibilidad: ajustar punto inicial de E y pasar la prima
        E_guess_crisis = E_prev * (1.0 + delta_E_expected) if delta_E_expected > 0 else None
        eq = eq_flexible_v2(
            sp=sp, pi=pi,
            Y_pot=Y_pot, P_NT=P_NT,
            E_prev=E_prev,
            Y_prev=Y_prev, r_prev=r_prev,
            E_guess=E_guess_crisis,
            j_curve_active=j_curve_active,
            delta_E_external=delta_E_expected,
            rho=rho,
            velocity_penalty=velocity_penalty,
            E_eff=E_eff,              # V3.0 Reforma 1B
            pi_local_prev=pi_local_prev,  # V3.0 Reforma 1A
            pi_star=pi_star,          # V3.0 Reforma 1A
        )

    elif regime == "crawling_peg":
        crawl_rate = pi.get("crawl_rate", 0.02)
        eq = eq_crawling_peg_v2(
            sp=sp, pi=pi,
            Y_pot=Y_pot, P_NT=P_NT,
            E_prev=E_prev,
            crawl_rate=crawl_rate,
            j_curve_active=j_curve_active,
            rho=rho,  # FASE 3.1
            velocity_penalty=velocity_penalty,
            pi_e=pi_local_prev, # V3.5
            r_prev=r_prev,
            Y_prev=Y_prev,
        )

    else:
        raise ValueError(
            f"Régimen '{regime}' no reconocido. "
            "Opciones: 'fixed', 'flexible', 'crawling_peg'."
        )

    # Guardar velocity_penalty en equilibrio para ser persistida por el StateManager
    eq_dict = dict(eq)
    eq_dict["velocity_penalty"] = velocity_penalty
    # V3.0: asegurar FX_intervention existe con default 0 (retrocompat. fixed/crawling)
    eq_dict.setdefault("FX_intervention", 0.0)
    return EquilibriumV2(**eq_dict)
