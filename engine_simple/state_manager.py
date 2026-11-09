"""
engine_simple/state_manager.py
==============================
Orquestador principal del estado de la simulación macroeconómica (10 turnos).
Edición: The Economic War Room (V1.2 SIMPLE).

Principios:
- Mantiene el historial inmutable de TurnSnapshot (t=0 a t=10).
- Flujo estricto de 8 pasos en cada avance de turno (step_forward).
- Integración de las 8 palancas de política y eventos exógenos/endógenos.
- Blindaje Anti-Bucle: Período de gracia (T1-T2) y persistencia de 2 turnos para Game Over.
- Reforma Cambiaria de Emergencia disponible en tiempo de ejecución.
- Serialización completa a JSON (to_dict / from_dict) para Supabase y Canvas.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from config_simple.parameters import (
    Equilibrium,
    PolicyInstruments,
    SalterSwanResult,
    StructuralParams,
    TurnSnapshot,
)
from config_simple.scenarios import SCENARIOS, get_scenario_params
from config_simple.scoring import GameOverResult, calc_period_score, check_game_over
from engine_simple.advisor import CabinetAdvice, generate_cabinet_advice, run_dry_run
from engine_simple.core import compute_salter_swan, solve_equilibrium
from engine_simple.dynamics import (
    compute_capital_flows,
    compute_credibility,
    compute_debt_to_gdp_nominal,
    compute_fiscal_balance,
    compute_flexible_exchange_rate_adjustment,
    compute_inflation,
    compute_output_gap,
    compute_sovereign_risk,
    compute_unemployment,
    update_adaptive_expectations,
    update_potential_output,
    update_reserves,
    update_P_NT,
)
from engine_simple.events import (
    ActiveEvent,
    Event,
    apply_event_deltas,
    create_event_from_scenario,
    evaluate_endogenous_events,
    evaluate_random_events,
    format_event_modal_data,
    get_event_by_id,
    tick_active_events,
)


class StateManager:
    """Orquestador de estado de la partida de 10 turnos."""

    def __init__(self, scenario_id: str = "chile_rule") -> None:
        self.scenario_id: str = scenario_id
        sp, pi, init = get_scenario_params(scenario_id)

        # Copias base de parámetros e instrumentos
        self.base_params: StructuralParams = copy.deepcopy(sp)
        self.current_params: StructuralParams = copy.deepcopy(self.base_params)
        self.current_instruments: PolicyInstruments = copy.deepcopy(pi)

        # Variables acumuladoras interturnos
        self.current_turn: int = 0
        self.Y_pot: float = float(init.get("Y_pot", 100.0))
        self.pi_e: float = float(init.get("pi_e", self.current_instruments["pi_target"]))
        self.B: float = float(init.get("B", 20.0))
        self.R: float = float(init.get("R", 60.0))
        self.P_NT: float = float(init.get("P_NT", 1.0))

        # Eventos, contadores de crecimiento y cooldown (V1.3)
        self.active_events: List[ActiveEvent] = []
        self.consecutive_high_growth: int = 0
        self.event_cooldown: int = 0
        self.pending_modal_event: Optional[Dict[str, Any]] = None

        # Blindaje Anti-Bucle y Alertas Críticas
        self.consecutive_danger_turns: Dict[str, int] = {
            "debt": 0,
            "reserves": 0,
            "inflation": 0,
            "unemployment": 0,
        }
        self.red_alert_active: bool = False
        self.red_alert_reason: str = ""

        # Historial de snapshots (0 a 10)
        self.history: List[TurnSnapshot] = []

        # Estado de Game Over
        self.is_game_over: bool = False
        self.game_over_reason: Optional[str] = None

        # Calibración inicial (turno 0)
        self._calibrate()

    def _calibrate(self) -> TurnSnapshot:
        """Inicializa el estado base (turno 0) según el escenario seleccionado."""
        self.current_turn = 0
        self.is_game_over = False
        self.game_over_reason = None
        self.active_events = []
        self.consecutive_high_growth = 0
        self.event_cooldown = 0
        self.pending_modal_event = None
        self.consecutive_danger_turns = {
            "debt": 0,
            "reserves": 0,
            "inflation": 0,
            "unemployment": 0,
        }
        self.red_alert_active = False
        self.red_alert_reason = ""
        self.history = []

        sp, pi, init = get_scenario_params(self.scenario_id)
        self.base_params = copy.deepcopy(sp)
        self.current_params = copy.deepcopy(self.base_params)
        self.current_instruments = copy.deepcopy(pi)

        self.Y_pot = float(init.get("Y_pot", 100.0))
        self.B = float(init.get("B", 20.0))
        self.R = float(init.get("R", 60.0))
        self.pi_e = float(init.get("pi_e", self.current_instruments["pi_target"]))
        self.P_NT = float(init.get("P_NT", 1.0))
        rho_init = float(init.get("rho", 0.50))

        # Resolver equilibrio instantáneo base t=0
        Y_init_target = float(init.get("Y", 100.0))
        debt_ratio_init = self.B / max(Y_init_target, 1.0)

        eq: Equilibrium = solve_equilibrium(
            sp=self.current_params,
            pi=self.current_instruments,
            P_NT=self.P_NT,
            E_prev=self.current_instruments["E"],
            Y_prev=Y_init_target,
            Y_pot=self.Y_pot,
            rho=rho_init,
            debt_ratio_prev=debt_ratio_init,
        )

        gap = compute_output_gap(eq["Y"], self.Y_pot)
        U = float(init.get("U", compute_unemployment(self.current_params["U_n"], gap, self.current_params["gamma_okun"])))
        pi = float(init.get("pi", self.current_instruments["pi_target"]))
        gY = 0.0

        PIB_nominal = eq["PIB_nominal"]
        recaudacion, costo_subsidios, intereses_deuda, deficit, B_new, deficit_primario = compute_fiscal_balance(
            Gc=self.current_instruments["Gc"],
            Ig=self.current_instruments["Ig"],
            tc=self.current_instruments["tc"],
            tk=self.current_instruments["tk"],
            tau=self.current_instruments["tau"],
            sx=self.current_instruments["sx"],
            Y=eq["Y"],
            X=eq["X"],
            M_imp=eq["M_imp"],
            B_prev=self.B,
            r_star=self.current_instruments["r_star"],
            rho=rho_init,
            G_needed=self.current_instruments.get("G_needed", 0.0),
            PIB_nominal=PIB_nominal,
        )

        debt_to_gdp_nominal = compute_debt_to_gdp_nominal(self.B, PIB_nominal)
        rho_risk, rating_risk = compute_sovereign_risk(
            B=self.B,
            PIB_nominal=PIB_nominal,
            R=self.R,
            pi=pi,
            U=U,
            Un=self.current_params["U_n"],
        )
        rating_final = init.get("rating", rating_risk)

        ss: SalterSwanResult = compute_salter_swan(
            eq_result=eq,
            sp=self.current_params,
            G_total=eq["G"],
            Y_pot=self.Y_pot,
        )
        score = calc_period_score(
            gap=gap,
            U=U,
            pi=pi,
            gY=gY,
            prev_score=None,
            debt_ratio=debt_to_gdp_nominal,
            Un=self.current_params["U_n"],
        )

        regime = self.current_instruments["regime"]
        crawl_rate = self.current_instruments.get("crawl_rate", 0.0)
        delta_E_expected = crawl_rate * 100.0 if regime == "crawling_peg" else 0.0
        KA = compute_capital_flows(
            f=self.current_params["f"],
            r_t=eq["r"],
            r_star=self.current_instruments["r_star"],
            rho=rho_init,
            delta_E_expected=delta_E_expected,
        )

        t0_snapshot: TurnSnapshot = {
            "t": 0,
            "Y": eq["Y"],
            "Y_pot": self.Y_pot,
            "r": eq["r"],
            "C": eq["C"],
            "I_priv": eq["I_priv"],
            "I_inv": eq["I_priv"],
            "Gc": eq["Gc"],
            "Ig": eq["Ig"],
            "G": eq["G"],
            "NX": eq["NX"],
            "X": eq["X"],
            "M_imp": eq["M_imp"],
            "A_domestic": eq["A_domestic"],
            "E": eq["E_endo"],
            "P_local": eq["P_local"],
            "P_T": eq["P_T"],
            "P_NT": self.P_NT,
            "q_real": eq["q_real"],
            "pi": pi,
            "pi_e": self.pi_e,
            "theta": 0.40,
            "U": U,
            "gap": gap,
            "gY": gY,
            "recaudacion": recaudacion,
            "costo_subsidios": costo_subsidios,
            "intereses_deuda": intereses_deuda,
            "deficit": deficit,
            "B": self.B,
            "PIB_nominal": PIB_nominal,
            "debt_to_gdp_nominal": debt_to_gdp_nominal,
            "R": self.R,
            "KA": KA,
            "rho": rho_risk,
            "rating": rating_final,
            "zone_ss": ss["zone"],
            "score": score,
            "red_alert_active": False,
            "red_alert_reason": "",
            "consecutive_alert_turns": 0,
            "policy_applied": copy.deepcopy(self.current_instruments),
            "events_triggered": [],
        }

        self.history.append(t0_snapshot)
        return t0_snapshot

    def start_simulation(self, scenario_id: Optional[str] = None) -> TurnSnapshot:
        """Reinicia la simulación con el escenario especificado o el actual."""
        if scenario_id is not None:
            self.scenario_id = scenario_id
        return self._calibrate()

    def switch_regime(
        self,
        new_regime: str,
        new_E: Optional[float] = None,
        new_crawl: Optional[float] = None,
    ) -> None:
        """
        Reforma Cambiaria de Emergencia:
        Permite al estudiante modificar el régimen cambiario durante la partida
        (por ejemplo, pasar de Tipo de Cambio Fijo a Flotación en México 1994
        o unificar el tipo de cambio en Bolivia 1985).
        """
        if new_regime not in ("fixed", "flexible", "crawling_peg"):
            raise ValueError(f"Régimen no reconocido: {new_regime}")

        self.current_instruments["regime"] = new_regime
        if new_E is not None:
            self.current_instruments["E"] = float(new_E)
        if new_crawl is not None:
            self.current_instruments["crawl_rate"] = float(new_crawl)

    def trigger_exogenous_event(self, event_id: str) -> None:
        """Gatilla manualmente un evento exógeno en el turno actual."""
        event = get_event_by_id(event_id)
        if any(ae["event"]["id"] == event_id for ae in self.active_events):
            return  # Ya activo

        self.current_params, self.current_instruments = apply_event_deltas(
            self.current_params, self.current_instruments, event
        )
        self.active_events.append({
            "event": event,
            "turns_remaining": event["duration"],
        })
        self.pending_modal_event = format_event_modal_data(event)

    def dismiss_event_modal(self) -> None:
        """Cierra el modal de evento emergente actual."""
        self.pending_modal_event = None

    def step_forward(self, policy_input: PolicyInstruments) -> TurnSnapshot:
        """
        Ejecuta el avance de 1 turno (de t a t+1) procesando el bucle de 8 pasos:

        1. Aplicación de las 8 palancas seleccionadas y eventos programados/activos.
        2. Resolución cerrada analítica del equilibrio macroeconómico Y_t e identidades.
        3. Cálculo de dinámicas de precios, inflación de 4 componentes, Okun y PIB potencial.
        4. Balance fiscal, deuda soberana sobre PIB nominal y credibilidad.
        5. Balanza de pagos (KA, NX, acumulación de reservas o flotación cambiaria).
        6. Verificación de Alerta Roja Crítica y evaluación de persistencia de Game Over (Regla 1).
        7. Cálculo del Score de Percepción Ciudadana (Regla 2).
        8. Creación y congelamiento del TurnSnapshot inmutable en el historial.
        """
        if self.is_game_over:
            raise RuntimeError(f"La partida ha terminado por colapso macroeconómico: {self.game_over_reason}")

        if self.current_turn >= 10:
            raise RuntimeError("La partida ya ha alcanzado el límite máximo de 10 turnos.")

        prev_snapshot = self.history[-1]
        next_turn = self.current_turn + 1
        self.pending_modal_event = None

        # ── PASO 1: Aplicar las 8 Palancas y Procesar Eventos ──
        inst = copy.deepcopy(policy_input)

        # Sincronizar aliases de compatibilidad
        inst["G"] = inst["Gc"] + inst["Ig"] + inst.get("G_needed", 0.0)
        inst["t"] = inst["tc"]

        # Si régimen es crawling_peg, actualizar el tipo de cambio proyectado
        if inst["regime"] == "crawling_peg":
            rate = inst.get("crawl_rate", 0.02)
            inst["E"] = prev_snapshot["E"] * (1.0 + rate)

        # Avanzar duraciones de eventos activos y revertir expirados
        self.active_events, expired, self.current_params, inst = tick_active_events(
            self.active_events, self.current_params, inst
        )

        events_triggered_this_turn: List[str] = []

        # Verificar eventos programados del escenario para este turno
        has_scheduled_event = False
        scenario_data = SCENARIOS.get(self.scenario_id, {})
        for sched in scenario_data.get("scheduled_events", []):
            if sched.get("turn") == next_turn:
                has_scheduled_event = True
                ev = create_event_from_scenario(sched)
                if not any(ae["event"]["id"] == ev["id"] for ae in self.active_events):
                    self.current_params, inst = apply_event_deltas(self.current_params, inst, ev)
                    self.active_events.append({
                        "event": ev,
                        "turns_remaining": ev["duration"],
                    })
                    events_triggered_this_turn.append(ev["name"])
                    self.pending_modal_event = format_event_modal_data(ev)

        # Evaluar y aplicar eventos endógenos (estallido social, círculo virtuoso)
        active_ids = [ae["event"]["id"] for ae in self.active_events]
        new_endo_events = evaluate_endogenous_events(
            prev_snapshot, self.consecutive_high_growth, active_ids
        )
        for ev in new_endo_events:
            self.current_params, inst = apply_event_deltas(self.current_params, inst, ev)
            self.active_events.append({
                "event": ev,
                "turns_remaining": ev["duration"],
            })
            events_triggered_this_turn.append(ev["name"])
            if self.pending_modal_event is None:
                self.pending_modal_event = format_event_modal_data(ev)

        # Evaluar eventos aleatorios leves con cooldown (V1.3)
        rnd_event, self.event_cooldown = evaluate_random_events(
            turn=next_turn,
            cooldown_counter=self.event_cooldown,
            active_event_ids=[ae["event"]["id"] for ae in self.active_events],
            has_scheduled_event_this_turn=has_scheduled_event,
            scenario_id=self.scenario_id,
        )
        if rnd_event is not None:
            self.current_params, inst = apply_event_deltas(self.current_params, inst, rnd_event)
            self.active_events.append({
                "event": rnd_event,
                "turns_remaining": rnd_event["duration"],
            })
            events_triggered_this_turn.append(rnd_event["name"])
            if self.pending_modal_event is None:
                self.pending_modal_event = format_event_modal_data(rnd_event)

        # ── PASO 2: Resolver Equilibrio Instantáneo IS-LM-BP (Closed-Form Analytical) ──
        rho_prev = prev_snapshot.get("rho", 0.50)
        debt_ratio_prev = prev_snapshot.get("debt_to_gdp_nominal", 0.20)

        eq: Equilibrium = solve_equilibrium(
            sp=self.current_params,
            pi=inst,
            P_NT=self.P_NT,
            E_prev=prev_snapshot["E"],
            Y_prev=prev_snapshot["Y"],
            Y_pot=self.Y_pot,
            rho=rho_prev,
            debt_ratio_prev=debt_ratio_prev,
        )

        # ── PASO 3: Dinámicas de Oferta, Empleo e Inflación (4 Fuerzas) ──
        gap = compute_output_gap(eq["Y"], self.Y_pot)
        U = compute_unemployment(self.current_params["U_n"], gap, self.current_params["gamma_okun"])
        gY = (eq["Y"] - prev_snapshot["Y"]) / prev_snapshot["Y"] if prev_snapshot["Y"] > 0 else 0.0

        E_curr = eq["E_endo"]
        prev_tau = prev_snapshot["policy_applied"].get("tau", inst["tau"]) if prev_snapshot.get("policy_applied") else inst["tau"]

        # Componente de señoreaje histórico si el escenario lo requiere (ej. Bolivia inicial)
        shock_seigniorage = 0.0
        if self.scenario_id in ("bolivia_hyper", "death_spiral") and next_turn <= 2:
            shock_seigniorage = 0.05

        pi = compute_inflation(
            pi_e=self.pi_e,
            gap=gap,
            E_t=E_curr,
            E_prev=prev_snapshot["E"],
            alpha_inf=self.current_params["alpha_inf"],
            beta_PT=self.current_params["beta_PT"],
            tau_t=inst["tau"],
            tau_prev=prev_tau,
            shock_seigniorage=shock_seigniorage,
        )

        # Precios no transables evolucionan con la inflación
        self.P_NT = update_P_NT(self.P_NT, pi)

        # PIB Potencial para el siguiente turno
        Y_pot_next = update_potential_output(
            Y_pot=self.Y_pot,
            Ig=eq["Ig"],
            g_pot=self.current_params["g_pot"],
            Ig_dep=self.current_params["Ig_dep"],
        )

        # ── PASO 4: Balance Fiscal, Deuda sobre PIB Nominal y Credibilidad ──
        PIB_nominal = eq["PIB_nominal"]
        recaudacion, costo_subsidios, intereses_deuda, deficit, B_new, deficit_primario = compute_fiscal_balance(
            Gc=inst["Gc"],
            Ig=inst["Ig"],
            tc=inst["tc"],
            tk=inst["tk"],
            tau=inst["tau"],
            sx=inst["sx"],
            Y=eq["Y"],
            X=eq["X"],
            M_imp=eq["M_imp"],
            B_prev=self.B,
            r_star=inst["r_star"],
            rho=rho_prev,
            G_needed=inst.get("G_needed", 0.0),
            PIB_nominal=PIB_nominal,
        )

        debt_to_gdp_nominal = compute_debt_to_gdp_nominal(B_new, PIB_nominal)

        # Credibilidad endógena θ_t ∈ [0.40, 0.80]
        theta = compute_credibility(
            r_ref=inst["r_ref"],
            pi_t=pi,
            deficit_primario=deficit_primario,
            Y=eq["Y"],
        )
        pi_e_next = update_adaptive_expectations(theta, inst["pi_target"], pi)

        # ── PASO 5: Balanza de Pagos, Reservas y Flotación Cambiaria ──
        regime = inst["regime"]
        crawl_rate = inst.get("crawl_rate", 0.0)
        delta_E_expected = crawl_rate * 100.0 if regime == "crawling_peg" else 0.0

        KA = compute_capital_flows(
            f=self.current_params["f"],
            r_t=eq["r"],
            r_star=inst["r_star"],
            rho=rho_prev,
            delta_E_expected=delta_E_expected,
        )

        R_new = update_reserves(self.R, eq["NX"], KA, regime)

        # Mecanismo de Fondo Soberano de Estabilización (FSE / Ahorro en Reservas):
        # Si la deuda ya está en su piso técnico (10% del PIB nominal), el superávit
        # excedente se atesora como patrimonio neto en las reservas internacionales.
        b_unconstrained = self.B + deficit
        pib_base = PIB_nominal if PIB_nominal > 0.0 else eq["Y"]
        b_min = max(2.0, 0.10 * pib_base)
        excess_surplus = max(0.0, b_min - b_unconstrained)
        if excess_surplus > 0.0:
            R_new = round(R_new + excess_surplus, 6)

        # En régimen flexible, el tipo de cambio absorbe el desbalance y flota
        if regime == "flexible":
            E_adjusted = compute_flexible_exchange_rate_adjustment(
                E_prev=prev_snapshot["E"],
                NX=eq["NX"],
                KA=KA,
            )
            inst["E"] = round(E_adjusted, 2)
            E_curr = inst["E"]

        rho_risk, rating_risk = compute_sovereign_risk(
            B=B_new,
            PIB_nominal=PIB_nominal,
            R=R_new,
            pi=pi,
            U=U,
            Un=self.current_params["U_n"],
        )
        ss: SalterSwanResult = compute_salter_swan(
            eq_result=eq,
            sp=self.current_params,
            G_total=eq["G"],
            Y_pot=self.Y_pot,
        )

        # ── PASO 6: Blindaje Anti-Bucle y Evaluación de Game Over (Regla 1) ──
        go_res: GameOverResult = check_game_over(
            turn=next_turn,
            debt_ratio_nominal=debt_to_gdp_nominal,
            reserves=R_new,
            pi=pi,
            U=U,
            gY=gY,
            consecutive_danger_turns=self.consecutive_danger_turns,
        )

        self.consecutive_danger_turns = go_res.counters
        self.red_alert_active = go_res.red_alert_active
        self.red_alert_reason = go_res.red_alert_reason

        if go_res.is_game_over:
            self.is_game_over = True
            self.game_over_reason = go_res.reason

        consecutive_alert_count = max(self.consecutive_danger_turns.values()) if self.consecutive_danger_turns else 0

        # ── PASO 7: Score de Aprobación Ciudadana Ponderado (Regla 2) ──
        score = calc_period_score(
            gap=gap,
            U=U,
            pi=pi,
            gY=gY,
            prev_score=prev_snapshot["score"],
            debt_ratio=debt_to_gdp_nominal,
            Un=self.current_params["U_n"],
        )

        # ── PASO 8: Registrar Snapshot del Turno y Congelar Estado ──
        snapshot: TurnSnapshot = {
            "t": next_turn,
            "Y": eq["Y"],
            "Y_pot": self.Y_pot,
            "r": eq["r"],
            "C": eq["C"],
            "I_priv": eq["I_priv"],
            "I_inv": eq["I_priv"],
            "Gc": eq["Gc"],
            "Ig": eq["Ig"],
            "G": eq["G"],
            "NX": eq["NX"],
            "X": eq["X"],
            "M_imp": eq["M_imp"],
            "A_domestic": eq["A_domestic"],
            "E": E_curr,
            "P_local": eq["P_local"],
            "P_T": eq["P_T"],
            "P_NT": self.P_NT,
            "q_real": eq["q_real"],
            "pi": pi,
            "pi_e": self.pi_e,
            "theta": theta,
            "U": U,
            "gap": gap,
            "gY": gY,
            "recaudacion": recaudacion,
            "costo_subsidios": costo_subsidios,
            "intereses_deuda": intereses_deuda,
            "deficit": deficit,
            "B": B_new,
            "PIB_nominal": PIB_nominal,
            "debt_to_gdp_nominal": debt_to_gdp_nominal,
            "R": R_new,
            "KA": KA,
            "rho": rho_risk,
            "rating": rating_risk,
            "zone_ss": ss["zone"],
            "score": score,
            "red_alert_active": self.red_alert_active,
            "red_alert_reason": self.red_alert_reason,
            "consecutive_alert_turns": consecutive_alert_count,
            "policy_applied": copy.deepcopy(inst),
            "events_triggered": events_triggered_this_turn,
        }

        self.history.append(snapshot)

        # Actualizar variables acumuladoras internas
        self.current_turn = next_turn
        self.B = B_new
        self.R = R_new
        self.Y_pot = Y_pot_next
        self.pi_e = pi_e_next
        self.current_instruments = copy.deepcopy(inst)

        if gY > 0.04:
            self.consecutive_high_growth += 1
        else:
            self.consecutive_high_growth = 0

        return snapshot

    def get_dry_run_projection(self, proposed_instruments: PolicyInstruments) -> TurnSnapshot:
        """Obtiene la proyección borrador para el turno t+1 sin avanzar el juego."""
        curr_snap = self.history[-1]
        return run_dry_run(
            current_snapshot=curr_snap,
            params=self.current_params,
            proposed_instruments=proposed_instruments,
            Y_pot=self.Y_pot,
            pi_e=self.pi_e,
            B_prev=self.B,
            R_prev=self.R,
        )

    def get_cabinet_advice(self, proposed_instruments: PolicyInstruments) -> CabinetAdvice:
        """Genera las recomendaciones didácticas de los 3 ministros de Gabinete."""
        curr_snap = self.history[-1]
        dry_snap = self.get_dry_run_projection(proposed_instruments)
        ss: SalterSwanResult = compute_salter_swan(
            dry_snap, self.current_params, proposed_instruments["G"]  # type: ignore[arg-type]
        )
        return generate_cabinet_advice(
            current_snapshot=curr_snap,
            dry_run_snapshot=dry_snap,
            ss_result=ss,
            target_pi=proposed_instruments["pi_target"],
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa el estado completo del juego a un diccionario compatible con JSON.
        Preparado para persistencia en Supabase y entrega de notas en Canvas.
        """
        return {
            "version": "1.3-SIMPLE",
            "scenario_id": self.scenario_id,
            "current_turn": self.current_turn,
            "Y_pot": self.Y_pot,
            "pi_e": self.pi_e,
            "B": self.B,
            "R": self.R,
            "P_NT": self.P_NT,
            "consecutive_high_growth": self.consecutive_high_growth,
            "event_cooldown": self.event_cooldown,
            "consecutive_danger_turns": copy.deepcopy(self.consecutive_danger_turns),
            "red_alert_active": self.red_alert_active,
            "red_alert_reason": self.red_alert_reason,
            "is_game_over": self.is_game_over,
            "game_over_reason": self.game_over_reason,
            "base_params": copy.deepcopy(self.base_params),
            "current_params": copy.deepcopy(self.current_params),
            "current_instruments": copy.deepcopy(self.current_instruments),
            "active_events": copy.deepcopy(self.active_events),
            "history": copy.deepcopy(self.history),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> StateManager:
        """
        Reconstruye una instancia de StateManager desde un payload serializado con 100% fidelidad.
        """
        instance = cls.__new__(cls)
        instance.scenario_id = payload["scenario_id"]
        instance.current_turn = int(payload["current_turn"])
        instance.Y_pot = float(payload["Y_pot"])
        instance.pi_e = float(payload["pi_e"])
        instance.B = float(payload["B"])
        instance.R = float(payload["R"])
        instance.P_NT = float(payload.get("P_NT", 1.0))
        instance.consecutive_high_growth = int(payload.get("consecutive_high_growth", 0))
        instance.event_cooldown = int(payload.get("event_cooldown", 0))
        instance.pending_modal_event = None
        instance.consecutive_danger_turns = copy.deepcopy(
            payload.get("consecutive_danger_turns", {"debt": 0, "reserves": 0, "inflation": 0, "unemployment": 0})
        )
        instance.red_alert_active = bool(payload.get("red_alert_active", False))
        instance.red_alert_reason = str(payload.get("red_alert_reason", ""))
        instance.is_game_over = bool(payload.get("is_game_over", False))
        instance.game_over_reason = payload.get("game_over_reason")

        instance.base_params = copy.deepcopy(payload["base_params"])
        instance.current_params = copy.deepcopy(payload["current_params"])
        instance.current_instruments = copy.deepcopy(payload["current_instruments"])
        instance.active_events = copy.deepcopy(payload.get("active_events", []))
        instance.history = copy.deepcopy(payload.get("history", []))

        return instance

    def get_endgame_summary(self) -> Dict[str, Any]:
        """Calcula el informe final de calificaciones al concluir los 10 turnos o por colapso."""
        played_turns = [s for s in self.history if s["t"] > 0]
        if not played_turns:
            return {
                "status": "Incompleto",
                "avg_score": 0.0,
                "turns_played": 0,
                "game_over": self.is_game_over,
                "reason": self.game_over_reason,
            }

        avg_score = sum(s["score"] for s in played_turns) / len(played_turns)
        last_snap = played_turns[-1]

        status = "Derrota por Colapso Macroeconómico" if self.is_game_over else "Victoria Económica (10 Turnos Completados)"

        return {
            "status": status,
            "scenario": SCENARIOS.get(self.scenario_id, {}).get("name", self.scenario_id),
            "avg_score": round(avg_score, 2),
            "turns_played": len(played_turns),
            "final_Y": round(last_snap["Y"], 2),
            "final_inflation": round(last_snap["pi"] * 100.0, 2),
            "final_unemployment": round(last_snap["U"] * 100.0, 2),
            "final_debt_ratio": round(last_snap["debt_to_gdp_nominal"] * 100.0, 2),
            "final_reserves": round(last_snap["R"], 2),
            "final_rating": last_snap["rating"],
            "game_over": self.is_game_over,
            "game_over_reason": self.game_over_reason,
        }
