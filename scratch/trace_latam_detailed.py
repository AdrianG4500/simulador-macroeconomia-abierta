"""
scratch/trace_latam_detailed.py
===============================
Trazado detallado de Crisis Latinoamericana con c0=26, I0=20, R=15, B=35.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.state_manager_v2 import SimStateManagerV2


def trace_latam():
    mgr = SimStateManagerV2()
    sp = {
        "c0": 26.0, "I0": 20.0, "t": 0.20,
        "c1": 0.65, "m1": 0.15, "NX0": -5.0,
        "f": 2.0, "alpha_PT": 0.50, "beta_PT": 0.35, "U_n": 0.06
    }
    init = {"R": 15.0, "B": 35.0, "pi_e": 0.15}
    mgr.calibrate("latam_crisis", "easy", sp, init)
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
    trace_latam()
