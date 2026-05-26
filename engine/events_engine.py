"""
engine/events_engine.py
=======================
Motor de eventos endógenos y exógenos (Fase 3).

Responsabilidades:
  - Evaluar condiciones endógenas (triggers reactivos) en cada turno.
  - Generar y samplear eventos exógenos de forma reproducible usando semillas hashes.
  - Aplicar modificaciones (deltas) a los parámetros estructurales o al estado global.
  - Retornar la lista de eventos disparados para persistencia.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any, TypedDict
from engine.game_state import GameState, NewsItem


class GameEvent(TypedDict):
    """
    Estructura de un evento de juego.

    Campos
    ------
    event_id:      ID único del evento
    type:          "endogenous" | "exogenous"
    headline:      Título del periódico en mayúsculas
    narrative:     Texto inmersivo de 2-3 oraciones
    impact_text:   Descripción resumida del impacto en negrita
    param_deltas:  Modificaciones a aplicar en StructuralParams o GameState
    prob:          Probabilidad base (solo para exógenos, 0.0 para endógenos)
    triggered_at:  Turno en que se disparó (t_new)
    """
    event_id:      str
    type:          str
    headline:      str
    narrative:     str
    impact_text:   str
    param_deltas:  dict[str, Any]
    prob:          float
    triggered_at:  int


# ─────────────────────────────────────────────────────────────────────────────
# PRESETS DE EVENTOS EXÓGENOS
# ─────────────────────────────────────────────────────────────────────────────

EXOGENOUS_EVENTS_DEFS = {
    "commodity_supercycle": {
        "headline": "📈 SUPERVENDEDORES: BOOM EN COMMODITIES",
        "narrative": "Un aumento drástico en la demanda global de materias primas dispara los precios de nuestras exportaciones. Los términos de intercambio mejoran de forma sin precedentes.",
        "impact_text": "Las exportaciones netas autónomas aumentan en 20 y el nivel de precios externos sube un 10%.",
        "param_deltas": {"NX0": 20.0, "P_star": 1.10},  # NX0 += 20, P_star *= 1.10 (se maneja en aplicación)
        "prob": 0.10,
    },
    "fed_rate_shock": {
        "headline": "🏦 LA FED ELEVA TASAS DE INTERÉS BRUSCAMENTE",
        "narrative": "La Reserva Federal de EE. UU. endurece su política monetaria para combatir la inflación doméstica. Los mercados internacionales experimentan un severo drenaje de liquidez.",
        "impact_text": "La tasa de interés de referencia internacional (r_star) aumenta en 400 puntos básicos (+4.0 puntos porcentuales).",
        "param_deltas": {"r_star": 4.0},  # r_star += 4.0
        "prob": 0.15,
    },
    "global_recession": {
        "headline": "📉 RECESIÓN GLOBAL EN PUERTA: SE RETRAE LA DEMANDA",
        "narrative": "Una desaceleración económica en las grandes potencias mundiales reduce la demanda externa. Las ventas al extranjero sufren una fuerte contracción y la elasticidad cae.",
        "impact_text": "Las exportaciones netas autónomas caen en 15 y la elasticidad-precio de exportaciones cae un 20%.",
        "param_deltas": {"NX0": -15.0, "epsilon_x": 0.80},  # NX0 -= 15, epsilon_x *= 0.80
        "prob": 0.08,
    },
    "tech_productivity": {
        "headline": "💻 BOOM DE PRODUCTIVIDAD: REVOLUCIÓN TECNOLÓGICA",
        "narrative": "La adopción masiva de nuevas herramientas informáticas y de inteligencia artificial optimiza procesos productivos de forma generalizada en el país.",
        "impact_text": "La tasa de crecimiento potencial anual del PIB aumenta un 1% (+0.01) de forma permanente.",
        "param_deltas": {"g_pot": 0.01},  # g_pot += 0.01
        "prob": 0.05,
    },
    "natural_disaster": {
        "headline": "🚨 SEVERO DESASTRE NATURAL AZOTA LA CAPITAL",
        "narrative": "Un evento climático imprevisto daña severamente infraestructuras clave y redes logísticas nacionales. Se requiere gasto inmediato de reconstrucción.",
        "impact_text": "El PIB potencial cae un 10% por destrucción de capital y se requiere un gasto público forzoso de reconstrucción de 5.0 MM.",
        "param_deltas": {"Y_pot": 0.90, "G_needed": 5.0},  # Y_pot *= 0.90, G_needed += 5.0
        "prob": 0.05,
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# EVALUACIÓN DE EVENTOS
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_events(state: GameState, seed_int: int) -> list[GameEvent]:
    """
    Evalúa eventos endógenos (triggers) y samplea eventos exógenos (probabilísticos).

    Parameters
    ----------
    state    : GameState actual (history[-1] contiene la snapshot del turno actual)
    seed_int : Semilla entera reproducible para el sampleo de Bernoulli

    Returns
    -------
    list[GameEvent] : Lista de eventos disparados este turno.
    """
    triggered: list[GameEvent] = []
    history = state["history"]
    if not history:
        return triggered

    current_snap = history[-1]
    t_new = current_snap["t"]  # Turno que se acaba de jugar (1–10)

    # 1. EVALUAR TRIGGERS ENDÓGENOS
    active_prev = state.get("active_events", [])

    # ID: social_unrest
    # Trigger: U > 0.12
    if current_snap["U"] > 0.12 and "social_unrest" not in active_prev:
        triggered.append(GameEvent(
            event_id="social_unrest",
            type="endogenous",
            headline="💥 GRAVES DISTURBIOS SOCIALES POR DESEMPLEO",
            narrative="La persistente falta de empleo ha desatado protestas masivas en las principales ciudades del país. La alta conflictividad social paraliza sectores clave y reduce la confianza de las familias.",
            impact_text="El PIB potencial cae un 5% por la paralización de capital y la propensión marginal a consumir disminuye en 0.05.",
            param_deltas={"Y_pot": 0.95, "c1": -0.05},
            prob=0.0,
            triggered_at=t_new
        ))

    # ID: bank_panic
    # Trigger: R / (Y * P_local) < 0.05
    # Nota: R es reservas y (Y * P_local) es el PIB nominal.
    nominal_gdp = current_snap["Y"] * current_snap["P_local"]
    reserves_gdp_ratio = current_snap["R"] / max(nominal_gdp, 1e-6)
    if reserves_gdp_ratio < 0.05 and "bank_panic" not in active_prev:
        triggered.append(GameEvent(
            event_id="bank_panic",
            type="endogenous",
            headline="🏦 PÁNICO BANCARIO: CORRIDA CONTRA EL PESO",
            narrative="Las escasas reservas internacionales desatan rumores de devaluación y corralito. Los ahorristas acuden masivamente a retirar depósitos de los bancos comerciales y demandar dólares.",
            impact_text="Las expectativas de devaluación (delta_E_expected) aumentan al 20% para el próximo período, elevando la prima cambiaria.",
            param_deltas={"delta_E_expected": 0.20},
            prob=0.0,
            triggered_at=t_new
        ))

    # ID: stagflation_trap
    # Trigger: gY < 0.01 AND pi > 0.10
    if current_snap["gY"] < 0.01 and current_snap["pi"] > 0.10 and "stagflation_trap" not in active_prev:
        triggered.append(GameEvent(
            event_id="stagflation_trap",
            type="endogenous",
            headline="📈 TRAMPA DE ESTANFLACIÓN: ESTANCAMIENTO E INERCIA",
            narrative="La coexistencia de nulo crecimiento con inflación alta consolida conductas defensivas en los formadores de precios. La inflación inercial se arraiga en la economía.",
            impact_text="La inflación base permanente (pi_0) aumenta un 5% (+0.05) estructuralmente.",
            param_deltas={"pi_0": 0.05},
            prob=0.0,
            triggered_at=t_new
        ))

    # ID: virtuous_circle
    # Trigger: 3 turnos consecutivos con gY > 0.04 AND deficit/Y < 0.02
    # El evaluador debe consultar el historial (los últimos 3snapshots, incluyendo el actual).
    if len(history) >= 3:
        consecutive = True
        for i in range(1, 4):
            snap = history[-i]
            # Turno 0 es calibración, no tiene gY relevante o se excluye
            if snap["t"] == 0:
                consecutive = False
                break
            # deficit / Y
            gY_ok = snap["gY"] > 0.04
            deficit_pct_ok = (snap["deficit"] / max(snap["Y"], 1e-6)) < 0.02
            if not (gY_ok and deficit_pct_ok):
                consecutive = False
                break
        if consecutive and "virtuous_circle" not in active_prev:
            triggered.append(GameEvent(
                event_id="virtuous_circle",
                type="endogenous",
                headline="🌟 CÍRCULO VIRTUOSO: CONFÍAN LOS MERCADOS",
                narrative="Tres meses consecutivos de alto crecimiento y sólido control fiscal despiertan un fuerte optimismo inversor. La prima de riesgo soberana cae y se estimula la inversión privada.",
                impact_text="La sensibilidad de la inversión a la tasa de interés (b) se reduce en 0.5 de forma favorable (menor crowding-out por tasas).",
                param_deltas={"b": 0.5},  # b += 0.5 en confianza inversora (mayor inversión para tasas dadas)
                prob=0.0,
                triggered_at=t_new
            ))

    # 2. EVALUAR EVENTOS EXÓGENOS ALEATORIOS
    # Inicializar randomizador con el seed reproducible
    prng = random.Random(seed_int)

    # Multiplicador de dificultad: 1.5x en modo "hard"
    prob_mult = 1.5 if state.get("difficulty", "easy") == "hard" else 1.0

    for ev_id, ev_def in EXOGENOUS_EVENTS_DEFS.items():
        # Evitar disparar el mismo evento exógeno dos veces seguidas o si ya está activo
        if ev_id in active_prev:
            continue

        base_prob = ev_def["prob"]
        adjusted_prob = min(0.95, base_prob * prob_mult)

        # Muestreo de Bernoulli
        if prng.random() < adjusted_prob:
            triggered.append(GameEvent(
                event_id=ev_id,
                type="exogenous",
                headline=ev_def["headline"],
                narrative=ev_def["narrative"],
                impact_text=ev_def["impact_text"],
                param_deltas=ev_def["param_deltas"],
                prob=base_prob,
                triggered_at=t_new
            ))

    return triggered


# ─────────────────────────────────────────────────────────────────────────────
# APLICACIÓN DE IMPACTO
# ─────────────────────────────────────────────────────────────────────────────

def apply_event_deltas(state: GameState, event: GameEvent) -> None:
    """
    Aplica las modificaciones físicas de un evento al GameState y a sus StructuralParams.

    Parameters
    ----------
    state : GameState mutable a actualizar
    event : GameEvent disparado a aplicar
    """
    sp = state["structural"]
    deltas = event["param_deltas"]

    # Registrar el evento en el listado de activos y news_feed
    state["active_events"].append(event["event_id"])

    # Añadir a news_feed
    severity = "critical" if event["type"] == "endogenous" or event["event_id"] in ("natural_disaster", "fed_rate_shock") else "warning"
    state["news_feed"].append(NewsItem(
        t=event["triggered_at"],
        category="event",
        message=f"{event['headline']}: {event['narrative']}",
        severity=severity
    ))

    # Aplicar deltas específicos
    for key, val in deltas.items():
        if key == "Y_pot":
            # Multiplicativo (e.g. Y_pot *= 0.95 o *= 0.90)
            state["Y_pot"] *= val
        elif key == "delta_E_expected":
            # Directo
            state["delta_E_expected"] = val
        elif key == "c1":
            # Aditivo
            sp["c1"] = round(max(0.1, sp["c1"] + val), 4)
        elif key == "pi_0":
            # Aditivo
            sp["pi_0"] = round(sp["pi_0"] + val, 4)
        elif key == "b":
            # Aditivo (virtuous_circle: b aumenta confianza, reduce costo de tasa)
            # En virtuous_circle: b += 0.5 (sensibilidad inversión a la tasa sube)
            sp["b"] = round(max(0.1, sp["b"] + val), 4)
        elif key == "NX0":
            # Aditivo
            sp["NX0"] = round(sp["NX0"] + val, 4)
        elif key == "P_star":
            # Multiplicativo (commodity_supercycle: P_star *= 1.10)
            sp["P_star"] = round(sp["P_star"] * val, 4)
        elif key == "r_star":
            # Aditivo (fed_rate_shock: r_star += 4.0)
            # Nota: r_star vive en PolicyInstruments y opcionalmente en StructuralParams
            if "r_star" in sp:
                sp["r_star"] = round(sp["r_star"] + val, 4)
            if "r_star" in state["policy"]:
                state["policy"]["r_star"] = round(state["policy"]["r_star"] + val, 4)
        elif key == "epsilon_x":
            # Multiplicativo (global_recession: epsilon_x *= 0.80)
            sp["epsilon_x"] = round(max(0.1, sp["epsilon_x"] * val), 4)
        elif key == "g_pot":
            # Aditivo
            sp["g_pot"] = round(sp["g_pot"] + val, 4)
        elif key == "G_needed":
            # Aditivo
            sp["G_needed"] = round(sp["G_needed"] + val, 4)
