"""
scratch/calibrate_scenarios.py
==============================
Algoritmo de búsqueda en rejilla amplio para calibrar los 4 escenarios de la V2.0.
Prueba rangos más altos de c0 e I0 para evitar colapsos tempranos de desempleo.
"""

from __future__ import annotations

import sys
from pathlib import Path
import copy

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.state_manager_v2 import SimStateManagerV2


def run_simulation(scenario_id: str, regime: str = "fixed", sp_overrides: dict = None, init_overrides: dict = None) -> dict:
    """
    Ejecuta una simulación en piloto automático usando SimStateManagerV2.
    """
    mgr = SimStateManagerV2()
    mgr.calibrate(scenario_id, difficulty="easy", custom_params=sp_overrides, custom_initial_state=init_overrides)
    mgr.start_simulation(regime=regime)
    
    if init_overrides:
        for k, v in init_overrides.items():
            if k in ("R", "B", "pi_e"):
                mgr.state[k] = v
                mgr.state["history"][0][k] = v
                
    for t in range(1, 11):
        if mgr.status == "game_over":
            break
        mgr.step_forward({})
        
    return {
        "status": mgr.status,
        "t": mgr.t,
        "reason": mgr.state.get("game_over_reason", "None") if mgr.status == "game_over" else "None",
        "history": mgr.state["history"]
    }


def search_tiger_asia():
    print("--- Buscando Tiger Asia ---")
    # Meta: sin política termina con pi > 8% en el turno 10 y sin Game Over.
    # Queremos que la inflación final esté entre 8% y 60% para evitar el circuit breaker de 150%.
    for c0 in [8.0, 9.0, 10.0, 11.0, 12.0]:
        for I0 in [8.0, 9.0, 10.0, 11.0, 12.0]:
            for m1 in [0.03, 0.04, 0.05]:
                for R_0 in [100.0, 120.0, 150.0]:
                    sp = {"c0": c0, "I0": I0, "m1": m1, "g_pot": 0.03}
                    init = {"R": R_0, "B": 15.0, "pi_e": 0.03}
                    res = run_simulation("tiger_asia", "fixed", sp, init)
                    if res["status"] == "endgame":
                        pi_final = res["history"][-1]["pi"] * 100
                        if 8.0 < pi_final < 80.0:
                            print(f"[EXITO] c0={c0}, I0={I0}, m1={m1}, R_0={R_0} -> Status=endgame, t={res['t']}, pi_final={pi_final:.2f}%")
                            return c0, I0, m1, R_0
    print("[FALLA] No se encontro solucion para Tiger Asia")
    return None


def search_trade_deficit():
    print("--- Buscando Desequilibrio Comercial ---")
    # Meta: sin política activa el circuit breaker entre el turno 6 y 8 (por Reservas).
    # Necesitamos c0 e I0 más altos para evitar colapso social inmediato en turnos iniciales.
    for c0 in [15.0, 20.0, 25.0]:
        for I0 in [15.0, 20.0, 25.0]:
            for m1 in [0.18, 0.20, 0.22, 0.24]:
                for R_0 in [30.0, 40.0, 50.0]:
                    sp = {"c0": c0, "I0": I0, "t": 0.25, "m1": m1, "NX0": -12.0}
                    init = {"R": R_0, "B": 10.0}
                    res = run_simulation("trade_deficit", "fixed", sp, init)
                    reason_clean = res['reason'].encode("ascii", "ignore").decode("ascii")
                    if res["status"] == "game_over" and 6 <= res["t"] <= 8 and "RESERVAS" in reason_clean:
                        print(f"[EXITO] c0={c0}, I0={I0}, m1={m1}, R_0={R_0} -> Status=game_over, t={res['t']}, Razon={reason_clean}")
                        return c0, I0, m1, R_0
    print("[FALLA] No se encontro solucion para Desequilibrio Comercial")
    return None


def search_latam_crisis():
    print("--- Buscando Crisis Latinoamericana ---")
    # Meta: U_inicial ~ 12% (10% - 15%), colapso antes de t=7.
    for c0 in [20.0, 25.0, 30.0, 35.0]:
        for I0 in [20.0, 25.0, 30.0, 35.0]:
            for R_0 in [10.0, 15.0, 20.0]:
                for B_0 in [20.0, 30.0, 40.0]:
                    sp = {"c0": c0, "I0": I0, "t": 0.22}
                    init = {"R": R_0, "B": B_0, "pi_e": 0.15}
                    res = run_simulation("latam_crisis", "fixed", sp, init)
                    U_init = res["history"][0]["U"] * 100
                    if res["status"] == "game_over" and res["t"] < 7 and 10.0 <= U_init <= 15.0:
                        reason_clean = res['reason'].encode("ascii", "ignore").decode("ascii")
                        print(f"[EXITO] c0={c0}, I0={I0}, R_0={R_0}, B_0={B_0} -> Status=game_over, t={res['t']}, U_init={U_init:.1f}%, Razon={reason_clean}")
                        return c0, I0, R_0, B_0
    print("[FALLA] No se encontro solucion para Crisis Latinoamericana")
    return None


def search_death_spiral():
    print("--- Buscando Espiral de la Muerte ---")
    # Meta: U_inicial ~ 20% (15% - 25%), colapso antes de t=4.
    for c0 in [25.0, 30.0, 35.0, 40.0]:
        for I0 in [15.0, 20.0, 25.0, 30.0]:
            for R_0 in [10.0, 15.0, 20.0]:
                for B_0 in [20.0, 30.0, 40.0]:
                    sp = {"c0": c0, "I0": I0}
                    init = {"R": R_0, "B": B_0, "pi_e": 0.60}
                    res = run_simulation("death_spiral", "fixed", sp, init)
                    U_init = res["history"][0]["U"] * 100
                    if res["status"] == "game_over" and res["t"] < 4 and 15.0 <= U_init <= 25.0:
                        reason_clean = res['reason'].encode("ascii", "ignore").decode("ascii")
                        print(f"[EXITO] c0={c0}, I0={I0}, R_0={R_0}, B_0={B_0} -> Status=game_over, t={res['t']}, U_init={U_init:.1f}%, Razon={reason_clean}")
                        return c0, I0, R_0, B_0
    print("[FALLA] No se encontro solucion para Espiral de la Muerte")
    return None


if __name__ == "__main__":
    search_tiger_asia()
    search_trade_deficit()
    search_latam_crisis()
    search_death_spiral()
