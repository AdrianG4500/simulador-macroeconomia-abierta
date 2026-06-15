"""
validation/test_phase3.py
==========================
Suite de verificación de la Fase 3: Eventos, Onboarding y Gabinete de Asesores.

Para ejecutar:
    python -m pytest validation/test_phase3.py -v --tb=short
"""

from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en el path
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pytest
from engine.state_manager_v2 import SimStateManagerV2
from engine.events_engine import evaluate_events, apply_event_deltas
from engine.advisor_system import generate_advisor_warnings


# =============================================================================
# TEST 1: TRIGGERS ENDÓGENOS REACTIVOS
# =============================================================================

def test_events_endogenous_triggers():
    """
    Verifica que las condiciones endógenas se disparan correctamente.
    """
    mgr = SimStateManagerV2()
    # Calibrar en un escenario saludable
    mgr.calibrate("Economia_Saludable")
    state = mgr.state
    
    # Simular una snapshot para t=1 con U > 12% para disparar social_unrest
    provisional_snap = {
        "t": 1, "Y": 100.0, "r": 5.0, "E": 10.0, "M": 40.0, "NX": 0.0,
        "C": 70.0, "I_inv": 15.0, "G": 20.0, "recaudacion": 20.0, "deficit": 0.0,
        "B": 60.0, "R": 50.0, "pi": 0.02, "pi_e": 0.03,
        "U": 0.13,  # U > 12% desata disturbios sociales
        "gap": 0.0, "gY": 0.0, "q_real": 1.0, "A_domestic": 100.0, "P_local": 1.0,
        "zone_ss": "II", "score": 80, "mult": 1.8, "policy_applied": {},
        "events_triggered": []
    }
    state["history"].append(provisional_snap)
    
    # Evaluar eventos con un seed
    events = evaluate_events(state, 12345)
    event_ids = [e["event_id"] for e in events]
    
    assert "social_unrest" in event_ids, "social_unrest debería haberse disparado debido a U > 12%"
    
    # Aplicar social_unrest
    social_ev = [e for e in events if e["event_id"] == "social_unrest"][0]
    Y_pot_before = state["Y_pot"]
    c1_before = state["structural"]["c1"]
    
    apply_event_deltas(state, social_ev)
    
    assert state["Y_pot"] == Y_pot_before * 0.97, "PIB potencial debería haberse reducido en un 3%"
    assert state["structural"]["c1"] == pytest.approx(c1_before - 0.02), "Propensión c1 debería haber disminuido en 0.02"
    assert "social_unrest" in state["active_events"], "social_unrest debe figurar en active_events"
    assert any("disturbios" in item["message"].lower() for item in state["news_feed"]), "Debe haber una noticia en el feed"


def test_bank_panic_trigger():
    """
    Verifica que bank_panic se dispara cuando R / (Y * P_local) < 5%.
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("Economia_Saludable")
    state = mgr.state
    
    # Simular una snapshot con reservas extremadamente bajas en relación al PIB nominal
    provisional_snap = {
        "t": 1, "Y": 100.0, "r": 5.0, "E": 10.0, "M": 40.0, "NX": 0.0,
        "C": 70.0, "I_inv": 15.0, "G": 20.0, "recaudacion": 20.0, "deficit": 0.0,
        "B": 60.0,
        "R": 2.0,  # Reservas muy bajas (2 / 100 = 2% < 5%)
        "pi": 0.02, "pi_e": 0.03, "U": 0.05,
        "gap": 0.0, "gY": 0.0, "q_real": 1.0, "A_domestic": 100.0, "P_local": 1.0,
        "zone_ss": "II", "score": 80, "mult": 1.8, "policy_applied": {},
        "events_triggered": []
    }
    state["history"].append(provisional_snap)
    
    events = evaluate_events(state, 12345)
    event_ids = [e["event_id"] for e in events]
    
    assert "bank_panic" in event_ids, "bank_panic debería dispararse con R/PIB_nominal < 5%"
    
    # Aplicar delta
    panic_ev = [e for e in events if e["event_id"] == "bank_panic"][0]
    apply_event_deltas(state, panic_ev)
    assert state["delta_E_expected"] == 0.05, "Expectativas de devaluación debieron dispararse a 5%"


def test_stagflation_trap_trigger():
    """
    Verifica que la trampa de estanflación se dispara cuando gY < 1% y pi > 10%.
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("Economia_Saludable")
    state = mgr.state
    
    provisional_snap = {
        "t": 1, "Y": 100.0, "r": 5.0, "E": 10.0, "M": 40.0, "NX": 0.0,
        "C": 70.0, "I_inv": 15.0, "G": 20.0, "recaudacion": 20.0, "deficit": 0.0,
        "B": 60.0, "R": 50.0,
        "pi": 0.12,  # pi > 10%
        "pi_e": 0.03, "U": 0.05, "gap": 0.0,
        "gY": -0.02, # gY < 1% (recesión)
        "q_real": 1.0, "A_domestic": 100.0, "P_local": 1.0,
        "zone_ss": "II", "score": 80, "mult": 1.8, "policy_applied": {},
        "events_triggered": []
    }
    state["history"].append(provisional_snap)
    
    events = evaluate_events(state, 12345)
    event_ids = [e["event_id"] for e in events]
    
    assert "stagflation_trap" in event_ids, "stagflation_trap debe dispararse con recesión e inflación alta"
    
    # Aplicar deltas
    trap_ev = [e for e in events if e["event_id"] == "stagflation_trap"][0]
    apply_event_deltas(state, trap_ev)
    assert state["structural"]["pi_0"] == 0.05, "Debe sumarse 0.05 a la inflación estructural pi_0"


# =============================================================================
# TEST 2: REPRODUCIBILIDAD DE SEMILLAS HASH
# =============================================================================

def test_events_reproducibility():
    """
    Verifica que evaluar eventos exógenos con el mismo seed da exactamente el mismo resultado,
    garantizando consistencia analítica.
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("Economia_Saludable")
    state = mgr.state
    
    # Simular un snapshot
    provisional_snap = {
        "t": 1, "Y": 100.0, "r": 5.0, "E": 10.0, "M": 40.0, "NX": 0.0,
        "C": 70.0, "I_inv": 15.0, "G": 20.0, "recaudacion": 20.0, "deficit": 0.0,
        "B": 60.0, "R": 50.0, "pi": 0.02, "pi_e": 0.03, "U": 0.05,
        "gap": 0.0, "gY": 0.0, "q_real": 1.0, "A_domestic": 100.0, "P_local": 1.0,
        "zone_ss": "II", "score": 80, "mult": 1.8, "policy_applied": {},
        "events_triggered": []
    }
    state["history"].append(provisional_snap)
    
    # Correr dos evaluaciones con la misma semilla
    events1 = evaluate_events(state, 55555)
    events2 = evaluate_events(state, 55555)
    
    ids1 = [e["event_id"] for e in events1]
    ids2 = [e["event_id"] for e in events2]
    
    assert ids1 == ids2, f"Los eventos deben ser idénticos para semillas idénticas. ids1={ids1}, ids2={ids2}"
    
    # Con otra semilla, el resultado puede o no diferir (aleatorio), pero al menos la reproducibilidad está garantizada


# =============================================================================
# TEST 3: PROYECCIONES PREVENTIVAS DEL GABINETE
# =============================================================================

def test_advisor_dry_run():
    """
    Verifica que las alertas preventivas del gabinete se disparen antes de que
    el jugador experimente la crisis cambiaria o de deuda.
    """
    mgr = SimStateManagerV2()

    # 1. Alerta de Reservas
    mgr.calibrate("Economia_Saludable")
    mgr.start_simulation("fixed")
    mgr.step_forward({"G": 20.0}) # Avanza a t=1

    # Forzar reservas bajas post-step para proyectar crisis en t=2 sin disparar el circuit breaker en t=1
    mgr.state["R"] = 4.0
    mgr.state["regime"] = "fixed"
    mgr.state["policy"]["regime"] = "fixed"

    warnings = generate_advisor_warnings(mgr.state)
    warning_advisors = [w["advisor"] for w in warnings]

    # Como las reservas son 4.0 y la balanza NX es deficitaria, la proyección t=2 las llevará por debajo de 0
    assert "Banco Central" in warning_advisors, "El Banco Central debería alertar de reservas críticas"
    assert any("reservas" in w["message"].lower() for w in warnings if w["advisor"] == "Banco Central")
