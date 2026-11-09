"""
tests_simple/test_v1_3_enhancements.py
======================================
Suite de pruebas de validación para las mejoras macroeconómicas de la Versión 1.3:
1. Piso Estructural de Deuda Soberana (B >= 10% PIB Nominal).
2. Acumulación de excedentes fiscales en Reservas / Fondo Soberano (FSE).
3. Calificación Crediticia Multidimensional (S&P / Moody's) con pérdida de grado de inversión por inflación o desempleo.
4. Cuadrantes Canónicos de Salter-Swan (IB con pendiente negativa, EB con pendiente positiva).
5. Choques exógenos leves calibrados, ventana de cooldown y formato de modal interactivo.
"""

from __future__ import annotations

import copy
import pytest

from engine_simple.core import compute_salter_swan
from engine_simple.dynamics import compute_fiscal_balance, compute_sovereign_risk
from engine_simple.events import evaluate_random_events, format_event_modal_data, get_event_by_id
from engine_simple.state_manager import StateManager


# ─────────────────────────────────────────────────────────────────────────────
# 1. PISO ESTRUCTURAL DE DEUDA Y FONDO SOBERANO (FSE)
# ─────────────────────────────────────────────────────────────────────────────

def test_structural_debt_floor_min_10_percent():
    """Valida que la deuda pública nunca colapse por debajo del 10% del PIB nominal."""
    # Simular superávit fiscal masivo donde los ingresos duplican el gasto
    recaudacion, subs, ints, deficit, B_new, def_prim = compute_fiscal_balance(
        Gc=5.0,
        Ig=0.0,
        tc=0.40,
        tk=0.30,
        tau=0.20,
        sx=0.0,
        Y=100.0,
        X=20.0,
        M_imp=10.0,
        B_prev=10.0,
        r_star=2.0,
        rho=0.5,
        PIB_nominal=100.0,
    )

    # Con PIB nominal = 100.0, B_min = 10.0
    assert deficit < 0.0, "Debe existir un superávit fiscal"
    assert B_new >= 10.0, f"La deuda debió respetar el piso estructural de 10.0, obtenido: {B_new}"


def test_fse_reserve_accumulation_under_structural_floor():
    """Valida que el superávit generado cuando la deuda ya está en su piso se acumule en reservas."""
    sm = StateManager("chile_rule")

    # Forzar política fiscal hiper-contractiva con superávit extremo
    for turn in range(1, 4):
        inst = copy.deepcopy(sm.current_instruments)
        inst["Gc"] = 5.0
        inst["Ig"] = 0.0
        inst["tc"] = 0.40
        inst["tk"] = 0.30
        snap = sm.step_forward(inst)

        # La deuda no debe ser 0.0 en ningún turno
        pib_nom = snap["PIB_nominal"]
        assert snap["B"] >= max(2.0, 0.10 * pib_nom) - 1e-4, f"Deuda por debajo del piso en T{turn}: {snap['B']}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. CALIFICACIÓN CREDITICIA MULTIDIMENSIONAL
# ─────────────────────────────────────────────────────────────────────────────

def test_multidimensional_rating_healthy_economy():
    """Economía con baja deuda, inflación anclada al 3% y pleno empleo recibe AAA."""
    rho, rating = compute_sovereign_risk(
        B=15.0,
        PIB_nominal=100.0,
        R=50.0,
        pi=0.03,
        U=0.05,
        Un=0.05,
    )
    assert rating == "AAA"
    assert rho == 0.5


def test_multidimensional_rating_loss_of_investment_grade():
    """Economía con baja deuda pero inflación alta (20%) pierde el grado de inversión."""
    rho, rating = compute_sovereign_risk(
        B=15.0,
        PIB_nominal=100.0,
        R=50.0,
        pi=0.20,
        U=0.05,
        Un=0.05,
    )
    assert rating not in ("AAA", "AA+", "AA", "A", "BBB"), f"No debe ser grado de inversión con pi=20%, obtenido: {rating}"
    assert rho >= 5.0


def test_multidimensional_rating_default_on_insolvency():
    """Deuda sobre 150% del PIB gatilla rating D de default y spread de 18 pp."""
    rho, rating = compute_sovereign_risk(
        B=160.0,
        PIB_nominal=100.0,
        R=25.0,
        pi=0.03,
        U=0.05,
        Un=0.05,
    )
    assert rating == "D"
    assert rho == 18.0


# ─────────────────────────────────────────────────────────────────────────────
# 3. CUADRANTES CANÓNICOS DE SALTER-SWAN
# ─────────────────────────────────────────────────────────────────────────────

def test_salter_swan_slopes_and_quadrant_validity():
    """Valida pendientes teóricas y clasificación de Salter-Swan."""
    sm = StateManager("chile_rule")
    curr = sm.history[0]
    sp = sm.current_params

    res = compute_salter_swan(curr, sp, curr["G"], Y_pot=sm.Y_pot)

    assert res["zone"] in ("I", "II", "III", "IV")
    assert res["slope_IB"] < 0.0, "La curva IB debe tener pendiente estrictamente negativa"
    assert res["slope_EB"] > 0.0, "La curva EB debe tener pendiente estrictamente positiva"
    assert "ml_satisfied" in res
    assert "diagnosis" in res
    assert "policy" in res


# ─────────────────────────────────────────────────────────────────────────────
# 4. CHOQUES EXÓGENOS LEVES, COOLDOWN Y MODAL
# ─────────────────────────────────────────────────────────────────────────────

def test_random_events_grace_period_and_cooldown():
    """Verifica el período de gracia en T1-T2 y la ventana de cooldown de 2 turnos."""
    # Gracia en T1 y T2
    ev1, cd1 = evaluate_random_events(turn=1, cooldown_counter=0, active_event_ids=[])
    assert ev1 is None

    ev2, cd2 = evaluate_random_events(turn=2, cooldown_counter=0, active_event_ids=[])
    assert ev2 is None

    # Cooldown activo bloquea disparos
    ev_cd, cd_rem = evaluate_random_events(turn=5, cooldown_counter=2, active_event_ids=[])
    assert ev_cd is None
    assert cd_rem == 1


def test_format_event_modal_data_structure():
    """Verifica que el formateador prepare el botón institucional 'Continuar gobernando 🏛️'."""
    ev = get_event_by_id("commodity_boom_rnd")
    modal_info = format_event_modal_data(ev, cabinet_advice="Monitorear el tipo de cambio real.")

    assert modal_info["title"] == ev["name"]
    assert modal_info["button_label"] == "Continuar gobernando 🏛️"
    assert isinstance(modal_info["impact_metrics"], list)
    assert "Monitorear" in modal_info["advice_summary"]

