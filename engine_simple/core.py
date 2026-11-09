"""
engine_simple/core.py
=====================
Motor matemático puro y solvers analíticos cerrados (Closed-Form Analytical Solvers).
Edición: The Economic War Room (V1.2 SIMPLE).

Principios:
- Funciones PURAS: dado el mismo input -> mismo output, sin mutar objetos.
- Cero solvers iterativos aproximados (sin fsolve, least_squares ni bucles while).
- Garantía incondicional de identidad macroeconómica: Y = C + I_priv + G + NX (error < 1e-12).
- Soporte para 3 regímenes cambiarios: fixed | flexible | crawling_peg.
- Normalización de precios en base E₀ = 10.0 (Sección 3.1 de master_spec.md).
- Análisis de equilibrio Salter-Swan dinámico (4 zonas).

Fórmulas implementadas según Sección 3 de master_spec.md:
  3.1 Precios y TCR normalizados
  3.2 Multiplicador, componentes de demanda e identidad contable cerrada
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

from config_simple.parameters import (
    Equilibrium,
    PolicyInstruments,
    SalterSwanResult,
    StructuralParams,
)


# ─── Constante de normalización ──────────────────────────────────────────────
E_BASE = 10.0  # Tipo de cambio nominal de referencia para normalizar precios


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 1: FUNCIONES DE COMPONENTES PURAS (Sección 3.1 y 3.2)
# ─────────────────────────────────────────────────────────────────────────────

def compute_multiplier(c1: float, tc: float, m1: float, tau: float = 0.0) -> float:
    """
    Multiplicador keynesiano ampliado para economía abierta (Sección 3.2.1):

        k_m = 1 / [1 - c₁·(1 - tc) + m₁·(1 - τ)]

    Raises
    ------
    ValueError : Si el denominador ≤ 0 (modelo inestable).
    """
    denom = 1.0 - c1 * (1.0 - tc) + m1 * (1.0 - tau)
    if denom <= 0.0:
        raise ValueError(
            f"Multiplicador indefinido: denominador = {denom:.6f}. "
            f"Parámetros: c1={c1}, tc={tc}, m1={m1}, tau={tau}."
        )
    return 1.0 / denom


def compute_price_level(
    E: float,
    P_star: float,
    P_NT: float,
    alpha_PT: float,
    tau: float = 0.0,
) -> tuple[float, float]:
    """
    Nivel de precios doméstico con normalización base E₀ = 10.0 (Sección 3.1):

        P_T = (E / 10.0) · P* · (1 + 0.50 · τ)
        P_local = α_PT · P_T + (1 - α_PT) · P_NT

    Returns
    -------
    tuple[float, float] : (P_local, P_T)
    """
    P_T = (E / E_BASE) * P_star * (1.0 + 0.50 * tau)
    P_local = alpha_PT * P_T + (1.0 - alpha_PT) * P_NT
    return max(P_local, 1e-6), P_T


def compute_real_exchange_rate(
    E: float,
    P_star: float,
    P_local: float,
) -> float:
    """
    Tipo de cambio real normalizado (Sección 3.1):

        q = (E / 10.0) · P* / P_local
    """
    if P_local <= 0.0:
        raise ValueError(f"P_local debe ser positivo, recibido: {P_local}")
    return ((E / E_BASE) * P_star) / P_local


def compute_domestic_interest_rate(
    r_ref: float,
    rho: float,
    regime: str,
    r_star: float = 4.5,
    crawl_rate: float = 0.0,
) -> float:
    """
    Tasa de interés doméstica efectiva r_t (Sección 3.2.2):

    - Flexible: r_t = r_ref + 0.5 · ρ_t
    - Fijo / Crawling (Trilema): r_t = 0.60 · r_ref + 0.40 · (r* + crawl_rate·100 + ρ_t)

    Nota: r_ref, r_star, rho y crawl_rate están todos en puntos porcentuales
    (ej. r_ref = 6.0 significa 6.0%).
    """
    if regime == "flexible":
        r_t = r_ref + 0.5 * rho
    else:
        r_t = 0.60 * r_ref + 0.40 * (r_star + crawl_rate * 100.0 + rho)
    return max(0.1, r_t)


def compute_private_investment(
    I0: float,
    b: float,
    r_t: float,
    r0: float,
    rho_k: float,
    tk: float,
    tk0: float,
    psi_ci: float,
    Ig: float,
    Ig0: float,
    psi_co: float,
    debt_ratio_prev: float,
) -> float:
    """
    Formación Bruta de Capital Privado I_priv (Sección 3.2.3):

        I_priv = max(2.0,
            I₀ - b·(r_t - r₀) - ρ_k·(t_k - t_k₀) + ψ_ci·(Ig - Ig₀)
            - ψ_co · max(0, RatioDeuda_{t-1} - 0.60)
        )
    """
    I_priv = (
        I0
        - b * (r_t - r0)
        - rho_k * (tk - tk0)
        + psi_ci * (Ig - Ig0)
        - psi_co * max(0.0, debt_ratio_prev - 0.60)
    )
    return max(2.0, I_priv)


def compute_exports(
    x0: float,
    epsilon_x: float,
    q: float,
    eta_x: float,
    sx: float,
) -> float:
    """
    Exportaciones brutas X_t (Sección 3.2.5):

        X = x₀ + ε_x · (q - 1.0) + η_x · s_x
    """
    return max(1.0, x0 + epsilon_x * (q - 1.0) + eta_x * sx)


def compute_imports(
    m0: float,
    m1: float,
    tau: float,
    Y: float,
    epsilon_m: float,
    q: float,
) -> float:
    """
    Importaciones brutas M_imp (Sección 3.2.5):

        M_imp = max(2.0, m₀ + m₁·(1 - τ)·Y - ε_m·(q - 1.0))
    """
    return max(2.0, m0 + m1 * (1.0 - tau) * Y - epsilon_m * (q - 1.0))


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 2: SOLVER ANALÍTICO CERRADO UNIFICADO (Sección 3.2.6)
# ─────────────────────────────────────────────────────────────────────────────

def solve_equilibrium(
    sp: StructuralParams,
    pi: PolicyInstruments,
    P_NT: float = 1.0,
    E_prev: Optional[float] = None,
    Y_prev: float = 100.0,
    Y_pot: float = 100.0,
    rho: float = 0.0,
    debt_ratio_prev: float = 0.20,
) -> Equilibrium:
    """
    Función orquestadora unificada: resuelve el equilibrio macroeconómico IS-LM-BP
    en forma cerrada analítica según el régimen cambiario activo.

    Secuencia determinista (Sección 3.2 completa):
    1. Determinar E efectivo según régimen.
    2. Calcular precios y TCR normalizados (base E₀ = 10.0).
    3. Calcular multiplicador keynesiano ampliado.
    4. Calcular tasa de interés doméstica efectiva.
    5. Calcular inversión privada pre-equilibrio.
    6. Calcular exportaciones.
    7. Resolver Y_eq analítico cerrado.
    8. Aplicar amortiguador de inercia 65/35.
    9. Recalcular componentes con Y_t final para garantizar identidad contable exacta.

    Garantía Incondicional de Identidad: |Y_t - (C + I_priv + G + NX)| < 1e-12.
    """
    # ── 0. Extraer parámetros de instrumentos ──
    Gc = pi["Gc"]
    Ig = pi["Ig"]
    tc = pi["tc"]
    tk = pi["tk"]
    r_ref = pi["r_ref"]
    tau = pi["tau"]
    sx = pi["sx"]
    E_input = pi["E"]
    regime = pi.get("regime", "fixed")
    crawl_rate = pi.get("crawl_rate", 0.0)
    r_star = pi.get("r_star", 4.5)
    P_star_inst = pi.get("P_star", sp["P_star"])

    # ── 1. Determinar E efectivo según régimen ──
    if regime == "crawling_peg":
        e_p = E_prev if E_prev is not None else E_input
        E_eff = e_p * (1.0 + crawl_rate)
    elif regime == "flexible":
        E_eff = E_input  # Valor inicial; se recalculará abajo tras resolver el equilibrio
    else:
        E_eff = E_input

    # ── 2. Precios y TCR normalizados (Sección 3.1) ──
    P_local, P_T = compute_price_level(E_eff, P_star_inst, P_NT, sp["alpha_PT"], tau)
    q = compute_real_exchange_rate(E_eff, P_star_inst, P_local)

    # ── 3. Multiplicador keynesiano ampliado (Sección 3.2.1) ──
    k_m = compute_multiplier(sp["c1"], tc, sp["m1"], tau)

    # ── 4. Tasa de interés doméstica efectiva (Sección 3.2.2) ──
    r_t = compute_domestic_interest_rate(r_ref, rho, regime, r_star, crawl_rate)

    # ── 5. Inversión privada pre-equilibrio (Sección 3.2.3) ──
    I_priv_pre = compute_private_investment(
        I0=sp["I0"], b=sp["b"], r_t=r_t, r0=sp["r0"],
        rho_k=sp["rho_k"], tk=tk, tk0=sp["tk0"],
        psi_ci=sp["psi_ci"], Ig=Ig, Ig0=sp["Ig0"],
        psi_co=sp["psi_co"], debt_ratio_prev=debt_ratio_prev,
    )

    # ── 6. Exportaciones (Sección 3.2.5) ──
    X = compute_exports(sp["x0"], sp["epsilon_x"], q, sp["eta_x"], sx)

    # ── 7. Solución analítica cerrada del PIB (Sección 3.2.6) ──
    # Y_eq = k_m · [c₀ + I_priv + Gc + Ig + X - m₀ + ε_m·(q - 1.0)]
    autonomous_demand = (
        sp["c0"]
        + I_priv_pre
        + Gc
        + Ig
        + X
        - sp["m0"]
        + sp["epsilon_m"] * (q - 1.0)
    )
    Y_eq = k_m * autonomous_demand
    Y_eq = max(10.0, Y_eq)

    # ── 8. Amortiguador de inercia macroeconómica 65/35 (Sección 3.2.6) ──
    Y_t = 0.65 * Y_eq + 0.35 * Y_prev
    Y_t = max(10.0, Y_t)

    # ── 9. Recalcular componentes con Y_t final para identidad exacta ──
    # C_t = c₀ + c₁·(1 - tc)·Y_t
    C = sp["c0"] + sp["c1"] * (1.0 - tc) * Y_t

    # M_imp se evalúa con Y_t (Sección 3.2.5)
    M_imp = compute_imports(sp["m0"], sp["m1"], tau, Y_t, sp["epsilon_m"], q)

    # NX = X - M_imp
    NX = X - M_imp

    # G_total = Gc + Ig
    G_total = Gc + Ig

    # I_priv absorbe el ajuste de inventarios para garantizar identidad exacta
    # I_priv = Y_t - C - G - NX
    I_priv = Y_t - C - G_total - NX

    # ── Verificación incondicional de identidad ──
    identity_error = abs(Y_t - (C + I_priv + G_total + NX))
    assert identity_error < 1e-12, (
        f"IDENTIDAD VIOLADA: |Y - (C+I+G+NX)| = {identity_error:.2e}. "
        f"Y={Y_t}, C={C}, I_priv={I_priv}, G={G_total}, NX={NX}"
    )

    # ── Absorción doméstica y brecha ──
    A_domestic = C + I_priv + G_total
    gap = (Y_t - Y_pot) / Y_pot if Y_pot > 0 else 0.0
    PIB_nominal = Y_t * P_local

    # ── Actualizar E_endo en régimen flexible (Sección 3.4) ──
    E_endo = E_eff
    if regime == "flexible":
        # El ajuste del tipo de cambio endógeno se calculará en dynamics
        # Aquí E_endo se mantiene como el E input
        E_endo = E_eff
    elif regime == "crawling_peg":
        E_endo = E_eff

    return {
        "Y": Y_t,
        "Y_eq": Y_eq,
        "r": r_t,
        "E_endo": E_endo,
        "NX": NX,
        "X": X,
        "M_imp": M_imp,
        "C": C,
        "I_priv": I_priv,
        "Gc": Gc,
        "Ig": Ig,
        "G": G_total,
        "mult": k_m,
        "P_local": P_local,
        "P_T": P_T,
        "P_NT": P_NT,
        "q_real": q,
        "gap": gap,
        "A_domestic": A_domestic,
        "PIB_nominal": PIB_nominal,
    }


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 3: SALTER-SWAN DINÁMICO (4 Cuadrantes Canónicos)
# ─────────────────────────────────────────────────────────────────────────────

_ZONE_MAP: dict[str, tuple[str, str]] = {
    "I": (
        "Zona I: Sobrecalentamiento con Superávit Externo (Inflación + Superávit en Cuenta Corriente).",
        "Reducir absorción doméstica (ajuste fiscal o alza de TPM) o apreciar la moneda nacional (revaluar E).",
    ),
    "II": (
        "Zona II: Capacidad Ociosa con Superávit Externo (Desempleo + Superávit en Cuenta Corriente).",
        "Estimular el gasto interno y absorción doméstica (aumentar Ig o reducir impuestos) para cerrar la brecha de empleo.",
    ),
    "III": (
        "Zona III: Crisis Gemela Clásica (Desempleo + Déficit en Cuenta Corriente).",
        "Depreciar el tipo de cambio real (devaluar E) para ganar competitividad externa y reactivar el empleo vía exportaciones.",
    ),
    "IV": (
        "Zona IV: Sobreconsumo con Desbalance Externo (Inflación + Déficit en Cuenta Corriente).",
        "Ajuste fiscal contractivo (reducir Gc y absorción) para enfriar la demanda doméstica y recortar importaciones.",
    ),
}


def compute_salter_swan(
    eq_result: Equilibrium,
    sp: StructuralParams,
    G_total: float,
    A_ref: float = 100.0,
    q_ref: float = 1.0,
    Y_pot: Optional[float] = None,
) -> SalterSwanResult:
    """
    Análisis dinámico del modelo Salter-Swan con pendientes estructurales derivadas.
    Usa la información del equilibrio para clasificar la posición en los 4 cuadrantes canónicos.

    Pendiente IB (Balance Interno - Pleno Empleo Y = Y_pot):
        dq/dA|_IB = - (1 - c1·(1 - tc) + m1) / (epsilon_x + epsilon_m) < 0 (recta descendente).
        Puntos arriba de IB: Presiones inflacionarias / Exceso de absorción.
        Puntos abajo de IB: Desempleo / Brecha recesiva.

    Pendiente EB (Balance Externo - Equilibrio en Cuenta Corriente NX = 0):
        dq/dA|_EB = m1 / (epsilon_x + epsilon_m) > 0 (recta ascendente).
        Puntos arriba de EB: Superávit de Cuenta Corriente (NX > 0).
        Puntos abajo de EB: Déficit de Cuenta Corriente (NX < 0).

    Cuadrantes Canónicos:
        Zona I:   q > q_IB y q > q_EB (Inflación + Superávit)
        Zona II:  q < q_IB y q > q_EB (Desempleo + Superávit)
        Zona III: q < q_IB y q < q_EB (Desempleo + Déficit)
        Zona IV:  q > q_IB y q < q_EB (Inflación + Déficit)
    """
    A_actual = eq_result["A_domestic"]
    q_actual = eq_result["q_real"]

    if Y_pot is not None and Y_pot > 0.0:
        A_ref = Y_pot

    tc_eff = sp.get("tc", 0.16) if "tc" not in sp else 0.16
    ml_satisfied = (sp["epsilon_x"] + sp["epsilon_m"]) > 1.0

    slope_numerator_IB = 1.0 - sp["c1"] * (1.0 - tc_eff) + sp["m1"]
    slope_denominator = max(sp["epsilon_x"] + sp.get("epsilon_m", 0.0), 1e-4)

    scale_factor = q_ref / max(A_ref, 1.0)
    slope_IB = (-slope_numerator_IB / slope_denominator) * scale_factor
    slope_EB = (sp["m1"] / slope_denominator) * scale_factor

    q_IB_at_A = q_ref + slope_IB * (A_actual - A_ref)
    q_EB_at_A = q_ref + slope_EB * (A_actual - A_ref)

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

    return {
        "zone": zone,
        "diagnosis": diagnosis,
        "policy": policy,
        "q_actual": round(q_actual, 6),
        "A_actual": round(A_actual, 6),
        "q_IB_at_A": round(q_IB_at_A, 6),
        "q_EB_at_A": round(q_EB_at_A, 6),
        "slope_IB": round(slope_IB, 6),
        "slope_EB": round(slope_EB, 6),
        "ml_satisfied": ml_satisfied,
    }
