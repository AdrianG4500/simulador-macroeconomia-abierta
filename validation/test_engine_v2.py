"""
validation/test_engine_v2.py
=============================
Suite de verificacion analitica del motor matematico V2.0.

Criterio de aceptacion Fase 1: 12/12 tests pasan con tolerancia < 0.01.

Para ejecutar:
    python -m pytest validation/test_engine_v2.py -v --tb=short

Tests:
    1.  test_multiplier_proporcional     - Multiplicador con impuesto proporcional
    2.  test_ml_condition_holds          - M-L cumplida: devaluacion mejora NX
    3.  test_ml_condition_fails          - M-L no cumplida: devaluacion empeora NX
    4.  test_j_curve_first_turn          - NX cae turno 1, sube turno 2
    5.  test_okun_uses_gap               - Okun usa gap, no gY
    6.  test_phillips_uses_gap           - Phillips usa gap + pass-through
    7.  test_pass_through                - Devaluacion 10% -> P_local sube ~5%
    8.  test_bp_imperfect                - BP con movilidad imperfecta
    9.  test_circuit_breaker             - R <= 0 -> regimen flexible, E se devalua
    10. test_crawling_peg                - E_1 = E_0 * (1 + crawl_rate)
    11. test_salter_swan_integrated      - A derivado de C+I+G del equilibrio
    12. test_deuda_crowding_out          - B alto -> mayor deficit -> menor I_inv
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Asegurar que el directorio raiz del proyecto este en el path
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.core_v2 import (
    compute_autonomous_demand,
    compute_bp_curve,
    compute_multiplier,
    compute_NX,
    compute_price_level,
    compute_real_exchange_rate,
    compute_salter_swan,
    eq_crawling_peg_v2,
    eq_fixed_v2,
    eq_flexible_v2,
    is_curve_v2,
    lm_curve_v2,
)
from engine.dynamics_v2 import (
    check_reserve_circuit_breaker,
    compute_fiscal_balance,
    compute_inflation,
    compute_j_curve_flag,
    compute_output_gap,
    compute_unemployment,
    update_reserves,
)
from config.parameters_v2 import (
    DEFAULT_STRUCTURAL_PARAMS,
    DEFAULT_POLICY_INSTRUMENTS,
    StructuralParams,
    PolicyInstruments,
)

# ── Tolerancia numerica global ────────────────────────────────────────────────
TOL = 0.01


# =============================================================================
# TEST 1: MULTIPLICADOR CON IMPUESTO PROPORCIONAL
# =============================================================================

def test_multiplier_proporcional():
    """
    c1=0.75, t=0.20, m1=0.15
    k_m = 1 / (1 - 0.75*(1-0.20) + 0.15)
        = 1 / (1 - 0.75*0.80 + 0.15)
        = 1 / (1 - 0.60 + 0.15)
        = 1 / 0.55
        = 1.81818...
    """
    k_m = compute_multiplier(c1=0.75, t=0.20, m1=0.15)
    expected = 1.0 / 0.55  # ~1.81818...

    assert abs(k_m - expected) < TOL, (
        f"Multiplicador V2: calculado={k_m:.6f}, esperado={expected:.6f}, "
        f"diferencia={abs(k_m - expected):.6f}"
    )
    # Verificar que el denominador V1 (sin t) da valor diferente
    k_m_v1 = 1.0 / (1.0 - 0.75 + 0.15)  # = 1/0.40 = 2.5
    assert abs(k_m - k_m_v1) > 0.05, (
        "El multiplicador V2 debe diferir del V1 cuando t > 0"
    )


# =============================================================================
# TEST 2: CONDICION MARSHALL-LERNER CUMPLIDA
# =============================================================================

def test_ml_condition_holds():
    """
    epsilon_x=0.80, epsilon_m=0.70 -> suma=1.50 > 1 (M-L cumplida)
    Una devaluacion de q mejora NX.
    """
    NX0, m1, Y = 5.0, 0.15, 100.0

    # Tipo de cambio real base y devaluado
    q_base    = 1.0
    q_devalued = 1.20   # Devaluacion del 20% en terminos reales

    NX_base,  _, _ = compute_NX(NX0, epsilon_x=0.80, epsilon_m=0.70, q=q_base,
                          m1=m1, Y=Y, j_curve_active=False)
    NX_after, _, _ = compute_NX(NX0, epsilon_x=0.80, epsilon_m=0.70, q=q_devalued,
                          m1=m1, Y=Y, j_curve_active=False)

    assert NX_after > NX_base, (
        f"Con M-L cumplida, devaluacion debe mejorar NX. "
        f"NX_base={NX_base:.4f}, NX_after={NX_after:.4f}"
    )
    # Verificar magnitud: delta_NX ~ epsilon_x * delta_q = 0.80 * 0.20 = 0.16
    delta_NX = NX_after - NX_base
    assert delta_NX > 0.10, (
        f"La mejora en NX deberia ser significativa, delta_NX={delta_NX:.4f}"
    )


# =============================================================================
# TEST 3: CONDICION MARSHALL-LERNER NO CUMPLIDA
# =============================================================================

def test_ml_condition_fails():
    """
    epsilon_x=0.30, epsilon_m=0.40 -> suma=0.70 < 1 (M-L NO cumplida)
    Una devaluacion de q EMPEORA NX.
    """
    NX0, m1, Y = 5.0, 0.15, 100.0

    q_base     = 1.0
    q_devalued = 1.20

    NX_base,  _, _ = compute_NX(NX0, epsilon_x=0.30, epsilon_m=0.40, q=q_base,
                          m1=m1, Y=Y, j_curve_active=False)
    NX_after, _, _ = compute_NX(NX0, epsilon_x=0.30, epsilon_m=0.40, q=q_devalued,
                          m1=m1, Y=Y, j_curve_active=False)

    assert NX_after < NX_base, (
        f"Con M-L NO cumplida, devaluacion debe EMPEORAR NX. "
        f"NX_base={NX_base:.4f}, NX_after={NX_after:.4f}"
    )


# =============================================================================
# TEST 4: EFECTO J-CURVE
# =============================================================================

def test_j_curve_first_turn():
    """
    Devaluacion de E=10 a E=12 (20%).
    Turno 1 (j_curve_active=True): NX cae (epsilon_x_short=0.1)
    Turno 2 (j_curve_active=False): NX sube (epsilon_x estructural=0.80)
    """
    NX0, epsilon_x, epsilon_m, m1, Y = 5.0, 0.80, 0.70, 0.15, 100.0
    q_devalued = 1.20  # simula devaluacion real

    # Turno 1: efecto J activo
    NX_t1, _, _ = compute_NX(NX0, epsilon_x=epsilon_x, epsilon_m=epsilon_m,
                       q=q_devalued, m1=m1, Y=Y,
                       j_curve_active=True, epsilon_x_short=0.1)

    # Turno 2: ajuste normal (M-L cumplida)
    NX_t2, _, _ = compute_NX(NX0, epsilon_x=epsilon_x, epsilon_m=epsilon_m,
                       q=q_devalued, m1=m1, Y=Y,
                       j_curve_active=False)

    assert NX_t2 > NX_t1, (
        f"NX turno 2 debe ser mayor que turno 1 (efecto J). "
        f"NX_t1={NX_t1:.4f}, NX_t2={NX_t2:.4f}"
    )

    # Verificar que j_curve_flag detecta la devaluacion correctamente
    assert compute_j_curve_flag(E_t=12.0, E_prev=10.0, threshold=0.02) is True
    assert compute_j_curve_flag(E_t=10.01, E_prev=10.0, threshold=0.02) is False


# =============================================================================
# TEST 5: OKUN USA GAP (NO gY)
# =============================================================================

def test_okun_uses_gap():
    """
    Y=90, Y_pot=100 -> gap=-0.10 -> U > U_n
    Verificar que la formula usa gap y no gY.
    """
    Y, Y_pot = 90.0, 100.0
    U_n, gamma_okun = 0.05, 0.50

    gap = compute_output_gap(Y, Y_pot)
    assert abs(gap - (-0.10)) < TOL, f"gap esperado=-0.10, calculado={gap}"

    U = compute_unemployment(U_n, gamma_okun, gap)
    expected_U = U_n - gamma_okun * gap   # 0.05 - 0.50*(-0.10) = 0.05 + 0.05 = 0.10
    assert abs(U - expected_U) < TOL, (
        f"U={U:.4f}, esperado={expected_U:.4f}"
    )
    assert U > U_n, (
        f"Con gap < 0, U debe ser > U_n. U={U:.4f}, U_n={U_n}"
    )

    # Verificar que si hubieramos usado gY=0.05 el resultado seria diferente
    # (economia crece 5% pero sigue por debajo del potencial)
    gY = 0.05
    U_v1_wrong = U_n - gamma_okun * gY   # 0.05 - 0.50*0.05 = 0.025 (INCORRECTO)
    assert U > U_v1_wrong, (
        "El desempleo V2 (gap) debe ser mayor que el calculado con gY "
        "cuando la economia esta por debajo del potencial."
    )


# =============================================================================
# TEST 6: PHILLIPS USA GAP + PASS-THROUGH
# =============================================================================

def test_phillips_uses_gap():
    """
    gap=-0.10, pi_e=0.03, alpha_inf=0.50, beta_PT=0.0 (sin shock cambiario)
    pi = 0.03 + 0.50*(-0.10) = 0.03 - 0.05 = -0.02 < pi_e
    """
    pi_e, alpha_inf, gap = 0.03, 0.50, -0.10
    beta_PT, delta_E, E_prev = 0.0, 0.0, 10.0

    pi = compute_inflation(pi_e, alpha_inf, gap, beta_PT, delta_E, E_prev)
    expected = pi_e + alpha_inf * gap  # 0.03 - 0.05 = -0.02
    assert abs(pi - expected) < TOL, f"pi={pi:.4f}, esperado={expected:.4f}"
    assert pi < pi_e, "Con gap < 0 y sin shock cambiario, pi debe ser < pi_e"

    # Con pass-through cambiario (devaluacion 10%)
    delta_E_shock = 1.0  # E sube de 10 a 11
    pi_with_pt = compute_inflation(pi_e, alpha_inf, gap, beta_PT=0.20,
                                   delta_E=delta_E_shock, E_prev=10.0)
    # pi = 0.03 + 0.50*(-0.10) + 0.20*(1.0/10.0) = -0.02 + 0.02 = 0.0
    expected_with_pt = -0.02 + 0.20 * (1.0 / 10.0)
    assert abs(pi_with_pt - expected_with_pt) < TOL, (
        f"pi_with_pt={pi_with_pt:.4f}, esperado={expected_with_pt:.4f}"
    )


# =============================================================================
# TEST 7: PASS-THROUGH CAMBIARIO EN PRECIOS
# =============================================================================

def test_pass_through():
    """
    E_0=10, E_1=11 (devaluacion 10%), alpha_PT=0.50, P_star=1.0, P_NT=1.0
    P_local_0 = alpha_PT*(E_0*P_star) + (1-alpha_PT)*P_NT = 0.5*10 + 0.5*1 = 5.5
    P_local_1 = alpha_PT*(E_1*P_star) + (1-alpha_PT)*P_NT = 0.5*11 + 0.5*1 = 6.0
    """
    P_star, P_NT, alpha_PT = 1.0, 1.0, 0.50

    P_local_0 = compute_price_level(E=10.0, P_star=P_star, P_NT=P_NT, alpha_PT=alpha_PT)
    P_local_1 = compute_price_level(E=11.0, P_star=P_star, P_NT=P_NT, alpha_PT=alpha_PT)

    assert abs(P_local_0 - 5.5) < TOL, f"P_local_0={P_local_0}, esperado=5.5"
    assert abs(P_local_1 - 6.0) < TOL, f"P_local_1={P_local_1}, esperado=6.0"

    # Propiedad matematica central: delta_P_local = alpha_PT * delta_E * P_star
    delta_E          = 11.0 - 10.0
    delta_P_expected = alpha_PT * delta_E * P_star   # = 0.5 * 1.0 * 1.0 = 0.5
    delta_P_actual   = P_local_1 - P_local_0         # = 6.0 - 5.5 = 0.5

    assert abs(delta_P_actual - delta_P_expected) < TOL, (
        f"delta_P_local={delta_P_actual:.4f}, "
        f"esperado alpha_PT*delta_E*P_star={delta_P_expected:.4f}."
    )

    # Con alpha_PT=0: ninguna devaluacion afecta P_local
    P_nt0 = compute_price_level(E=10.0, P_star=P_star, P_NT=P_NT, alpha_PT=0.0)
    P_nt1 = compute_price_level(E=11.0, P_star=P_star, P_NT=P_NT, alpha_PT=0.0)
    assert abs(P_nt0 - P_nt1) < TOL, "Con alpha_PT=0, la devaluacion no afecta P_local"

    # Con alpha_PT=1.0: cambio en P_local = exactamente delta_E * P_star
    P_tr0 = compute_price_level(E=10.0, P_star=P_star, P_NT=P_NT, alpha_PT=1.0)
    P_tr1 = compute_price_level(E=11.0, P_star=P_star, P_NT=P_NT, alpha_PT=1.0)
    assert abs((P_tr1 - P_tr0) - delta_E * P_star) < TOL, (
        "Con alpha_PT=1, el cambio en P_local debe ser igual a delta_E*P_star"
    )


# =============================================================================
# TEST 8: BP CON MOVILIDAD IMPERFECTA
# =============================================================================

def test_bp_imperfect():
    """
    r_star=5.0, delta_E_expected=0.0, NX=-5.0, f=1.0
    r_BP = 5.0 + 0.0 - (-5.0/1.0) = 5.0 + 5.0 = 10.0

    Con movilidad perfecta (f -> inf): r_BP = r* = 5.0
    Con movilidad imperfecta (f=1): r_BP = 10.0 (prima por deficit comercial)
    """
    r_star, delta_E_expected, NX, f = 5.0, 0.0, -5.0, 1.0

    r_bp = compute_bp_curve(r_star, delta_E_expected, NX, f)
    expected = r_star + delta_E_expected - (NX / f)  # 5 + 0 - (-5/1) = 10
    assert abs(r_bp - expected) < TOL, f"r_BP={r_bp:.4f}, esperado={expected:.4f}"
    assert abs(r_bp - 10.0) < TOL, f"r_BP debe ser 10.0, calculado={r_bp}"

    # Verificar que con f muy grande se aproxima al caso perfecto
    r_bp_perfect = compute_bp_curve(r_star, delta_E_expected, NX, f=1e6)
    assert abs(r_bp_perfect - r_star) < TOL, (
        f"Con f muy grande, r_BP debe ~ r*. "
        f"r_BP={r_bp_perfect:.6f}, r*={r_star}"
    )


# =============================================================================
# TEST 9: CIRCUIT BREAKER (COLAPSO DE RESERVAS)
# =============================================================================

def test_circuit_breaker():
    """
    R <= 0 bajo TC Fijo -> regimen se fuerza a "flexible", E se devalua.
    """
    # Escenario: TC Fijo con reservas agotadas
    triggered, new_regime, new_E = check_reserve_circuit_breaker(
        R=-5.0, regime="fixed", E_current=10.0, devaluation_factor=1.20
    )
    assert triggered is True, "Circuit breaker debe activarse con R <= 0 bajo TC Fijo"
    assert new_regime == "flexible", f"Regimen post-crisis debe ser 'flexible', got '{new_regime}'"
    assert abs(new_E - 12.0) < TOL, f"E post-crisis debe ser 12.0, got {new_E}"

    # Escenario: TC Fijo con reservas positivas -> sin crisis
    no_trigger, regime_same, E_same = check_reserve_circuit_breaker(
        R=10.0, regime="fixed", E_current=10.0
    )
    assert no_trigger is False, "Sin crisis cuando R > 0"
    assert regime_same == "fixed"
    assert abs(E_same - 10.0) < TOL

    # Escenario: TC Flexible con R < 0 -> no aplica (no hay que defender E)
    no_trigger_flex, _, _ = check_reserve_circuit_breaker(
        R=-5.0, regime="flexible", E_current=10.0
    )
    assert no_trigger_flex is False, "El circuit breaker no aplica bajo TC Flexible"


# =============================================================================
# TEST 10: CRAWLING PEG
# =============================================================================

def test_crawling_peg():
    """
    E_0=10.0, crawl_rate=0.02
    E_1 = 10.0 * (1 + 0.02) = 10.20
    delta_E_expected ~ 0.02 (expectativas ancladas al crawl)
    """
    sp: StructuralParams = dict(DEFAULT_STRUCTURAL_PARAMS)  # type: ignore[assignment]
    pi: PolicyInstruments = dict(DEFAULT_POLICY_INSTRUMENTS)  # type: ignore[assignment]
    pi["regime"] = "crawling_peg"
    pi["crawl_rate"] = 0.02
    pi["E"] = 10.0

    result = eq_crawling_peg_v2(
        sp=sp, pi=pi,
        Y_pot=100.0, P_NT=1.0,
        E_prev=10.0, crawl_rate=0.02,
    )

    # E_endo registra el nuevo E del crawl
    assert abs(result["E_endo"] - 10.20) < TOL, (
        f"E tras crawl debe ser 10.20, got {result['E_endo']}"
    )
    # El resultado debe ser economicamente valido
    assert result["Y"] > 0, f"Y debe ser positivo, got {result['Y']}"
    assert result["P_local"] > 0, f"P_local debe ser positivo, got {result['P_local']}"


# =============================================================================
# TEST 11: SALTER-SWAN INTEGRADO
# =============================================================================

def test_salter_swan_integrated():
    """
    A_domestic derivado del equilibrio IS-LM: A = C + I + G
    La zona se clasifica sin input manual.
    """
    sp: StructuralParams = dict(DEFAULT_STRUCTURAL_PARAMS)  # type: ignore[assignment]
    pi: PolicyInstruments = dict(DEFAULT_POLICY_INSTRUMENTS)  # type: ignore[assignment]

    # Resolver equilibrio base
    eq = eq_fixed_v2(sp=sp, pi=pi, Y_pot=100.0, P_NT=1.0)

    # Verificar que A_domestic = C + I_inv + G
    A_check = eq["C"] + eq["I_inv"] + pi["G"]
    assert abs(eq["A_domestic"] - A_check) < TOL, (
        f"A_domestic ({eq['A_domestic']:.4f}) debe ser igual a C+I+G ({A_check:.4f})"
    )

    # Calcular Salter-Swan dinamico
    ss = compute_salter_swan(eq, sp, G=pi["G"])

    # La zona debe ser una de las 4 validas
    assert ss["zone"] in {"I", "II", "III", "IV"}, f"Zona invalida: {ss['zone']}"

    # Las pendientes deben tener los signos correctos
    assert ss["slope_IB"] < 0, f"Pendiente IB debe ser negativa, got {ss['slope_IB']}"
    assert ss["slope_EB"] > 0, f"Pendiente EB debe ser positiva, got {ss['slope_EB']}"

    # q_actual debe coincidir con el equilibrio
    assert abs(ss["q_actual"] - eq["q_real"]) < TOL, (
        f"q en Salter-Swan ({ss['q_actual']}) debe coincidir con q_real ({eq['q_real']})"
    )

    # A_actual debe coincidir con el equilibrio
    assert abs(ss["A_actual"] - eq["A_domestic"]) < TOL, (
        f"A en Salter-Swan ({ss['A_actual']}) debe coincidir con A_domestic ({eq['A_domestic']})"
    )


# =============================================================================
# TEST 12: DEUDA Y CROWDING-OUT
# =============================================================================

def test_deuda_crowding_out():
    """
    B alto -> mayor carga de intereses -> mayor deficit -> B crece mas.
    La inversion I_inv se reduce en el escenario de alta deuda
    porque r es mas alto bajo movilidad imperfecta.
    """
    sp_base: StructuralParams = dict(DEFAULT_STRUCTURAL_PARAMS)  # type: ignore[assignment]
    pi_base: PolicyInstruments = dict(DEFAULT_POLICY_INSTRUMENTS)  # type: ignore[assignment]
    pi_base["regime"] = "fixed"

    # Escenario A: B bajo
    G, t, r_base = 20.0, 0.20, 5.0
    Y_base = 100.0
    B_low  = 20.0
    B_high = 200.0

    rec_low,  int_low,  def_low,  B_new_low  = compute_fiscal_balance(G, t, Y_base, r_base, B_low)
    rec_high, int_high, def_high, B_new_high = compute_fiscal_balance(G, t, Y_base, r_base, B_high)

    # Mayor deuda -> mayores intereses
    assert int_high > int_low, (
        f"Con B alto, los intereses deben ser mayores. "
        f"int_low={int_low:.2f}, int_high={int_high:.2f}"
    )
    # Mayor deficit acumulado
    assert def_high > def_low, (
        f"Con B alto, el deficit debe ser mayor. "
        f"def_low={def_low:.2f}, def_high={def_high:.2f}"
    )

    # Verificar que la deuda se acumula correctamente
    expected_B_new_low  = B_low  + def_low
    expected_B_new_high = B_high + def_high
    assert abs(B_new_low  - expected_B_new_low)  < TOL
    assert abs(B_new_high - expected_B_new_high) < TOL

    # El crowding-out se manifiesta en r mas alto bajo movilidad imperfecta:
    # con B alto, el soberano presiona la tasa -> r_star efectivo sube -> I_inv cae.
    # Aqui simulamos el efecto subiendo r_star en el escenario de alta deuda.
    r_high_debt = r_base + (int_high - int_low) / Y_base  # r efectivo mas alto

    I_inv_low_debt  = sp_base["I0"] - sp_base["b"] * r_base
    I_inv_high_debt = sp_base["I0"] - sp_base["b"] * r_high_debt

    assert I_inv_high_debt < I_inv_low_debt, (
        f"Con alta deuda, I_inv debe ser menor (crowding-out). "
        f"I_low={I_inv_low_debt:.4f}, I_high={I_inv_high_debt:.4f}"
    )


# =============================================================================
# TEST 13: AUDITORIA DE IDENTIDAD MACROECONOMICA (FASE 1.2)
# =============================================================================

def test_macroeconomic_identity_v21():
    """
    Verifica la identidad macroeconomica Y = C + I + G + NX para regimenes de TC
    Fijo y Flexible con los parametros estructurales y de politica por defecto.
    """
    sp: StructuralParams = dict(DEFAULT_STRUCTURAL_PARAMS)  # type: ignore[assignment]
    pi: PolicyInstruments = dict(DEFAULT_POLICY_INSTRUMENTS)  # type: ignore[assignment]
    
    Y_pot = 100.0
    P_NT = 1.0
    G = pi["G"]

    # 1. Caso Tipo de Cambio FIJO
    eq_fixed = eq_fixed_v2(sp=sp, pi=pi, Y_pot=Y_pot, P_NT=P_NT)
    Y_fix = eq_fixed["Y"]
    C_fix = eq_fixed["C"]
    I_fix = eq_fixed["I_inv"]
    NX_fix = eq_fixed["NX"]
    G_fix = eq_fixed["G_total"]  # usar G_total del equilibrio, no del snapshot

    assert abs(Y_fix - (C_fix + I_fix + G_fix + NX_fix)) < 1e-3, (
        f"La identidad macroeconomica no cuadra en TC Fijo: "
        f"Y={Y_fix:.6f}, C+I+G+NX={C_fix + I_fix + G_fix + NX_fix:.6f}, "
        f"diferencia={abs(Y_fix - (C_fix + I_fix + G_fix + NX_fix)):.6f}"
    )

    # 2. Caso Tipo de Cambio FLEXIBLE
    eq_flex = eq_flexible_v2(sp=sp, pi=pi, Y_pot=Y_pot, P_NT=P_NT, E_prev=pi["E"])
    Y_flx = eq_flex["Y"]
    C_flx = eq_flex["C"]
    I_flx = eq_flex["I_inv"]
    NX_flx = eq_flex["NX"]
    G_flx = eq_flex["G_total"]

    assert abs(Y_flx - (C_flx + I_flx + G_flx + NX_flx)) < 1e-3, (
        f"La identidad macroeconomica no cuadra en TC Flexible: "
        f"Y={Y_flx:.6f}, C+I+G+NX={C_flx + I_flx + G_flx + NX_flx:.6f}, "
        f"diferencia={abs(Y_flx - (C_flx + I_flx + G_flx + NX_flx)):.6f}"
    )


# =============================================================================
# TEST 14: AUDITORIA DE LA NUEVA CURVA BP CON SEPARACION UIP (FASE 1.2)
# =============================================================================

def test_bp_curve_uip_separation():
    """
    Verifica que la curva BP devuelva exactamente r_star + delta_E_expected + rho - (NX/f)
    cuando se especifica una prima de riesgo rho.
    """
    r_star = 5.0
    delta_E_expected = 0.10
    NX = -2.0
    f = 5.0
    rho = 0.05
    
    result = compute_bp_curve(
        r_star=r_star,
        delta_E_expected=delta_E_expected,
        NX=NX,
        f=f,
        rho=rho
    )
    
    expected = r_star + delta_E_expected + rho * 100.0 - (NX / f)
    
    assert abs(result - expected) < 1e-10, (
        f"La curva BP con separacion UIP falló. "
        f"Resultado={result:.6f}, Esperado={expected:.6f}, "
        f"diferencia={abs(result - expected):.6e}"
    )


# =============================================================================
# TEST 15: TEST DE ARANCELES (FASE 2.2)
# =============================================================================

def test_tariff_transmission_v21():
    """
    Efecto de la introducción de aranceles (tau = 0.20).
    Al introducir un arancel:
    1. Se reducen las importaciones (M_imp_1 < M_imp_0).
    2. Al reducirse las filtraciones al exterior, el multiplicador keynesiano
       efectivo de gasto doméstico aumenta (k_m_1 > k_m_0).
    """
    sp: StructuralParams = dict(DEFAULT_STRUCTURAL_PARAMS)
    pi: PolicyInstruments = dict(DEFAULT_POLICY_INSTRUMENTS)
    pi["regime"] = "fixed"
    
    # Equilibrio base con arancel tau = 0.0
    eq0 = eq_fixed_v2(sp=sp, pi=pi, Y_pot=100.0, P_NT=1.0)
    k_m_0 = eq0["mult"]
    M_imp_0 = eq0["M_imp"]
    
    # Equilibrio con arancel tau = 0.20
    pi_new = dict(pi)
    pi_new["tau"] = 0.20
    eq1 = eq_fixed_v2(sp=sp, pi=pi_new, Y_pot=100.0, P_NT=1.0)
    k_m_1 = eq1["mult"]
    M_imp_1 = eq1["M_imp"]
    
    # El arancel reduce la fuga por importaciones: el multiplicador efectivo sube
    assert k_m_1 > k_m_0, (
        f"El multiplicador efectivo k_m_1 ({k_m_1:.4f}) debe ser mayor que "
        f"k_m_0 ({k_m_0:.4f}) debido a la reducción de filtraciones (1-tau)."
    )
    
    # Las importaciones brutas deben caer
    assert M_imp_1 < M_imp_0, (
        f"Las importaciones brutas M_imp_1 ({M_imp_1:.4f}) deben caer "
        f"respecto a M_imp_0 ({M_imp_0:.4f}) tras el arancel."
    )


# =============================================================================
# TEST 16: TEST DE CONTROLES DE CAPITAL EN LA CURVA BP (FASE 2.2)
# =============================================================================

def test_capital_controls_bp_v21():
    """
    Controles de capital k_c reducen la movilidad f_eff = f * (1 - k_c).
    Bajo déficit comercial (NX = -10.0) y sensibilidad moderada (f = 5.0):
    - Sin controles (k_c = 0.0) -> r_0
    - Con controles fuertes (k_c = 0.8) -> r_1
    La tasa r_1 requerida para el equilibrio externo debe subir violentamente.
    """
    r_star = 5.0
    delta_E_expected = 0.0
    NX = -10.0
    f = 5.0
    
    # Escenario 1: Sin controles (k_c = 0)
    k_c_0 = 0.0
    f_eff_0 = max(f * (1.0 - k_c_0), 1e-4)
    r_0 = compute_bp_curve(r_star=r_star, delta_E_expected=delta_E_expected, NX=NX, f=f_eff_0)
    
    # Escenario 2: Controles fuertes (k_c = 0.8)
    k_c_1 = 0.8
    f_eff_1 = max(f * (1.0 - k_c_1), 1e-4)
    r_1 = compute_bp_curve(r_star=r_star, delta_E_expected=delta_E_expected, NX=NX, f=f_eff_1)
    
    # Tasa requerida debe subir significativamente para frenar salida de capitales
    assert r_1 > r_0, (
        f"La tasa requerida con controles fuertes ({r_1:.2f}%) debe ser "
        f"mayor que sin controles ({r_0:.2f}%)."
    )
    assert abs(r_0 - 7.0) < TOL
    assert abs(r_1 - 15.0) < TOL


# =============================================================================
# TEST 17: COMPOSICION DEL GASTO FISCAL (FASE 2.2)
# =============================================================================

def test_fiscal_composition_v21():
    """
    Compara gasto corriente vs. inversión pública con el mismo Gasto Total (G_total = 20):
    1. G_c = 20, I_g = 0
    2. G_c = 0, I_g = 20
    En el período actual (estático), ambos deben generar exactamente el mismo nivel de PIB (Y).
    """
    sp: StructuralParams = dict(DEFAULT_STRUCTURAL_PARAMS)
    pi_base: PolicyInstruments = dict(DEFAULT_POLICY_INSTRUMENTS)
    pi_base["regime"] = "fixed"
    
    # Escenario 1: Solo gasto corriente
    pi_1 = dict(pi_base)
    pi_1["G_c"] = 20.0
    pi_1["I_g"] = 0.0
    eq_1 = eq_fixed_v2(sp=sp, pi=pi_1, Y_pot=100.0, P_NT=1.0)
    
    # Escenario 2: Solo inversión pública
    pi_2 = dict(pi_base)
    pi_2["G_c"] = 0.0
    pi_2["I_g"] = 20.0
    eq_2 = eq_fixed_v2(sp=sp, pi=pi_2, Y_pot=100.0, P_NT=1.0)
    
    # A nivel estático, la demanda agregada total de G_total = 20 es idéntica
    assert abs(eq_1["Y"] - eq_2["Y"]) < TOL, (
        f"El PIB estático Y debe ser idéntico con igual G_total. "
        f"Y_1={eq_1['Y']:.6f}, Y_2={eq_2['Y']:.6f}"
    )
    assert abs(eq_1["G_total"] - 20.0) < TOL
    assert abs(eq_2["G_total"] - 20.0) < TOL


def test_dutch_disease_v21():
    """
    Verifica geométricamente y analíticamente el fenómeno de la Enfermedad Holandesa (Fase 3.2):
    Una apreciación nominal extrema del tipo de cambio (reducción drástica de E) reduce
    el precio transable P_T y consecuentemente el tipo de cambio real interno q_int = P_T / P_NT,
    lo que devora la participación del sector transable en la composición del PIB (share_T_1 < share_T_0).
    """
    sp: StructuralParams = dict(DEFAULT_STRUCTURAL_PARAMS)
    pi: PolicyInstruments = dict(DEFAULT_POLICY_INSTRUMENTS)
    
    Y_pot = 100.0
    P_NT = 1.0
    
    # 1. Equilibrio inicial con E_0 = 10.0
    pi_0 = dict(pi)
    pi_0["E"] = 10.0
    pi_0["regime"] = "fixed"
    eq_0 = eq_fixed_v2(sp=sp, pi=pi_0, Y_pot=Y_pot, P_NT=P_NT)
    
    q_int_0 = eq_0["q_int"]
    share_T_0 = eq_0["Y_T"] / eq_0["Y"]
    
    # 2. Equilibrio final con apreciación nominal extrema E_1 = 2.0
    pi_1 = dict(pi)
    pi_1["E"] = 2.0
    pi_1["regime"] = "fixed"
    eq_1 = eq_fixed_v2(sp=sp, pi=pi_1, Y_pot=Y_pot, P_NT=P_NT)
    
    q_int_1 = eq_1["q_int"]
    share_T_1 = eq_1["Y_T"] / eq_1["Y"]
    
    # Validaciones teóricas de Enfermedad Holandesa:
    assert q_int_1 < q_int_0, (
        f"El TCR interno q_int debería caer tras una apreciación real. "
        f"q_int_0={q_int_0:.4f}, q_int_1={q_int_1:.4f}"
    )
    assert share_T_1 < share_T_0, (
        f"El sector transable debería contraerse proporcionalmente (Enfermedad Holandesa). "
        f"share_T_0={share_T_0:.2%}, share_T_1={share_T_1:.2%}"
    )


# =============================================================================
# RUNNER DIRECTO (sin pytest)
# =============================================================================

if __name__ == "__main__":
    tests = [
        ("test_multiplier_proporcional",  test_multiplier_proporcional),
        ("test_ml_condition_holds",       test_ml_condition_holds),
        ("test_ml_condition_fails",       test_ml_condition_fails),
        ("test_j_curve_first_turn",       test_j_curve_first_turn),
        ("test_okun_uses_gap",            test_okun_uses_gap),
        ("test_phillips_uses_gap",        test_phillips_uses_gap),
        ("test_pass_through",             test_pass_through),
        ("test_bp_imperfect",             test_bp_imperfect),
        ("test_circuit_breaker",          test_circuit_breaker),
        ("test_crawling_peg",             test_crawling_peg),
        ("test_salter_swan_integrated",   test_salter_swan_integrated),
        ("test_deuda_crowding_out",       test_deuda_crowding_out),
        ("test_macroeconomic_identity_v21", test_macroeconomic_identity_v21),
        ("test_bp_curve_uip_separation",  test_bp_curve_uip_separation),
        ("test_tariff_transmission_v21",  test_tariff_transmission_v21),
        ("test_capital_controls_bp_v21",  test_capital_controls_bp_v21),
        ("test_fiscal_composition_v21",   test_fiscal_composition_v21),
        ("test_dutch_disease_v21",        test_dutch_disease_v21),
    ]

    passed, failed = 0, 0
    print("\n" + "="*65)
    print("  SUITE DE VERIFICACION ANALITICA — Motor V2.1")
    print("="*65)

    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}")
            print(f"        {e}")
            failed += 1

    print("-"*65)
    print(f"  Resultado: {passed}/{len(tests)} tests pasaron")
    if failed == 0:
        print(f"  CRITERIO DE ACEPTACION FASE 2: CUMPLIDO ({len(tests)}/{len(tests)})")
    else:
        print(f"  CRITERIO NO CUMPLIDO: {failed} tests fallaron")
    print("="*65 + "\n")

    sys.exit(0 if failed == 0 else 1)
