"""
ui/controls.py — Widgets de control para el simulador Mundell-Fleming + Salter-Swan.
Solo retorna valores; no llama al motor directamente.
"""
from __future__ import annotations
import streamlit as st
from config.parameters import CRISIS_PRESETS, get_base_params

_PRESET_OPTIONS: dict[str, str] = {
    "Base":                        "base",
    "Bolivia 2024 (Estanflación)": "Bolivia_2024_Stagflation",
    "Boom Exportador":             "Boom_Exportador",
    "Credit Crunch":               "Credit_Crunch",
}
_UI_PRESETS: dict[str, dict] = {"base": {}, **CRISIS_PRESETS}


def _apply_preset(preset_key: str, prefix: str, base: dict) -> None:
    ov = _UI_PRESETS.get(preset_key, {})
    for k in ("G","T","r_star","c1","m1","x1","b","k","h"):
        bk = "r_star" if k == "r_star" else k
        st.session_state[f"{prefix}_{k}"] = float(ov.get(bk, base[bk if bk != "r_star" else "r_star"]))
    if prefix == "fixed":
        st.session_state["fixed_E"] = float(ov.get("E", base["E"]))
    if prefix == "flexible":
        st.session_state["flexible_M"] = float(ov.get("M", base["M"]))


def _init_state(prefix: str, base: dict, regime: str) -> None:
    defaults = {
        f"{prefix}_G": base["G"], f"{prefix}_T": base["T"],
        f"{prefix}_r_star": base["r_star"], f"{prefix}_c1": base["c1"],
        f"{prefix}_m1": base["m1"], f"{prefix}_x1": base["x1"],
        f"{prefix}_b": base["b"], f"{prefix}_k": base["k"],
        f"{prefix}_h": base["h"],
    }
    if regime == "fixed":
        defaults[f"{prefix}_E"] = base["E"]
    if regime == "flexible":
        defaults[f"{prefix}_M"] = base["M"]
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _structural_expander(prefix: str) -> dict[str, float]:
    with st.expander("Parámetros estructurales", expanded=False):
        c1 = st.slider("Propensión marginal a consumir c₁", 0.40, 0.95,
                       st.session_state[f"{prefix}_c1"], 0.05, "%.2f", key=f"{prefix}_c1_slider")
        m1 = st.slider("Propensión marginal a importar m₁", 0.05, 0.40,
                       st.session_state[f"{prefix}_m1"], 0.05, "%.2f", key=f"{prefix}_m1_slider")
        x1 = st.slider("Sensibilidad exportaciones al TC x₁", 0.5, 3.0,
                       st.session_state[f"{prefix}_x1"], 0.1, "%.1f", key=f"{prefix}_x1_slider")
        b  = st.slider("Sensibilidad inversión a r (b)", 0.5, 5.0,
                       st.session_state[f"{prefix}_b"], 0.5, "%.1f", key=f"{prefix}_b_slider")
        k  = st.slider("Sensibilidad demanda dinero a Y (k)", 0.1, 1.0,
                       st.session_state[f"{prefix}_k"], 0.05, "%.2f", key=f"{prefix}_k_slider")
        h  = st.slider("Sensibilidad demanda dinero a r (h)", 0.5, 5.0,
                       st.session_state[f"{prefix}_h"], 0.5, "%.1f", key=f"{prefix}_h_slider")
    return dict(c1=c1, m1=m1, x1=x1, b=b, k=k, h=h)


def render_fixed_controls() -> dict[str, float]:
    base, prefix = get_base_params(), "fixed"
    _init_state(prefix, base, "fixed")

    preset_lbl = st.selectbox("Escenario de crisis", list(_PRESET_OPTIONS),
                              key=f"{prefix}_preset_label")
    if st.button("Cargar preset", key=f"{prefix}_load_preset"):
        _apply_preset(_PRESET_OPTIONS[preset_lbl], prefix, base)
        st.rerun()
    st.divider()

    st.markdown("**Política Fiscal**")
    G = st.slider("Gasto de Gobierno G", 5.0, 50.0, st.session_state["fixed_G"],
                  1.0, "%.0f", key="fixed_G_slider",
                  help="↑G desplaza la IS a la derecha → ↑Y (TC fijo).")
    T = st.slider("Impuestos T", 5.0, 50.0, st.session_state["fixed_T"],
                  1.0, "%.0f", key="fixed_T_slider",
                  help="↑T contrae la IS → ↓Y.")

    st.markdown("**Política Cambiaria**")
    E = st.slider("Tipo de Cambio Nominal E", 5.0, 20.0, st.session_state["fixed_E"],
                  0.5, "%.1f", key="fixed_E_slider",
                  help="↑E = devaluación → ↑NX → IS se desplaza a derecha.")

    st.markdown("**Condición Externa**")
    r_star = st.slider("Tasa de Interés Internacional r*", 1.0, 12.0,
                       st.session_state["fixed_r_star"], 0.5, "%.1f",
                       key="fixed_r_star_slider",
                       help="Bajo movilidad perfecta, r = r* en equilibrio.")

    struct = _structural_expander(prefix)

    for k, v in dict(G=G, T=T, E=E, r_star=r_star, **struct).items():
        st.session_state[f"{prefix}_{k}"] = v

    return {**base, "G": G, "T": T, "E": E, "r_star": r_star, **struct}


def render_flexible_controls() -> dict[str, float]:
    base, prefix = get_base_params(), "flexible"
    _init_state(prefix, base, "flexible")

    preset_lbl = st.selectbox("Escenario de crisis", list(_PRESET_OPTIONS),
                              key=f"{prefix}_preset_label")
    if st.button("Cargar preset", key=f"{prefix}_load_preset"):
        _apply_preset(_PRESET_OPTIONS[preset_lbl], prefix, base)
        st.rerun()
    st.divider()

    st.markdown("**Política Fiscal**")
    G = st.slider("Gasto de Gobierno G", 5.0, 50.0, st.session_state["flexible_G"],
                  1.0, "%.0f", key="flexible_G_slider",
                  help="En TC flexible, ↑G → apreciación cambiaria, Y no cambia.")
    T = st.slider("Impuestos T", 5.0, 50.0, st.session_state["flexible_T"],
                  1.0, "%.0f", key="flexible_T_slider")

    st.markdown("**Política Monetaria**")
    M = st.slider("Oferta Monetaria M", 15.0, 70.0, st.session_state["flexible_M"],
                  1.0, "%.0f", key="flexible_M_slider",
                  help="↑M → LM se desplaza → ↑Y. Política monetaria efectiva en TC flexible.")

    st.markdown("**Condición Externa**")
    r_star = st.slider("Tasa de Interés Internacional r*", 1.0, 12.0,
                       st.session_state["flexible_r_star"], 0.5, "%.1f",
                       key="flexible_r_star_slider")

    struct = _structural_expander(prefix)

    for k, v in dict(G=G, T=T, M=M, r_star=r_star, **struct).items():
        st.session_state[f"{prefix}_{k}"] = v

    return {**base, "G": G, "T": T, "M": M, "r_star": r_star, **struct}


def render_salter_controls() -> tuple[float, float]:
    prefix = "salter"
    if "salter_A" not in st.session_state:
        st.session_state["salter_A"] = 100.0
    if "salter_q" not in st.session_state:
        st.session_state["salter_q"] = 1.0

    _SS_PRESETS = {
        "Equilibrio ideal (punto bliss)":                    (100.0, 1.0),
        "Bolivia 2024 (Zona III — déficit + desempleo)":     (75.0,  0.75),
        "Boom exportador (Zona I — superávit + sobreempleo)":(115.0, 1.30),
        "Ajuste fiscal (Zona II — superávit + desempleo)":   (88.0,  1.15),
    }

    preset_ss = st.selectbox("Escenario ilustrativo", list(_SS_PRESETS), key="salter_preset")
    if st.button("Cargar escenario", key="salter_load"):
        st.session_state["salter_A"], st.session_state["salter_q"] = _SS_PRESETS[preset_ss]
        st.rerun()
    st.divider()

    st.markdown("**Instrumentos de política**")
    A = st.slider("Absorción doméstica A", 40.0, 160.0, st.session_state["salter_A"],
                  1.0, "%.0f", key="salter_A_slider",
                  help="↑A expande demanda interna (política fiscal/monetaria expansiva).")
    q = st.slider("Tipo de Cambio Real q", 0.10, 2.00, st.session_state["salter_q"],
                  0.05, "%.2f", key="salter_q_slider",
                  help="q > 1 → depreciación real (mayor competitividad). q = 1 → equilibrio.")

    st.session_state["salter_A"] = A
    st.session_state["salter_q"] = q
    return A, q
