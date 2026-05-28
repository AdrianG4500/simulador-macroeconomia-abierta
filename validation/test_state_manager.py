"""
validation/test_state_manager.py
=================================
Suite de verificacion del motor de simulacion V2.0 — Fase 2.

Criterio de aceptacion Fase 2: 8/8 tests pasan.

Para ejecutar:
    python -m pytest validation/test_state_manager.py -v --tb=short
    python validation/test_state_manager.py

Tests:
    1. test_10_turns_no_crash         - 10 turnos sin excepciones
    2. test_circuit_breaker_fires     - R <= 0 bajo TC Fijo -> flexible forzado
    3. test_credibility_crisis        - Fixed->Flexible -> delta_E_expected = 0.25
    4. test_j_curve_two_turns         - NX cae con J-curve activa, sube al resolverse
    5. test_game_over_hyperinflation  - Politica que lleva pi > 150% -> game_over
    6. test_debt_snowball             - B crece aceleradamente con r alto y deficit
    7. test_crawling_peg_10_turns     - E_10 = E_0 * (1.02)^10
    8. test_endgame_delta_score       - Resumen endgame con delta_score correcto
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

from engine.state_manager_v2 import SimStateManagerV2
from config.parameters_v2 import DEFAULT_STRUCTURAL_PARAMS, DEFAULT_POLICY_INSTRUMENTS


# =============================================================================
# TEST 1: 10 TURNOS SIN CRASH
# =============================================================================

def test_10_turns_no_crash():
    """
    La simulacion completa de 10 turnos con parametros base no debe
    lanzar excepciones y debe dejar el estado en 'endgame'.
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("Economia_Saludable", "easy")
    mgr.start_simulation("fixed")

    snaps = []
    for i in range(10):
        snap = mgr.step_forward({})
        snaps.append(snap)
        # Si hubo game_over, la simulacion debe detenerse
        if mgr.state["status"] in ("game_over", "endgame"):
            break

    assert mgr.state["t"] == 10 or mgr.state["status"] == "game_over", (
        f"Despues de 10 turnos, t debe ser 10 o haber game_over. "
        f"t={mgr.state['t']}, status={mgr.state['status']}"
    )
    assert mgr.state["status"] in ("endgame", "game_over"), (
        f"Status debe ser 'endgame' o 'game_over', got '{mgr.state['status']}'"
    )
    assert len(mgr.state["history"]) == mgr.state["t"] + 1, (
        f"history debe tener t+1 entradas. "
        f"len={len(mgr.state['history'])}, t+1={mgr.state['t']+1}"
    )
    assert len(mgr.state["scores"]) == len(mgr.state["history"]), (
        "scores debe tener el mismo numero de entradas que history"
    )

    # Verificar que cada snapshot tiene los campos requeridos
    required_keys = {"t", "Y", "r", "E", "NX", "pi", "U", "gap", "score"}
    for snap in mgr.state["history"]:
        assert required_keys.issubset(snap.keys()), (
            f"Snapshot t={snap['t']} falta campos: {required_keys - snap.keys()}"
        )

    # Verificar que Y es positivo en todos los turnos
    for snap in mgr.state["history"]:
        assert snap["Y"] > 0, f"Y debe ser positivo en t={snap['t']}, got {snap['Y']}"


# =============================================================================
# TEST 2: CIRCUIT BREAKER (RESERVAS AGOTADAS)
# =============================================================================

def test_circuit_breaker_fires():
    """
    Con R inicial muy baja y NX muy negativo bajo TC Fijo,
    las reservas deben llegar a 0 y disparar el circuit breaker
    (regimen cambia a 'flexible' automaticamente).
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("Economia_Saludable")

    # Configurar crisis: reservas minimas y balanza comercial muy deficitaria
    mgr.state["R"] = 1.0
    mgr.state["structural"]["NX0"] = -60.0   # Enorme deficit comercial
    mgr.state["structural"]["f"] = 1e-4      # Baja movilidad para simular sudden stop

    mgr.start_simulation("fixed")

    # El primer turno debe agotar las reservas y disparar el circuit breaker
    snap = mgr.step_forward({})

    assert mgr.state["regime"] == "flexible", (
        f"Circuit Breaker debe cambiar regimen a 'flexible'. "
        f"Regimen actual: '{mgr.state['regime']}'"
    )

    # Debe haber un news item de crisis cambiaria
    crisis_news = [
        n for n in mgr.state["news_feed"]
        if n["severity"] == "critical"
    ]
    assert len(crisis_news) >= 1, (
        "Debe haber al menos un NewsItem critico tras el circuit breaker"
    )
    assert any("crisis" in n["category"].lower() for n in crisis_news), (
        "El NewsItem debe tener categoria 'crisis'"
    )

    # Debe haber advertencias del gabinete
    assert len(mgr.state["advisor_warnings"]) >= 1, (
        "Debe haber al menos una advertencia del gabinete tras el circuit breaker"
    )


# =============================================================================
# TEST 3: CRISIS DE CREDIBILIDAD (FIXED -> FLEXIBLE)
# =============================================================================

def test_credibility_crisis():
    """
    Un cambio manual de Fixed a Flexible debe:
    - Establecer delta_E_expected = 0.25
    - Agregar un NewsItem de crisis
    - Agregar una advertencia al gabinete
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("Economia_Saludable")
    mgr.start_simulation("fixed")

    # Cambio manual de regimen Fixed -> Flexible
    mgr.force_regime_change("flexible")

    assert mgr.state["delta_E_expected"] == 0.25, (
        f"delta_E_expected debe ser 0.25 tras crisis de credibilidad. "
        f"Actual: {mgr.state['delta_E_expected']}"
    )
    assert mgr.state["regime"] == "flexible", (
        f"Regimen debe cambiar a 'flexible'. Actual: '{mgr.state['regime']}'"
    )

    # Verificar news_feed
    credibility_news = [
        n for n in mgr.state["news_feed"]
        if n["severity"] == "critical"
    ]
    assert len(credibility_news) >= 1, (
        "Debe haber un NewsItem critico tras la crisis de credibilidad"
    )

    # Verificar advisor_warnings
    assert len(mgr.state["advisor_warnings"]) >= 1, (
        "Debe haber al menos una advertencia del gabinete"
    )

    # Despues del siguiente step_forward, delta_E_expected debe resetearse
    mgr.state["active_events"] = [
        "bank_panic", "social_unrest", "stagflation_trap", "virtuous_circle",
        "commodity_supercycle", "fed_rate_shock", "global_recession",
        "tech_productivity", "natural_disaster"
    ]
    snap = mgr.step_forward({"M": 50.0})   # M exogena bajo flexible

    assert mgr.state["delta_E_expected"] == 0.0, (
        f"delta_E_expected debe resetearse a 0.0 tras el turno. "
        f"Actual: {mgr.state['delta_E_expected']}"
    )


# =============================================================================
# TEST 4: EFECTO J-CURVE EN DOS TURNOS
# =============================================================================

def test_j_curve_two_turns():
    """
    Secuencia de J-curve:
    - Turno 1: Gran devaluacion -> j_curve_active = True para el sig. turno
    - Turno 2: j_curve_active = True -> NX usa epsilon_x_short (NX bajo)
    - Turno 3: j_curve_active = False -> NX usa epsilon_x estructural (NX alto)
    -> NX_turno2 < NX_turno3 (J-curve: cae, luego sube)
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("Economia_Saludable")
    mgr.start_simulation("fixed")

    E_inicial = mgr.state["policy"]["E"]  # E inicial (e.g. 10.0)

    # Turno 1: Gran devaluacion (> 2% umbral de J-curve)
    E_devaluada = E_inicial * 1.25   # 25% de devaluacion
    snap1 = mgr.step_forward({"E": E_devaluada})
    NX_t1 = snap1["NX"]

    # Verificar que j_curve_active se activo para el siguiente turno
    assert mgr.state["j_curve_active"] is True, (
        f"j_curve_active debe ser True tras devaluacion del 25%. "
        f"E_inicial={E_inicial:.2f}, E_nueva={E_devaluada:.2f}"
    )

    # Turno 2: Misma E, j_curve activa -> NX con epsilon_x_short
    snap2 = mgr.step_forward({"E": E_devaluada})
    NX_t2 = snap2["NX"]

    # j_curve_active debe ser False ahora (no hubo nueva devaluacion)
    assert mgr.state["j_curve_active"] is False, (
        "j_curve_active debe ser False si no hubo nueva devaluacion en turno 2"
    )

    # Turno 3: Misma E, sin j_curve -> NX con epsilon_x estructural
    snap3 = mgr.step_forward({"E": E_devaluada})
    NX_t3 = snap3["NX"]

    # La propiedad J-curve: NX_t2 < NX_t3 (la J-curve cae y luego sube)
    assert NX_t2 < NX_t3, (
        f"Efecto J-curve: NX debe ser menor cuando j_curve activa (t2) "
        f"que cuando se resuelve (t3). NX_t2={NX_t2:.4f}, NX_t3={NX_t3:.4f}"
    )

    # Verificar que la devaluacion efectivamente ocurrio
    assert snap1["E"] > E_inicial, (
        f"E debe haber aumentado en el turno de devaluacion. "
        f"E_inicial={E_inicial}, E_snap1={snap1['E']}"
    )


# =============================================================================
# TEST 5: GAME OVER POR HIPERINFLACION
# =============================================================================

def test_game_over_hyperinflation():
    """
    Con parametros extremos (alta pi_e, alta pendiente Phillips, gran devaluacion),
    la inflacion debe superar el 150% y disparar el Game Over.
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("Economia_Saludable", custom_params={"c0": 30.0, "I0": 30.0, "I_g": 0.0})

    # Configurar parametros para garantizar hiperinflacion
    mgr.state["structural"]["alpha_inf"] = 3.0    # Curva de Phillips muy empinada
    mgr.state["structural"]["beta_PT"]   = 0.5    # Pass-through alto
    mgr.state["pi_e"]                    = 1.0    # 100% de expectativas inflacionarias

    mgr.start_simulation("fixed")

    # Gran devaluacion: E se duplica (devaluation_rate = 1.0 = 100%)
    E_original = mgr.state["policy"]["E"]
    snap = mgr.step_forward({"E": E_original * 2.0})

    # pi = pi_e + alpha_inf*gap + beta_PT * devaluation_rate
    # >= 1.0 + 0 + 0.5*1.0 = 1.5 (limite)
    # Con cualquier gap > 0: pi > 1.5 -> game_over
    pi_t = snap["pi"]

    assert pi_t > 1.50, (
        f"Con parametros extremos, pi debe superar 1.50 (150%). "
        f"pi_t = {pi_t:.4f}"
    )
    assert mgr.state["status"] == "game_over", (
        f"Con pi > 150%, el estado debe ser 'game_over'. "
        f"Status actual: '{mgr.state['status']}'"
    )
    assert mgr.state["game_over_reason"] is not None, (
        "Debe haber una razon de game_over registrada"
    )
    # Verificar que la razon menciona la inflacion
    reason_lower = mgr.state["game_over_reason"].lower()
    assert "inflaci" in reason_lower or "hiper" in reason_lower, (
        f"La razon de game_over debe mencionar inflacion/hiperinflacion. "
        f"Razon: '{mgr.state['game_over_reason']}'"
    )


# =============================================================================
# TEST 6: EFECTO BOLA DE NIEVE DE LA DEUDA
# =============================================================================

def test_debt_snowball():
    """
    Con alta deuda inicial, alto gasto publico y altas tasas de interes,
    la deuda B debe crecer cada turno (efecto bola de nieve).
    La tasa de crecimiento de B debe ser no-decreciente (snowball effect).
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("Economia_Saludable")

    # Configurar escenario de deficit persistente
    mgr.state["B"] = 120.0           # Alta deuda inicial
    mgr.state["structural"]["t"] = 0.10   # Tasa impositiva baja
    mgr.state["policy"]["r_star"] = 8.0   # Alta tasa de interes internacional

    mgr.start_simulation("fixed")

    B_values = [mgr.state["B"]]
    for i in range(6):
        snap = mgr.step_forward({"G": 35.0})  # Gasto alto
        B_values.append(snap["B"])

        if mgr.state["status"] in ("game_over", "endgame"):
            break

    # B debe crecer en cada turno
    for i in range(len(B_values) - 1):
        assert B_values[i + 1] > B_values[i], (
            f"Deuda debe crecer cada turno. "
            f"B[{i}]={B_values[i]:.2f}, B[{i+1}]={B_values[i+1]:.2f}"
        )

    # Verificar aceleracion (snowball): el incremento debe ser no-decreciente
    # (al menos en los primeros periodos antes de que otros efectos dominen)
    deltas = [B_values[i + 1] - B_values[i] for i in range(len(B_values) - 1)]
    if len(deltas) >= 2:
        # Al menos el ultimo incremento no debe ser menor que el primero
        # (snowball: los intereses se acumulan sobre una base mayor)
        assert deltas[-1] >= deltas[0], (
            f"Efecto bola de nieve: el incremento de B debe acelerarse. "
            f"delta[0]={deltas[0]:.2f}, delta[-1]={deltas[-1]:.2f}"
        )


# =============================================================================
# TEST 7: CRAWLING PEG 10 TURNOS
# =============================================================================

def test_crawling_peg_10_turns():
    """
    Bajo crawling peg con tasa del 2% por turno,
    tras 10 turnos el tipo de cambio debe ser E_0 * (1.02)^10 ≈ E_0 * 1.2190.
    """
    mgr = SimStateManagerV2()
    mgr.calibrate("Economia_Saludable")

    E_0       = mgr.state["policy"]["E"]   # E inicial del escenario
    crawl     = 0.02
    mgr.state["policy"]["crawl_rate"] = crawl

    mgr.start_simulation("crawling_peg")

    for _ in range(10):
        mgr.step_forward({})
        if mgr.state["status"] == "game_over":
            pytest.skip("Simulacion termino en game_over antes de 10 turnos")

    # E esperada tras 10 turnos
    E_expected = E_0 * (1.0 + crawl) ** 10

    # El E del ultimo snapshot debe coincidir con E_expected
    E_final = mgr.state["history"][-1]["E"]

    assert abs(E_final - E_expected) < 0.05, (
        f"E_final = {E_final:.4f}, esperado {E_expected:.4f} "
        f"(E_0={E_0:.2f}, crawl={crawl}, 10 turnos). "
        f"Diferencia: {abs(E_final - E_expected):.6f}"
    )

    # Verificar que E crece monotonamente
    E_series = [snap["E"] for snap in mgr.state["history"]]
    for i in range(len(E_series) - 1):
        assert E_series[i + 1] >= E_series[i] - 1e-6, (
            f"E debe crecer monotonamente bajo crawling peg. "
            f"E[{i}]={E_series[i]:.4f}, E[{i+1}]={E_series[i+1]:.4f}"
        )


# =============================================================================
# TEST 8: ENDGAME DELTA SCORE
# =============================================================================

def test_endgame_delta_score():
    """
    Despues de completar 10 turnos, get_endgame_summary() debe:
    - Retornar un EndgameSummary valido con todos los campos requeridos
    - delta_score = score(t_final) - score(t=0)
    - verdict debe ser uno de los valores validos
    - total_score debe ser la suma de scores de los turnos jugados
    """
    mgr = SimStateManagerV2()
    # Dar suficientes reservas para aguantar 10 turnos de deficit comercial, y baja deuda para evitar default
    mgr.calibrate("Economia_Saludable", custom_initial_state={"R": 200.0, "B": 10.0})
    mgr.start_simulation("fixed")

    for _ in range(10):
        mgr.step_forward({})

    summary = mgr.get_endgame_summary()

    # Verificar campos requeridos
    required_keys = {
        "total_score", "avg_score_per_turn", "delta_score",
        "t0_snapshot", "t10_snapshot", "verdict", "dimension_deltas"
    }
    assert required_keys.issubset(summary.keys()), (
        f"EndgameSummary falta campos: {required_keys - summary.keys()}"
    )

    # Verificar tipos
    assert isinstance(summary["total_score"], int), "total_score debe ser int"
    assert isinstance(summary["delta_score"], float), "delta_score debe ser float"
    assert isinstance(summary["avg_score_per_turn"], float), "avg_score debe ser float"

    # Verificar veredicto
    assert summary["verdict"] in ("reelected", "removed", "impeached"), (
        f"verdict debe ser uno de: reelected/removed/impeached. "
        f"Got: '{summary['verdict']}'"
    )

    # Verificar consistencia del delta_score
    score_t0     = mgr.state["history"][0]["score"]
    score_final  = mgr.state["history"][-1]["score"]
    expected_delta = float(score_final - score_t0)
    assert abs(summary["delta_score"] - expected_delta) < 1.0, (
        f"delta_score inconsistente. "
        f"Calculado={summary['delta_score']}, "
        f"Esperado={expected_delta} (score_t0={score_t0}, score_final={score_final})"
    )

    # Verificar total_score: suma de scores de turnos 1-10
    turn_scores = mgr.state["scores"][1:]   # Excluir t=0
    assert summary["total_score"] == sum(turn_scores), (
        f"total_score={summary['total_score']}, "
        f"suma directa={sum(turn_scores)}"
    )

    # Verificar que dimension_deltas tiene las 5 dimensiones
    required_dims = {"Y", "U", "pi", "deficit_pct", "R"}
    assert required_dims.issubset(summary["dimension_deltas"].keys()), (
        f"dimension_deltas falta campos: {required_dims - summary['dimension_deltas'].keys()}"
    )

    # Verificar que el snapshot t0 y t10 son correctos
    assert summary["t0_snapshot"]["t"] == 0, "t0_snapshot debe ser t=0"
    assert summary["t10_snapshot"]["t"] == 10, (
        f"t10_snapshot debe ser t=10, got t={summary['t10_snapshot']['t']}"
    )

    # Si la economia se mantiene estable (no hay cambios de politica),
    # el delta_score deberia estar cerca de 0 (ni mejora ni empeora drasticamente)
    # Este es un test de cordura, no de valor exacto
    assert abs(summary["delta_score"]) <= 100.0, (
        f"delta_score fuera de rango razonable: {summary['delta_score']}"
    )


# =============================================================================
def test_sovereign_risk_crowding_out_v21():
    """
    Verifica la dinámica de Deuda Soberana y Crowding Out (Fase 3.2):
    1. Evalúa compute_sovereign_risk para confirmar que deuda hiper-tóxica (B = 500)
       da rating 'DEFAULT' y rho masivo (0.25).
    2. Pasa rho al solver y confirma que la tasa de interés interna r se dispara (r_B > r_A).
    3. Confirma que la Inversión Privada colapsa debido a esta tasa extrema (I_inv_B < I_inv_A),
       demostrando el crowding out por riesgo país.
    """
    from engine.dynamics_v2 import compute_sovereign_risk
    from engine.core_v2 import eq_fixed_v2
    from config.parameters_v2 import DEFAULT_STRUCTURAL_PARAMS, DEFAULT_POLICY_INSTRUMENTS

    Y_pot = 100.0
    R = 50.0

    # 1. Evaluar riesgo soberano para Deuda Baja vs Deuda Hiper-tóxica
    rho_A, rating_A = compute_sovereign_risk(B=10.0, Y_pot=Y_pot, R=R)
    rho_B, rating_B = compute_sovereign_risk(B=500.0, Y_pot=Y_pot, R=R)

    assert rating_A == "A", f"Deuda baja debería tener calificación A. Got: {rating_A}"
    assert rating_B == "DEFAULT", f"Deuda hiper-tóxica debería tener calificación DEFAULT. Got: {rating_B}"
    assert rho_B > rho_A, f"La prima rho de B debería ser mayor. rho_A={rho_A}, rho_B={rho_B}"
    assert abs(rho_B - 0.25) < 1e-6, f"La prima rho en DEFAULT debería ser 0.25. Got: {rho_B}"

    # 2. Pasar rho al solver eq_fixed_v2
    sp = dict(DEFAULT_STRUCTURAL_PARAMS)
    pi = dict(DEFAULT_POLICY_INSTRUMENTS)
    pi["regime"] = "fixed"

    eq_A = eq_fixed_v2(sp=sp, pi=pi, Y_pot=Y_pot, P_NT=1.0, rho=rho_A)
    eq_B = eq_fixed_v2(sp=sp, pi=pi, Y_pot=Y_pot, P_NT=1.0, rho=rho_B)

    # 3. Confirmar transmisión de tasa de interés e inversión
    assert eq_B["r"] > eq_A["r"], (
        f"La tasa de interés r se debería disparar con mayor prima de riesgo. "
        f"r_A={eq_A['r']:.4f}, r_B={eq_B['r']:.4f}"
    )
    assert eq_B["I_inv"] < eq_A["I_inv"], (
        f"La inversión privada I_inv debería colapsar por crowding out. "
        f"I_A={eq_A['I_inv']:.4f}, I_B={eq_B['I_inv']:.4f}"
    )


# =============================================================================
# TEST 10: FLOTACIÓN SUCIA (DIRTY FLOAT - FASE 4.1)
# =============================================================================

def test_dirty_float_v21():
    """
    Verifica el comportamiento del régimen de Flotación Sucia (Fase 4.1):
    1. Calibra Economia_Saludable con régimen 'dirty_float'.
    2. Establece una banda cambiaria superior E_band_upper = 11.0.
    3. Provoca una devaluación severa incrementando la oferta monetaria (M = 80.0).
    4. Confirma que el tipo de cambio nominal se acota exactamente en 11.0.
    5. Confirma que se registra una intervención cambiaria positiva (FX_intervention > 0)
       y que las reservas internacionales disminuyen por ese monto.
    """
    mgr = SimStateManagerV2()
    # Calibrar y setear régimen
    mgr.calibrate("Economia_Saludable", "easy")
    mgr.state["regime"] = "dirty_float"
    mgr.state["policy"]["regime"] = "dirty_float"

    # Registrar R anterior
    R_prev = mgr.state["R"]

    # Forzar banda superior y devaluación severa vía M = 80.0
    # Bajo dirty_float, E_band_upper por defecto es E_prev * 1.10 (11.0)
    mgr.start_simulation("dirty_float")
    snap = mgr.step_forward({"M": 80.0, "E_band_upper": 11.0})

    assert snap["E"] == 11.0, f"El tipo de cambio nominal debería estar acotado en 11.0. Got: {snap['E']}"
    assert snap["FX_intervention"] > 0.0, f"Debería registrarse una intervención cambiaria. Got: {snap['FX_intervention']}"

    # Verificar drenaje físico de reservas
    expected_R = round(R_prev - snap["FX_intervention"], 6)
    assert abs(snap["R"] - expected_R) < 1e-5, (
        f"Las reservas internacionales no cuadran tras la intervención. "
        f"R={snap['R']}, Esperado={expected_R}"
    )


# =============================================================================
# RUNNER DIRECTO (sin pytest)
# =============================================================================

if __name__ == "__main__":
    tests = [
        ("test_10_turns_no_crash",        test_10_turns_no_crash),
        ("test_circuit_breaker_fires",    test_circuit_breaker_fires),
        ("test_credibility_crisis",       test_credibility_crisis),
        ("test_j_curve_two_turns",        test_j_curve_two_turns),
        ("test_game_over_hyperinflation", test_game_over_hyperinflation),
        ("test_debt_snowball",            test_debt_snowball),
        ("test_crawling_peg_10_turns",    test_crawling_peg_10_turns),
        ("test_endgame_delta_score",      test_endgame_delta_score),
        ("test_sovereign_risk_crowding_out_v21", test_sovereign_risk_crowding_out_v21),
        ("test_dirty_float_v21",          test_dirty_float_v21),
    ]

    passed, failed = 0, 0
    print("\n" + "=" * 65)
    print("  SUITE DE VERIFICACION — State Manager V2.0 (Fase 2)")
    print("=" * 65)

    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}")
            print(f"        {e}")
            failed += 1

    print("-" * 65)
    print(f"  Resultado: {passed}/{len(tests)} tests pasaron")
    if failed == 0:
        print("  CRITERIO DE ACEPTACION FASE 2: CUMPLIDO (10/10)")
    else:
        print(f"  CRITERIO NO CUMPLIDO: {failed} tests fallaron")
    print("=" * 65 + "\n")

    sys.exit(0 if failed == 0 else 1)
