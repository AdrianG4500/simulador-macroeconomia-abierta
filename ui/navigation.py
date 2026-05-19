import streamlit as st
from engine.state_manager import SimStateManager
from config.shocks_engine import STRUCTURED_SHOCKS
from ui.period_controls import render_policy_controls

def render_navigation():
    mgr = SimStateManager()

    st.sidebar.header("🕹️ Controles de Simulación")
    st.sidebar.markdown("""<style>
        [data-testid="stSidebar"] { border-right: 1px solid #1e293b; background-color: #111827; }
        .stButton button { border-radius: 6px; font-weight: 600; }
    </style>""", unsafe_allow_html=True)

    regime = st.sidebar.radio("Selector de régimen", ["🏛️ TC Fijo", "🌊 TC Flexible", "🔐 Movilidad Imperfecta"], key="regime_selector", help="Elige el régimen cambiario y de movilidad de capitales.")
    st.sidebar.divider()

    if mgr.status == "calibrated" and mgr.t == 0:
        if st.sidebar.button("🚀 Iniciar Simulación (t=0 → t=1)"):
            mgr.start_simulation(regime)
            st.rerun()

    if mgr.status == "running":
        st.sidebar.info(f"Semestre actual: t={mgr.t}/10 | Régimen: {regime}")

        current_params = mgr.state["history"][-1]["params"]
        policy = render_policy_controls(regime, current_params)
        st.sidebar.divider()

        shock = st.sidebar.selectbox("Shock", ["Ninguno"] + list(STRUCTURED_SHOCKS.keys()), help="Elige un evento exógeno.")
        st.sidebar.divider()

        if mgr.t < 10:
            if st.sidebar.button("⏭️ Siguiente Semestre"):
                mgr.step_forward(policy_changes=policy, shock_key=shock if shock != "Ninguno" else None)
                st.rerun()

    if mgr.status != "init":
        if st.sidebar.button("🔄 Reiniciar a Calibración"):
            mgr.reset_to_calibration()
            st.rerun()
