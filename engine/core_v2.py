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


def compute_price_level(
    E: float,
    P_star: float,
    P_NT: float,
    alpha_PT: float,
    tau: float = 0.0,
) -> float:
    """
    Nivel de precios doméstico general (ponderación de transables y no transables).

    P_T = E · P* · (1 + τ)
    P_local = α_PT · P_T + (1 - α_PT) · P_NT

    Parameters
    ----------
    E       : Tipo de cambio nominal
    P_star  : Nivel de precios externo (base = 1.0)
    P_NT    : Precio de bienes no-transables (variable de estado)
    alpha_PT: Peso bienes transables en la canasta de precios ∈ [0,1]
    tau     : Arancel a importaciones ∈ [0,1); default 0.0

    Returns
    -------
    float : Nivel de precios doméstico P_local
    """
    if not (0.0 <= alpha_PT <= 1.0):
        raise ValueError(f"alpha_PT debe estar en [0,1], recibido: {alpha_PT}")
    P_T = E * P_star * (1.0 + tau)
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

    q_int = P_T / P_NT
    share_T = max(0.05, min(0.95, alpha_PT * q_int))
    Y_T = Y * share_T
    Y_NT = Y * (1.0 - share_T)

    Returns
    -------
    tuple[float, float, float]
        (q_int, Y_T, Y_NT)
    """
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
    return r_star + delta_E_expected + rho - slope_correction


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

    # Movilidad de capitales efectiva (controles reducen flujo)
    f_eff = max(sp["f"] * (1.0 - k_c), 1e-4)

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
    A_auto = sp["c0"] + sp["c1"] * Tr + sp["I0"] - rho_k * t_k + G_total + NX0_eff

    # ── 3. Sistema 2×2: IS y BP simultáneas (Y, r) ───────────────────────────
    m1_eff = sp["m1"] * (1.0 - tau)  # propensión marginal a importar efectiva
    rhs_bp = (
        r_star + delta_E_expected + rho
        - NX0_eff / f_eff
        - eps_eff_sx * q / f_eff
    )

    A_mat = np.array([
        [1.0,              sp["b"] * k_m],
        [-m1_eff / f_eff,  1.0          ],
    ])
    b_vec = np.array([
        k_m * (A_auto + eps_eff_sx * q),
        rhs_bp,
    ])

    try:
        sol = np.linalg.solve(A_mat, b_vec)
        Y, r = float(sol[0]), float(sol[1])
    except np.linalg.LinAlgError:
        # Sistema singular: recurrir a solución simplificada r = r* + ΔEₑ + ρ
        r = r_star + delta_E_expected + rho
        Y = k_m * (A_auto + eps_eff_sx * q - sp["b"] * r)

    Y = max(10.0, Y)

    # ── 4. M endógena (LM) ───────────────────────────────────────────────────
    M_real_eq = (sp["k"] * Y - sp["h"] * r) / velocity_penalty
    M_endo = M_real_eq * P_local

    # ── 5. Variables derivadas ────────────────────────────────────────────────
    NX, X, M_imp = compute_NX(
        sp["NX0"], sp["epsilon_x"], sp["epsilon_m"],
        q, sp["m1"], Y, j_curve_active,
        x0=sp.get("x0", 0.0), x1=sp.get("x1", 0.0),
        Y_star=sp.get("Y_star", 0.0), m0=sp.get("m0", 0.0),
        tau=tau, s_x=s_x,
    )
    C     = sp["c0"] + sp["c1"] * (Y * (1.0 - t_c) + Tr)
    I_inv = sp["I0"] - sp["b"] * r - rho_k * t_k
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
    rho: float = 0.0,  # FASE 3.1
    velocity_penalty: float = 1.0,
) -> EquilibriumV2:
    """
    Equilibrio IS-LM-BP bajo Tipo de Cambio FLEXIBLE (V2.1).

    Bajo TC flexible:
    - M es exógena (instrumento del banco central).
    - E se determina endógenamente para limpiar el mercado externo.

    V2.1 incorpora: G_c+I_g=G_total, Tr, t_c, t_k, rho_k, tau, s_x, k_c.
    La dependencia circular E → P_local → M_real → (Y, r) → NX → E
    se resuelve iterativamente con criterio de convergencia |ΔE| < tol.

    Parameters
    ----------
    sp               : Parámetros estructurales
    pi               : Instrumentos de política
    Y_pot            : PIB potencial actual
    P_NT             : Precio de no-transables (estado)
    E_prev           : Tipo de cambio del período anterior (punto inicial)
    Y_prev           : Y del período anterior (punto inicial; opcional)
    r_prev           : r del período anterior (punto inicial; opcional)
    E_guess          : Estimación inicial de E_endo (sobrescribe E_prev si se provee)
    j_curve_active   : Flag de efecto J-curve
    delta_E_external : Prima de devaluación exógena (e.g. 0.25 en crisis de
                       credibilidad). Se suma al delta_E endógeno en la BP.
    max_iter         : Máximo de iteraciones del loop externo
    tol              : Criterio de convergencia en E
    rho              : Prima de riesgo soberano (riesgo país)

    Returns
    -------
    EquilibriumV2
    """
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

    # Demanda autónoma (sin el término -b*r)
    A_auto_base = sp["c0"] + sp["c1"] * Tr + sp["I0"] - rho_k * t_k + G_total + NX0_eff

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

            delta_E_e = (E_s_safe - E_prev) / max(E_prev, 1e-9) + delta_E_external

            # IS: Y = k_m · (A_auto_base - b·r + eps_eff_sx·q)
            eq_IS = Y_s - k_m * (A_auto_base - sp["b"] * r_s + eps_eff_sx * q_s)
            # LM: r = (k·Y - M_real / velocity_penalty) / h
            eq_LM = r_s - (sp["k"] * Y_s - M_real_s / velocity_penalty) / sp["h"]
            # BP: r = r* + ΔEₑ + ρ - NX/f_eff
            eq_BP = r_s - compute_bp_curve(r_star, delta_E_e, NX_s, f_eff, rho=rho)
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

        # Criterio de convergencia en E
        if abs(E_new - E_current) < tol:
            E_current = E_new
            break
        E_current = E_new

    # Calcular valores finales con E convergido
    P_local_f = compute_price_level(E_current, P_star, P_NT, sp["alpha_PT"], tau=tau)
    q_f       = compute_real_exchange_rate(E_current, P_star, P_local_f)
    M_real_f  = (M / P_local_f) / velocity_penalty

    NX, X, M_imp = compute_NX(
        sp["NX0"], sp["epsilon_x"], sp["epsilon_m"],
        q_f, sp["m1"], Y_new, j_curve_active,
        x0=sp.get("x0", 0.0), x1=sp.get("x1", 0.0),
        Y_star=sp.get("Y_star", 0.0), m0=sp.get("m0", 0.0),
        tau=tau, s_x=s_x,
    )
    C     = sp["c0"] + sp["c1"] * (Y_new * (1.0 - t_c) + Tr)
    I_inv = sp["I0"] - sp["b"] * r_new - rho_k * t_k
    gap   = (Y_new - Y_pot) / Y_pot if Y_pot > 0 else 0.0
    A_dom = C + I_inv + G_total   # Absorción doméstica (SIN NX)

    # Economía Dual (FASE 3.1)
    P_T = E_current * P_star * (1.0 + tau)
    q_int, Y_T, Y_NT = compute_sectoral_composition(Y_new, P_T, P_NT, sp["alpha_PT"])

    # ── FIX F-01: Verificación de identidad macroeconómica Y = C+I+G+NX ─────
    _identity_gap = abs(Y_new - (A_dom + NX))
    if _identity_gap > 1e-3:
        _log.warning(
            "[eq_flexible_v2] Identidad Y = C+I+G+NX violada. "
            "Y=%.6f, C+I+G+NX=%.6f, brecha=%.6f. "
            "Revisar convergencia del solver o parámetros del escenario.",
            Y_new, A_dom + NX, _identity_gap,
        )

    return EquilibriumV2(
        Y=round(Y_new, 6),
        r=round(r_new, 6),
        E_endo=round(E_current, 6),
        M_endo=float("nan"),        # M es exógena bajo TC flexible
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
    rho: float = 0.0,  # FASE 3.1
    prev_risk_penalty: float = 0.0,
    prev_velocity_penalty: float = 1.0,
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
    rho               : Prima de riesgo soberano (riesgo país)
    prev_risk_penalty : Penalización de riesgo del turno previo
    prev_velocity_penalty : Penalización de velocidad de dinero previa

    Returns
    -------
    EquilibriumV2

    Raises
    ------
    ValueError
         Si el régimen no es reconocido.
    """
    # ── PENALIZACIÓN POR VALORES EXTREMOS (TAREA 6) ─────────────────────────
    G_total = pi.get("G_c", pi.get("G", 20.0)) + pi.get("I_g", 0.0)
    M_val = pi.get("M", 40.0)
    
    new_risk_penalty = 0.0
    new_velocity_penalty_shock = 0.0
    
    # Sliders de gasto: G total desproporcionado (penalizaciones exponenciales)
    if G_total > 30.0:
        new_risk_penalty += 0.02 * (math.exp(0.4 * (G_total - 30.0)) - 1.0)
    elif G_total < 5.0:
        new_risk_penalty += 0.03 * (math.exp(0.5 * (5.0 - G_total)) - 1.0)
        
    # Oferta monetaria desproporcionada (penalizaciones exponenciales)
    if M_val > 120.0:
        new_risk_penalty += 0.01 * (math.exp(0.2 * (M_val - 120.0)) - 1.0)
        new_velocity_penalty_shock += 0.05 * (math.exp(0.25 * (M_val - 120.0)) - 1.0)
    elif M_val < 15.0:
        new_risk_penalty += 0.03 * (math.exp(0.4 * (15.0 - M_val)) - 1.0)
        new_velocity_penalty_shock += 0.05 * (math.exp(0.4 * (15.0 - M_val)) - 1.0)

    # Inercia intertemporal: 0.6 * previo + 0.4 * nuevo
    risk_penalty = 0.6 * prev_risk_penalty + 0.4 * new_risk_penalty
    velocity_penalty = 0.6 * prev_velocity_penalty + 0.4 * (1.0 + new_velocity_penalty_shock)
        
    rho = rho + risk_penalty * 100.0  # escala en puntos porcentuales para UIP
    
    regime = pi.get("regime", "fixed")

    if regime == "fixed":
        eq = eq_fixed_v2(
            sp=sp, pi=pi,
            Y_pot=Y_pot, P_NT=P_NT,
            delta_E_expected=delta_E_expected,
            j_curve_active=j_curve_active,
            rho=rho,  # FASE 3.1
            velocity_penalty=velocity_penalty,
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
            rho=rho,  # FASE 3.1
            velocity_penalty=velocity_penalty,
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
        )

    else:
        raise ValueError(
            f"Régimen '{regime}' no reconocido. "
            "Opciones: 'fixed', 'flexible', 'crawling_peg'."
        )

    # Guardar penalizaciones en equilibrio para ser persistidas por el StateManager
    eq_dict = dict(eq)
    eq_dict["risk_penalty"] = risk_penalty
    eq_dict["velocity_penalty"] = velocity_penalty
    return EquilibriumV2(**eq_dict)
