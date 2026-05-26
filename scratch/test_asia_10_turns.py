"""
scratch/test_asia_10_turns.py
==============================
Busca la combinación de c0 e I0 que sobrevive 10 turnos con pi > 8%.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.state_manager_v2 import SimStateManagerV2


def search_tiger_asia():
    for c0 in [1.0, 1.5, 2.0, 2.5, 3.0]:
        for I0 in [1.0, 1.5, 2.0, 2.5, 3.0]:
            mgr = SimStateManagerV2()
            sp = {"c0": c0, "I0": I0, "m1": 0.03, "g_pot": 0.03}
            init = {"R": 150.0, "B": 15.0, "pi_e": 0.03}
            mgr.calibrate("tiger_asia", "easy", sp, init)
            mgr.start_simulation("fixed")
            
            for t in range(1, 11):
                if mgr.status == "game_over":
                    break
                mgr.step_forward({})
                
            if mgr.status == "endgame":
                last = mgr.state["history"][-1]
                pi_final = last["pi"] * 100
                if 8.0 < pi_final < 120.0:
                    print(f"[EXITO] c0={c0}, I0={I0} -> Status={mgr.status}, t={mgr.t}, pi_final={pi_final:.2f}%, R_final={last['R']:.1f}")
                    return c0, I0
    print("[FALLA] No se encontro solucion para Tiger Asia")
    return None


if __name__ == "__main__":
    search_tiger_asia()
