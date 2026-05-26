import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from engine.state_manager_v2 import SimStateManagerV2
from config.scoring_v2 import check_game_over

mgr = SimStateManagerV2()
mgr.calibrate('Economia_Saludable')
mgr.start_simulation('fixed')

E_0 = mgr.state['policy']['E']
E_dev = E_0 * 1.25
snap = mgr.step_forward({'E': E_dev})
status = mgr.state['status']
reason = mgr.state['game_over_reason'] or ''
# Strip emojis for printing
reason_clean = reason.encode('ascii', 'replace').decode('ascii')
print(f't=1: status={status}')
print(f'  reason={reason_clean}')
print(f'  gY={snap["gY"]:.4f}, U={snap["U"]:.4f}, pi={snap["pi"]:.4f}')
print(f'  B={snap["B"]:.2f}, Y={snap["Y"]:.2f}, B_Y={snap["B"]/snap["Y"]:.4f}')
print(f'  R={snap["R"]:.2f}')

# Test manually each condition
go, msg = check_game_over(snap["gY"], snap["U"], snap["pi"], snap["R"], mgr.state["regime"], snap["B"], snap["Y"])
msg_clean = (msg or '').encode('ascii', 'replace').decode('ascii')
print(f'check_game_over: {go}, {msg_clean}')
