"""
ui/navigation.py
================
Controlador lateral (Sidebar) de navegación y mandos del juego V2.0 (Fase 3).

Administra el avance de turnos, el cambio dinámico de régimen cambiario,
la inyección manual de shocks y la aplicación de dificultad.
"""

from __future__ import annotations

import streamlit as st
from engine.state_manager_v2 import SimStateManagerV2
from ui.period_controls import render_policy_controls
from ui.difficulty_mode import render_difficulty_parameters

# Shocks exógenos que se pueden inyectar de forma manual
MANUAL_SHOCKS = {
    "Ninguno": None,
    "📈 Boom de Commodities": "commodity_supercycle",
    "🏦 Shock de Tasas de la Fed": "fed_rate_shock",
    "📉 Recesión Global": "global_recession",
    "💻 Boom de Productividad": "tech_productivity",
    "🚨 Desastre Natural": "natural_disaster",
}


def render_navigation() -> None:
    """
    Renderiza la barra lateral con mandos del juego y navegación principal.
    """
    # Recuperar el orquestador V2 de session_state
    if "mgr" not in st.session_state:
        from engine.state_manager_v2 import SimStateManagerV2
        st.session_state["mgr"] = SimStateManagerV2()
        
    mgr: SimStateManagerV2 = st.session_state["mgr"]
    state = mgr.state

    st.sidebar.header("🕹️ Controles de Gobierno")
    st.sidebar.markdown("""
    <style>
        [data-testid="stSidebar"] { border-right: 1px solid #1e293b; background-color: #111827; }
        .stButton button { border-radius: 6px; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

    if mgr.status == "running" or mgr.status == "endgame":
        # 1. VISUALIZAR METADATOS ACTUALES
        regime_label = {
            "fixed": "🏛️ TC Fijo",
            "flexible": "🌊 TC Flexible",
            "crawling_peg": "⚙️ Crawling Peg"
        }.get(state["regime"], state["regime"])
        
        diff_label = "🟢 Fácil" if state["difficulty"] == "easy" else "🔴 Difícil"
        
        st.sidebar.markdown(f"""
        <div style='background-color: #1e293b; padding: 10px; border-radius: 6px; margin-bottom: 12px; border: 1px solid #334155;'>
          <div style='font-size: 0.75rem; color: #94a3b8;'>ESTADO ECONÓMICO</div>
          <div style='font-size: 0.95rem; font-weight: 700; color: #f8fafc; margin-top: 2px;'>Semestre: t = {mgr.t}/10</div>
          <div style='font-size: 0.8rem; color: #cbd5e1; margin-top: 4px;'>Régimen: <b>{regime_label}</b></div>
          <div style='font-size: 0.8rem; color: #cbd5e1;'>Dificultad: <b>{diff_label}</b></div>
        </div>
        """, unsafe_allow_html=True)

        # 2. SELECTOR DE RÉGIMEN CAMBIARIO EN TIEMPO REAL
        st.sidebar.subheader("🔄 Cambiar Régimen")
        regime_ui = st.sidebar.selectbox(
            "Seleccionar Nuevo Régimen",
            options=["fixed", "flexible", "crawling_peg"],
            index=["fixed", "flexible", "crawling_peg"].index(state["regime"]),
            format_func=lambda x: "🏛️ Tipo de Cambio Fijo" if x == "fixed" else "🌊 Tipo de Cambio Flexible" if x == "flexible" else "⚙️ Crawling Peg (Deslizamiento)",
            key="regime_selector_in_game"
        )
        
        # Si el jugador cambia de régimen, forzar el cambio cambiario inmediatamente
        if regime_ui != state["regime"]:
            mgr.force_regime_change(regime_ui)
            st.toast(f"ℹ️ Régimen cambiario modificado a: {regime_ui}", icon="🔄")
            st.rerun()

        st.sidebar.divider()

        # 3. RENDERIZAR PARÁMETROS ESTRUCTURALES Y NIEBLA DE GUERRA
        struct_changes = render_difficulty_parameters(state)
        if struct_changes:
            for k, v in struct_changes.items():
                state["structural"][k] = v
            st.toast("⚙️ Parámetro estructural ajustado.", icon="🛠️")
            st.rerun()

        st.sidebar.divider()

        # 4. RENDERIZAR CONTROLES DE POLÍTICA (G, E, M, crawl_rate)
        current_params = state["policy"]
        policy_changes = render_policy_controls(state["regime"], current_params)
        
        # 5. SELECTOR DE INYECCIÓN DE SHOCK MANUAL
        st.sidebar.divider()
        st.sidebar.subheader("⚡ Evento Exógeno Inducido")
        selected_shock_name = st.sidebar.selectbox(
            "Inyectar Shock al País",
            options=list(MANUAL_SHOCKS.keys()),
            help="Permite inyectar de forma manual un desastre o boom económico en el siguiente semestre con fines didácticos."
        )
        selected_shock_id = MANUAL_SHOCKS[selected_shock_name]

        # 6. AVANZAR DE PERÍODO
        st.sidebar.divider()
        if mgr.t < 10 and mgr.status == "running":
            if st.sidebar.button("⏭️ APLICAR POLÍTICAS Y AVANZAR", use_container_width=True, type="primary"):
                # Avanzar la simulación un turno
                mgr.step_forward(
                    policy_changes=policy_changes,
                    shock_key=selected_shock_id
                )
                st.rerun()
        elif mgr.status == "endgame":
            st.sidebar.success("🏁 ¡Simulación de 10 turnos completada!")

    # 7. BOTÓN DE REINICIAR A CALIBRACIÓN
    if mgr.status != "init":
        st.sidebar.divider()
        if st.sidebar.button("🔄 Reiniciar Gobierno (Onboarding)", use_container_width=True, type="secondary"):
            mgr.reset()
            st.rerun()
