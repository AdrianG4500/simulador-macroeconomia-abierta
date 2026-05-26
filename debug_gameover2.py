import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from engine.state_manager_v2 import SimStateManagerV2

mgr = SimStateManagerV2()
mgr.calibrate('Economia_Saludable')
mgr.start_simulation('fixed')

try:
    for i in range(10):
        snap = mgr.step_forward({})
        if mgr.state['status'] == 'game_over':
            print(f"Turn {i+1} Game Over!")
            reason = mgr.state['game_over_reason'] or ''
            reason_clean = reason.encode('ascii', 'replace').decode('ascii')
            print(f"Reason: {reason_clean}")
            print(f"gY={snap['gY']:.4f}, U={snap['U']:.4f}, pi={snap['pi']:.4f}, B={snap['B']:.2f}, Y={snap['Y']:.2f}, R={snap['R']:.2f}")
            break
except Exception as e:
    print(f"Exception at turn {i+1}: {e}")

for s in mgr.state['history']:
    print(f"t={s['t']}, Y={s['Y']:.2f}, gY={s['gY']:.4f}, pi={s['pi']:.4f}, E={s['E']:.2f}, M={s['M']:.2f}, R={s['R']:.2f}, NX={s['NX']:.2f}, r={s['r']:.4f}")
