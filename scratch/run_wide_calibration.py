from engine.state_manager_v2 import SimStateManagerV2
import math

def run_simulation(scenario_id: str, regime: str = "fixed", sp_overrides: dict = None, init_overrides: dict = None) -> dict:
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

print("=== SEARCHING TIGER ASIA ===")
# Meta: pi_final > 8.0 (8%) y pi_final < 80.0 (80%) y status == "endgame" (t == 10)
found_asia = False
for c0 in [15.0, 20.0, 25.0, 30.0]:
    for I0 in [15.0, 20.0, 25.0, 30.0]:
        for m1 in [0.03, 0.05, 0.08]:
            for R_0 in [150.0, 200.0]:
                sp = {"c0": c0, "I0": I0, "m1": m1, "g_pot": 0.03}
                init = {"R": R_0, "B": 15.0, "pi_e": 0.03}
                res = run_simulation("tiger_asia", "fixed", sp, init)
                if res["status"] == "endgame":
                    pi_final = res["history"][-1]["pi"] * 100
                    if 8.0 < pi_final < 80.0:
                        print(f"[ASIA MATCH] c0={c0}, I0={I0}, m1={m1}, R_0={R_0} -> pi_final={pi_final:.2f}%")
                        found_asia = True
                        break
            if found_asia: break
        if found_asia: break
    if found_asia: break

print("\n=== SEARCHING DEATH SPIRAL ===")
# Meta: colapso (game_over) antes del turno 5 (t < 5)
# En test_integration: assert mgr.status == "game_over" and mgr.t < 5
found_spiral = False
for c0 in [15.0, 20.0, 25.0, 30.0, 35.0]:
    for I0 in [10.0, 15.0, 20.0, 25.0, 30.0]:
        for R_0 in [5.0, 10.0, 15.0]:
            for B_0 in [40.0, 50.0, 60.0]:
                for pi_e in [0.50, 0.70, 0.90]:
                    sp = {"c0": c0, "I0": I0}
                    init = {"R": R_0, "B": B_0, "pi_e": pi_e}
                    res = run_simulation("death_spiral", "fixed", sp, init)
                    if res["status"] == "game_over" and res["t"] < 5:
                        reason = res["reason"].encode("ascii", "ignore").decode("ascii")
                        print(f"[SPIRAL MATCH] c0={c0}, I0={I0}, R_0={R_0}, B_0={B_0}, pi_e={pi_e} -> t={res['t']}, reason={reason}")
                        found_spiral = True
                        break
                if found_spiral: break
            if found_spiral: break
        if found_spiral: break
    if found_spiral: break

