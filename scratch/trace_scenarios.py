"""
scratch/trace_scenarios.py
==========================
Traza detalladamente las variables de los escenarios para calibración.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.state_manager_v2 import SimStateManagerV2


def trace_scenario(scenario_id: str, regime: str = "fixed"):
    print(f"\n==================================================")
    print(f"TRACING SCENARIO: {scenario_id}")
    print(f"==================================================")
    
    mgr = SimStateManagerV2()
    mgr.calibrate(scenario_id, difficulty="easy")
    mgr.start_simulation(regime=regime)
    
    snap = mgr.state["history"][-1]
    print(f"t=0: Y={snap['Y']:.1f}, R={snap['R']:.1f}, B={snap['B']:.1f}, pi={snap['pi']*100:.1f}%, U={snap['U']*100:.1f}%, deficit={snap.get('deficit', 0.0):.1f}")
    
    for t in range(1, 11):
        if mgr.status == "game_over":
            reason = mgr.state.get("game_over_reason", "No reason")
            safe_reason = reason.encode("ascii", "ignore").decode("ascii")
            print(f"*** GAME OVER at t={t-1}. Reason: {safe_reason}")
            break
            
        policy = mgr.state["policy"]
        mgr.step_forward(policy_changes={
            "G": policy["G"],
            "E": policy["E"],
            "M": policy["M"],
            "crawl_rate": policy.get("crawl_rate", 0.02)
        })
        
        snap = mgr.state["history"][-1]
        print(f"t={t}: Y={snap['Y']:.1f}, R={snap['R']:.1f}, B={snap['B']:.1f}, pi={snap['pi']*100:.1f}%, U={snap['U']*100:.1f}%, deficit={snap.get('deficit', 0.0):.1f}, r={snap.get('r', 0.0):.1f}")


if __name__ == "__main__":
    trace_scenario("trade_deficit", "fixed")
    trace_scenario("latam_crisis", "fixed")
    trace_scenario("death_spiral", "fixed")
