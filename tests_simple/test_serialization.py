"""
tests_simple/test_serialization.py
==================================
Pruebas de Serialización JSON (to_dict / from_dict) e Integración de UI.
Edición: The Economic War Room (V1.2 SIMPLE).

Verifica:
1. Reconstrucción con 100% fidelidad de StateManager desde un payload JSON.
2. Robustez de cálculos de interfaz de usuario y vistas previas.
"""

from __future__ import annotations

import copy
import json
import pytest

from engine_simple.state_manager import StateManager


def test_json_serialization_roundtrip():
    """5.4.1: Juega 3 turnos, exporta a JSON, deserializa y verifica igualdad total."""
    sm = StateManager("mexico_tequila")

    # Jugar turno 1
    pi1 = copy.deepcopy(sm.current_instruments)
    pi1["r_ref"] = 12.0
    pi1["Gc"] = 15.0
    sm.step_forward(pi1)

    # Jugar turno 2 con cambio de régimen
    sm.switch_regime("flexible")
    pi2 = copy.deepcopy(sm.current_instruments)
    pi2["r_ref"] = 14.0
    sm.step_forward(pi2)

    # Serializar a dict y a string JSON
    dict_payload = sm.to_dict()
    json_str = json.dumps(dict_payload)
    loaded_dict = json.loads(json_str)

    # Deserializar en una nueva instancia
    sm_restored = StateManager.from_dict(loaded_dict)

    # Verificaciones de atributos clave
    assert sm_restored.scenario_id == sm.scenario_id
    assert sm_restored.current_turn == sm.current_turn
    assert sm_restored.current_turn == 2
    assert sm_restored.B == sm.B
    assert sm_restored.R == sm.R
    assert sm_restored.Y_pot == sm.Y_pot
    assert sm_restored.pi_e == sm.pi_e
    assert sm_restored.is_game_over == sm.is_game_over
    assert sm_restored.current_instruments["regime"] == sm.current_instruments["regime"]

    # Verificar que el historial completo coincide snapshot a snapshot
    assert len(sm_restored.history) == len(sm.history)
    for s_orig, s_rest in zip(sm.history, sm_restored.history):
        assert s_orig["t"] == s_rest["t"]
        assert s_orig["Y"] == s_rest["Y"]
        assert s_orig["pi"] == s_rest["pi"]
        assert s_orig["score"] == s_rest["score"]
        assert s_orig["debt_to_gdp_nominal"] == s_rest["debt_to_gdp_nominal"]


def test_ui_advice_and_dry_run_integration():
    """5.4.2: Verifica que get_dry_run_projection y get_cabinet_advice funcionen sin fallas."""
    sm = StateManager("chile_rule")

    pi = copy.deepcopy(sm.current_instruments)
    pi["Gc"] = 13.0
    pi["Ig"] = 8.0
    pi["r_ref"] = 5.5

    # Proyección en tiempo real (Live Dry-Run)
    dry_snap = sm.get_dry_run_projection(pi)
    assert dry_snap["t"] == 1
    assert dry_snap["Y"] > 0
    assert abs(dry_snap["Y"] - (dry_snap["C"] + dry_snap["I_priv"] + dry_snap["G"] + dry_snap["NX"])) < 1e-12

    # Asesoría didáctica del Gabinete
    advice = sm.get_cabinet_advice(pi)
    assert "central_bank" in advice
    assert "treasury" in advice
    assert "labor_growth" in advice
    assert "salter_swan" in advice
    assert len(advice["central_bank"]) > 10

