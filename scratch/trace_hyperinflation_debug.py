from engine.state_manager_v2 import SimStateManagerV2
mgr = SimStateManagerV2()
mgr.calibrate("Economia_Saludable", custom_params={"c0": 25.0, "I0": 25.0})
mgr.state["structural"]["alpha_inf"] = 3.0    # Curva de Phillips muy empinada
mgr.state["structural"]["beta_PT"]   = 0.5    # Pass-through alto
mgr.state["pi_e"]                    = 1.0    # 100% de expectativas inflacionarias
mgr.start_simulation("fixed")
print("Structural Params:")
for k, v in mgr.state["structural"].items():
    if k in ["c0", "c1", "t", "I0", "b", "NX0", "f", "alpha_PT", "beta_PT", "m1"]:
        print(f"  {k}: {v}")
print("Policy Instruments:")
for k, v in mgr.state["policy"].items():
    if k in ["G", "G_c", "I_g", "E", "M", "r_star", "regime"]:
        print(f"  {k}: {v}")

snap0 = mgr.state['history'][0]
print(f"Turn 0: Y={snap0['Y']:.2f}, r={snap0['r']:.2f}, pi={snap0['pi']:.4f}, B={snap0['B']:.2f}, R={snap0['R']:.2f}, rho={snap0['rho']:.4f}, rating={snap0['rating']}")
E_original = mgr.state["policy"]["E"]
snap = mgr.step_forward({"E": E_original * 2.0})
print(f"Turn 1: Y={snap['Y']:.2f}, r={snap['r']:.2f}, pi={snap['pi']:.4f}, gap={snap['gap']:.4f}, B={snap['B']:.2f}, R={snap['R']:.2f}, rho={snap['rho']:.4f}, rating={snap['rating']}")
print(f"status: {mgr.status}")
print(f"game_over_reason: {mgr.state.get('game_over_reason')}")


