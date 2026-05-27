"""
engine/state_manager_v2.py
==========================
Orquestador del juego (Shadow Launch V2.0). Única clase que muta el GameState.

Flujo de partida (CLI y UI):
    mgr = SimStateManagerV2()
    mgr.calibrate(scenario_id, difficulty, custom_params, custom_initial_state)
    mgr.start_simulation(regime)
    for _ in range(10):
        snap = mgr.step_forward(policy_changes)
    summary = mgr.get_endgame_summary()

Principios arquitectónicos:
    - NO importa de ui/, streamlit, ni session_state.
    - Funciona completamente en aislamiento desde CLI/pytest.
    - La UI lee GameState; el StateManager escribe.
    - Cada llamada a step_forward sigue los 13 pasos definidos en la spec.

Jerarquía de imports:
    config/parameters_v2 → engine/core_v2 → engine/dynamics_v2
    → config/scoring_v2 → engine/game_state → engine/state_manager_v2
"""

from __future__ import annotations

import math
from typing import Optional

from config.parameters_v2 import (
    DEFAULT_POLICY_INSTRUMENTS,
    DEFAULT_STRUCTURAL_PARAMS,
    PolicyInstruments,
    StructuralParams,
    get_scenario_params,
)
from config.scoring_v2 import (
    calc_endgame_delta_score,
    calc_period_score_v2,
    check_game_over,
)
from engine.core_v2 import (
    compute_salter_swan,
    solve_equilibrium_v2,
)
from engine.dynamics_v2 import (
    check_reserve_circuit_breaker,
    compute_fiscal_balance,
    compute_inflation,
    compute_j_curve_flag,
    compute_output_gap,
    compute_sovereign_risk,
    compute_unemployment,
    update_adaptive_expectations,
    update_non_tradable_price,
    update_potential_output,
    update_reserves,
)
from engine.game_state import (
    EndgameSummary,
    GameState,
    NewsItem,
    TurnSnapshot,
)
from engine.events_engine import evaluate_events, apply_event_deltas
from engine.advisor_system import generate_advisor_warnings
import hashlib


class SimStateManagerV2:
    """
    Orquestador del juego. Única clase que muta el GameState.

    Atributos
    ---------
    state : GameState | None
        Estado actual de la simulación. None hasta llamar calibrate().
    """

    def __init__(self) -> None:
        self.state: Optional[GameState] = None

    @property
    def t(self) -> int:
        if self.state is None:
            return 0
        return self.state["t"]

    @property
    def status(self) -> str:
        if self.state is None:
            return "init"
        return self.state["status"]

    # ─────────────────────────────────────────────────────────────────────────
    # CALIBRACIÓN
    # ─────────────────────────────────────────────────────────────────────────

    def calibrate(
        self,
        scenario_id: str = "Economia_Saludable",
        difficulty: str = "easy",
        custom_params: Optional[dict] = None,
        custom_initial_state: Optional[dict] = None,
    ) -> GameState:
        """
        Inicializa el GameState con los parámetros del escenario y calcula t=0.

        Pasos:
        1. Cargar preset del escenario.
        2. Aplicar custom_params (override de parámetros estructurales/política).
        3. Aplicar custom_initial_state (override de R₀, B₀, pi_e₀, Y_pot₀).
        4. Calcular equilibrio t=0 (sin shocks ni cambios de política).
        5. Construir history[0] (TurnSnapshot de referencia).
        6. Inicializar GameState con status="calibrated".

        Parameters
        ----------
        scenario_id          : ID del escenario (ver config/parameters_v2.py)
        difficulty           : "easy" | "hard"
        custom_params        : Overrides de StructuralParams o PolicyInstruments
        custom_initial_state : Overrides de estado inicial (R, B, pi_e, Y_pot)

        Returns
        -------
        GameState : Estado inicializado (status="calibrated")
        """
        # 1. Cargar escenario
        try:
            sp, pi, init_state = get_scenario_params(scenario_id)
        except (KeyError, AttributeError):
            sp = dict(DEFAULT_STRUCTURAL_PARAMS)
            pi = dict(DEFAULT_POLICY_INSTRUMENTS)
            init_state = {
                "Y_pot": sp["Y_pot_0"],
                "P_NT":  1.0,
                "pi_e":  0.03,
                "R":     50.0,
                "B":     60.0,
            }

        # 2. Aplicar custom_params
        if custom_params:
            for key, val in custom_params.items():
                if key in sp:
                    sp[key] = val
                elif key in pi:
                    pi[key] = val

        # Sincronizar t_c con t si t_c no fue modificado pero t sí
        if pi.get("t_c") == 0.20 and sp.get("t") != 0.20:
            pi["t_c"] = sp["t"]

        # Sincronizar G_c e I_g si G no coincide con G_c + I_g
        if pi.get("G") != pi.get("G_c", 0.0) + pi.get("I_g", 0.0):
            pi["G_c"] = pi["G"] - pi.get("I_g", 0.0)

        # 3. Aplicar custom_initial_state
        if custom_initial_state:
            for key, val in custom_initial_state.items():
                init_state[key] = val

        # Extraer valores del estado inicial
        Y_pot_0 = float(init_state.get("Y_pot", sp.get("Y_pot_0", 100.0)))
        P_NT_0  = float(init_state.get("P_NT", 1.0))
        pi_e_0  = float(init_state.get("pi_e", 0.03))
        R_0     = float(init_state.get("R", 50.0))
        B_0     = float(init_state.get("B", 60.0))

        # Calcular riesgo soberano t=0
        rho_0, rating_0 = compute_sovereign_risk(B_0, Y_pot_0, R_0)

        # 4. Calcular equilibrio t=0
        eq0 = solve_equilibrium_v2(
            sp=sp, pi=pi,
            Y_pot=Y_pot_0, P_NT=P_NT_0,
            E_prev=pi["E"],
            j_curve_active=False,
            delta_E_expected=0.0,
            rho=rho_0 * 100.0,  # FASE 3.1
        )

        # Variables derivadas t=0
        gap_0 = compute_output_gap(eq0["Y"], Y_pot_0)
        U_0   = compute_unemployment(sp["U_n"], sp["gamma_okun"], gap_0)
        pi_t0 = pi_e_0  # En t=0, inflación actual = expectativas (sin shocks)

        # Finanzas públicas t=0
        rec_0, _int_0, def_0, _B_upd = compute_fiscal_balance(
            G=pi["G"],
            t=sp["t"],
            Y=eq0["Y"],
            r=eq0["r"],
            B_prev=B_0,
            G_c=pi.get("G_c", 15.0),
            I_g=pi.get("I_g", 5.0),
            Tr=pi.get("Tr", 0.0),
            t_c=pi.get("t_c", sp.get("t", 0.20)),
            t_k=pi.get("t_k", 0.0),
            tau=pi.get("tau", 0.0),
            M_imp=eq0.get("M_imp", 0.0),
            r_star=pi.get("r_star", 5.0),
            rho=rho_0,
        )
        deficit_pct_0 = def_0 / max(eq0["Y"], 1e-6)

        # Score t=0 (referencia)
        score_0 = calc_period_score_v2(
            gap=gap_0, U=U_0, pi=pi_t0,
            deficit_pct=deficit_pct_0,
            R=R_0, R_0=R_0,
        )

        # Salter-Swan t=0
        ss_0 = compute_salter_swan(eq0, sp, pi["G"])

        # Determinar E y M del snapshot (según régimen)
        regime_0 = pi.get("regime", "fixed")
        E_0 = pi["E"]
        M_endo_raw = eq0.get("M_endo", float("nan"))
        M_0 = M_endo_raw if not math.isnan(M_endo_raw) else pi["M"]

        # 5. Construir TurnSnapshot t=0
        snapshot_0: TurnSnapshot = {
            "t":              0,
            "Y":              round(eq0["Y"], 4),
            "r":              round(eq0["r"], 4),
            "E":              round(E_0, 4),
            "M":              round(M_0, 4),
            "NX":             round(eq0["NX"], 4),
            "C":              round(eq0["C"], 4),
            "I_inv":          round(eq0["I_inv"], 4),
            "G":              pi["G"],
            "recaudacion":    round(rec_0, 4),
            "deficit":        round(def_0, 4),
            "B":              round(B_0, 2),
            "R":              round(R_0, 4),
            "pi":             round(pi_t0, 4),
            "pi_e":           round(pi_e_0, 4),
            "U":              round(U_0, 4),
            "gap":            round(gap_0, 4),
            "gY":             0.0,
            "q_real":         round(eq0["q_real"], 4),
            "A_domestic":     round(eq0["A_domestic"], 4),
            "P_local":        round(eq0["P_local"], 4),
            "zone_ss":        ss_0["zone"],
            "score":          score_0,
            "mult":           round(eq0["mult"], 4),
            "policy_applied": dict(pi),
            "events_triggered": [],
            "X":              round(eq0.get("X", float("nan")), 4),
            "M_imp":          round(eq0.get("M_imp", float("nan")), 4),
            "Y_T":            round(eq0.get("Y_T", 0.0), 4),
            "Y_NT":           round(eq0.get("Y_NT", 0.0), 4),
            "rho":            round(rho_0, 4),
            "rating":         rating_0,
            "FX_intervention": 0.0,
        }

        # 6. Inicializar GameState
        self.state = {
            "scenario_id":      scenario_id,
            "difficulty":       difficulty,
            "regime":           regime_0,
            "t":                0,
            "status":           "calibrated",
            "game_over_reason": None,
            "structural":       sp,
            "policy":           pi,
            "Y_pot":            Y_pot_0,
            "P_local":          eq0["P_local"],
            "P_NT":             P_NT_0,
            "pi_e":             pi_e_0,
            "delta_E_expected": 0.0,
            "j_curve_active":   False,
            "R":                R_0,
            "B":                B_0,
            "history":          [snapshot_0],
            "active_events":    [],
            "news_feed":        [],
            "advisor_warnings": [],
            "scores":           [score_0],
            "delta_score":      None,
        }

        return self.state

    # ─────────────────────────────────────────────────────────────────────────
    # INICIO DE SIMULACIÓN
    # ─────────────────────────────────────────────────────────────────────────

    def start_simulation(self, regime: str) -> None:
        """
        Establece el régimen inicial y avanza el estado a "running".

        Debe llamarse después de calibrate() y antes del primer step_forward().

        Parameters
        ----------
        regime : Régimen cambiario: "fixed" | "flexible" | "crawling_peg"

        Raises
        ------
        RuntimeError
            Si el estado no está en "calibrated".
        """
        if self.state is None:
            raise RuntimeError("Debe llamar calibrate() antes de start_simulation().")
        if self.state["status"] != "calibrated":
            raise RuntimeError(
                f"start_simulation() requiere status='calibrated', "
                f"actual: '{self.state['status']}'."
            )
        self.state["regime"]          = regime
        self.state["policy"]["regime"] = regime
        self.state["status"]           = "running"

    # ─────────────────────────────────────────────────────────────────────────
    # AVANCE DE TURNO (NÚCLEO DEL JUEGO)
    # ─────────────────────────────────────────────────────────────────────────

    def step_forward(
        self,
        policy_changes: Optional[dict] = None,
        shock_key: Optional[str] = None,
    ) -> TurnSnapshot:
        """
        Avanza la simulación un turno siguiendo los 13 pasos de la spec.

        Secuencia fija (no reordenable):
            1.  Validar estado
            2.  Aplicar cambios de política y detectar cambio de régimen
            3.  Resolver Y_pot del turno
            4.  Calcular equilibrio IS-LM-BP-V2
            5.  Calcular variables derivadas (gap, gY, pi, U, etc.)
            6.  Calcular dinámicas fiscales y externas
            7.  Verificar Circuit Breaker (R ≤ 0 bajo TC Fijo)
            8.  Evaluar Salter-Swan dinámico
            9.  Procesar eventos (stub para Fase 3)
            10. Calcular score del turno
            11. Guardar TurnSnapshot en history
            12. Actualizar GameState (t += 1)
            13. Verificar condiciones de Game Over

        Parameters
        ----------
        policy_changes : dict, optional
            Cambios en los instrumentos de política. Claves válidas:
            G, E, M, r_star, regime, crawl_rate
        shock_key : str, optional
            Identificador de shock exógeno (Fase 3).

        Returns
        -------
        TurnSnapshot : Snapshot del turno completado.

        Raises
        ------
        RuntimeError
            Si el estado no está en "running" o t >= 10.
        """
        state = self.state

        # ── PASO 1: VALIDAR ───────────────────────────────────────────────────
        if state is None:
            raise RuntimeError(
                "Debe llamar calibrate() y start_simulation() primero."
            )
        if state["status"] != "running":
            raise RuntimeError(
                f"step_forward() requiere status='running'. "
                f"Estado actual: '{state['status']}'."
            )
        if state["t"] >= 10:
            raise RuntimeError(
                f"La simulación completó 10 turnos. Estado: '{state['status']}'."
            )

        # ── PASO 2: APLICAR CAMBIOS DE POLÍTICA ───────────────────────────────
        t_new = state["t"] + 1
        sp: StructuralParams = dict(state["structural"])
        pi: PolicyInstruments = dict(state["policy"])
        old_regime = state["regime"]

        # delta_E_expected puede ser 0.25 si hubo crisis de credibilidad el turno anterior
        delta_E_expected = state["delta_E_expected"]

        if policy_changes:
            for key, val in policy_changes.items():
                if key in pi:
                    pi[key] = val
                elif key in sp:
                    sp[key] = val

        # Sincronizar t_c con t si t_c no fue modificado pero t sí
        if pi.get("t_c") == 0.20 and sp.get("t") != 0.20:
            pi["t_c"] = sp["t"]

        # Sincronizar G_c e I_g si G no coincide con G_c + I_g o si G cambió
        if "G" in (policy_changes or {}) or pi.get("G") != pi.get("G_c", 0.0) + pi.get("I_g", 0.0):
            pi["G_c"] = pi["G"] - pi.get("I_g", 0.0)

        # Detectar cambio de régimen solicitado por el jugador
        new_regime = pi.get("regime", old_regime)
        if new_regime != old_regime:
            state["policy"] = pi
            self.force_regime_change(new_regime)
            pi = dict(state["policy"])
            delta_E_expected = state["delta_E_expected"]  # Actualizar tras force_regime_change

        regime = pi["regime"]

        # ── FILTRO DEL TRILEMA (V2.1) ─────────────────────────────────────────
        # Bajo TC Fijo o Crawling Peg la oferta monetaria es ENDÓGENA:
        # el banco central sacrifica M para mantener E. Cualquier cambio
        # que el jugador intente sobre M se ignora (ya lo calcula eq_fixed).
        if regime in ("fixed", "crawling_peg"):
            if "M" in (policy_changes or {}):
                import logging as _lg
                _lg.getLogger(__name__).info(
                    "[Trilema] Cambio de M ignorado bajo régimen '%s'. "
                    "M es endógena bajo TC Fijo / Crawling Peg.", regime
                )
                pi.pop("M", None)  # M la calcula eq_fixed; no se sobreescribe

        # Controles de Capital: si el jugador activa k_c > 0 bajo movilidad
        # perfecta anterior (k_c==0), loggear la transición. La matemática
        # (f_eff = f*(1-k_c)) se encarga del resto.
        old_kc = float(state["policy"].get("k_c", 0.0))
        new_kc = float(pi.get("k_c", old_kc))
        if old_kc == 0.0 and new_kc > 0.0:
            import logging as _lg
            _lg.getLogger(__name__).info(
                "[Trilema] Controles de capital activados (k_c=%.2f). "
                "Transición a movilidad imperfecta implícita: f_eff = f*(1-k_c).",
                new_kc
            )
            state["news_feed"].append(NewsItem(
                t=state["t"] + 1,
                category="policy",
                message=(
                    f"🛡️ CONTROLES DE CAPITAL: Se restringen los flujos financieros "
                    f"(k_c={new_kc:.0%}). La movilidad de capitales efectiva se reduce. "
                    "La curva BP se vuelve más empinada."
                ),
                severity="warning",
            ))
        # ────────────────────────────────────────────────────────────────────

        # ── PASO 3: RESOLVER Y_pot ────────────────────────────────────────────
        endogenous_shock = 0.0   # Fase 3: eventos endógenos pueden modificar esto
        Y_pot = update_potential_output(
            state["Y_pot"],
            sp["g_pot"],
            endogenous_shock,
            I_g=pi.get("I_g", 0.0),
        )

        # Valores del turno anterior (de la última entrada del historial)
        prev = state["history"][-1]
        E_prev = prev["E"]
        Y_prev = prev["Y"]
        r_prev = prev["r"]

        # j_curve_active: flag del estado (fue seteado al final del turno anterior)
        j_curve_active = state["j_curve_active"]

        # ── PASO 4: CALCULAR EQUILIBRIO IS-LM-BP ─────────────────────────────
        # Calcular riesgo país al inicio del turno basado en las variables del turno anterior
        rho, rating = compute_sovereign_risk(state["B"], state["Y_pot"], state["R"])

        is_intervention = False
        intervention_amount = 0.0
        E_band_upper = None

        if regime == "dirty_float":
            E_band_upper = pi.get("E_band_upper")
            if E_band_upper is None:
                E_band_upper = E_prev * 1.10

            # Resolver equilibrio flexible puro temporalmente
            pi_temp = dict(pi)
            pi_temp["regime"] = "flexible"
            eq = solve_equilibrium_v2(
                sp=sp,
                pi=pi_temp,
                Y_pot=Y_pot,
                P_NT=state["P_NT"],
                E_prev=E_prev,
                Y_prev=Y_prev,
                r_prev=r_prev,
                j_curve_active=j_curve_active,
                delta_E_expected=delta_E_expected,
                rho=rho * 100.0,
            )

            # Si el tipo de cambio endógeno supera la banda
            if eq["E_endo"] > E_band_upper:
                is_intervention = True
                # Re-resolver en TC fijo con E = E_band_upper
                pi_temp["regime"] = "fixed"
                pi_temp["E"] = E_band_upper
                eq = solve_equilibrium_v2(
                    sp=sp,
                    pi=pi_temp,
                    Y_pot=Y_pot,
                    P_NT=state["P_NT"],
                    E_prev=E_prev,
                    Y_prev=Y_prev,
                    r_prev=r_prev,
                    j_curve_active=j_curve_active,
                    delta_E_expected=delta_E_expected,
                    rho=rho * 100.0,
                )
                intervention_amount = max(0.0, (pi["M"] - eq["M_endo"]) / E_band_upper)
            else:
                is_intervention = False
                intervention_amount = 0.0
        else:
            eq = solve_equilibrium_v2(
                sp=sp,
                pi=pi,
                Y_pot=Y_pot,
                P_NT=state["P_NT"],
                E_prev=E_prev,
                Y_prev=Y_prev,
                r_prev=r_prev,
                j_curve_active=j_curve_active,
                delta_E_expected=delta_E_expected,
                rho=rho * 100.0,
            )

        # ── PASO 5: VARIABLES DERIVADAS ───────────────────────────────────────
        Y = eq["Y"]
        r = eq["r"]
        gap = compute_output_gap(Y, Y_pot)
        gY  = (Y - Y_prev) / max(abs(Y_prev), 1e-6)

        # Determinar E_current y M_snap según régimen
        M_endo_raw = eq.get("M_endo", float("nan"))
        E_endo_raw = eq.get("E_endo", float("nan"))

        if regime == "fixed":
            E_current = pi["E"]
            M_snap = M_endo_raw if not math.isnan(M_endo_raw) else pi["M"]

        elif regime == "flexible":
            E_current = E_endo_raw if not math.isnan(E_endo_raw) else E_prev
            M_snap = pi["M"]
            pi["E"] = E_current          # Track E actual para el próximo turno

        elif regime == "crawling_peg":
            crawl_rate = pi.get("crawl_rate", 0.02)
            E_current = (
                E_endo_raw if not math.isnan(E_endo_raw)
                else E_prev * (1.0 + crawl_rate)
            )
            M_snap = M_endo_raw if not math.isnan(M_endo_raw) else pi["M"]
            pi["E"] = E_current          # Actualizar E para el próximo turno

        elif regime == "dirty_float":
            if is_intervention:
                E_current = E_band_upper
                M_snap = eq["M_endo"]
            else:
                E_current = E_endo_raw if not math.isnan(E_endo_raw) else E_prev
                M_snap = pi["M"]
            pi["E"] = E_current

        else:
            E_current = E_prev
            M_snap = pi["M"]

        delta_E = E_current - E_prev

        # Inflación del período (Phillips con pass-through)
        pi_t = compute_inflation(
            pi_e=state["pi_e"],
            alpha_inf=sp["alpha_inf"],
            gap=gap,
            beta_PT=sp["beta_PT"],
            delta_E=delta_E,
            E_prev=max(E_prev, 1e-9),
            pi_0=sp.get("pi_0", 0.0),
        )

        # Desempleo (Okun con gap)
        U = compute_unemployment(sp["U_n"], sp["gamma_okun"], gap)

        # Expectativas adaptativas para el próximo turno
        pi_e_new = update_adaptive_expectations(pi_t)

        # Precio de no-transables: crece con inflación núcleo (sin pass-through).
        # FIX DT-4: pi_core se acota a 0 para evitar deflación absurda de P_NT
        # en períodos de devaluación fuerte donde beta_PT·(ΔE/E) > pi_t.
        devaluation_rate = delta_E / max(E_prev, 1e-9)
        pi_core = max(0.0, pi_t - sp["beta_PT"] * devaluation_rate)
        P_NT_new = update_non_tradable_price(state["P_NT"], pi_core)

        # J-curve flag para el PRÓXIMO turno (¿hubo devaluación significativa?)
        j_curve_next = compute_j_curve_flag(E_current, E_prev)

        # Resetear delta_E_expected (ya fue usado en el equilibrio de este turno)
        state["delta_E_expected"] = 0.0

        # ── PASO 6: DINÁMICAS FISCALES Y EXTERNAS ────────────────────────────
        # pi["G"] = G_total fue sincronizado por eq_fixed/eq_flexible
        G_snap = eq.get("G_total", pi.get("G", pi.get("G_c", 0.0) + pi.get("I_g", 0.0)))
        rec, interests, deficit, B_new = compute_fiscal_balance(
            G=G_snap,
            t=pi.get("t_c", sp.get("t", 0.20)),
            Y=Y,
            r=r,
            B_prev=state["B"],
            G_c=pi.get("G_c"),
            I_g=pi.get("I_g"),
            Tr=pi.get("Tr", 0.0),
            t_c=pi.get("t_c"),
            t_k=pi.get("t_k", 0.0),
            tau=pi.get("tau", 0.0),
            M_imp=eq.get("M_imp", 0.0),
            r_star=pi.get("r_star"),
            rho=rho,
        )
        R_new = update_reserves(state["R"], eq["NX"], regime)
        if regime == "dirty_float" and is_intervention:
            R_new = round(R_new - intervention_amount, 6)

        # ── PASO 7: CIRCUIT BREAKER ───────────────────────────────────────────
        crisis_fired, new_regime_cb, E_crisis = check_reserve_circuit_breaker(
            R=R_new, regime=regime, E_current=E_current
        )

        if crisis_fired:
            state["regime"] = "flexible"
            pi["regime"]    = "flexible"
            pi["M"]         = M_snap   # Inherit endogenous M to avoid sudden contraction
            E_current       = E_crisis
            delta_E         = E_current - E_prev
            j_curve_next    = True   # Devaluación de crisis activa J-curve

            state["news_feed"].append(NewsItem(
                t=state["t"] + 1,
                category="crisis",
                message=(
                    "⚠️ CRISIS CAMBIARIA: Las reservas internacionales se agotaron. "
                    f"El banco central abandona la paridad. "
                    f"E se devalúa automáticamente a {E_current:.2f}."
                ),
                severity="critical",
            ))
            state["advisor_warnings"].append(
                "El tipo de cambio ahora flota libremente. "
                "Controla la oferta monetaria para estabilizar la economía."
            )

        # ── PASO 8: SALTER-SWAN DINÁMICO ──────────────────────────────────────
        A_ref = state["history"][0]["A_domestic"]
        q_ref = state["history"][0]["q_real"]
        ss = compute_salter_swan(eq, sp, G_snap, A_ref=A_ref, q_ref=q_ref)

        # ── PASO 9: PROCESAR EVENTOS (REAL — FASE 3) ──────────────────────────
        events_triggered: list[str] = []

        # Construir TurnSnapshot provisional para que el evaluador pueda ver las variables de este turno
        provisional_snap: TurnSnapshot = {
            "t":              t_new,
            "Y":              round(Y, 4),
            "r":              round(r, 4),
            "E":              round(E_current, 4),
            "M":              round(M_snap, 4),
            "NX":             round(eq["NX"], 4),
            "C":              round(eq["C"], 4),
            "I_inv":          round(eq["I_inv"], 4),
            "G":              G_snap,
            "recaudacion":    round(rec, 4),
            "deficit":        round(deficit, 4),
            "B":              round(B_new, 2),
            "R":              round(R_new, 4),
            "pi":             round(pi_t, 4),
            "pi_e":           round(state["pi_e"], 4),
            "U":              round(U, 4),
            "gap":            round(gap, 4),
            "gY":             round(gY, 4),
            "q_real":         round(eq["q_real"], 4),
            "A_domestic":     round(eq["A_domestic"], 4),
            "P_local":        round(eq["P_local"], 4),
            "zone_ss":        ss["zone"],
            "score":          0,  # Provisional
            "mult":           round(eq["mult"], 4),
            "policy_applied": dict(pi),
            "events_triggered": [],
            "X":              round(eq.get("X", float("nan")), 4),
            "M_imp":          round(eq.get("M_imp", float("nan")), 4),
            "Y_T":            round(eq.get("Y_T", 0.0), 4),
            "Y_NT":           round(eq.get("Y_NT", 0.0), 4),
            "rho":            round(rho, 4),
            "rating":         rating,
            "FX_intervention": round(intervention_amount, 4),
        }

        # Guardar en historial temporalmente
        state["history"].append(provisional_snap)

        # Generar semilla reproducible a partir de scenario_id + t_new
        seed_str = f"{state['scenario_id']}_{t_new}"
        seed_int = int(hashlib.sha256(seed_str.encode('utf-8')).hexdigest(), 16) % 10**8

        # Evaluar eventos disparados
        events = evaluate_events(state, seed_int)

        # Quitar el snapshot provisional del historial
        state["history"].pop()

        # Si hay un shock manual solicitado desde CLI/UI, añadirlo como exógeno si no está activo
        if shock_key and shock_key not in state.get("active_events", []):
            from engine.events_engine import EXOGENOUS_EVENTS_DEFS, GameEvent
            if shock_key in EXOGENOUS_EVENTS_DEFS:
                ev_def = EXOGENOUS_EVENTS_DEFS[shock_key]
                shock_event = GameEvent(
                    event_id=shock_key,
                    type="exogenous",
                    headline=ev_def["headline"],
                    narrative=ev_def["narrative"],
                    impact_text=ev_def["impact_text"],
                    param_deltas=ev_def["param_deltas"],
                    prob=ev_def["prob"],
                    triggered_at=t_new
                )
                events.append(shock_event)

        # Aplicar los deltas de los eventos
        for ev in events:
            apply_event_deltas(state, ev)
            events_triggered.append(ev["event_id"])

        # ── PASO 10: CALCULAR SCORE ───────────────────────────────────────────
        deficit_pct = deficit / max(Y, 1e-6)
        R_0_ref     = state["history"][0]["R"]   # Reservas iniciales como referencia
        score_t     = calc_period_score_v2(
            gap=gap, U=U, pi=pi_t,
            deficit_pct=deficit_pct,
            R=R_new, R_0=R_0_ref,
        )

        # ── PASO 11: GUARDAR SNAPSHOT ─────────────────────────────────────────
        snap: TurnSnapshot = {
            "t":              t_new,
            "Y":              round(Y, 4),
            "r":              round(r, 4),
            "E":              round(E_current, 4),
            "M":              round(M_snap, 4),
            "NX":             round(eq["NX"], 4),
            "C":              round(eq["C"], 4),
            "I_inv":          round(eq["I_inv"], 4),
            "G":              G_snap,
            "recaudacion":    round(rec, 4),
            "deficit":        round(deficit, 4),
            "B":              round(B_new, 2),
            "R":              round(R_new, 4),
            "pi":             round(pi_t, 4),
            "pi_e":           round(state["pi_e"], 4),
            "U":              round(U, 4),
            "gap":            round(gap, 4),
            "gY":             round(gY, 4),
            "q_real":         round(eq["q_real"], 4),
            "A_domestic":     round(eq["A_domestic"], 4),
            "P_local":        round(eq["P_local"], 4),
            "zone_ss":        ss["zone"],
            "score":          score_t,
            "mult":           round(eq["mult"], 4),
            "policy_applied": dict(pi),
            "events_triggered": events_triggered,
            "X":              round(eq.get("X", float("nan")), 4),
            "M_imp":          round(eq.get("M_imp", float("nan")), 4),
            "Y_T":            round(eq.get("Y_T", 0.0), 4),
            "Y_NT":           round(eq.get("Y_NT", 0.0), 4),
            "rho":            round(rho, 4),
            "rating":         rating,
            "FX_intervention": round(intervention_amount, 4),
        }

        state["history"].append(snap)
        state["scores"].append(score_t)

        # ── PASO 12: ACTUALIZAR GAMESTATE ─────────────────────────────────────
        state["t"]             = t_new
        state["Y_pot"]         = Y_pot
        state["P_local"]       = eq["P_local"]
        state["P_NT"]          = P_NT_new
        state["pi_e"]          = pi_e_new
        state["j_curve_active"] = j_curve_next
        state["R"]             = R_new
        state["B"]             = B_new
        state["structural"]    = sp
        state["policy"]        = pi

        if state["t"] >= 10:
            state["status"] = "endgame"

        # ── PASO 13: VERIFICAR GAME OVER ─────────────────────────────────────
        game_over, reason = check_game_over(
            gY=gY, U=U, pi=pi_t,
            R=R_new, regime=regime,
            B=B_new, Y=Y,
        )
        if game_over and state["status"] != "endgame":
            state["status"]           = "game_over"
            state["game_over_reason"] = reason

        # Generar advisor warnings para el siguiente turno (t + 1)
        state["advisor_warnings"] = generate_advisor_warnings(state)

        return snap

    # ─────────────────────────────────────────────────────────────────────────
    # CAMBIO FORZADO DE RÉGIMEN
    # ─────────────────────────────────────────────────────────────────────────

    def force_regime_change(self, new_regime: str) -> None:
        """
        Aplica un cambio manual de régimen con sus consecuencias económicas.

        Transiciones y sus efectos:
        - Fixed → Flexible : Crisis de Credibilidad (delta_E_expected = 0.25)
        - Flexible → Fixed  : Requiere R suficientes para defender la paridad
        - Cualquier → Crawling: Transición neutral
        - Crawling → Cualquier: Transición neutral

        Parameters
        ----------
        new_regime : Nuevo régimen: "fixed" | "flexible" | "crawling_peg"

        Raises
        ------
        RuntimeError
            Si no hay estado activo.
        """
        if self.state is None:
            raise RuntimeError("No hay estado activo. Llame calibrate() primero.")

        state     = self.state
        old_regime = state["regime"]

        if old_regime == new_regime:
            return

        # Aplicar el cambio
        state["regime"]           = new_regime
        state["policy"]["regime"] = new_regime

        # Consecuencias de la transición
        if old_regime == "fixed" and new_regime == "flexible":
            # Crisis de Credibilidad: el mercado anticipa una devaluación del 25%
            state["delta_E_expected"] = 0.25
            state["news_feed"].append(NewsItem(
                t=state["t"],
                category="crisis",
                message=(
                    "⚠️ CRISIS DE CREDIBILIDAD: El gobierno abandona el tipo de cambio fijo. "
                    "El mercado anticipa una devaluación del 25% este período. "
                    "La tasa de interés subirá para compensar."
                ),
                severity="critical",
            ))
            state["advisor_warnings"].append(
                "Transición a TC Flexible con alta expectativa de devaluación. "
                "El próximo turno registrará mayor inflación y presión sobre tasas."
            )

        elif old_regime == "flexible" and new_regime == "fixed":
            # Anclar el tipo de cambio requiere reservas suficientes
            R_threshold = (
                state["history"][0]["R"] * 0.30
                if state["history"]
                else 10.0
            )
            if state["R"] < R_threshold:
                state["news_feed"].append(NewsItem(
                    t=state["t"],
                    category="warning",
                    message=(
                        f"⚠️ Reservas insuficientes (R = {state['R']:.1f}) para "
                        f"defender el tipo de cambio fijo. "
                        f"Mínimo recomendado: {R_threshold:.1f}."
                    ),
                    severity="warning",
                ))
            state["delta_E_expected"] = 0.0

        else:
            # Otras transiciones: neutral
            state["delta_E_expected"] = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # RESUMEN FINAL (ENDGAME)
    # ─────────────────────────────────────────────────────────────────────────

    def get_endgame_summary(self) -> EndgameSummary:
        """
        Calcula el resumen de fin de partida y el veredicto de reelección.

        Solo puede llamarse cuando status ∈ {"endgame", "game_over"}.

        Returns
        -------
        EndgameSummary : Resumen con delta_score, veredicto y deltas por dimensión.

        Raises
        ------
        RuntimeError
            Si la simulación aún no ha terminado.
        """
        state = self.state
        if state is None:
            raise RuntimeError("No hay simulación activa.")
        if state["status"] not in ("endgame", "game_over"):
            raise RuntimeError(
                f"La simulación no ha terminado. Estado: '{state['status']}'."
            )

        history = state["history"]
        snap_0  = history[0]
        snap_f  = history[-1]

        # Delta score: mejora de puntaje del período
        delta_score = calc_endgame_delta_score(history)

        # Scores de los turnos jugados (excluyendo referencia t=0)
        turn_scores = state["scores"][1:]
        total_score  = sum(turn_scores)
        avg_score    = total_score / max(len(turn_scores), 1)

        # Deltas por dimensión (positivo = mejora)
        Y_0, Y_f = snap_0["Y"], snap_f["Y"]
        dimension_deltas = {
            "Y":          round(Y_f - Y_0, 4),
            "U":          round(snap_0["U"]  - snap_f["U"],  4),  # positivo = baja desempleo
            "pi":         round(snap_0["pi"] - snap_f["pi"], 4),  # positivo = baja inflación
            "deficit_pct": round(
                snap_0["deficit"] / max(snap_0["Y"], 1.0)
                - snap_f["deficit"] / max(snap_f["Y"], 1.0),
                4
            ),  # positivo = baja déficit
            "R":          round(snap_f["R"] - snap_0["R"], 4),    # positivo = suben reservas
        }

        # Veredicto
        if state["status"] == "game_over":
            verdict = "impeached"
        elif delta_score >= 0:
            verdict = "reelected"
        else:
            verdict = "removed"

        summary: EndgameSummary = {
            "total_score":        total_score,
            "avg_score_per_turn": round(avg_score, 2),
            "delta_score":        round(delta_score, 2),
            "t0_snapshot":        snap_0,
            "t10_snapshot":       snap_f,
            "verdict":            verdict,
            "dimension_deltas":   dimension_deltas,
        }

        state["delta_score"] = round(delta_score, 2)
        return summary

    # ─────────────────────────────────────────────────────────────────────────
    # UTILIDADES
    # ─────────────────────────────────────────────────────────────────────────

    def get_history_df(self):
        """
        Retorna el historial completo como DataFrame de pandas.

        Útil para visualización en la UI y para análisis en CLI.
        """
        import pandas as pd
        if not self.state or not self.state["history"]:
            return pd.DataFrame()

        cols = [
            "t", "Y", "r", "E", "M", "NX", "pi", "pi_e", "U",
            "gap", "gY", "B", "R", "deficit", "score", "zone_ss",
            "A_domestic", "q_real", "P_local",
        ]
        rows = []
        for snap in self.state["history"]:
            rows.append({col: snap[col] for col in cols})
        return pd.DataFrame(rows)

    def reset(self) -> None:
        """Resetea el state manager. Requiere nueva calibración para simular."""
        self.state = None

    def get_last_snapshot(self) -> Optional[TurnSnapshot]:
        """Retorna el último TurnSnapshot del historial, o None si vacío."""
        if self.state and self.state["history"]:
            return self.state["history"][-1]
        return None

    def is_over(self) -> bool:
        """True si la simulación terminó (endgame o game_over)."""
        return (
            self.state is not None
            and self.state["status"] in ("endgame", "game_over")
        )

    def __repr__(self) -> str:
        if self.state is None:
            return "SimStateManagerV2(state=None)"
        return (
            f"SimStateManagerV2("
            f"t={self.state['t']}, "
            f"status='{self.state['status']}', "
            f"regime='{self.state['regime']}'"
            f")"
        )
