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

import math
from typing import Optional

import numpy as np
from scipy.optimize import fsolve

from config.parameters_v2 import (
    EquilibriumV2,
    PolicyInstruments,
    SalterSwanResult,
    StructuralParams,
)


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 2: FUNCIONES DE COMPONENTES (PURAS)
# ─────────────────────────────────────────────────────────────────────────────

def compute_multiplier(c1: float, t: float, m1: float) -> float:
    """
    Multiplicador keynesiano con impuesto proporcional.

    k_m = 1 / (1 - c₁·(1-t) + m₁)

    Diferencia con V1.0: el impuesto lump-sum T desaparece.
    El ajuste fiscal opera vía 't' (tasa) que reduce la renta disponible
    endógenamente: Yd = Y·(1-t).

    Parameters
    ----------
    c1 : float
        Propensión marginal a consumir.
    t  : float
        Tasa impositiva proporcional ∈ (0, 1).
    m1 : float
        Propensión marginal a importar.

    Returns
    -------
    float
        Multiplicador keynesiano.

    Raises
    ------
    ValueError
        Si el denominador ≤ 0 (modelo inestable / parámetros inválidos).
    """
    denominator = 1.0 - c1 * (1.0 - t) + m1
    if denominator <= 0.0:
        raise ValueError(
            f"Multiplicador indefinido: 1 - c1·(1-t) + m1 = {denominator:.6f}. "
            f"Parámetros: c1={c1}, t={t}, m1={m1}. "
            "El modelo requiere denominador > 0."
        )
    return 1.0 / denominator


def compute_autonomous_demand(
    c0: float,
    I0: float,
    G: float,
    NX0: float,
    r: float,
    b: float,
) -> float:
    """
    Demanda autónoma agregada (A).

    A = c0 + I0 - b·r + G + NX0

    Nota V2.0: el término -c1·T desaparece porque T = t·Y es endógeno.
    La recaudación no forma parte de la demanda autónoma; entra vía el
    multiplicador como reducción de la renta disponible.

    Parameters
    ----------
    c0  : Consumo autónomo
    I0  : Inversión autónoma
    G   : Gasto público
    NX0 : Exportaciones netas autónomas
    r   : Tasa de interés (para el componente I0 - b·r)
    b   : Sensibilidad inversión–tasa de interés

    Returns
    -------
    float : Demanda autónoma A
    """
    return c0 + I0 - b * r + G + NX0


def compute_price_level(
    E: float,
    P_star: float,
    P_NT: float,
    alpha_PT: float,
) -> float:
    """
    Nivel de precios local con pass-through cambiario.

    P_local = α_PT · (E · P*) + (1 - α_PT) · P_NT

    Parameters
    ----------
    E       : Tipo de cambio nominal
    P_star  : Nivel de precios externo (base = 1.0)
    P_NT    : Precio de bienes no-transables (variable de estado)
    alpha_PT: Peso bienes transables en la canasta de precios ∈ [0,1]

    Returns
    -------
    float : Nivel de precios doméstico P_local
    """
    if not (0.0 <= alpha_PT <= 1.0):
        raise ValueError(f"alpha_PT debe estar en [0,1], recibido: {alpha_PT}")
    return alpha_PT * (E * P_star) + (1.0 - alpha_PT) * P_NT


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


def compute_NX(
    NX0: float,
    epsilon_x: float,
    epsilon_m: float,
    q: float,
    m1: float,
    Y: float,
    j_curve_active: bool = False,
    epsilon_x_short: float = 0.10,
) -> float:
    """
    Exportaciones netas con condición Marshall-Lerner y efecto J-curve.

    Condición Marshall-Lerner: una devaluación mejora NX si y solo si
    ε_x + ε_m > 1. Si no se cumple, el coeficiente de q es negativo.

    Efecto J-curve: en el primer turno post-devaluación, las exportaciones
    responden lentamente (ε_x_short ≈ 0.1 < ε_x estructural), causando
    una caída inicial de NX.

    Fórmula:
        Si j_curve_active:
            NX = NX0 + ε_x_short · q - m1 · Y
        Sino (según condición M-L):
            NX = NX0 + ε_x · q - m1 · Y          (si M-L se cumple)
            NX = NX0 - (ε_m - ε_x) · q - m1 · Y  (si M-L NO se cumple)

    Parameters
    ----------
    NX0            : Exportaciones netas autónomas
    epsilon_x      : Elasticidad precio de exportaciones
    epsilon_m      : Elasticidad precio de importaciones
    q              : Tipo de cambio real
    m1             : Propensión marginal a importar
    Y              : Ingreso
    j_curve_active : True → primer turno post-devaluación (efecto J)
    epsilon_x_short: Elasticidad de corto plazo para el efecto J

    Returns
    -------
    float : Exportaciones netas NX
    """
    ml_satisfied = (epsilon_x + epsilon_m) > 1.0

    if j_curve_active:
        # Efecto J: respuesta lenta de exportaciones
        effective_epsilon = epsilon_x_short
    elif ml_satisfied:
        # Condición M-L cumplida: devaluación mejora NX
        effective_epsilon = epsilon_x
    else:
        # Condición M-L NO cumplida: devaluación EMPEORA NX
        # El efecto neto sobre q es negativo: -(ε_m - ε_x) si ε_m > ε_x
        # Modelado como coeficiente negativo efectivo
        effective_epsilon = -(epsilon_m - epsilon_x)

    return NX0 + effective_epsilon * q - m1 * Y


def compute_bp_curve(
    r_star: float,
    delta_E_expected: float,
    NX: float,
    f: float,
) -> float:
    """
    Curva BP con movilidad imperfecta de capitales (Paridad Descubierta de Intereses).

    r_BP = r* + ΔEₑ - NX / f

    Casos límite:
    - f → ∞ (movilidad perfecta): NX/f → 0 → r_BP = r* + ΔEₑ (caso clásico)
    - f pequeño (movilidad baja): NX/f es significativo → BP inclinada

    Parameters
    ----------
    r_star           : Tasa de interés internacional
    delta_E_expected : Variación esperada del tipo de cambio (expectativas)
    NX               : Exportaciones netas actuales
    f                : Parámetro de movilidad de capitales

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
    return r_star + delta_E_expected - (NX / f)


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
) -> EquilibriumV2:
    """
    Equilibrio IS-LM-BP bajo Tipo de Cambio FIJO.

    Bajo TC fijo:
    - E es exógeno (instrumento del banco central).
    - M se acomoda endógenamente para mantener r = r_BP.
    - La condición externa determina r.

    Pasos:
    1. Calcular P_local con pass-through.
    2. Calcular q = E·P*/P_local.
    3. Determinar r = r_BP (condición externa).
    4. Calcular A (demanda autónoma).
    5. Resolver IS para Y.
    6. Calcular M_endo para satisfacer LM con ese (Y, r).

    Parameters
    ----------
    sp               : Parámetros estructurales
    pi               : Instrumentos de política
    Y_pot            : PIB potencial actual
    P_NT             : Precio de bienes no-transables (estado)
    delta_E_expected : Variación esperada del TC (= 0 bajo TC fijo creíble)
    j_curve_active   : Flag de efecto J-curve activo

    Returns
    -------
    EquilibriumV2
    """
    E       = pi["E"]
    G       = pi["G"]
    r_star  = pi["r_star"]
    P_star  = sp["P_star"]

    # 1. Nivel de precios local (pass-through cambiario)
    P_local = compute_price_level(E, P_star, P_NT, sp["alpha_PT"])

    # 2. Tipo de cambio real
    q = compute_real_exchange_rate(E, P_star, P_local)

    # 3. Tasa de interés: condición de equilibrio externo
    #    Necesitamos NX para r_BP, pero NX depende de Y que aún no conocemos.
    #    Estrategia: solución analítica conjunta IS + BP.
    #
    #    IS: Y = k_m · (A_base + ε_x·q - b·r)   donde A_base = c0+I0+G+NX0
    #    BP: r = r* + ΔEₑ - NX/f  y  NX = NX0 + ε_eff·q - m1·Y
    #
    #    Sustituyendo NX en BP:
    #    r = r* + ΔEₑ - (NX0 + ε_eff·q - m1·Y) / f
    #    r = r* + ΔEₑ - NX0/f - ε_eff·q/f + m1·Y/f  ... (i)
    #
    #    De IS: Y = k_m·(c0+I0+G+NX0-b·r + ε_x·q)
    #    Sustituyendo (i) en IS y resolviendo para Y, r:

    k_m = compute_multiplier(sp["c1"], sp["t"], sp["m1"])
    slope = 1.0 - sp["c1"] * (1.0 - sp["t"]) + sp["m1"]  # = 1/k_m

    # Componente autónomo sin el efecto de r (lo separaremos)
    A_auto = sp["c0"] + sp["I0"] + G + sp["NX0"]

    # Elasticidad efectiva de NX a q (según M-L y J-curve)
    ml_ok = (sp["epsilon_x"] + sp["epsilon_m"]) > 1.0
    if j_curve_active:
        eps_eff = 0.10
    elif ml_ok:
        eps_eff = sp["epsilon_x"]
    else:
        eps_eff = -(sp["epsilon_m"] - sp["epsilon_x"])

    # Sistema 2x2: IS y BP simultáneas (Y, r)
    # IS: Y·slope - ε_x·q·k_m + b·k_m·r = k_m·A_auto  → Y·slope + b·k_m·r = k_m·(A_auto + ε_x·q)
    # BP: -m1·Y/f + r = r* + ΔEₑ - NX0/f - ε_eff·q/f
    #
    # Forma matricial: [slope, b·k_m] [Y]   [k_m·(A_auto + ε_x·q)          ]
    #                  [-m1/f, 1    ] [r] = [r* + ΔEₑ - NX0/f - ε_eff·q/f ]

    rhs_bp = r_star + delta_E_expected - sp["NX0"] / sp["f"] - eps_eff * q / sp["f"]

    A_mat = np.array([
        [slope,          sp["b"] * k_m],
        [-sp["m1"] / sp["f"], 1.0],
    ])
    b_vec = np.array([
        k_m * (A_auto + sp["epsilon_x"] * q),
        rhs_bp,
    ])

    try:
        sol = np.linalg.solve(A_mat, b_vec)
        Y, r = float(sol[0]), float(sol[1])
    except np.linalg.LinAlgError:
        # Sistema singular: recurrir a solución simplificada r = r*
        r = r_star + delta_E_expected
        A_simple = compute_autonomous_demand(sp["c0"], sp["I0"], G, sp["NX0"], r, sp["b"])
        Y = k_m * (A_simple + eps_eff * q)

    # 4. M endógena (para satisfacer LM dado Y y r)
    M_real = k_m * Y / k_m   # reescalado — en realidad: M_real satisface LM
    # LM: r = (k·Y - M_real) / h → M_real = k·Y - h·r
    M_real_eq = sp["k"] * Y - sp["h"] * r
    M_endo = M_real_eq * P_local  # convertir a nominal

    # 5. Variables derivadas
    NX    = compute_NX(sp["NX0"], sp["epsilon_x"], sp["epsilon_m"],
                       q, sp["m1"], Y, j_curve_active)
    C     = sp["c0"] + sp["c1"] * Y * (1.0 - sp["t"])
    I_inv = sp["I0"] - sp["b"] * r
    mult  = k_m
    gap   = (Y - Y_pot) / Y_pot if Y_pot > 0 else 0.0
    A_dom = C + I_inv + G

    return EquilibriumV2(
        Y=round(Y, 6),
        r=round(r, 6),
        E_endo=float("nan"),        # E es exógeno bajo TC fijo
        M_endo=round(M_endo, 6),
        NX=round(NX, 6),
        C=round(C, 6),
        I_inv=round(I_inv, 6),
        mult=round(mult, 6),
        P_local=round(P_local, 6),
        q_real=round(q, 6),
        M_real=round(M_real_eq, 6),
        gap=round(gap, 6),
        A_domestic=round(A_dom, 6),
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
) -> EquilibriumV2:
    """
    Equilibrio IS-LM-BP bajo Tipo de Cambio FLEXIBLE.

    Bajo TC flexible:
    - M es exógena (instrumento del banco central).
    - E se determina endógenamente para limpiar el mercado externo.

    La dependencia circular E → P_local → M_real → (Y, r) → NX → E
    se resuelve iterativamente con criterio de convergencia |ΔE| < tol.

    Dentro de cada iteración, el sistema IS-LM-BP se resuelve con fsolve.

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

    Returns
    -------
    EquilibriumV2
    """
    M      = pi["M"]
    r_star = pi["r_star"]
    G      = pi["G"]
    P_star = sp["P_star"]

    k_m   = compute_multiplier(sp["c1"], sp["t"], sp["m1"])
    slope = 1.0 - sp["c1"] * (1.0 - sp["t"]) + sp["m1"]

    # Elasticidad efectiva según M-L y J-curve
    ml_ok = (sp["epsilon_x"] + sp["epsilon_m"]) > 1.0
    if j_curve_active:
        eps_eff = 0.10
    elif ml_ok:
        eps_eff = sp["epsilon_x"]
    else:
        eps_eff = -(sp["epsilon_m"] - sp["epsilon_x"])

    # Punto inicial de E
    E_current = E_guess if E_guess is not None else E_prev

    # Loop de convergencia externo (circular E ↔ P_local)
    for _ in range(max_iter):
        P_local = compute_price_level(E_current, P_star, P_NT, sp["alpha_PT"])
        M_real  = M / P_local
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
            P_loc_s = compute_price_level(E_s_safe, P_star, P_NT, sp["alpha_PT"])
            P_loc_s = max(1e-4, P_loc_s)
            q_s     = compute_real_exchange_rate(E_s_safe, P_star, P_loc_s)
            M_real_s = M / P_loc_s

            A_s  = compute_autonomous_demand(sp["c0"], sp["I0"], G, sp["NX0"], r_s, sp["b"])
            NX_s = compute_NX(sp["NX0"], sp["epsilon_x"], sp["epsilon_m"],
                              q_s, sp["m1"], Y_s, j_curve_active)

            delta_E_e = (E_s_safe - E_prev) / max(E_prev, 1e-9) + delta_E_external

            # IS: Y = k_m · (A + ε_x·q)
            eq_IS = Y_s - k_m * (A_s + eps_eff * q_s)
            # LM: r = (k·Y - M_real) / h
            eq_LM = r_s - (sp["k"] * Y_s - M_real_s) / sp["h"]
            # BP: r = r* + ΔEₑ - NX/f
            eq_BP = r_s - compute_bp_curve(r_star, delta_E_e, NX_s, sp["f"])
            return [eq_IS, eq_LM, eq_BP]

        try:
            sol = fsolve(system, [Y0, r0, E0], full_output=True)
            Y_new, r_new, E_new = float(sol[0][0]), float(sol[0][1]), float(sol[0][2])
            E_new = max(1e-4, E_new)
        except Exception:
            Y_new, r_new, E_new = Y0, r0, E0

        # Criterio de convergencia en E
        if abs(E_new - E_current) < tol:
            E_current = E_new
            break
        E_current = E_new

    # Calcular valores finales con E convergido
    P_local_f = compute_price_level(E_current, P_star, P_NT, sp["alpha_PT"])
    q_f       = compute_real_exchange_rate(E_current, P_star, P_local_f)
    M_real_f  = M / P_local_f

    NX    = compute_NX(sp["NX0"], sp["epsilon_x"], sp["epsilon_m"],
                       q_f, sp["m1"], Y_new, j_curve_active)
    C     = sp["c0"] + sp["c1"] * Y_new * (1.0 - sp["t"])
    I_inv = sp["I0"] - sp["b"] * r_new
    gap   = (Y_new - Y_pot) / Y_pot if Y_pot > 0 else 0.0
    A_dom = C + I_inv + G

    return EquilibriumV2(
        Y=round(Y_new, 6),
        r=round(r_new, 6),
        E_endo=round(E_current, 6),
        M_endo=float("nan"),        # M es exógena bajo TC flexible
        NX=round(NX, 6),
        C=round(C, 6),
        I_inv=round(I_inv, 6),
        mult=round(k_m, 6),
        P_local=round(P_local_f, 6),
        q_real=round(q_f, 6),
        M_real=round(M_real_f, 6),
        gap=round(gap, 6),
        A_domestic=round(A_dom, 6),
    )


def eq_crawling_peg_v2(
    sp: StructuralParams,
    pi: PolicyInstruments,
    Y_pot: float,
    P_NT: float,
    E_prev: float,
    crawl_rate: float,
    j_curve_active: bool = False,
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

    Returns
    -------
    SalterSwanResult
    """
    A_actual = eq_result["A_domestic"]
    q_actual = eq_result["q_real"]

    # Condición Marshall-Lerner
    ml_satisfied = (sp["epsilon_x"] + sp["epsilon_m"]) > 1.0

    # Pendientes derivadas del modelo
    # Usamos un delta_q pequeño para normalizar las pendientes en el espacio (A, q)
    # Las pendientes son proporcionales a la respuesta de la economía
    slope_numerator_IB = 1.0 - sp["c1"] * (1.0 - sp["t"]) + sp["m1"]  # = 1/k_m
    slope_denominator  = max(sp["epsilon_x"], 1e-6)

    slope_IB = -slope_numerator_IB / slope_denominator   # negativa
    slope_EB = sp["m1"] / slope_denominator               # positiva

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

    Returns
    -------
    EquilibriumV2

    Raises
    ------
    ValueError
        Si el régimen no es reconocido.
    """
    regime = pi.get("regime", "fixed")

    if regime == "fixed":
        return eq_fixed_v2(
            sp=sp, pi=pi,
            Y_pot=Y_pot, P_NT=P_NT,
            delta_E_expected=delta_E_expected,
            j_curve_active=j_curve_active,
        )

    elif regime == "flexible":
        # En crisis de credibilidad: ajustar punto inicial de E y pasar la prima
        E_guess_crisis = E_prev * (1.0 + delta_E_expected) if delta_E_expected > 0 else None
        return eq_flexible_v2(
            sp=sp, pi=pi,
            Y_pot=Y_pot, P_NT=P_NT,
            E_prev=E_prev,
            Y_prev=Y_prev, r_prev=r_prev,
            E_guess=E_guess_crisis,
            j_curve_active=j_curve_active,
            delta_E_external=delta_E_expected,
        )

    elif regime == "crawling_peg":
        crawl_rate = pi.get("crawl_rate", 0.02)
        return eq_crawling_peg_v2(
            sp=sp, pi=pi,
            Y_pot=Y_pot, P_NT=P_NT,
            E_prev=E_prev,
            crawl_rate=crawl_rate,
            j_curve_active=j_curve_active,
        )

    else:
        raise ValueError(
            f"Régimen '{regime}' no reconocido. "
            "Opciones: 'fixed', 'flexible', 'crawling_peg'."
        )
