"""
scratch/test_asia_values.py
===========================
Prueba valores de c0 e I0 bajos para Tiger Asia y reporta Y0, gap0, pi0, U0.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.state_manager_v2 import SimStateManagerV2


def test_asia():
    for c0 in [1.0, 2.0, 3.0, 4.0, 5.0]:
        for I0 in [1.0, 2.0, 3.0, 4.0, 5.0]:
            mgr = SimStateManagerV2()
            sp = {"c0": c0, "I0": I0, "m1": 0.05}
            init = {"R": 100.0, "B": 15.0, "pi_e": 0.03}
            mgr.calibrate("tiger_asia", "easy", sp, init)
            
            snap = mgr.state["history"][0]
            print(f"c0={c0}, I0={I0} -> Y0={snap['Y']:.2f}, gap0={snap.get('gap', 0.0)*100:.2f}%, pi0={snap['pi']*100:.2f}%, U0={snap['U']*100:.2f}%")


if __name__ == "__main__":
    test_asia()
