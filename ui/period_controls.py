import streamlit as st

def render_policy_controls(regime: str, current_params: dict) -> dict:
    """
    Renderiza los 5 controles manipulables (G, T, E, M, r).
    Retorna el diccionario con las políticas ajustadas.
    """
    st.sidebar.subheader("Instrumentos de Política")

    policies = {}

    controls = {
        "G": {"name": "Gasto público", "min": 5.0, "max": 60.0, "unit": "% PIB norm.", "help": "Instrumento fiscal: ↑G desplaza IS→. Efectivo bajo TC fijo, neutral bajo TC flexible."},
        "T": {"name": "Impuestos lump-sum", "min": 5.0, "max": 50.0, "unit": "% PIB norm.", "help": "Política tributaria: ↑T reduce ingreso disponible → ↓C → IS←. Efecto menor que G por c₁<1."},
        "E": {"name": "Tipo de cambio nominal", "min": 1.0, "max": 30.0, "unit": "Bs/USD", "help": "Instrumento cambiario (TC fijo): ↑E = devaluación → ↑competitividad → ↑NX → IS→."},
        "M": {"name": "Oferta monetaria", "min": 10.0, "max": 500.0, "unit": "Unid. modelo", "help": "Instrumento monetario (TC flexible): ↑M desplaza LM→ → ↓r → ↑Y. Endógena bajo TC fijo."},
        "r": {"name": "Tasa doméstica", "min": 0.0, "max": 20.0, "unit": "% anual", "help": "Solo activa en Movilidad Imperfecta. En MF perfecto, r = r* por arbitraje de capitales."}
    }

    def render_control(key, config, disabled=False, disabled_help=""):
        val_default = current_params.get(key, config["min"])
        val_default = max(config["min"], min(config["max"], float(val_default)))

        help_text = disabled_help if disabled else config["help"]

        slider_key = f"slider_policy_{key}"
        num_key = f"num_policy_{key}"

        if slider_key not in st.session_state:
            st.session_state[slider_key] = val_default
        if num_key not in st.session_state:
            st.session_state[num_key] = val_default

        def update_from_slider():
            st.session_state[num_key] = st.session_state[slider_key]

        def update_from_num():
            st.session_state[slider_key] = st.session_state[num_key]

        st.sidebar.markdown(f"**{config['name']} ({key})** [{config['unit']}]", help=help_text)
        c1, c2 = st.sidebar.columns([3, 1])

        with c1:
            st.slider(
                "slider_hidden",
                min_value=config["min"],
                max_value=config["max"],
                step=0.1 if key != "M" else 1.0,
                help=help_text,
                disabled=disabled,
                key=slider_key,
                on_change=update_from_slider,
                label_visibility="collapsed"
            )
        with c2:
            st.number_input(
                "num_hidden",
                min_value=config["min"],
                max_value=config["max"],
                step=0.1 if key != "M" else 1.0,
                disabled=disabled,
                key=num_key,
                on_change=update_from_num,
                label_visibility="collapsed"
            )

        if not disabled:
            if st.session_state[num_key] != val_default:
                policies[key] = st.session_state[num_key]

    disable_E = (regime == "🌊 TC Flexible")
    help_E = "E se determina por equilibrio" if disable_E else ""

    disable_M = (regime == "🏛️ TC Fijo")
    help_M = "M se ajusta automáticamente" if disable_M else ""

    disable_r = (regime != "🔐 Movilidad Imperfecta")
    help_r = "r = r* en movilidad perfecta" if disable_r else ""

    render_control("G", controls["G"])
    render_control("T", controls["T"])
    render_control("E", controls["E"], disabled=disable_E, disabled_help=help_E)
    render_control("M", controls["M"], disabled=disable_M, disabled_help=help_M)
    render_control("r", controls["r"], disabled=disable_r, disabled_help=help_r)

    return policies
