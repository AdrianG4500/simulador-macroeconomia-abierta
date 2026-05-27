from engine.state_manager_v2 import SimStateManagerV2
mgr = SimStateManagerV2()
mgr.calibrate('tiger_asia', 'easy')
mgr.start_simulation('fixed')
print(f"Turn 0: Y={mgr.state['history'][0]['Y']:.2f}, B={mgr.state['history'][0]['B']:.2f}, pi={mgr.state['history'][0]['pi']:.4f}")
for t in range(1, 11):
    snap = mgr.step_forward({})
    print(f"Turn {t}: Y={snap['Y']:.2f}, r={snap['r']:.2f}, deficit={snap['deficit']:.2f}, B={snap['B']:.2f}, pi={snap['pi']:.4f}, pi_e={snap['pi_e']:.4f}, status={mgr.status}")
    if mgr.status == 'game_over':
        break

