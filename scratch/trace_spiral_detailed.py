"""
scratch/trace_spiral_detailed.py
================================
Busca la combinación de c0 e I0 para Espiral de la Muerte.
Queremos U_inicial entre 15% y 25%, y Game Over antes del turno 4.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.state_manager_v2 import SimStateManagerV2


def search_death_spiral():
    for c0 in [35.0, 40.0, 45.0, 50.0, 55.0, 60.0]:
        for I0 in [20.0, 25.0, 30.0, 35.0, 40.0]:
            for R_0 in [10.0, 15.0, 20.0]:
                for B_0 in [30.0, 40.0, 50.0]:
                    mgr = SimStateManagerV2()
                    # Parámetros estructurales del escenario death_spiral
                    sp = {
                        "c0": c0, "I0": I0, "t": 0.25,
                        "c1": 0.60, "NX0": -12.0,
                        "epsilon_x": 0.30, "epsilon_m": 0.35, "f": 1.5,
                        "alpha_PT": 0.60, "beta_PT": 0.45, "U_n": 0.08, "g_pot": -0.01
                    }
                    init = {"R": R_0, "B": B_0, "pi_e": 0.70}
                    mgr.calibrate("death_spiral", "easy", sp, init)
                    mgr.start_simulation("fixed")
                    
                    for t in range(1, 11):
                        if mgr.status == "game_over":
                            break
                        mgr.step_forward({})
                        
                    U_init = mgr.state["history"][0]["U"] * 100
                    if mgr.status == "game_over" and mgr.t < 4 and 15.0 <= U_init <= 25.0:
                        reason = mgr.state.get("game_over_reason", "None")
                        reason_clean = reason.encode("ascii", "ignore").decode("ascii")
                        print(f"[EXITO] c0={c0}, I0={I0}, R_0={R_0}, B_0={B_0} -> Status={mgr.status}, t={mgr.t}, U_init={U_init:.1f}%, Razon={reason_clean}")
                        return c0, I0, R_0, B_0
    print("[FALLA] No se encontro solucion para Espiral de la Muerte")
    return None


if __name__ == "__main__":
    search_death_spiral()
