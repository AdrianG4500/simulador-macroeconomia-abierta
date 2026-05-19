import streamlit as st
from config.template_parser import parse_calibration_template
from engine.state_manager import SimStateManager
from config.validation_rules import VALIDATION_RULES

TEMPLATE_EXAMPLE = """
c0=20
c1=0.8
T=10
I0=10
G=20
NX0=2
b=1
x1=1
k=0.5
h=2
M=50
r_star=5
m1=0.2
E=1
"""

def render_calibration_panel():
    st.header("⚙️ Estado 0: Calibración")

    col1, col2 = st.columns(2)

    with col1:
        text_input = st.text_area("Pegar plantilla de calibración (t=0)", value=TEMPLATE_EXAMPLE, height=300)
        if st.button("📥 Cargar Plantilla"):
            params, errors = parse_calibration_template(text_input)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                st.session_state["temp_params"] = params
                st.success("Plantilla cargada correctamente.")

    with col2:
        if "temp_params" in st.session_state:
            st.subheader("Parámetros Detectados")
            params = st.session_state["temp_params"]
            for k, v in params.items():
                if k in VALIDATION_RULES:
                    rule = VALIDATION_RULES[k]
                    params[k] = st.slider(
                        label=f"{rule['label']} [{rule['unit']}]",
                        min_value=rule["min"],
                        max_value=rule["max"],
                        step=rule["step"],
                        value=max(rule["min"], min(rule["max"], float(v))),
                        help=rule["rationale"],
                        key=f"f4_{k}_slider"
                    )
                else:
                    params[k] = st.slider(f"{k}", min_value=0.0, max_value=max(100.0, v*2), value=float(v), step=0.1)

            if st.button("✅ Confirmar Estado 0"):
                mgr = SimStateManager()
                mgr.calibrate(params)
                st.rerun()
