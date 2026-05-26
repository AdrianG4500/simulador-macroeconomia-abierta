"""
scratch/trace_deficit_detailed.py
=================================
Trazado detallado del escenario trade_deficit con c0=10, I0=20, m1=0.2, R=120.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.state_manager_v2 import SimStateManagerV2


def trace_deficit():
    mgr = SimStateManagerV2()
    sp = {"c0": 10.0, "I0": 20.0, "t": 0.25, "m1": 0.20, "NX0": -10.0}
    init = {"R": 120.0, "B": 10.0}
    mgr.calibrate("trade_deficit", "easy", sp, init)
    mgr.start_simulation("fixed")
    
    print("t=0 Initial State:")
    snap = mgr.state["history"][-1]
    print(f"  Y: {snap['Y']:.1f}, R: {snap['R']:.2f}, B: {snap['B']:.2f}, U: {snap['U']*100:.1f}%, pi: {snap['pi']*100:.1f}%, regime: {mgr.state['regime']}")
    
    for t in range(1, 11):
        if mgr.status == "game_over":
            print(f"\n*** GAME OVER in t={t-1} ***")
            print(f"Reason: {mgr.state.get('game_over_reason')}")
            break
            
        mgr.step_forward({})
        snap = mgr.state["history"][-1]
        print(f"\nt={t}:")
        print(f"  Y: {snap['Y']:.1f}, R: {snap['R']:.2f}, B: {snap['B']:.2f}, U: {snap['U']*100:.1f}%, pi: {snap['pi']*100:.1f}%, regime: {mgr.state['regime']}, deficit: {snap['deficit']:.1f}")


if __name__ == "__main__":
    trace_deficit()
