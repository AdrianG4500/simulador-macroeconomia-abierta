"""
engine_simple/dynamics.py
=========================
Leyes de movimiento interturnos y dinámicas macroeconómicas.
Edición: The Economic War Room (V1.2 SIMPLE).

Principios:
- Funciones PURAS: sin efectos laterales, sin estado global.
- Implementa Secciones 3.3 y 3.4 de master_spec.md:
  3.3 Oferta Agregada, Empleo (Okun), Inflación Multicausal (Phillips 4 fuerzas),
      Credibilidad Endógena y Expectativas Adaptativas.
  3.4 Finanzas Públicas (Recaudación desagregada, Deuda sobre PIB Nominal),
      Flujos de Capital y Reservas Internacionales.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 3.3.1: PIB POTENCIAL Y BRECHA DEL PRODUCTO
# ─────────────────────────────────────────────────────────────────────────────

def compute_output_gap(Y: float, Y_pot: float) -> float:
    """
    Brecha del producto (output gap):
        gap = (Y - Y_pot) / Y_pot
    """
    if Y_pot <= 0.0:
        raise ValueError(f"Y_pot debe ser positivo, recibido: {Y_pot}")
    return (Y - Y_pot) / Y_pot


def update_potential_output(
    Y_pot: float,
    Ig: float,
    g_pot: float = 0.025,
    Ig_dep: float = 5.0,
) -> float:
    """
    Evolución del PIB Potencial (Sección 3.3.1):

        Y_pot_new = Y_pot · (1 + g_pot) + 0.18 · (Ig - Ig_dep)

    Parameters
    ----------
    Y_pot : PIB Potencial del período anterior.
    Ig    : Inversión pública en infraestructura aplicada este período.
    g_pot : Tasa de crecimiento natural autónomo del potencial.
    Ig_dep: Nivel de inversión de reposición/depreciación.
    """
    if Y_pot <= 0.0:
        raise ValueError(f"Y_pot debe ser positivo, recibido: {Y_pot}")
    return Y_pot * (1.0 + g_pot) + 0.18 * (Ig - Ig_dep)


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 3.3.2: MERCADO LABORAL — LEY DE OKUN LINEAL
# ─────────────────────────────────────────────────────────────────────────────

def compute_unemployment(
    U_n: float,
    gap: float,
    gamma_okun: float = 0.45,
) -> float:
    """
    Tasa de desempleo según la Ley de Okun lineal (Sección 3.3.2):

        U = max(0.02, U_n - γ_okun · gap)

    Acotada inferiormente por U_floor = 0.02 (2% piso friccional absoluto).
    """
    U = U_n - gamma_okun * gap
    return max(0.02, U)


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 3.3.3: INFLACIÓN MULTICAUSAL — CURVA DE PHILLIPS DE 4 FUERZAS
# ─────────────────────────────────────────────────────────────────────────────

def compute_inflation(
    pi_e: float,
    gap: float,
    E_t: float,
    E_prev: float,
    alpha_inf: float = 0.25,
    beta_PT: float = 0.20,
    tau_t: float = 0.0,
    tau_prev: float = 0.0,
    shock_seigniorage: float = 0.0,
    **kwargs,
) -> float:
    """
    Inflación multicausal de 4 fuerzas reales (Sección 3.3.3):

        π_t = π^e_t + α_inf · Gap_t + β_PT · (E_t - E_{t-1})/E_{t-1}
              + 0.15 · (τ_t - τ_{t-1}) + Shock_señoreaje

    Parameters
    ----------
    pi_e            : Expectativas de inflación vigentes.
    gap             : Brecha del producto.
    E_t             : Tipo de cambio nominal actual.
    E_prev          : Tipo de cambio nominal del turno anterior.
    alpha_inf       : Sensibilidad de inflación a la brecha (demanda).
    beta_PT         : Pass-through de devaluación cambiaria.
    tau_t           : Arancel actual.
    tau_prev        : Arancel del turno anterior.
    shock_seigniorage : Componente adicional de señoreaje/financiamiento monetario.
    """
    if E_prev <= 0.0:
        E_prev = 10.0  # fallback seguro

    devaluation_rate = (E_t - E_prev) / E_prev
    tariff_cost = 0.15 * (tau_t - tau_prev)

    pi = (
        pi_e
        + alpha_inf * gap
        + beta_PT * devaluation_rate
        + tariff_cost
        + shock_seigniorage
    )
    return pi


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 3.3.4: CREDIBILIDAD ENDÓGENA Y EXPECTATIVAS ADAPTATIVAS
# ─────────────────────────────────────────────────────────────────────────────

def compute_credibility(
    r_ref: float,
    pi_t: float,
    deficit_primario: float,
    Y: float,
) -> float:
    """
    Credibilidad endógena θ_t ∈ [0.40, 0.80] (Sección 3.3.4):

    - Base garantizada: θ_base = 0.40 (nunca menor a 40%).
    - Bono por rigor monetario (Taylor): +0.20 si r_ref ≥ π_t · 100.
    - Bono por disciplina fiscal: +0.20 si Déficit Primario ≤ 1.5% del PIB.

    Parameters
    ----------
    r_ref             : Tasa de política monetaria en p.p. (ej. 6.0 = 6.0%).
    pi_t              : Inflación del período (fracción, ej. 0.03 = 3%).
    deficit_primario  : Déficit fiscal primario (Gc + Ig + SubsidioExport - Recaudación).
    Y                 : PIB real.
    """
    theta = 0.40

    # Bono Taylor: tasa de política ≥ inflación (en p.p.)
    if r_ref >= pi_t * 100.0:
        theta += 0.20

    # Bono de disciplina fiscal: déficit primario ≤ 1.5% del PIB
    if Y > 0.0 and deficit_primario <= 0.015 * Y:
        theta += 0.20

    return min(0.80, max(0.40, theta))


def update_adaptive_expectations(
    theta: float,
    pi_target: float,
    pi_t: float,
) -> float:
    """
    Expectativas de inflación adaptativas (Sección 3.3.4):

        π^e_{t+1} = θ_t · π_meta + (1 - θ_t) · π_t

    Con π_meta = 0.03 por defecto.
    """
    return theta * pi_target + (1.0 - theta) * pi_t


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 3.4.1: FINANZAS PÚBLICAS — RECAUDACIÓN DESAGREGADA Y DEUDA
# ─────────────────────────────────────────────────────────────────────────────

def compute_fiscal_balance(
    Gc: float,
    Ig: float,
    tc: float,
    tk: float,
    tau: float,
    sx: float,
    Y: float,
    X: float,
    M_imp: float,
    B_prev: float,
    r_star: float,
    rho: float,
    G_needed: float = 0.0,
) -> tuple[float, float, float, float, float, float]:
    """
    Balance fiscal desagregado (Sección 3.4.1):

        Recaudación = (tc + tk) · Y + τ · M_imp
        CostoSubsidios = sx · X
        InteresesDeuda = ((r* + ρ) / 100) · B_{t-1}
        Déficit = Gc + Ig + CostoSubsidios + InteresesDeuda + G_needed - Recaudación
        B_new = max(0.0, B_prev + Déficit)

    Returns
    -------
    tuple : (recaudacion, costo_subsidios, intereses_deuda, deficit, B_new, deficit_primario)
    """
    recaudacion = (tc + tk) * Y + tau * M_imp
    costo_subsidios = sx * X
    intereses_deuda = ((r_star + rho) / 100.0) * B_prev
    gasto_total = Gc + Ig + costo_subsidios + intereses_deuda + G_needed
    deficit = gasto_total - recaudacion
    B_new = max(0.0, B_prev + deficit)

    # Déficit primario (sin intereses de deuda)
    deficit_primario = Gc + Ig + costo_subsidios + G_needed - recaudacion

    return (
        round(recaudacion, 6),
        round(costo_subsidios, 6),
        round(intereses_deuda, 6),
        round(deficit, 6),
        round(B_new, 6),
        round(deficit_primario, 6),
    )


def compute_debt_to_gdp_nominal(B: float, PIB_nominal: float) -> float:
    """
    Ratio de Sostenibilidad Fiscal sobre PIB Nominal (Sección 3.4.2):

        RatioDeuda = B / PIB_Nominal
    """
    if PIB_nominal <= 0.0:
        return 999.0
    return B / PIB_nominal


# ─────────────────────────────────────────────────────────────────────────────
# SECCIÓN 3.4.3: FLUJOS DE CAPITAL Y RESERVAS INTERNACIONALES
# ─────────────────────────────────────────────────────────────────────────────

def compute_capital_flows(
    f: float,
    r_t: float,
    r_star: float,
    rho: float,
    delta_E_expected: float = 0.0,
) -> float:
    """
    Flujo neto de capitales (Sección 3.4.3):

        KA = f · ((r_t - r* - ρ - ΔE^e) / 100)

    Nota: Todas las tasas están en puntos porcentuales.
    """
    return f * ((r_t - r_star - rho - delta_E_expected) / 100.0)


def update_reserves(
    R_prev: float,
    NX: float,
    KA: float,
    regime: str,
) -> float:
    """
    Actualización de Reservas Internacionales (Sección 3.4.3):

    - Fijo / Crawling:  R_t = R_{t-1} + NX + KA
    - Flexible:         R_t = R_{t-1} + 0.15 · (NX + KA)
    """
    if regime in ("fixed", "crawling_peg"):
        R_new = R_prev + NX + KA
    else:
        R_new = R_prev + 0.15 * (NX + KA)

    return round(max(0.0, R_new), 6)


def compute_flexible_exchange_rate_adjustment(
    E_prev: float,
    NX: float,
    KA: float,
) -> float:
    """
    Ajuste del tipo de cambio en régimen Flexible (Sección 3.4.3):

        E_t = E_{t-1} · [1 - 0.015 · (NX + KA)]

    El tipo de cambio absorbe el desbalance externo. Acotado entre 1.0 y 50.0.
    """
    bp_balance = NX + KA
    E_new = E_prev * (1.0 - 0.015 * bp_balance)
    return max(1.0, min(50.0, E_new))


# ─────────────────────────────────────────────────────────────────────────────
# RIESGO SOBERANO Y CALIFICACIÓN CREDITICIA
# ─────────────────────────────────────────────────────────────────────────────

def compute_sovereign_risk(
    B: float,
    PIB_nominal: float,
    R: float,
) -> tuple[float, str]:
    """
    Calcula la prima de riesgo soberano ρ (en p.p.) y la calificación crediticia
    basadas en el Ratio Deuda/PIB Nominal y el nivel de reservas.

    Escalera:
    - Deuda/PIB_nom < 25% : ρ = 0.5  -> AAA
    - Deuda/PIB_nom < 40% : ρ = 1.0  -> AA+
    - Deuda/PIB_nom < 55% : ρ = 1.5  -> AA
    - Deuda/PIB_nom < 70% : ρ = 2.5  -> A
    - Deuda/PIB_nom < 85% : ρ = 4.0  -> BBB
    - Deuda/PIB_nom < 100%: ρ = 6.0  -> BB
    - Deuda/PIB_nom < 130%: ρ = 9.0  -> B
    - Deuda/PIB_nom < 150%: ρ = 13.0 -> CCC
    - Deuda/PIB_nom ≥ 150%: ρ = 18.0 -> D

    Reservas < 10 MUSD: +2.0 pp extra.
    Reservas < 5 MUSD:  +4.0 pp extra.

    Returns
    -------
    tuple[float, str] : (rho en p.p., rating)
    """
    debt_ratio = B / max(PIB_nominal, 1.0)

    if debt_ratio < 0.25:
        rho = 0.5
        rating = "AAA"
    elif debt_ratio < 0.40:
        rho = 1.0
        rating = "AA+"
    elif debt_ratio < 0.55:
        rho = 1.5
        rating = "AA"
    elif debt_ratio < 0.70:
        rho = 2.5
        rating = "A"
    elif debt_ratio < 0.85:
        rho = 4.0
        rating = "BBB"
    elif debt_ratio < 1.00:
        rho = 6.0
        rating = "BB"
    elif debt_ratio < 1.30:
        rho = 9.0
        rating = "B"
    elif debt_ratio < 1.50:
        rho = 13.0
        rating = "CCC"
    else:
        rho = 18.0
        rating = "D"

    # Penalidad adicional por reservas bajas
    if R < 5.0:
        rho += 4.0
        if rating not in ("CCC", "D"):
            rating += " (Crisis de Reservas)"
    elif R < 10.0:
        rho += 2.0

    return round(rho, 4), rating


# ─────────────────────────────────────────────────────────────────────────────
# EVOLUCIÓN DE PRECIOS NO TRANSABLES (P_NT)
# ─────────────────────────────────────────────────────────────────────────────

def update_P_NT(P_NT_prev: float, pi_t: float) -> float:
    """
    Precios de bienes no transables crecen con la inflación doméstica.

        P_NT_new = P_NT_prev · (1 + π_t)
    """
    return max(0.1, P_NT_prev * (1.0 + pi_t))
