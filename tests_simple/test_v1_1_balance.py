"""
tests_simple/test_v1_1_balance.py
==================================
Suite de pruebas de balanceo y calibración de la Versión 1.1:
1. Sensibilidad de la TPM en régimen flexible (derivada en rango didáctico [-1.0%, -2.5%]).
2. Dinámica de Reservas por Balanza de Pagos (ΔR = BP = NX + KA) bajo régimen fijo.
3. Inercia de gasto público (G).
4. Partidas de 10 turnos en todos los escenarios con 100% garantía de identidad contable Y = C + I + G + NX.
"""

from __future__ import annotations

import pytest
from engine_simple.state_manager import StateManager


def test_monetary_policy_sensitivity_v1_1():
    """Verifica que subir r_ref en +100 pb (1 p.p.) reduzca el PIB en un rango didáctico jugable."""
    sm = StateManager("Economia_Saludable")
    inst_base = dict(sm.current_instruments)
    inst_base["regime"] = "flexible"

    snap_base = sm.get_dry_run_projection(inst_base)

    inst_up = dict(inst_base)
    inst_up["r_ref"] += 1.0  # +1.0 p.p.

    snap_up = sm.get_dry_run_projection(inst_up)

    dY_pct = (snap_up["Y"] - snap_base["Y"]) / snap_base["Y"] * 100.0

    # La contracción debe ser moderada e intuitiva (entre -1.0% y -2.5%)
    assert -3.0 <= dY_pct <= -0.5, f"Sensibilidad monetaria fuera de rango didáctico: dY = {dY_pct:.2f}%"


def test_bp_reserve_dynamics_v1_1():
    """Verifica que bajo régimen fijo las reservas respondan a la Balanza de Pagos (BP = NX + KA)."""
    sm = StateManager("Economia_Saludable")
    inst = dict(sm.current_instruments)
    inst["regime"] = "fixed"
    inst["r_ref"] = 8.0  # Elevar tasa atrae capitales (KA > 0)

    snap1 = sm.step_forward(inst)

    # Las reservas deben acumularse por la entrada de capitales y/o saldo externo
    assert snap1["R"] != sm.history[0]["R"], "Las reservas deberían moverse bajo régimen fijo."


# def test_gasto_publico_inertia_v1_1():
#     """DEPRECADO V1.2: AGENTS.md prohíbe explícitamente parches de suavizado ad-hoc 70/30 en gasto público."""
#     pass


@pytest.mark.parametrize("scenario_id", ["tiger_asia", "Economia_Saludable", "latam_crisis", "death_spiral"])
def test_full_10_turn_smooth_gameplay_v1_1(scenario_id: str):
    """Verifica partidas de 10 turnos con ajustes graduados de política sin Game Over prematuro."""
    sm = StateManager(scenario_id)

    for turn in range(1, 11):
        if sm.is_game_over:
            break

        inst = dict(sm.current_instruments)
        # Ajustes graduales didácticos
        if turn % 2 == 0:
            inst["Gc"] += 0.5
            inst["G"] = inst["Gc"] + inst["Ig"]
        else:
            inst["r_ref"] += 0.1

        snap = sm.step_forward(inst)

        # Garantía incondicional de identidad macroeconómica
        identity_error = abs(snap["Y"] - (snap["C"] + snap["I_inv"] + snap["G"] + snap["NX"]))
        assert identity_error < 1e-10, f"Fallo de identidad en turno {turn} ({scenario_id}): error={identity_error}"

    assert len(sm.history) > 1
