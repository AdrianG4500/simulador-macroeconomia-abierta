from engine.core_v2 import eq_fixed_v2, eq_flexible_v2
from config.parameters_v2 import DEFAULT_STRUCTURAL_PARAMS, DEFAULT_POLICY_INSTRUMENTS

sp = dict(DEFAULT_STRUCTURAL_PARAMS)
pi = dict(DEFAULT_POLICY_INSTRUMENTS)
Y_pot = 100.0
P_NT = 1.0

eq_fixed = eq_fixed_v2(sp=sp, pi=pi, Y_pot=Y_pot, P_NT=P_NT)
print("Fixed Regime:")
print(f"  Y: {eq_fixed['Y']:.4f}")
print(f"  r: {eq_fixed['r']:.4f}")
print(f"  C: {eq_fixed['C']:.4f}")
print(f"  I_inv: {eq_fixed['I_inv']:.4f}")
print(f"  NX: {eq_fixed['NX']:.4f}")
print(f"  G_total: {eq_fixed['G_total']:.4f}")
print(f"  C+I+G+NX: {eq_fixed['C'] + eq_fixed['I_inv'] + eq_fixed['G_total'] + eq_fixed['NX']:.4f}")

eq_flex = eq_flexible_v2(sp=sp, pi=pi, Y_pot=Y_pot, P_NT=P_NT, E_prev=pi["E"])
print("\nFlexible Regime:")
print(f"  Y: {eq_flex['Y']:.4f}")
print(f"  r: {eq_flex['r']:.4f}")
print(f"  E_endo: {eq_flex['E_endo']:.4f}")
print(f"  C: {eq_flex['C']:.4f}")
print(f"  I_inv: {eq_flex['I_inv']:.4f}")
print(f"  NX: {eq_flex['NX']:.4f}")
print(f"  G_total: {eq_flex['G_total']:.4f}")
print(f"  C+I+G+NX: {eq_flex['C'] + eq_flex['I_inv'] + eq_flex['G_total'] + eq_flex['NX']:.4f}")
