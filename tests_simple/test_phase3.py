"""
tests_simple/test_phase3.py
============================
Suite de pruebas unitarias e integración para la Fase 3:
- Motor de Eventos (events.py)
- Sistema de Asesores y Dry-Run (advisor.py)
- Orquestador de Estado (state_manager.py)
- Verificación incondicional de identidad macroeconómica Y = C + I + G + NX en todos los turnos.
"""

from __future__ import annotations

import pytest
from config_simple.parameters import PolicyInstruments
from config_simple.scenarios import SCENARIOS
from engine_simple.advisor import generate_cabinet_advice, run_dry_run
from engine_simple.events import (
    apply_event_deltas,
    evaluate_endogenous_events,
    get_event_by_id,
    revert_event_deltas,
    tick_active_events,
)
from engine_simple.state_manager import StateManager


# ─────────────────────────────────────────────────────────────────────────────
# 1. PRUEBAS DEL MOTOR DE EVENTOS (events.py)
# ─────────────────────────────────────────────────────────────────────────────

def test_events_catalog_and_copies():
    """Verifica que los eventos predefinidos existan y retornen copias independientes."""
    event_ids = ["commodity_boom", "global_recession", "fed_hike_kor", "social_unrest", "virtuous_circle"]
    for eid in event_ids:
        ev1 = get_event_by_id(eid)
        ev2 = get_event_by_id(eid)
        assert ev1["id"] == eid
        assert ev1 is not ev2  # Copias independientes


def test_apply_and_revert_event_deltas():
    """Prueba la aplicación y reversión pura de deltas paramétricos."""
    sm = StateManager("chile_rule")
    p_orig = sm.current_params
    inst_orig = sm.current_instruments

    ev = get_event_by_id("commodity_boom")
    p_mod, inst_mod = apply_event_deltas(p_orig, inst_orig, ev)

    assert p_mod["x0"] == p_orig["x0"] + 5.0
    assert p_orig["x0"] == 18.0  # El original no mutó

    p_rev, inst_rev = revert_event_deltas(p_mod, inst_mod, ev)
    assert p_rev["x0"] == p_orig["x0"]


def test_tick_active_events_duration():
    """Prueba que la duración de los eventos disminuya y se revierta al expirar."""
    sm = StateManager("chile_rule")
    ev = get_event_by_id("fed_hike_kor")
    p_mod, inst_mod = apply_event_deltas(sm.current_params, sm.current_instruments, ev)

    active_events = [{"event": ev, "turns_remaining": 2}]

    # Turno 1 -> queda 1 turno
    active_events, expired, p_curr, inst_curr = tick_active_events(active_events, p_mod, inst_mod)
    assert len(active_events) == 1
    assert active_events[0]["turns_remaining"] == 1
    assert len(expired) == 0
    assert inst_curr["r_star"] == inst_mod["r_star"]

    # Turno 2 -> llega a 0 y se revierte
    active_events, expired, p_curr, inst_curr = tick_active_events(active_events, p_curr, inst_curr)
    assert len(active_events) == 0
    assert len(expired) == 1
    assert inst_curr["r_star"] == sm.current_instruments["r_star"]


def test_evaluate_endogenous_events():
    """Prueba el gatillado automático de eventos endógenos por desempleo o alto crecimiento."""
    sm = StateManager("chile_rule")

    # Caso 1: Sin condiciones
    evs = evaluate_endogenous_events(sm.history[-1], 0, [])
    assert len(evs) == 0

    # Caso 2: U > 15%
    high_u_snap = dict(sm.history[-1])
    high_u_snap["U"] = 0.16
    evs_u = evaluate_endogenous_events(high_u_snap, 0, [])
    assert len(evs_u) == 1
    assert evs_u[0]["id"] == "social_unrest"

    # Caso 3: 3 turnos de alto crecimiento
    evs_g = evaluate_endogenous_events(sm.history[-1], 3, [])
    assert len(evs_g) == 1
    assert evs_g[0]["id"] == "virtuous_circle"


# ─────────────────────────────────────────────────────────────────────────────
# 2. PRUEBAS DEL SISTEMA DE ASESORES (advisor.py)
# ─────────────────────────────────────────────────────────────────────────────

def test_dry_run_non_mutating():
    """Verifica que el Dry-Run no modifique el estado real de la simulación."""
    sm = StateManager("chile_rule")
    t0_snap = sm.history[-1]

    proposed = dict(sm.current_instruments)
    proposed["Gc"] = 20.0
    proposed["Ig"] = 10.0
    proposed["G"] = 30.0  # Gran aumento de gasto

    dry_snap = sm.get_dry_run_projection(proposed)

    assert dry_snap["G"] == 30.0
    assert dry_snap["t"] == 1

    # El estado real de StateManager sigue en t=0 y G=20.0
    assert sm.current_turn == 0
    assert sm.current_instruments["G"] == 20.0
    assert sm.history[-1]["G"] == t0_snap["G"]


def test_cabinet_advice_generation():
    """Verifica que se generen recomendaciones válidas para los 3 ministros y Salter-Swan."""
    sm = StateManager("chile_rule")
    proposed = dict(sm.current_instruments)

    advice = sm.get_cabinet_advice(proposed)

    assert "central_bank" in advice
    assert "treasury" in advice
    assert "labor_growth" in advice
    assert "salter_swan" in advice
    assert "overall_summary" in advice
    assert isinstance(advice["projected_score"], float)
    assert isinstance(advice["risk_alerts"], list)
    assert isinstance(advice["projected_score"], float)
    assert isinstance(advice["risk_alerts"], list)


# ─────────────────────────────────────────────────────────────────────────────
# 3. PRUEBAS DE INTEGRACIÓN DE STATEMANAGER (state_manager.py)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("scenario_id", list(SCENARIOS.keys()))
def test_statemanager_calibration_all_scenarios(scenario_id: str):
    """Verifica la calibración inicial t=0 para los 4 escenarios históricos."""
    sm = StateManager(scenario_id)
    assert sm.current_turn == 0
    assert len(sm.history) == 1

    snap = sm.history[0]

    # Identidad contable en t=0
    identity_error = abs(snap["Y"] - (snap["C"] + snap["I_inv"] + snap["G"] + snap["NX"]))
    assert identity_error < 1e-12, f"Fallo de identidad contable en t=0 ({scenario_id}): error={identity_error}"


@pytest.mark.parametrize("scenario_id", list(SCENARIOS.keys()))
def test_full_10_turn_gameplay_all_scenarios(scenario_id: str):
    """
    Simula una partida completa de 10 turnos en cada escenario,
    verificando la identidad contable Y = C + I + G + NX en CADA turno.
    """
    sm = StateManager(scenario_id)

    for turn in range(1, 11):
        if sm.is_game_over:
            break

        # Variar ligeramente instrumentos para probar dinámicas
        inst = dict(sm.current_instruments)
        if turn % 2 == 0:
            inst["Gc"] += 1.0
            inst["G"] = inst["Gc"] + inst["Ig"]
        else:
            inst["r_ref"] += 0.25

        snap = sm.step_forward(inst)

        # Garantía incondicional de identidad macroeconómica
        identity_error = abs(snap["Y"] - (snap["C"] + snap["I_inv"] + snap["G"] + snap["NX"]))
        assert identity_error < 1e-12, f"Fallo de identidad en turno {turn} ({scenario_id}): error={identity_error}"

    summary = sm.get_endgame_summary()
    assert summary["turns_played"] >= 1
    assert "avg_score" in summary


def test_exogenous_event_trigger_in_gameplay():
    """Verifica la activación manual de un evento exógeno durante la partida."""
    sm = StateManager("Economia_Saludable")
    sm.trigger_exogenous_event("commodity_boom")

    assert len(sm.active_events) == 1
    assert sm.active_events[0]["event"]["id"] == "commodity_boom"

    inst = dict(sm.current_instruments)
    snap1 = sm.step_forward(inst)

    # El boom de materias primas debió incrementar NX0 y mejorar el PIB o saldo externo
    assert snap1["Y"] > 0
    identity_error = abs(snap1["Y"] - (snap1["C"] + snap1["I_inv"] + snap1["G"] + snap1["NX"]))
    assert identity_error < 1e-12
