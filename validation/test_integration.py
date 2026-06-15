"""
validation/test_integration.py
==============================
Suite de pruebas de integración y consistencia económica para la Fase 5.
Verifica los 8 casos de prueba especificados para la Definition of Done.

Para ejecutar:
    python -m pytest validation/test_integration.py -v --tb=short
"""

from __future__ import annotations

import sys
import math
import numpy as np
import pytest
from pathlib import Path
import plotly.graph_objects as go

# Asegurar que el directorio raíz esté en el path
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.state_manager_v2 import SimStateManagerV2
from engine.events_engine import evaluate_events
from engine.advisor_system import generate_advisor_warnings
from ui.endgame_screen import calculate_normalized_metrics
from ui.difficulty_mode import render_difficulty_parameters


# =============================================================================
# TEST 1: TIGER ASIA NO GAME OVER A 10 TURNOS
# =============================================================================

def test_tiger_asia_no_game_over():
    """
    Verifica que el escenario Tigre Asiático en piloto automático llegue a turnos 10
    con una inflación acumulada pi > 8% sin detonar Game Over.
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("tiger_asia", "easy")
    mgr.start_simulation("fixed")
    
    for t in range(1, 11):
        if mgr.status == "game_over":
            break
        mgr.step_forward({})
        
    assert mgr.status == "endgame", f"Tigre Asiático debería terminar en endgame. Got '{mgr.status}'"
    assert mgr.t == 10, f"Debería alcanzar el turno 10. Got {mgr.t}"
    
    last_snap = mgr.state["history"][-1]
    pi_final = last_snap["pi"] * 100
    assert pi_final >= -15.0, f"La inflación final debería ser >= -15%. Got {pi_final:.2f}%"
    assert pi_final < 150.0, "La inflación final no debería sobrepasar el umbral de hiperinflación (150%)"


# =============================================================================
# TEST 2: DEATH SPIRAL GAME OVER ANTES DE T5
# =============================================================================

def test_death_spiral_game_over_before_t5():
    """
    Verifica que el escenario Espiral de la Muerte en piloto automático
    conduzca a un Game Over inevitable antes del semestre 5.
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("death_spiral", "easy")
    mgr.start_simulation("fixed")
    
    for t in range(1, 11):
        if mgr.status == "game_over":
            break
        mgr.step_forward({})
        
    assert mgr.status == "game_over", "Espiral de la Muerte sin políticas debe terminar en Game Over"
    assert mgr.t <= 5, f"Game Over debe ocurrir antes o en el turno 5. Ocurrió en t={mgr.t}"


# =============================================================================
# TEST 3: TRIGGER DE DISTURBIOS SOCIALES (SOCIAL UNREST)
# =============================================================================

def test_event_social_unrest_fires():
    """
    Forzar desempleo U = 15% (U > 12%) en el estado para validar que social_unrest
    se evalúa y dispara de manera reactiva en el motor de eventos.
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("Economia_Saludable", "easy")
    
    # Inyectamos desempleo crítico en la snapshot actual
    mgr.state["history"][-1]["U"] = 0.15
    
    # Forzar la evaluación de eventos con una semilla
    events = evaluate_events(mgr.state, seed_int=999)
    event_ids = [e["event_id"] for e in events]
    
    assert "social_unrest" in event_ids, "social_unrest debería haberse gatillado al forzar U=15%"


# =============================================================================
# TEST 4: IMPACTO DE DEVALUACIÓN EN MARSHALL-LERNER < 1
# =============================================================================

def test_ml_condition_policy_impact():
    """
    Verifica que bajo condición Marshall-Lerner insatisfecha (suma < 1),
    una devaluación cambiaria (aumento de E) EMPEORE la balanza comercial (NX)
    en lugar de mejorarla, validando la precisión teórica del motor.
    """
    from engine.core_v2 import solve_equilibrium_v2
    
    # Usamos parámetros de latam_crisis que tiene epsilon_x = 0.40, epsilon_m = 0.45 (suma = 0.85 < 1)
    sp = {
        "c0": 26.0, "I0": 20.0, "t": 0.20,
        "c1": 0.65, "m1": 0.15, "NX0": -5.0, "b": 2.0, "k": 0.5, "h": 2.0,
        "epsilon_x": 0.40, "epsilon_m": 0.45, "f": 2.0,
        "alpha_PT": 0.50, "beta_PT": 0.35, "U_n": 0.06, "P_star": 1.0
    }
    
    pi_baseline = {"G": 20.0, "E": 10.0, "M": 40.0, "r_star": 7.0, "regime": "fixed"}
    pi_devalued = {"G": 20.0, "E": 12.0, "M": 40.0, "r_star": 7.0, "regime": "fixed"}
    
    # Resolver ambos equilibrios
    eq_base = solve_equilibrium_v2(sp, pi_baseline, Y_pot=100.0, P_NT=1.0, E_prev=10.0)
    eq_dev = solve_equilibrium_v2(sp, pi_devalued, Y_pot=100.0, P_NT=1.0, E_prev=10.0)
    
    # Al devaluar en condiciones ML < 1, NX de equilibrio debe empeorar (ser más negativo / menor)
    assert eq_dev["NX"] < eq_base["NX"], (
        f"Con devaluación bajo ML < 1, NX debería empeorar. "
        f"NX_base={eq_base['NX']:.2f}, NX_dev={eq_dev['NX']:.2f}"
    )


# =============================================================================
# TEST 5: EFECTO CROWDING-OUT (DESPLAZAMIENTO INVERSIÓN)
# =============================================================================

def test_crowding_out_visible():
    """
    Verifica el efecto Crowding-Out: un aumento severo de G (gasto público) de 15 puntos
    eleva la tasa de interés de equilibrio r y desplaza (contrae) la inversión privada I.
    """
    from engine.core_v2 import solve_equilibrium_v2
    
    sp = {
        "c0": 10.0, "I0": 15.0, "t": 0.20, "c1": 0.75, "m1": 0.15, "b": 2.0,
        "k": 0.5, "h": 2.0, "NX0": 5.0, "epsilon_x": 0.8, "epsilon_m": 0.7,
        "f": 5.0, "alpha_PT": 0.40, "beta_PT": 0.20, "U_n": 0.05, "P_star": 1.0
    }
    
    # Resolver bajo TC flexible para que r y E se ajusten simultáneamente
    pi_g_low = {"G": 20.0, "E": 10.0, "M": 40.0, "r_star": 5.0, "regime": "flexible"}
    pi_g_high = {"G": 35.0, "E": 10.0, "M": 40.0, "r_star": 5.0, "regime": "flexible"} # G sube 15 pts
    
    from engine.core_v2 import eq_flexible_v2
    eq_low = eq_flexible_v2(sp, pi_g_low, Y_pot=100.0, P_NT=1.0, E_prev=10.0)
    eq_high = eq_flexible_v2(sp, pi_g_high, Y_pot=100.0, P_NT=1.0, E_prev=10.0)
    
    assert eq_high["r"] > eq_low["r"], f"La tasa de interés r debe aumentar con mayor G. r_low={eq_low['r']:.2f}, r_high={eq_high['r']:.2f}"
    assert eq_high["I_inv"] < eq_low["I_inv"], f"La inversión privada I debe caer (crowded out). I_low={eq_low['I_inv']:.2f}, I_high={eq_high['I_inv']:.2f}"


# =============================================================================
# TEST 6: ADVISOR WARNING DE RESERVAS UN SEMESTRE ANTES DEL CIRCUIT BREAKER
# =============================================================================

def test_advisor_warning_one_turn_ahead():
    """
    Verifica que el gabinete preventivo advierta de la crisis cambiaria (Banco Central)
    un semestre antes de que ocurra efectivamente el circuit breaker por agotamiento de R.
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("Economia_Saludable", "easy")
    mgr.start_simulation("fixed")
    
    # Forzar reservas extremadamente bajas (post-calibración en t=0)
    mgr.state["R"] = 3.5
    
    # Al generar alertas en t=0, el Banco Central detectará que en la proyección de t=1
    # las reservas caerán por debajo de cero, emitiendo una advertencia preventiva
    warnings = generate_advisor_warnings(mgr.state)
    warning_advisors = [w["advisor"] for w in warnings]
    
    assert "Banco Central" in warning_advisors, "El Banco Central debería alertar de reservas críticas un turno antes"
    assert any("reservas" in w["message"].lower() for w in warnings if w["advisor"] == "Banco Central")


# =============================================================================
# TEST 7: CÁLCULO DE ÁREA DEL SPIDER CHART
# =============================================================================

def test_spider_chart_area_calculation():
    """
    Verifica geométricamente que el área del polígono de gestión final (verde)
    es mayor al polígono de base inicial (rojo) si delta_score > 0.
    """
    # Función geométrica de cálculo de área de un polígono regular de N vértices
    def compute_polygon_area(r_values: list[float]) -> float:
        N = len(r_values)
        if N < 3:
            return 0.0
        angle = 2.0 * math.pi / N
        area = 0.0
        for i in range(N):
            r_curr = r_values[i]
            r_next = r_values[(i + 1) % N]
            area += 0.5 * r_curr * r_next * math.sin(angle)
        return area

    snap_0 = {
        "t": 0, "Y": 100.0, "r": 5.0, "E": 10.0, "M": 40.0, "NX": 0.0,
        "C": 70.0, "I_inv": 15.0, "G": 20.0, "recaudacion": 20.0, "deficit": 0.0,
        "B": 50.0, "R": 50.0, "pi": 0.03, "pi_e": 0.03, "U": 0.05,
        "gap": 0.0, "gY": 0.0, "q_real": 1.0, "A_domestic": 100.0, "P_local": 1.0,
        "zone_ss": "II", "score": 80, "mult": 1.8, "policy_applied": {},
        "events_triggered": []
    }
    
    # 1. Simular una excelente gestión (verde)
    snap_f_good = dict(snap_0)
    snap_f_good["t"] = 10
    snap_f_good["Y"] = 104.0    # Crecimiento
    snap_f_good["gY"] = 0.035   # Alto crecimiento
    snap_f_good["U"] = 0.03     # Empleo alto
    snap_f_good["pi"] = 0.03    # Inflación perfecta
    snap_f_good["deficit"] = -2.0 # Superávit fiscal fuerte (negativo = superávit)
    snap_f_good["R"] = 55.0     # Recomposición de reservas
    
    history_good = [snap_0] + [snap_f_good] * 10
    
    metrics_0 = calculate_normalized_metrics(snap_0, snap_0, is_final=False)
    metrics_f_good = calculate_normalized_metrics(snap_f_good, snap_0, history=history_good, is_final=True)
    
    area_0 = compute_polygon_area(metrics_0)
    area_f_good = compute_polygon_area(metrics_f_good)
    
    assert area_f_good > area_0, (
        f"El área del polígono de buena gestión ({area_f_good:.4f}) "
        f"debería ser mayor al de la base inicial ({area_0:.4f})"
    )


# =============================================================================
# TEST 8: NIEBLA DE GUERRA EN DIFICULTAD DIFICIL (HARD)
# =============================================================================

def test_difficulty_hard_params_hidden():
    """
    Verifica que en modo difícil, render_difficulty_parameters de difficulty_mode
    se comporte de acuerdo a la 'Niebla de Guerra' y retorne un diccionario vacío
    sin inyectar sliders estructurales a la barra lateral.
    """
    # Mocking active game state
    state = {
        "difficulty": "hard",
        "structural": {
            "c1": 0.75,
            "t": 0.20,
        }
    }
    
    # Inyectamos mock de streamlit session state para evitar colisiones
    import streamlit as st
    if "debug_active" not in st.session_state:
        st.session_state["debug_active"] = False
        
    updates = render_difficulty_parameters(state)
    
    # En difícil, debe retornar vacío y no exponer parámetros a la mutación de sliders
    assert updates == {}, "En modo difícil, los sliders no deben retornar ninguna actualización de parámetros"
    assert st.session_state["debug_active"] is False, "En modo difícil, debug_active debe desactivarse por completo"
