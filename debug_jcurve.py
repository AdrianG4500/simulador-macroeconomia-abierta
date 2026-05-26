import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from engine.state_manager_v2 import SimStateManagerV2

mgr = SimStateManagerV2()
mgr.calibrate("Economia_Saludable")
mgr.start_simulation("fixed")

E_inicial = mgr.state["policy"]["E"]
E_devaluada = E_inicial * 1.25

try:
    snap1 = mgr.step_forward({"E": E_devaluada})
    if mgr.state['status'] == 'game_over':
        reason = mgr.state['game_over_reason'] or ''
        print(f"Game over at turn 1! Reason: {reason.encode('ascii', 'replace').decode('ascii')}")
        print(f"gY={snap1['gY']:.4f}, U={snap1['U']:.4f}, pi={snap1['pi']:.4f}, B={snap1['B']:.2f}, Y={snap1['Y']:.2f}, R={snap1['R']:.2f}")
    else:
        snap2 = mgr.step_forward({"E": E_devaluada})
        print("Turn 2 success")
except Exception as e:
    print(f"Exception: {e}")
