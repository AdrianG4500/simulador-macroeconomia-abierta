"""
scratch/test_trade_deficit.py
==============================
Busca parámetros para Desequilibrio Comercial que colapse entre t=6 y t=8 por reservas.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.state_manager_v2 import SimStateManagerV2


def search_trade_deficit():
    for c0 in [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0]:
        for I0 in [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0]:
            for m1 in [0.15, 0.18, 0.20, 0.22, 0.25]:
                for R_0 in [25.0, 30.0, 35.0, 40.0, 50.0]:
                    mgr = SimStateManagerV2()
                    # Aumentamos t para evitar default de deuda
                    sp = {"c0": c0, "I0": I0, "t": 0.25, "m1": m1, "NX0": -10.0}
                    init = {"R": R_0, "B": 10.0}
                    mgr.calibrate("trade_deficit", "easy", sp, init)
                    mgr.start_simulation("fixed")
                    
                    for t in range(1, 11):
                        if mgr.status == "game_over":
                            break
                        mgr.step_forward({})
                        
                    if mgr.status == "game_over" and 6 <= mgr.t <= 8:
                        reason = mgr.state.get("game_over_reason", "None")
                        reason_clean = reason.encode("ascii", "ignore").decode("ascii")
                        if "RESERVAS" in reason_clean:
                            print(f"[EXITO] c0={c0}, I0={I0}, m1={m1}, R_0={R_0} -> Status={mgr.status}, t={mgr.t}, Razon={reason_clean}")
                            return c0, I0, m1, R_0
    print("[FALLA] No se encontro solucion para Desequilibrio Comercial")
    return None


if __name__ == "__main__":
    search_trade_deficit()
