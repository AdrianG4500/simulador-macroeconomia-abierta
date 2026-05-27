from engine.state_manager_v2 import SimStateManagerV2

def run_simulation(sp_overrides: dict, init_overrides: dict) -> dict:
    mgr = SimStateManagerV2()
    mgr.calibrate("death_spiral", difficulty="easy", custom_params=sp_overrides, custom_initial_state=init_overrides)
    mgr.start_simulation(regime="fixed")
    
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

print("=== SEARCHING SPIRAL WITH HIGH C0/I0 ===")
for c0 in [20.0, 25.0, 30.0, 35.0]:
    for I0 in [15.0, 20.0, 25.0, 30.0]:
        for R_0 in [5.0, 10.0]:
            for B_0 in [45.0, 50.0, 55.0]:
                for pi_e in [0.60, 0.70, 0.80]:
                    sp = {"c0": c0, "I0": I0}
                    init = {"R": R_0, "B": B_0, "pi_e": pi_e}
                    res = run_simulation(sp, init)
                    if res["status"] == "game_over" and res["t"] < 5:
                        U_init = res["history"][0]["U"] * 100
                        print(f"[MATCH] c0={c0}, I0={I0}, R_0={R_0}, B_0={B_0}, pi_e={pi_e} -> t={res['t']}, U_init={U_init:.1f}%")
