"""
tests_simple/test_scenarios_playability_10_turns.py
===================================================
Pruebas de Jugabilidad Completa a 10 Turnos para los 4 Escenarios Históricos.
Edición: The Economic War Room (V1.2 SIMPLE).

Verifica que cuando el estudiante aplica las políticas económicas históricas correctas:
1. 🇰🇷 Corea del Sur (1985): Llega a Turno 10 con Score > 75 y acumulación de reservas.
2. 🇨🇱 Chile (2000–2005): Llega a Turno 10 con Score > 80 e inflación anclada al 3%.
3. 🇲🇽 México (1994–1995): Supera la crisis del Tequila, NO agota reservas en T3 y culmina 10 turnos.
4. 🇧🇴 Bolivia (1982–1985): Aplica el D.S. 21060, vence la hiperinflación y culmina 10 turnos.
"""

from __future__ import annotations

import copy
import pytest
from engine_simple.state_manager import StateManager


def test_playability_korea_1985():
    """5.3.1: Simulación completa de 10 turnos de Corea del Sur (1985)."""
    sm = StateManager("tiger_asia")
    assert sm.current_turn == 0
    assert abs(sm.history[0]["Y"] - 100.0) < 1e-5

    for turn in range(1, 11):
        pi = copy.deepcopy(sm.current_instruments)
        # Receta Histórica: Fuerte inversión en infraestructura (Ig -> 12), apoyo exportador y tasa prudente
        pi["Ig"] = min(12.0, 9.0 + (turn - 1) * 0.35)
        pi["Gc"] = min(15.0, 12.0 + (turn - 1) * 0.35)
        pi["tc"] = 0.16
        pi["tk"] = 0.09
        pi["sx"] = 0.05
        pi["tau"] = 0.04
        pi["r_ref"] = 7.0 if turn < 4 else 6.25  # Subir tasa en T3 por shock externo de la Fed

        snap = sm.step_forward(pi)
        assert sm.is_game_over is False, f"Game Over prematuro en Corea turno {turn}: {sm.game_over_reason}"
        assert snap["t"] == turn

    summary = sm.get_endgame_summary()
    assert summary["game_over"] is False
    assert summary["turns_played"] == 10
    assert summary["avg_score"] >= 75.0, f"Score insuficiente: {summary['avg_score']}"
    assert sm.history[-1]["R"] >= 80.0, "Las reservas debieron preservarse o aumentar"


def test_playability_chile_2000_2005():
    """5.3.2: Simulación completa de 10 turnos de Chile (2000–2005) con política contracíclica."""
    sm = StateManager("chile_rule")
    assert sm.current_turn == 0

    for turn in range(1, 11):
        pi = copy.deepcopy(sm.current_instruments)

        if turn in (3, 4, 5):
            # Contracíclica en desaceleración: Estímulo con inversión pública y rebaja de tasa
            pi["Ig"] = 8.0
            pi["Gc"] = 14.5
            pi["r_ref"] = 4.25
            pi["tau"] = 0.04
        elif turn in (6, 7, 8):
            # Superciclo del cobre: Ahorro fiscal moderando Gc y apertura arancelaria al 2%
            pi["Ig"] = 6.0
            pi["Gc"] = 12.5
            pi["r_ref"] = 5.25
            pi["tau"] = 0.02
        elif turn in (9, 10):
            # Cierre post-boom reactivando demanda contracíclicamente con fuerte estímulo
            pi["Ig"] = 8.0
            pi["Gc"] = 15.5
            pi["r_ref"] = 3.5
            pi["tau"] = 0.03
        else:
            # Estabilidad de régimen
            pi["Ig"] = 6.0
            pi["Gc"] = 14.0
            pi["r_ref"] = 5.0
            pi["tau"] = 0.05

        snap = sm.step_forward(pi)
        assert sm.is_game_over is False, f"Game Over en Chile turno {turn}: {sm.game_over_reason}"

    summary = sm.get_endgame_summary()
    assert summary["game_over"] is False
    assert summary["turns_played"] == 10
    assert summary["avg_score"] >= 80.0, f"Score insuficiente: {summary['avg_score']}"
    assert abs(sm.history[-1]["pi"] - 0.03) < 0.05, "Inflación debió quedar anclada cerca de la meta (tolerancia 5% post-shock)"


def test_playability_mexico_1994_tequila():
    """5.3.3: Simulación completa de México 1994 superando la crisis de reservas en T3."""
    sm = StateManager("mexico_tequila")
    assert sm.current_turn == 0
    assert sm.history[0]["R"] == 22.0

    for turn in range(1, 11):
        pi = copy.deepcopy(sm.current_instruments)

        if turn == 1:
            # T1: Shock Tequila. Decretar Reforma Cambiaria a Régimen Flexible para cortar la sangría
            sm.switch_regime("flexible")
            pi["regime"] = "flexible"
            pi["r_ref"] = 14.0  # Alza de emergencia de TPM
            pi["Gc"] = 13.0     # Contención del gasto corriente
            pi["tc"] = 0.15
        elif turn == 2:
            # T2: Mantener tasa alta para frenar fuga de capitales
            pi["r_ref"] = 13.0
            pi["Gc"] = 13.0
            pi["sx"] = 0.03     # Impulso exportador TLCAN
        elif turn >= 3:
            # T3-T10: Recuperación con tipo de cambio competitivo y moderación gradual de tasa
            pi["r_ref"] = max(7.5, 13.0 - (turn - 2) * 1.0)
            pi["Ig"] = min(7.0, 4.0 + (turn - 2) * 0.5)
            pi["sx"] = 0.04
            pi["Gc"] = 13.5

        snap = sm.step_forward(pi)
        assert sm.is_game_over is False, f"Game Over en México turno {turn}: {sm.game_over_reason}"
        # Verificar explícitamente que las reservas NO colapsaron en T3
        if turn == 3:
            assert snap["R"] > 2.0, f"Reservas agotadas en T3: {snap['R']} MUSD"

    summary = sm.get_endgame_summary()
    assert summary["game_over"] is False
    assert summary["turns_played"] == 10


def test_playability_bolivia_1982_ds21060():
    """5.3.4: Simulación de Bolivia superando la hiperinflación con el plan D.S. 21060."""
    sm = StateManager("bolivia_hyper")
    assert sm.current_turn == 0
    assert sm.history[0]["pi"] == 0.24  # 24% inicial

    for turn in range(1, 11):
        pi = copy.deepcopy(sm.current_instruments)

        if turn <= 3:
            # T1-T3: Terapia de shock D.S. 21060 + Reforma Tributaria Ley 843
            # 1. Recorte drástico del gasto corriente sobredimensionado
            pi["Gc"] = 14.0
            pi["Ig"] = 2.0
            # 2. Reforma tributaria Ley 843 (subir tc al 18% y tk al 12%)
            pi["tc"] = 0.18
            pi["tk"] = 0.12
            # 3. Tasa fuertemente real positiva
            pi["r_ref"] = 18.0
            # 4. Desacelerar deslizamiento cambiario para cortar el pass-through
            pi["crawl_rate"] = 0.02
            pi["tau"] = 0.10
            pi["sx"] = 0.03
        else:
            # T4-T10: Reactivación post-estabilización según receta histórica (normalizar tasa a 7% y expandir Ig)
            pi["Gc"] = 14.0
            pi["Ig"] = min(8.0, 3.0 + (turn - 3) * 1.0)
            pi["tc"] = 0.18
            pi["tk"] = 0.12
            pi["r_ref"] = 7.0
            pi["sx"] = 0.04
            pi["tau"] = 0.08
            pi["crawl_rate"] = 0.01

        snap = sm.step_forward(pi)
        assert sm.is_game_over is False, f"Game Over en Bolivia turno {turn}: {sm.game_over_reason}"

        # Comprobar que en T3 la inflación cayó fuertemente respecto a la hiperinflación inicial
        if turn == 3:
            assert snap["pi"] < 0.12, f"La inflación no cedió lo suficiente en T3: {snap['pi']*100:.1f}%"
            assert snap["theta"] >= 0.60, f"La credibilidad debió aumentar: {snap['theta']}"

    summary = sm.get_endgame_summary()
    assert summary["game_over"] is False
    assert summary["turns_played"] == 10
    assert sm.history[-1]["pi"] < 0.06, "Inflación final debe estar controlada"

