from engine.state_manager_v2 import SimStateManagerV2
mgr = SimStateManagerV2()
mgr.calibrate("Economia_Saludable", custom_initial_state={"R": 200.0})
mgr.start_simulation("fixed")
for t in range(1, 11):
    if mgr.status == 'game_over':
        print(f"Game Over at turn {mgr.t} because: {mgr.state.get('game_over_reason')}")
        break
    snap = mgr.step_forward({})
    print(f"Turn {t}: Y={snap['Y']:.2f}, r={snap['r']:.2f}, deficit={snap['deficit']:.2f}, B={snap['B']:.2f}, R={snap['R']:.2f}, gY={snap['gY']:.4f}, U={snap['U']:.4f}, status={mgr.status}")
