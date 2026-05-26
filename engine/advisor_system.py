"""
engine/advisor_system.py
========================
Sistema de alertas preventivas del Gabinete de Asesores (Fase 3).

El sistema proyecta el próximo período realizando un "dry-run" del equilibrio
IS-LM-BP si se mantiene la política económica actual (sin cambios).
Si se detecta que alguna variable cruza un umbral crítico, se genera un warning.
"""

from __future__ import annotations

import math
from typing import TypedDict
from engine.core_v2 import solve_equilibrium_v2
from engine.dynamics_v2 import (
    compute_fiscal_balance,
    compute_output_gap,
    compute_unemployment,
    update_potential_output,
    update_reserves,
)
from engine.game_state import GameState


class AdvisorWarning(TypedDict):
    """
    Alertas generadas por los ministros del gabinete.
    """
    advisor: str  # "Banco Central" | "Ministerio de Trabajo" | "Ministerio de Hacienda" | "Asesor Cambiario"
    message: str


def generate_advisor_warnings(state: GameState) -> list[AdvisorWarning]:
    """
    Proyecta el próximo período aplicando la política actual sin cambios y
    verifica si se cruza algún umbral crítico de alerta.

    Parameters
    ----------
    state : GameState actual

    Returns
    -------
    list[AdvisorWarning] : Lista de alertas emitidas por el gabinete de asesores.
    """
    warnings: list[AdvisorWarning] = []
    
    if not state or not state["history"]:
        return warnings

    # Extraer parámetros estructurales e instrumentos de política actuales
    sp = dict(state["structural"])
    pi = dict(state["policy"])

    # Valores actuales de las variables de estado continuas
    Y_pot_curr = state["Y_pot"]
    P_NT_curr = state["P_NT"]
    R_curr = state["R"]
    B_curr = state["B"]
    regime = state["regime"]

    prev_snap = state["history"][-1]
    E_prev = prev_snap["E"]
    Y_prev = prev_snap["Y"]
    r_prev = prev_snap["r"]

    # 1. PROYECCIÓN SIMPLE PARA EL TURNO SIGUIENTE (t + 1)
    # Crecimiento potencial estructural (g_pot)
    Y_pot_next = update_potential_output(Y_pot_curr, sp["g_pot"], endogenous_shock=0.0)

    # Inflación núcleo proyectada (sin componente cambiario)
    if len(state["history"]) >= 2:
        E_prev_prev = state["history"][-2]["E"]
    else:
        E_prev_prev = E_prev
    delta_E_curr = E_prev - E_prev_prev
    devaluation_rate_curr = delta_E_curr / max(E_prev_prev, 1e-9)
    pi_core = prev_snap["pi"] - sp["beta_PT"] * devaluation_rate_curr
    P_NT_next = P_NT_curr * (1.0 + pi_core)

    # Solver de equilibrio IS-LM-BP
    try:
        eq = solve_equilibrium_v2(
            sp=sp,
            pi=pi,
            Y_pot=Y_pot_next,
            P_NT=P_NT_next,
            E_prev=E_prev,
            Y_prev=Y_prev,
            r_prev=r_prev,
            j_curve_active=state["j_curve_active"],
            delta_E_expected=state["delta_E_expected"],
        )
    except Exception:
        # Fallback si el solver falla en el dry-run: usar valores actuales
        eq = {
            "Y": Y_prev,
            "r": r_prev,
            "NX": prev_snap["NX"],
            "P_local": prev_snap["P_local"],
            "E_endo": prev_snap["E"] if regime == "flexible" else float("nan"),
        }

    # 2. CALCULAR MÉTRICAS PROYECTADAS
    Y_proj = eq["Y"]
    r_proj = eq["r"]
    NX_proj = eq["NX"]

    # Desempleo proyectado
    gap_proj = compute_output_gap(Y_proj, Y_pot_next)
    U_proj = compute_unemployment(sp["U_n"], sp["gamma_okun"], gap_proj)

    # Reservas proyectadas
    R_proj = update_reserves(R_curr, NX_proj, regime)

    # Balance fiscal y deuda proyectados
    _, _, deficit_proj, B_proj = compute_fiscal_balance(
        G=pi["G"],
        t=sp["t"],
        Y=Y_proj,
        r=r_proj,
        B_prev=B_curr,
    )

    # Expectativas cambiarias proyectadas (delta_E_expected)
    if regime == "flexible":
        E_endo = eq.get("E_endo", float("nan"))
        E_proj = E_endo if not math.isnan(E_endo) else E_prev
    elif regime == "crawling_peg":
        E_proj = E_prev * (1.0 + pi.get("crawl_rate", 0.02))
    else:
        E_proj = pi["E"]
    
    delta_E_proj = E_proj - E_prev
    delta_E_expected_proj = delta_E_proj / max(E_prev, 1e-9)

    # 3. EVALUACIÓN DE UMBRALES CRÍTICOS Y EMISIÓN DE DE WARNINGS

    # --- BANCO CENTRAL ---
    # R proyectada <= 0 bajo TC Fijo, o en declive extremo (menor al 30% del t=0)
    R_0_ref = state["history"][0]["R"]
    if regime == "fixed":
        if R_proj <= 0.0:
            warnings.append(AdvisorWarning(
                advisor="Banco Central",
                message="Ministro, las reservas cruzarán el nivel crítico el próximo mes (R proyectada <= 0). Se recomienda revisión urgente de la política cambiaria para evitar una devaluación descontrolada."
            ))
        elif R_proj < R_0_ref * 0.30:
            warnings.append(AdvisorWarning(
                advisor="Banco Central",
                message="Alerta cambiaria: Las reservas internacionales proyectadas están por debajo del 30% del nivel inicial. La defensa del tipo de cambio fijo se está volviendo insostenible."
            ))

    # --- MINISTERIO DE TRABAJO ---
    # U proyectada > 10%
    if U_proj > 0.10:
        warnings.append(AdvisorWarning(
            advisor="Ministerio de Trabajo",
            message=f"El desempleo proyectado alcanzará el {U_proj:.1%}, superando el umbral de tolerancia social. Existe riesgo inminente de conflictividad social y caída severa en la propensión a consumir."
        ))

    # --- MINISTERIO DE HACIENDA ---
    # B/Y proyectada > 80%
    B_Y_ratio_proj = B_proj / max(Y_proj, 1.0)
    if B_Y_ratio_proj > 0.80:
        warnings.append(AdvisorWarning(
            advisor="Ministerio de Hacienda",
            message=f"La relación Deuda/PIB proyectada supera el umbral de sostenibilidad del 80% (actualmente: {B_Y_ratio_proj:.1%}). Los mercados globales y acreedores podrían requerir una mayor prima de riesgo soberana el próximo trimestre."
        ))

    # --- ASESOR CAMBIARIO ---
    # delta_E_expected > 10%
    if delta_E_expected_proj > 0.10:
        warnings.append(AdvisorWarning(
            advisor="Asesor Cambiario",
            message=f"Las expectativas de devaluación para el próximo mes están elevadas ({delta_E_expected_proj:.1%}). Insistir con una política cambiaria de anclaje nominal rígido podría gatillar una corrida bancaria devastadora."
        ))

    return warnings
