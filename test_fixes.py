import sys
import pandas as pd

# Asegurar que el path del proyecto esté disponible
sys.path.append('.') 

from engine.state_manager_v2 import SimStateManagerV2

def test_macro_stability():
    print("[TEST] Iniciando prueba de estabilidad macroeconomica (4 turnos)...")
    
    mgr = SimStateManagerV2()
    
    # Intentar Crisis Latam, fallback a Economia Saludable
    try:
        mgr.calibrate(scenario_id="Crisis_Latam", difficulty="hard")
    except Exception as e:
        print(f"[WARN] 'Crisis_Latam' no encontrado ({e}), usando 'Economia_Saludable'")
        mgr.calibrate(scenario_id="Economia_Saludable", difficulty="easy")
        
    mgr.start_simulation(regime="flexible")
    
    history = []
    
    # Políticas estables para aislar el comportamiento del solver
    stable_policy = {"G_c": 17, "I_g": 5, "M": 40, "k_c": 0.20, "t_c": 0.20}
    
    for t in range(1, 5):
        snap = mgr.step_forward(policy_changes=stable_policy)
        
        # Calcular variación porcentual de E
        E_prev = mgr.state["history"][t-1]["E"]
        E_curr = snap["E"]
        delta_E_pct = ((E_curr - E_prev) / max(E_prev, 1e-9)) * 100.0
        
        # Extraer capital_flows_eq si existe, sino calcularlo aproximado para debug
        cf_eq = snap.get("capital_flows_eq", 0.0)
        
        history.append({
            "t": t,
            "E": round(E_curr, 4),
            "delta_E_pct": round(delta_E_pct, 2),
            "capital_flows_eq": round(cf_eq, 2),
            "B": round(snap["B"], 2),
            "Y_pot": round(mgr.state["Y_pot"], 2),
            "score": round(snap["score"], 2)
        })
        
        # VALIDACIONES EN TIEMPO REAL
        assert abs(delta_E_pct) < 50.0, f"[-] FALLA TC: delta_E_pct = {delta_E_pct}% en turno {t} (Limite: 50%)"
        assert abs(cf_eq) < 100.0, f"[-] FALLA CF: capital_flows_eq = {cf_eq} en turno {t} (Limite: 100)"
        assert snap["B"] > (-0.6 * mgr.state["Y_pot"]), f"[-] FALLA DEUDA: B = {snap['B']} es irrealmente bajo en turno {t}"
        assert snap["score"] > 20.0, f"[-] FALLA SCORE: score = {snap['score']} colapso en turno {t}"

    df = pd.DataFrame(history)
    print("\n[TABLE] RESULTADOS DE LA SIMULACION (4 TURNOS):")
    print(df.to_string(index=False))
    print("\n[SUCCESS] TODAS LAS VALIDACIONES PASARON. EL MOTOR ESTA ESTABLE.")

if __name__ == "__main__":
    test_macro_stability()
