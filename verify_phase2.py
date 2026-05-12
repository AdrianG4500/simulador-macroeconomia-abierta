"""Script de verificacion numerica completa de Fase 2."""
import sys
sys.path.insert(0, ".")

from config.parameters import get_base_params, CRISIS_PRESETS
from engine.core import eq_fixed, eq_flexible, autonomous_demand, is_curve, lm_curve
from engine.salter_swan import get_zone
from engine.cache import cached_eq_fixed, cached_eq_flexible
from ui.charts import plot_islm_fixed, plot_islm_flexible, plot_salter_swan
from ui.narrative import generate_fixed_narrative, generate_flexible_narrative, generate_salter_narrative
from utils.export import export_scenario

p = get_base_params()
f = eq_fixed(p)
x = eq_flexible(p)

# Base checks
assert abs(f["mult"] - 2.5) < 0.01
assert abs(f["Y"] - 100.0) < 0.01
assert abs(f["M_endo"] - 40.0) < 0.01
assert abs(x["Y"] - 100.0) < 0.01
assert abs(x["E_endo"] - 10.0) < 0.01
print("BASE: OK")

# G=30 fijo -> Y=125, M=52.5
p30 = dict(p); p30["G"] = 30.0
f30 = eq_fixed(p30)
assert abs(f30["Y"] - 125.0) < 0.1, f"Y={f30['Y']}"
assert abs(f30["M_endo"] - 52.5) < 0.1, f"M={f30['M_endo']}"
print(f"G=30 FIJO -> Y={f30['Y']:.2f}, M_endo={f30['M_endo']:.2f}: OK")

# M=55 flexible -> Y=130, E~17.5
p55 = dict(p); p55["M"] = 55.0
x55 = eq_flexible(p55)
assert abs(x55["Y"] - 130.0) < 0.1, f"Y={x55['Y']}"
assert abs(x55["E_endo"] - 18.0) < 0.1, f"E={x55['E_endo']}"  # analitico: (0.40*130+10-35)/1.5=18.0
print(f"M=55 FLEXIBLE -> Y={x55['Y']:.2f}, E_endo={x55['E_endo']:.4f}: OK")

# Salter-Swan zonas
z3 = get_zone(75.0, 0.75)
assert z3["zone"] == "III", f"zona={z3['zone']}"
z1 = get_zone(115.0, 1.3)
assert z1["zone"] == "I", f"zona={z1['zone']}"
z2 = get_zone(88.0, 1.15)
z4 = get_zone(115.0, 0.8)
print(f"Salter zonas -> A=75 q=0.75: {z3['zone']}, A=115 q=1.3: {z1['zone']}")
print(f"               A=88 q=1.15: {z2['zone']}, A=115 q=0.8: {z4['zone']}: OK")

# Narrativas
n = generate_fixed_narrative(10, 0, 0, 0, f30["Y"], f30["M_endo"], f30["NX"], f30["mult"])
assert len(n) > 50
print("Narrativa fijo: OK")

n2 = generate_flexible_narrative(0, 0, 15, 0, x55["Y"], x55["E_endo"], x55["NX"], x55["mult"])
assert len(n2) > 50
print("Narrativa flexible: OK")

# Export
df = export_scenario("fixed", p, p30, dict(f), dict(f30))
assert "Delta" in df.columns
assert len(df) > 5
delta_Y_row = df[df["Variable"].str.contains("PIB")]["Delta"].values
assert abs(delta_Y_row[0] - 25.0) < 0.5, f"Delta Y={delta_Y_row[0]}"
print(f"Export CSV -> Delta Y = {delta_Y_row[0]:.2f}: OK")

# Graficos (sin Streamlit, solo verifica que retorna Figure)
import plotly.graph_objects as go
fig1 = plot_islm_fixed(f30["Y"], f30["r"], p, p30)
fig2 = plot_islm_flexible(x55["Y"], x55["r"], p, p55)
z_bliss = get_zone(100.0, 1.0)
fig3 = plot_salter_swan(100.0, 1.0, z_bliss)
assert all(isinstance(f_, go.Figure) for f_ in [fig1, fig2, fig3])
print("Graficos Plotly: OK")

print("\nALL PHASE 2 VERIFICATIONS PASSED")
