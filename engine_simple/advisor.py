"""
engine_simple/advisor.py
=========================
Sistema de asesoría de Gabinete Económico y simulación preventiva (Dry-Run).
Edición: The Economic War Room (V1.2 SIMPLE).

Principios:
- Dry-Run en memoria: resuelve el equilibrio y dinámicas proyectadas para el turno t+1
  sin alterar el estado real.
- Emisión de dictámenes socráticos de 3 asesores ministeriales:
  1. 🏦 Banco Central: Inflación, Reservas, Tasa Real, Pass-through cambiario.
  2. 🏛️ Ministerio de Hacienda: Deuda/PIB Nominal, Regla Fiscal, Balance Primario.
  3. 🏭 Ministerio de Trabajo y Comercio: Desempleo, Competitividad (q), Aranceles/Subsidios.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional, TypedDict

from config_simple.parameters import (
    Equilibrium,
    PolicyInstruments,
    SalterSwanResult,
    StructuralParams,
    TurnSnapshot,
)
from config_simple.scoring import calc_period_score
from engine_simple.core import compute_salter_swan, solve_equilibrium
from engine_simple.dynamics import (
    compute_capital_flows,
    compute_debt_to_gdp_nominal,
    compute_fiscal_balance,
    compute_inflation,
    compute_output_gap,
    compute_sovereign_risk,
    compute_unemployment,
    update_reserves,
)


class CabinetAdvice(TypedDict):
    """Estructura del dictamen del Gabinete Económico."""
    central_bank: str
    treasury: str
    labor_growth: str
    salter_swan: str
    overall_summary: str
    projected_score: float
    risk_alerts: list[str]


def run_dry_run(
    current_snapshot: TurnSnapshot,
    params: StructuralParams,
    proposed_instruments: PolicyInstruments,
    Y_pot: float,
    pi_e: float,
    B_prev: float,
    R_prev: float,
) -> TurnSnapshot:
    """
    Ejecuta una proyección en borrador ("Dry-Run") del turno t+1.
    No altera el estado del juego; retorna un TurnSnapshot proyectado.
    """
    p_copy = copy.deepcopy(params)
    inst_copy = copy.deepcopy(proposed_instruments)

    # Parámetros de contexto
    rho_prev = current_snapshot.get("rho", 0.5)
    debt_ratio_prev = current_snapshot.get("debt_to_gdp_nominal", 0.20)
    P_NT = current_snapshot.get("P_NT", 1.0)
    E_prev = current_snapshot["E"]
    Y_prev = current_snapshot["Y"]

    # 1. Resolver equilibrio instantáneo
    eq: Equilibrium = solve_equilibrium(
        sp=p_copy,
        pi=inst_copy,
        P_NT=P_NT,
        E_prev=E_prev,
        Y_prev=Y_prev,
        Y_pot=Y_pot,
        rho=rho_prev,
        debt_ratio_prev=debt_ratio_prev,
    )

    # 2. Dinámicas proyectadas
    gap = compute_output_gap(eq["Y"], Y_pot)
    U = compute_unemployment(p_copy["U_n"], gap, p_copy.get("gamma_okun", 0.45))

    E_curr = eq["E_endo"]
    tau_curr = inst_copy["tau"]
    tau_prev_val = current_snapshot["policy_applied"].get("tau", tau_curr) if current_snapshot.get("policy_applied") else tau_curr

    pi = compute_inflation(
        pi_e=pi_e,
        gap=gap,
        E_t=E_curr,
        E_prev=E_prev,
        alpha_inf=p_copy.get("alpha_inf", 0.25),
        beta_PT=p_copy["beta_PT"],
        tau_t=tau_curr,
        tau_prev=tau_prev_val,
    )

    gY = (eq["Y"] - Y_prev) / Y_prev if Y_prev > 0 else 0.0

    PIB_nominal = eq["PIB_nominal"]

    # Balance fiscal con piso de deuda estructural
    recaudacion, costo_subsidios, intereses_deuda, deficit, B_new, deficit_primario = compute_fiscal_balance(
        Gc=inst_copy["Gc"],
        Ig=inst_copy["Ig"],
        tc=inst_copy["tc"],
        tk=inst_copy["tk"],
        tau=inst_copy["tau"],
        sx=inst_copy["sx"],
        Y=eq["Y"],
        X=eq["X"],
        M_imp=eq["M_imp"],
        B_prev=B_prev,
        r_star=inst_copy["r_star"],
        rho=rho_prev,
        PIB_nominal=PIB_nominal,
    )

    debt_to_gdp_nominal = compute_debt_to_gdp_nominal(B_new, PIB_nominal)

    # Flujos de capital y reservas (con ahorro en FSE si deuda está en piso)
    regime = inst_copy.get("regime", "fixed")
    crawl_rate = inst_copy.get("crawl_rate", 0.0)
    delta_E_expected = crawl_rate * 100.0 if regime == "crawling_peg" else 0.0

    KA = compute_capital_flows(
        f=p_copy["f"],
        r_t=eq["r"],
        r_star=inst_copy["r_star"],
        rho=rho_prev,
        delta_E_expected=delta_E_expected,
    )
    b_unconstrained = B_prev + deficit
    b_min = max(2.0, 0.10 * (PIB_nominal if PIB_nominal > 0.0 else eq["Y"]))
    excess_surplus = max(0.0, b_min - b_unconstrained)
    R_new = update_reserves(R_prev, eq["NX"], KA, regime)
    if excess_surplus > 0.0:
        R_new = round(R_new + excess_surplus, 6)

    rho_risk, rating_risk = compute_sovereign_risk(
        B=B_new,
        PIB_nominal=PIB_nominal,
        R=R_new,
        pi=pi,
        U=U,
        Un=p_copy["U_n"],
    )

    # Salter-Swan
    ss: SalterSwanResult = compute_salter_swan(eq, p_copy, eq["G"], Y_pot=Y_pot)

    # Score proyectado
    prev_score = current_snapshot.get("score", 70.0)
    score = calc_period_score(
        gap=gap, U=U, pi=pi, gY=gY,
        prev_score=prev_score,
        debt_ratio=debt_to_gdp_nominal,
        Un=p_copy["U_n"],
    )

    dry_snapshot: TurnSnapshot = {
        "t": current_snapshot["t"] + 1,
        "Y": eq["Y"],
        "Y_pot": Y_pot,
        "r": eq["r"],
        "C": eq["C"],
        "I_priv": eq["I_priv"],
        "I_inv": eq["I_priv"],
        "Gc": eq["Gc"],
        "Ig": eq["Ig"],
        "G": eq["G"],
        "NX": eq["NX"],
        "X": eq["X"],
        "M_imp": eq["M_imp"],
        "A_domestic": eq["A_domestic"],
        "E": E_curr,
        "P_local": eq["P_local"],
        "P_T": eq["P_T"],
        "P_NT": P_NT,
        "q_real": eq["q_real"],
        "pi": pi,
        "pi_e": pi_e,
        "theta": 0.40,
        "U": U,
        "gap": gap,
        "gY": gY,
        "recaudacion": recaudacion,
        "costo_subsidios": costo_subsidios,
        "intereses_deuda": intereses_deuda,
        "deficit": deficit,
        "B": B_new,
        "PIB_nominal": PIB_nominal,
        "debt_to_gdp_nominal": debt_to_gdp_nominal,
        "R": R_new,
        "KA": KA,
        "rho": rho_risk,
        "rating": rating_risk,
        "zone_ss": ss["zone"],
        "score": score,
        "red_alert_active": False,
        "red_alert_reason": "",
        "consecutive_alert_turns": 0,
        "policy_applied": copy.deepcopy(inst_copy),
        "events_triggered": [],
    }

    return dry_snapshot


def generate_cabinet_advice(
    current_snapshot: TurnSnapshot,
    dry_run_snapshot: TurnSnapshot,
    ss_result: SalterSwanResult,
    target_pi: float = 0.03,
) -> CabinetAdvice:
    """
    Genera el informe de asesoría del Gabinete Económico comparando el estado actual
    con el proyectado por el Dry-Run.

    Los 3 asesores formulan preguntas socráticas y alertas sin regalar la respuesta exacta.
    """
    alerts: list[str] = []

    # ─── 1. 🏦 BANCO CENTRAL (Monetario y Cambiario) ──────────────────────
    pi_proj = dry_run_snapshot["pi"]
    R_proj = dry_run_snapshot["R"]
    regime = dry_run_snapshot["policy_applied"]["regime"]
    r_ref = dry_run_snapshot["policy_applied"]["r_ref"]

    cb_msg = []
    tasa_real = r_ref - pi_proj * 100.0

    if pi_proj > target_pi + 0.05:
        cb_msg.append(
            f"⚠️ **Alerta de Inflación**: La inflación proyectada ({pi_proj*100:.1f}%) supera la meta del "
            f"{target_pi*100:.1f}%. ¿Es momento de revisar la TPM hacia arriba para anclar las expectativas?"
        )
        alerts.append("Alta inflación proyectada")
    elif pi_proj > target_pi + 0.02:
        cb_msg.append(
            f"📊 **Inflación moderadamente elevada**: {pi_proj*100:.1f}%. "
            f"Tasa real: {tasa_real:.1f}%. ¿Necesita un ajuste preventivo?"
        )
    elif pi_proj < 0.0:
        cb_msg.append(
            f"📉 **Riesgo de Deflación**: Inflación negativa ({pi_proj*100:.1f}%). "
            f"¿Conviene recortar la tasa de política para estimular?"
        )
    else:
        cb_msg.append(
            f"✅ **Estabilidad Monetaria**: Inflación proyectada ({pi_proj*100:.1f}%) alineada con la meta central."
        )

    if regime in ("fixed", "crawling_peg") and R_proj < 10.0:
        cb_msg.append(
            f"🔴 **Peligro en Reservas**: Bajo régimen {regime}, las reservas proyectadas bajan a {R_proj:.1f} MUSD. "
            f"¿Es momento de considerar una transición cambiaria o subir tasas para atraer capitales?"
        )
        alerts.append("Reservas internacionales críticamente bajas")

    if tasa_real < 0.0 and pi_proj > 0.10:
        cb_msg.append(
            f"📌 **Tasa Real Negativa**: La tasa real es {tasa_real:.1f}%. "
            f"Esto alimenta expectativas inflacionarias y debilita la credibilidad."
        )

    cb_advice = " ".join(cb_msg)

    # ─── 2. 🏛️ MINISTERIO DE HACIENDA (Fiscal y Deuda) ───────────────────
    deficit_proj = dry_run_snapshot["deficit"]
    B_proj = dry_run_snapshot["B"]
    debt_ratio_proj = dry_run_snapshot["debt_to_gdp_nominal"]
    rating_proj = dry_run_snapshot["rating"]

    treasury_msg = []
    if deficit_proj > 5.0:
        treasury_msg.append(
            f"⚠️ **Déficit Fiscal Elevado**: {deficit_proj:.1f} MUSD. "
            f"¿Es posible mejorar la recaudación (tc, tk, τ) o contener gasto corriente (Gc)?"
        )
    elif deficit_proj < -2.0:
        treasury_msg.append(
            f"💚 **Superávit Fiscal**: Generando superávit de {-deficit_proj:.1f} MUSD. "
            f"¿Es hora de redirigir recursos a inversión productiva (Ig)?"
        )
    else:
        treasury_msg.append(f"📊 **Balance Fiscal Manejable**: Déficit de {deficit_proj:.1f} MUSD.")

    if debt_ratio_proj > 0.60:
        treasury_msg.append(
            f"🔴 **Deuda Crítica**: Ratio Deuda/PIB Nominal en {debt_ratio_proj*100:.1f}%. "
            f"Rating: **{rating_proj}**. ¿Es prioridad la consolidación fiscal?"
        )
        alerts.append(f"Ratio Deuda/PIB Nominal elevado ({debt_ratio_proj*100:.1f}%)")
    else:
        treasury_msg.append(f"Rating soberano: **{rating_proj}** (Deuda/PIB Nominal = {debt_ratio_proj*100:.1f}%).")

    treasury_advice = " ".join(treasury_msg)

    # ─── 3. 🏭 MINISTERIO DE TRABAJO Y COMERCIO (Empleo y Competitividad) ─
    U_proj = dry_run_snapshot["U"]
    gY_proj = dry_run_snapshot["gY"]
    gap_proj = dry_run_snapshot["gap"]
    q_proj = dry_run_snapshot["q_real"]

    labor_msg = []
    if U_proj > 0.10:
        labor_msg.append(
            f"⚠️ **Desempleo Alto**: Se proyecta {U_proj*100:.1f}%. "
            f"¿Se justifica un impulso fiscal vía Ig o un estímulo monetario?"
        )
        alerts.append(f"Alto desempleo proyectado ({U_proj*100:.1f}%)")
    elif U_proj > 0.07:
        labor_msg.append(f"📊 Desempleo moderado: {U_proj*100:.1f}%. El mercado laboral muestra holgura.")
    else:
        labor_msg.append(f"✅ **Empleo Saludable**: Desempleo proyectado en {U_proj*100:.1f}%.")

    if gY_proj < -0.02:
        labor_msg.append(
            f"📉 **Recesión Proyectada**: Contracción del {gY_proj*100:.1f}%. Brecha: {gap_proj*100:.1f}%."
        )
        alerts.append("Contracción económica proyectada")
    elif gY_proj > 0.04:
        labor_msg.append(f"🚀 **Expansión Sólida**: Crecimiento del +{gY_proj*100:.1f}%.")
    else:
        labor_msg.append(f"📈 Crecimiento del PIB moderado (+{gY_proj*100:.1f}%).")

    if q_proj < 0.85:
        labor_msg.append(
            f"💱 **Moneda Sobrevaluada**: TCR = {q_proj:.2f}. "
            f"¿Se necesita una corrección cambiaria para recuperar competitividad exportadora?"
        )
    elif q_proj > 1.20:
        labor_msg.append(
            f"💱 **Alta Competitividad Cambiaria**: TCR = {q_proj:.2f}. "
            f"Favorable para exportaciones pero puede presionar costos importados."
        )

    labor_advice = " ".join(labor_msg)

    # ─── 4. RECOMENDACIÓN SALTER-SWAN ──────────────────────────────────────
    ss_advice = (
        f"**Zona Salter-Swan {ss_result['zone']}**: {ss_result['diagnosis']} "
        f"-> *Recomendación*: {ss_result['policy']}"
    )

    # ─── 5. RESUMEN GENERAL ───────────────────────────────────────────────
    score_curr = current_snapshot.get("score", 70.0)
    score_proj = dry_run_snapshot["score"]
    delta_score = score_proj - score_curr

    if delta_score > 2.0:
        summary_text = (
            f"🟢 **Evaluación Positiva**: El paquete de medidas proyecta aumentar la Percepción "
            f"Pública en +{delta_score:.1f} puntos (Score: {score_proj:.1f})."
        )
    elif delta_score < -2.0:
        summary_text = (
            f"🔴 **Evaluación Negativa**: El paquete de medidas deteriora la Percepción "
            f"Pública en {delta_score:.1f} puntos (Score: {score_proj:.1f})."
        )
    else:
        summary_text = (
            f"🟡 **Impacto Neutro**: Percepción Pública estable (Score proyectado: {score_proj:.1f})."
        )

    return {
        "central_bank": cb_advice,
        "treasury": treasury_advice,
        "labor_growth": labor_advice,
        "salter_swan": ss_advice,
        "overall_summary": summary_text,
        "projected_score": score_proj,
        "risk_alerts": alerts,
    }
