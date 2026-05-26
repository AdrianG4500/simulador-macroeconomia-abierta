"""
scratch/run_calibration_diagnostics.py
======================================
Ejecuta simulaciones en piloto automático para los 4 escenarios y reporta
el turno de Game Over (o finalización) y variables clave, usando texto ascii seguro.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en el path
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.state_manager_v2 import SimStateManagerV2


def test_scenario(scenario_id: str, regime: str = "fixed"):
    mgr = SimStateManagerV2()
    mgr.calibrate(scenario_id, difficulty="easy")
    mgr.start_simulation(regime=regime)
    
    # Simular turnos sin cambiar políticas
    game_over = False
    turn_limit = 10
    
    for t in range(1, turn_limit + 1):
        if mgr.status == "game_over":
            game_over = True
            break
            
        # Avanzar aplicando las políticas vigentes
        policy = mgr.state["policy"]
        mgr.step_forward(policy_changes={
            "G": policy["G"],
            "E": policy["E"],
            "M": policy["M"],
            "crawl_rate": policy.get("crawl_rate", 0.02)
        })
        
    print(f"=== Escenario: {scenario_id} ===")
    print(f"Estado final: {mgr.status}")
    print(f"Turno alcanzado: {mgr.t}")
    if mgr.status == "game_over":
        reason = mgr.state.get("game_over_reason", "No reason provided")
        # Remover caracteres no-ascii para evitar crash CP1252
        safe_reason = reason.encode("ascii", "ignore").decode("ascii")
        print(f"Razon de Game Over: {safe_reason}")
    else:
        last_snap = mgr.state["history"][-1]
        print(f"Inflacion final (pi): {last_snap['pi']*100:.2f}%")
        print(f"Desempleo final (U): {last_snap['U']*100:.2f}%")
        print(f"Reservas finales (R): {last_snap['R']:.2f}")
        print(f"Deuda final (B): {last_snap['B']:.2f}")
    print()


if __name__ == "__main__":
    test_scenario("tiger_asia", "fixed")
    test_scenario("trade_deficit", "fixed")
    test_scenario("latam_crisis", "fixed")
    test_scenario("death_spiral", "fixed")
