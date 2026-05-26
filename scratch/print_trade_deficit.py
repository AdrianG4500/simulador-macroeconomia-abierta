"""
scratch/print_trade_deficit.py
==============================
Muestra qué pasa con diferentes combinaciones para trade_deficit.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.state_manager_v2 import SimStateManagerV2


def print_trade_deficit():
    for c0 in [10.0, 15.0, 20.0]:
        for I0 in [10.0, 15.0, 20.0]:
            for m1 in [0.15, 0.20]:
                for R_0 in [30.0, 40.0]:
                    mgr = SimStateManagerV2()
                    sp = {"c0": c0, "I0": I0, "t": 0.25, "m1": m1, "NX0": -10.0}
                    init = {"R": R_0, "B": 10.0}
                    mgr.calibrate("trade_deficit", "easy", sp, init)
                    mgr.start_simulation("fixed")
                    
                    for t in range(1, 11):
                        if mgr.status == "game_over":
                            break
                        mgr.step_forward({})
                        
                    reason = mgr.state.get("game_over_reason", "None") if mgr.status == "game_over" else "None"
                    reason_clean = reason.encode("ascii", "ignore").decode("ascii")
                    print(f"c0={c0}, I0={I0}, m1={m1}, R_0={R_0} -> Status={mgr.status}, t={mgr.t}, Razon={reason_clean}")


if __name__ == "__main__":
    print_trade_deficit()
