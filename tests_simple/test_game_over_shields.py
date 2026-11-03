"""
tests_simple/test_game_over_shields.py
======================================
Pruebas del Blindaje Anti-Bucle y Reglas de Hierro de Game Over.
Edición: The Economic War Room (V1.2 SIMPLE).

Verifica:
1. Inmunidad incondicional en los Turnos 1 y 2 (período de gracia inicial).
2. Regla de persistencia de 2 turnos consecutivos desde Turno 3.
3. Activación de Alerta Roja Crítica preventiva en el 1er turno de peligro.
"""

from __future__ import annotations

import copy
import pytest

from config_simple.parameters import PolicyInstruments
from config_simple.scoring import check_game_over
from engine_simple.state_manager import StateManager


def test_grace_period_immunity_t1_and_t2():
    """5.2.1: En los turnos 1 y 2 es IMPOSIBLE el Game Over incluso con variables en zona crítica."""
    # Prueba directa de la función pura check_game_over
    for t in (1, 2):
        res = check_game_over(
            turn=t,
            debt_ratio_nominal=2.00,  # 200% deuda
            reserves=0.0,             # Cero reservas
            pi=1.50,                  # 150% inflación
            U=0.40,                   # 40% desempleo
            gY=-0.30,
        )
        assert res.is_game_over is False, f"Game Over declarado indebidamente en turno {t}"
        assert res.red_alert_active is True, f"Debe activar alerta roja en turno {t}"


def test_state_manager_grace_period():
    """5.2.1 (Integración): StateManager no permite Game Over en t=1 o t=2 con políticas destructivas."""
    sm = StateManager("chile_rule")

    destructive_pi: PolicyInstruments = copy.deepcopy(sm.current_instruments)
    destructive_pi["Gc"] = 35.0
    destructive_pi["Ig"] = 25.0
    destructive_pi["tc"] = 0.05
    destructive_pi["tk"] = 0.00
    destructive_pi["r_ref"] = 1.0  # Tasa mínima hiper-inflacionaria
    destructive_pi["tau"] = 0.00
    destructive_pi["sx"] = 0.20

    # Turno 1
    snap1 = sm.step_forward(destructive_pi)
    assert sm.is_game_over is False
    assert snap1["t"] == 1

    # Turno 2
    snap2 = sm.step_forward(destructive_pi)
    assert sm.is_game_over is False
    assert snap2["t"] == 2


def test_two_consecutive_turns_persistence_rule():
    """5.2.2: Prueba que un cruce en T3 emita Alerta Roja pero no Game Over, y si persiste en T4 declare Game Over."""
    counters = {"debt": 0, "reserves": 0, "inflation": 0, "unemployment": 0}

    # Turno 3: 1er turno en zona crítica de reservas (R = 1.5 MUSD <= 2.0)
    res_t3 = check_game_over(
        turn=3,
        debt_ratio_nominal=0.40,
        reserves=1.5,
        pi=0.03,
        U=0.05,
        consecutive_danger_turns=counters,
    )
    assert res_t3.is_game_over is False, "T3 no debe ser Game Over en el 1er turno"
    assert res_t3.red_alert_active is True, "T3 debe emitir Alerta Roja Crítica"
    assert "CRISIS DE BALANZA DE PAGOS" in res_t3.red_alert_reason
    assert res_t3.counters["reserves"] == 1

    # Caso A: Si en Turno 4 se corrige (R = 12.0 MUSD) -> Se desactiva y no hay Game Over
    res_t4_fixed = check_game_over(
        turn=4,
        debt_ratio_nominal=0.40,
        reserves=12.0,
        pi=0.03,
        U=0.05,
        consecutive_danger_turns=res_t3.counters,
    )
    assert res_t4_fixed.is_game_over is False
    assert res_t4_fixed.counters["reserves"] == 0

    # Caso B: Si en Turno 4 se repite la condición crítica (R = 1.0 MUSD) -> GAME OVER
    res_t4_dead = check_game_over(
        turn=4,
        debt_ratio_nominal=0.40,
        reserves=1.0,
        pi=0.03,
        U=0.05,
        consecutive_danger_turns=res_t3.counters,
    )
    assert res_t4_dead.is_game_over is True, "Debe declarar Game Over por persistencia de 2 turnos"
    assert "CRISIS DE BALANZA DE PAGOS" in str(res_t4_dead.reason)
    assert res_t4_dead.counters["reserves"] == 2

