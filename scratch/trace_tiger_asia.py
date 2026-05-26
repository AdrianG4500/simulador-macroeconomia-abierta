"""
scratch/trace_tiger_asia.py
===========================
Muestra la evolución del escenario 'tiger_asia' turno por turno.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.state_manager_v2 import SimStateManagerV2


def trace_tiger_asia():
    mgr = SimStateManagerV2()
    mgr.calibrate("tiger_asia", difficulty="easy")
    mgr.start_simulation(regime="fixed")
    
    print("t=0 Initial State:")
    snap = mgr.state["history"][-1]
    print(f"  Y: {snap['Y']:.2f}, gap: {snap.get('gap', 0.0)*100:.2f}%, pi: {snap['pi']*100:.2f}%, U: {snap['U']*100:.2f}%, R: {snap['R']:.2f}, B: {snap['B']:.2f}")
    
    for t in range(1, 11):
        if mgr.status == "game_over":
            print(f"\n*** GAME OVER in t={t-1} ***")
            print(f"Reason: {mgr.state.get('game_over_reason')}")
            break
            
        policy = mgr.state["policy"]
        mgr.step_forward(policy_changes={
            "G": policy["G"],
            "E": policy["E"],
            "M": policy["M"],
            "crawl_rate": policy.get("crawl_rate", 0.02)
        })
        
        snap = mgr.state["history"][-1]
        print(f"\nt={t}:")
        print(f"  Y: {snap['Y']:.2f}, gap: {snap.get('gap', 0.0)*100:.2f}%, pi: {snap['pi']*100:.2f}%, U: {snap['U']*100:.2f}%, R: {snap['R']:.2f}, B: {snap['B']:.2f}, r: {snap['r']:.2f}")
        print(f"  G: {policy['G']:.2f}, E: {policy['E']:.2f}, M_endo: {snap.get('M_endo', 0.0):.2f}")


if __name__ == "__main__":
    trace_tiger_asia()
