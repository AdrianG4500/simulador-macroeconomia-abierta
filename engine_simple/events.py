"""
engine_simple/events.py
========================
Motor de eventos históricos programados y endógenos.
Edición: The Economic War Room (V1.2 SIMPLE).

Principios:
- Funciones PURAS para aplicar y revertir deltas sobre copias de parámetros/instrumentos.
- Eventos exógenos programados por escenario (vinculados a scheduled_events en scenarios.py).
- Eventos endógenos gatillados por condiciones del estado.
- Duraciones definidas en turnos y reversión limpia sin mutar objetos originales.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

from config_simple.parameters import PolicyInstruments, StructuralParams, TurnSnapshot

EventType = Literal["exogenous", "endogenous"]


class Event(TypedDict):
    """Estructura de definición de un evento macroeconómico."""
    id: str
    name: str
    description: str
    category: EventType
    duration: int
    param_deltas: Dict[str, float]
    policy_deltas: Dict[str, float]


class ActiveEvent(TypedDict):
    """Representación de un evento activo en el estado del juego."""
    event: Event
    turns_remaining: int


# ─────────────────────────────────────────────────────────────────────────────
# CATÁLOGO DE EVENTOS PREDEFINIDOS (Genéricos + Históricos Vinculados)
# ─────────────────────────────────────────────────────────────────────────────

PREDEFINED_EVENTS: Dict[str, Event] = {
    # ── Eventos genéricos ──
    "commodity_boom": {
        "id": "commodity_boom",
        "name": "Boom de Materias Primas",
        "description": "Alza extraordinaria de precios internacionales impulsa exportaciones (+5.0 en x0).",
        "category": "exogenous",
        "duration": 3,
        "param_deltas": {"x0": 5.0},
        "policy_deltas": {},
    },
    "global_recession": {
        "id": "global_recession",
        "name": "Recesión Global",
        "description": "Contracción mundial reduce la demanda de exportaciones (-6.0 en x0).",
        "category": "exogenous",
        "duration": 2,
        "param_deltas": {"x0": -6.0},
        "policy_deltas": {},
    },

    # ── Corea T3 ──
    "fed_hike_kor": {
        "id": "fed_hike_kor",
        "name": "Shock de Tasas Internacionales y Fricción Comercial",
        "description": "La Reserva Federal sube tasas (+1.5%) encareciendo el crédito externo y tensionando la balanza de capitales.",
        "category": "exogenous",
        "duration": 3,
        "param_deltas": {},
        "policy_deltas": {"r_star": 1.5},
    },

    # ── Chile T3 y T6 ──
    "global_slowdown_chl": {
        "id": "global_slowdown_chl",
        "name": "Desaceleración Comercial Global",
        "description": "Recesión en socios comerciales deprime la demanda externa de exportaciones (-4.0).",
        "category": "exogenous",
        "duration": 3,
        "param_deltas": {"x0": -4.0},
        "policy_deltas": {},
    },
    "copper_supercycle_chl": {
        "id": "copper_supercycle_chl",
        "name": "Superciclo de Commodities / Boom del Cobre",
        "description": "Salto en cotizaciones internacionales impulsa exportaciones (+8.0).",
        "category": "exogenous",
        "duration": 4,
        "param_deltas": {"x0": 8.0},
        "policy_deltas": {},
    },

    # ── México T1 ──
    "capital_flight_mex": {
        "id": "capital_flight_mex",
        "name": "Efecto Tequila: Ataque Especulativo y Fuga de Capitales",
        "description": "Inversionistas huyen hacia dólares. La Fed sube tasas (+2.5%) y la prima de riesgo se dispara (+3.0 pp).",
        "category": "exogenous",
        "duration": 3,
        "param_deltas": {},
        "policy_deltas": {"r_star": 2.5},
    },

    # ── Bolivia T1 ──
    "seigniorage_shock_bol": {
        "id": "seigniorage_shock_bol",
        "name": "Espiral Inflacionaria y Colapso de Recaudación",
        "description": "El rezago Olivera-Tanzi desintegra la recaudación real, obligando al fisco a monetizar el déficit.",
        "category": "exogenous",
        "duration": 3,
        "param_deltas": {},
        "policy_deltas": {},
    },

    # ── Eventos endógenos ──
    "social_unrest": {
        "id": "social_unrest",
        "name": "Estallido Social / Presión de Empleo",
        "description": "Desempleo crítico (>15%) desencadena protestas masivas, elevando el gasto público de emergencia.",
        "category": "endogenous",
        "duration": 2,
        "param_deltas": {},
        "policy_deltas": {"G_needed": 3.0},
    },
    "virtuous_circle": {
        "id": "virtuous_circle",
        "name": "Círculo Virtuoso de Confianza",
        "description": "Tres turnos de alto crecimiento (>4%) elevan la confianza inversionista (+2.0 en I0).",
        "category": "endogenous",
        "duration": 2,
        "param_deltas": {"I0": 2.0},
        "policy_deltas": {},
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES AUXILIARES PURAS
# ─────────────────────────────────────────────────────────────────────────────

def get_event_by_id(event_id: str) -> Event:
    """Obtiene una copia profunda de un evento predefinido por su ID."""
    if event_id not in PREDEFINED_EVENTS:
        raise ValueError(f"Evento desconocido: {event_id}. Eventos válidos: {list(PREDEFINED_EVENTS.keys())}")
    return copy.deepcopy(PREDEFINED_EVENTS[event_id])


def create_event_from_scenario(scheduled: Dict[str, Any]) -> Event:
    """
    Crea un Event a partir de la definición scheduled_events de scenarios.py.
    Si el evento existe en el catálogo predefinido, lo usa como base y aplica deltas adicionales.
    """
    event_id = scheduled["id"]

    if event_id in PREDEFINED_EVENTS:
        event = copy.deepcopy(PREDEFINED_EVENTS[event_id])
    else:
        event = Event(
            id=event_id,
            name=scheduled.get("title", event_id),
            description=scheduled.get("description", ""),
            category="exogenous",
            duration=scheduled.get("duration", 3),
            param_deltas={},
            policy_deltas={},
        )

    # Aplicar deltas declarados en el escenario
    if "deltas" in scheduled:
        for key, val in scheduled["deltas"].items():
            if key in ("r_star", "G_needed", "crawl_rate"):
                event["policy_deltas"][key] = event["policy_deltas"].get(key, 0.0) + float(val)
            else:
                event["param_deltas"][key] = event["param_deltas"].get(key, 0.0) + float(val)

    if "title" in scheduled:
        event["name"] = scheduled["title"]
    if "description" in scheduled:
        event["description"] = scheduled["description"]

    return event


def evaluate_endogenous_events(
    last_snapshot: Optional[TurnSnapshot],
    consecutive_high_growth_turns: int,
    active_event_ids: List[str],
) -> List[Event]:
    """
    Evalúa si se cumplen las condiciones para gatillar eventos endógenos.

    Condiciones:
    - social_unrest: U > 15% (0.15) en el último turno.
    - virtuous_circle: consecutive_high_growth_turns >= 3.
    """
    triggered: List[Event] = []

    if last_snapshot is not None:
        if last_snapshot["U"] > 0.15 and "social_unrest" not in active_event_ids:
            triggered.append(get_event_by_id("social_unrest"))

    if consecutive_high_growth_turns >= 3 and "virtuous_circle" not in active_event_ids:
        triggered.append(get_event_by_id("virtuous_circle"))

    return triggered


def apply_event_deltas(
    params: StructuralParams,
    instruments: PolicyInstruments,
    event: Event,
) -> Tuple[StructuralParams, PolicyInstruments]:
    """
    Aplica los deltas de un evento sobre copias de StructuralParams y PolicyInstruments.
    Función pura: no modifica los diccionarios de entrada.
    """
    p_new: StructuralParams = copy.deepcopy(params)
    inst_new: PolicyInstruments = copy.deepcopy(instruments)

    for key, val in event["param_deltas"].items():
        if key in p_new:
            p_new[key] = float(p_new[key]) + float(val)  # type: ignore

    for key, val in event["policy_deltas"].items():
        if key in inst_new:
            inst_new[key] = float(inst_new[key]) + float(val)  # type: ignore

    return p_new, inst_new


def revert_event_deltas(
    params: StructuralParams,
    instruments: PolicyInstruments,
    event: Event,
) -> Tuple[StructuralParams, PolicyInstruments]:
    """
    Revierte los deltas de un evento expirado.
    Función pura: no modifica los diccionarios de entrada.
    """
    p_new: StructuralParams = copy.deepcopy(params)
    inst_new: PolicyInstruments = copy.deepcopy(instruments)

    for key, val in event["param_deltas"].items():
        if key in p_new:
            p_new[key] = float(p_new[key]) - float(val)  # type: ignore

    for key, val in event["policy_deltas"].items():
        if key in inst_new:
            inst_new[key] = float(inst_new[key]) - float(val)  # type: ignore

    return p_new, inst_new


def tick_active_events(
    active_events: List[ActiveEvent],
    params: StructuralParams,
    instruments: PolicyInstruments,
) -> Tuple[List[ActiveEvent], List[Event], StructuralParams, PolicyInstruments]:
    """
    Avanza 1 turno el contador de duraciones de los eventos activos.
    Revierte y elimina los eventos cuya duración ha expirado.

    Returns
    -------
    (still_active, expired_events, updated_params, updated_instruments)
    """
    p_curr = copy.deepcopy(params)
    inst_curr = copy.deepcopy(instruments)
    still_active: List[ActiveEvent] = []
    expired_events: List[Event] = []

    for ae in active_events:
        rem = ae["turns_remaining"] - 1
        if rem <= 0:
            p_curr, inst_curr = revert_event_deltas(p_curr, inst_curr, ae["event"])
            expired_events.append(ae["event"])
        else:
            still_active.append({
                "event": ae["event"],
                "turns_remaining": rem,
            })

    return still_active, expired_events, p_curr, inst_curr
