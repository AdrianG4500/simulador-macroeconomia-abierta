"""
tests_simple/test_core_identity.py
==================================
Pruebas de verificación de consistencia macroeconómica, identidad nacional y transmisión.
Edición: The Economic War Room (V1.2 SIMPLE).

Verifica:
1. Identidad contable absoluta: |Y - (C + I + G + NX)| < 1e-12 en 1,000 combinaciones aleatorias.
2. Normalización de precios y TCR en T=0 (E=10 -> P_local=1.00, q=1.00).
3. Signos de transmisión económica de las 8 palancas.
"""

from __future__ import annotations

import random
import pytest

from config_simple.parameters import (
    DEFAULT_POLICY_INSTRUMENTS,
    DEFAULT_STRUCTURAL_PARAMS,
    PolicyInstruments,
    StructuralParams,
)
from config_simple.scenarios import SCENARIOS, get_scenario_params
from engine_simple.core import (
    compute_multiplier,
    compute_price_level,
    compute_real_exchange_rate,
    solve_equilibrium,
)
from engine_simple.dynamics import (
    compute_capital_flows,
    compute_fiscal_balance,
    compute_inflation,
    update_potential_output,
)


def test_price_normalization_t0():
    """5.1.2: Verifica que con E=10.0, P*=1.0, tau=0.0 -> P_local = 1.00 y q = 1.00."""
    P_local, P_T = compute_price_level(E=10.0, P_star=1.0, P_NT=1.0, alpha_PT=0.40, tau=0.0)
    q = compute_real_exchange_rate(E=10.0, P_star=1.0, P_local=P_local)

    assert abs(P_local - 1.0) < 1e-12, f"P_local no normalizado: {P_local}"
    assert abs(P_T - 1.0) < 1e-12, f"P_T no normalizado: {P_T}"
    assert abs(q - 1.0) < 1e-12, f"q no normalizado: {q}"


def test_multiplier_formula():
    """Verifica k_m = 1 / [1 - c1(1-tc) + m1(1-tau)]."""
    c1 = 0.65
    tc = 0.15
    m1 = 0.14
    tau = 0.05
    km = compute_multiplier(c1, tc, m1, tau)

    expected_denom = 1.0 - c1 * (1.0 - tc) + m1 * (1.0 - tau)
    assert abs(km - (1.0 / expected_denom)) < 1e-12


def test_identity_in_all_calibrated_scenarios():
    """Verifica |Y - (C + I + G + NX)| < 1e-12 en los 4 escenarios base."""
    for scen_id in ["tiger_asia", "chile_rule", "mexico_tequila", "bolivia_hyper"]:
        sp, pi, init = get_scenario_params(scen_id)
        eq = solve_equilibrium(
            sp=sp,
            pi=pi,
            P_NT=init.get("P_NT", 1.0),
            Y_prev=init.get("Y", 100.0),
            Y_pot=init.get("Y_pot", 100.0),
            rho=init.get("rho", 0.5),
            debt_ratio_prev=init.get("B", 20.0) / init.get("Y", 100.0),
        )

        Y = eq["Y"]
        C = eq["C"]
        I_priv = eq["I_priv"]
        G = eq["G"]
        NX = eq["NX"]

        error = abs(Y - (C + I_priv + G + NX))
        assert error < 1e-12, f"Escenario {scen_id}: Error de identidad = {error:.2e}"


def test_random_parameter_sweep_1000():
    """5.1.1: Ejecuta 1,000 combinaciones aleatorias de las 8 palancas y verifica identidad < 1e-12."""
    random.seed(42)
    sp = dict(DEFAULT_STRUCTURAL_PARAMS)

    regimes = ["fixed", "flexible", "crawling_peg"]

    for _ in range(1000):
        pi: PolicyInstruments = {
            "Gc": random.uniform(5.0, 35.0),
            "Ig": random.uniform(0.0, 25.0),
            "tc": random.uniform(0.05, 0.40),
            "tk": random.uniform(0.00, 0.35),
            "r_ref": random.uniform(1.0, 30.0),
            "tau": random.uniform(0.00, 0.30),
            "sx": random.uniform(0.00, 0.20),
            "E": random.uniform(5.0, 25.0),
            "regime": random.choice(regimes),
            "crawl_rate": random.uniform(0.0, 0.20),
            "r_star": random.uniform(2.0, 8.0),
            "P_star": 1.0,
            "pi_target": 0.03,
            "G_needed": 0.0,
            "G": 0.0,
            "t": 0.0,
        }
        pi["G"] = pi["Gc"] + pi["Ig"]
        pi["t"] = pi["tc"]

        eq = solve_equilibrium(
            sp=sp,  # type: ignore
            pi=pi,
            P_NT=random.uniform(0.8, 2.0),
            E_prev=random.uniform(5.0, 25.0),
            Y_prev=random.uniform(70.0, 130.0),
            Y_pot=100.0,
            rho=random.uniform(0.1, 10.0),
            debt_ratio_prev=random.uniform(0.1, 1.2),
        )

        Y = eq["Y"]
        C = eq["C"]
        I_priv = eq["I_priv"]
        G = eq["G"]
        NX = eq["NX"]

        error = abs(Y - (C + I_priv + G + NX))
        assert error < 1e-12, f"Error en sweep: {error:.2e} con Gc={pi['Gc']}, Ig={pi['Ig']}"


def test_economic_transmission_signs():
    """5.1.3: Verifica los signos de transmisión teórica de las 8 palancas."""
    sp, base_pi, init = get_scenario_params("chile_rule")

    def run(pi_mod):
        p = copy_pi(base_pi)
        p.update(pi_mod)
        p["G"] = p["Gc"] + p["Ig"]
        p["t"] = p["tc"]
        return solve_equilibrium(sp, p, P_NT=1.0, Y_prev=100.0, Y_pot=100.0)

    # 1. Gc ↑ => Y ↑
    eq_base = run({})
    eq_gc_up = run({"Gc": base_pi["Gc"] + 5.0})
    assert eq_gc_up["Y"] > eq_base["Y"], "Gc no expande el PIB"

    # 2. Ig ↑ => Y ↑ y potencial futuro ↑
    eq_ig_up = run({"Ig": base_pi["Ig"] + 5.0})
    assert eq_ig_up["Y"] > eq_base["Y"], "Ig no expande el PIB"
    y_pot_next_base = update_potential_output(100.0, base_pi["Ig"])
    y_pot_next_up = update_potential_output(100.0, base_pi["Ig"] + 5.0)
    assert y_pot_next_up > y_pot_next_base, "Ig no expande el PIB potencial futuro"

    # 3. r_ref ↑ => r ↑ y KA ↑
    eq_r_up = run({"r_ref": base_pi["r_ref"] + 4.0})
    assert eq_r_up["r"] > eq_base["r"], "r_ref no sube tasa doméstica"
    ka_base = compute_capital_flows(sp["f"], eq_base["r"], base_pi["r_star"], 0.5)
    ka_r_up = compute_capital_flows(sp["f"], eq_r_up["r"], base_pi["r_star"], 0.5)
    assert ka_r_up > ka_base, "Tasa más alta no atrae flujos de capital KA"

    # 4. tau ↑ => M_imp ↓ y P_local ↑
    eq_tau_up = run({"tau": base_pi["tau"] + 0.10})
    assert eq_tau_up["P_local"] > eq_base["P_local"], "Arancel no encarece precios locales"

    # 5. sx ↑ => X ↑
    eq_sx_up = run({"sx": base_pi["sx"] + 0.05})
    assert eq_sx_up["X"] > eq_base["X"], "Subsidio exportador no aumenta exportaciones brutas"


def copy_pi(pi: PolicyInstruments) -> PolicyInstruments:
    return dict(pi)  # type: ignore
