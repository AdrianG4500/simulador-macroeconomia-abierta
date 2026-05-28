"""
ui/dashboard_main.py
====================
Layout de visualización y juego principal durante los 10 turnos (Fase 5.1).
Implementa una arquitectura inmersiva de 3 sectores con theming dinámico avanzado:
  - Sector Izquierdo (Sidebar - Panel de Control): Título, Selector de Temas, y inputs de política macroeconómica.
  - Sector Central (Área de Trabajo Analítica): Cabecera con 6 KPIs macroeconómicos de alta resolución y 4 pestañas estratégicas con placeholders premium.
  - Sector Derecho (Gabinete Presidencial): Moody's Rating Badge, Sala de Crisis con alertas de transmisión y placeholder del Asistente IA.
"""

from __future__ import annotations

import streamlit as st
from engine.state_manager_v2 import SimStateManagerV2
from ui.styles import EXECUTIVE_CSS, STRATEGY_CSS
from ui.charts_v2 import (
    plot_gdp_decomposition,
    plot_sectoral_composition,
    plot_fiscal_odometer,
    plot_butterfly_trade,
    plot_exchange_intervention,
    plot_salter_swan,
    plot_islm_bp_dynamic,
    plot_trilemma_ternary,
    plot_debt_snowball,
    plot_business_cycle_clock,
    plot_reelection_radar,
    STRATEGY_COLORS
)

import plotly.graph_objects as go

def _render_kpi_card_with_history(label: str, val_current: float, target: float, unit: str, history_snaps: list, value_key: str, is_lower_better: bool = False, is_pi_nt: bool = False) -> tuple[str, go.Figure, str]:
    import math
    history_values = []
    semestres = []
    
    for snap in history_snaps[-5:]:
        t = snap.get("t", 0)
        semestres.append(f"t={t}")
        if is_pi_nt:
            val = snap.get("pi_e", 0.03) * 100.0 - 0.2
        else:
            val = snap.get(value_key, 0.0)
            if value_key in ["pi", "U"]:
                val *= 100.0
        history_values.append(val)
        
    deviations = []
    for val in history_values:
        if is_lower_better:
            dev = target - val
        else:
            dev = val - target
        deviations.append(dev)
        
    current_dev = deviations[-1] if deviations else 0.0
    
    if current_dev >= 0:
        color = "#10b981"  # Verde esmeralda
        delta_str = f"▲ +{abs(current_dev):.2f} {unit} vs Meta"
        if is_lower_better:
            delta_str = f"▼ -{abs(current_dev):.2f} {unit} vs Meta (Favorable)"
        else:
            delta_str = f"▲ +{abs(current_dev):.2f} {unit} vs Meta (Favorable)"
    else:
        color = "#ef4444"  # Rojo
        delta_str = f"▼ -{abs(current_dev):.2f} {unit} vs Meta"
        if is_lower_better:
            delta_str = f"▲ +{abs(current_dev):.2f} {unit} vs Meta (Desviación)"
        else:
            delta_str = f"▼ -{abs(current_dev):.2f} {unit} vs Meta (Desviación)"
            
    if unit == "%":
        value_str = f"{val_current:.2f}%"
    elif unit == "PTS":
        value_str = f"{int(val_current)}"
    else:
        value_str = f"{val_current:.2f} {unit}"
        
    html_card = f"""
    <div style="background-color: #0f172a; border-left: 5px solid {color}; padding: 12px; border-radius: 4px; margin-bottom: 5px; min-height: 110px; border-top: 1px solid #1e293b; border-right: 1px solid #1e293b; border-bottom: 1px solid #1e293b; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
      <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px;">{label}</div>
      <div style="font-size: 1.8rem; font-weight: 800; color: {color}; margin-top: 4px; line-height: 1.1; font-family: 'JetBrains Mono', monospace;">{value_str}</div>
      <div style="font-size: 0.75rem; color: {color}; font-weight: 700; margin-top: 6px;">{delta_str}</div>
    </div>
    """
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=semestres,
        y=deviations,
        marker_color=color,
        width=0.25,
        hovertemplate="Semestre %{x}: %{y:+.2f}<extra></extra>"
    ))
    
    fig.update_layout(
        xaxis=dict(
            type='category',
            showgrid=False,
            showline=True,
            linecolor='#334155',
            tickfont=dict(size=8, color="#94a3b8")
        ),
        yaxis=dict(
            zeroline=True,
            zerolinewidth=1.5,
            zerolinecolor='#64748b',
            showgrid=True,
            gridcolor='#1e293b',
            tickfont=dict(size=8, color="#94a3b8")
        ),
        margin=dict(l=5, r=5, t=5, b=5),
        height=95,
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    
    return html_card, fig, color


def render_game_dashboard(mgr: SimStateManagerV2) -> None:
    """
    Orquesta el layout de 3 sectores y aplica el Theming Dinámico (Executive vs Strategy).
    """
    state = mgr.state
    
    # ── TAREA 1: MOTOR DE THEMING DINÁMICO ──────────────────────────────────
    if "theme" not in st.session_state:
        st.session_state["theme"] = "strategy"  # Default theme
        
    # Inicializar toggle del tema en el sidebar
    st.sidebar.markdown("<h2 style='text-align: center; margin-bottom: 0;'>⚙️ THEME </h2>", unsafe_allow_html=True)
    theme_selection = st.sidebar.toggle(
        "Activar Strategy Mode",
        value=(st.session_state["theme"] == "strategy"),
        help="Alterna entre el Executive Mode (Bloomberg Financiero Claro) y el Strategy Mode (Simulación Geopolítica Oscura)."
    )
    
    # Actualizar estado de tema basado en el toggle
    st.session_state["theme"] = "strategy" if theme_selection else "executive"
    
    # Inyectar el bloque de CSS puro dinámicamente
    if st.session_state["theme"] == "strategy":
        st.markdown(STRATEGY_CSS, unsafe_allow_html=True)
    else:
        st.markdown(EXECUTIVE_CSS, unsafe_allow_html=True)
        
    # ── TAREA 2: SECTOR IZQUIERDO (Sidebar - Panel de Control) ────────────────
    st.sidebar.title("🎮 Panel de Control")
    st.sidebar.markdown("<p style='font-size: 0.8rem; text-align: center;'>Administración Macroeconómica Nacional</p>", unsafe_allow_html=True)
    st.sidebar.divider()
    
    # Metadatos breves de administración actual
    t_val = mgr.t
    active_regime = state.get("regime", "fixed")
    regime_ui = active_regime.upper()
    diff_ui = state.get("difficulty", "easy").upper()
    
    st.sidebar.markdown(f"""
    <div class="macro-card" style="padding: 12px; margin-bottom: 15px; border-left: 4px solid #1570EF;">
      <div style="font-size: 0.7rem; font-weight: 700; text-transform: uppercase;">Estado de la Gestión</div>
      <div style="font-size: 1rem; font-weight: 700; margin-top: 4px;">Semestre actual: t = {t_val}/10</div>
      <div style="font-size: 0.75rem; margin-top: 2px;">Régimen Cambiario: <b>{regime_ui}</b></div>
      <div style="font-size: 0.75rem;">Dificultad de Partida: <b>{diff_ui}</b></div>
    </div>
    """, unsafe_allow_html=True)
    
    # ── MEDIDA EXTREMA: Cambio de régimen de emergencia en caliente
    st.sidebar.markdown("<p style='font-size: 0.8rem; font-weight: 700; margin-top: 5px; color: #ef4444; text-transform: uppercase; letter-spacing: 0.5px;'>🚨 Medida Extrema</p>", unsafe_allow_html=True)
    if active_regime in ["fixed", "crawling_peg", "dirty_float"]:
        btn_text = "🔓 Liberar Tipo de Cambio"
        target_regime = "flexible"
    else:
        btn_text = "🔒 Anclar Tipo de Cambio"
        target_regime = "fixed"
        
    if st.sidebar.button(btn_text, use_container_width=True, type="secondary", help="¡ATENCIÓN! Cambiar el régimen cambiario de emergencia penalizará su credibilidad (Score Presidencial -20 pts) y recalculará la economía actual de inmediato."):
        mgr.emergency_regime_switch(target_regime)
        st.toast("🚨 ¡CAMBIO DE RÉGIMEN APLICADO! Se recalculó la economía y se penalizó el Score Presidencial.", icon="⚠️")
        st.rerun()
        
    # Obtener valores actuales de políticas para pre-población de sliders bloqueados
    history = state.get("history", [{}])
    last_snap = history[-1]
    m_current = float(last_snap.get("policy_applied", {}).get("M", last_snap.get("M", 40.0)))
    e_current = float(last_snap.get("policy_applied", {}).get("E", last_snap.get("E", 10.0)))

    # Acordeones para simular sliders e inputs de políticas
    with st.sidebar.expander("🏛️ Política Fiscal", expanded=False):
        st.markdown("<p style='font-size:0.75rem; margin-bottom:10px;'>Ajuste la asignación de recursos y estructura impositiva:</p>", unsafe_allow_html=True)
        st.slider("Gasto Corriente ($G_c$)", min_value=0.0, max_value=40.0, value=15.0, step=1.0, key="fiscal_gc_mock")
        st.slider("Inversión Pública ($I_g$)", min_value=0.0, max_value=30.0, value=5.0, step=1.0, key="fiscal_ig_mock")
        st.slider("Tasa de Impuesto al Consumo ($t_c$)", min_value=0.0, max_value=0.50, value=0.20, step=0.01, key="fiscal_tc_mock")
        st.slider("Transferencias Directas ($Tr$)", min_value=0.0, max_value=20.0, value=0.0, step=1.0, key="fiscal_tr_mock")
        
    with st.sidebar.expander("🏦 Política Monetaria", expanded=False):
        st.markdown("<p style='font-size:0.75rem; margin-bottom:10px;'>Controle el suministro de dinero doméstico y liquidez:</p>", unsafe_allow_html=True)
        if active_regime in ["fixed", "crawling_peg"]:
            st.slider("Oferta Monetaria Exógena ($M$)", min_value=10.0, max_value=150.0, value=float(m_current), step=5.0, key="monetary_m_mock", disabled=True, help="Endógena por Tipo de Cambio Fijo")
            st.caption("⚠️ *M es endógena por régimen de Tipo de Cambio Fijo.*")
        else:
            st.slider("Oferta Monetaria Exógena ($M$)", min_value=10.0, max_value=150.0, value=float(m_current), step=5.0, key="monetary_m_mock")
        st.slider("Encaje Legal Bancario ($\\theta$)", min_value=0.0, max_value=0.30, value=0.10, step=0.01, key="monetary_theta_mock")
        
    with st.sidebar.expander("⚖️ Comercio Exterior y Cambios", expanded=False):
        st.markdown("<p style='font-size:0.75rem; margin-bottom:10px;'>Ajuste las barreras y la paridad nominal cambiaria:</p>", unsafe_allow_html=True)
        if active_regime == "flexible":
            st.slider("Tipo de Cambio Nominal ($E$)", min_value=1.0, max_value=30.0, value=float(e_current), step=0.5, key="trade_e_mock", disabled=True, help="Flotante y Endógeno por Régimen Flexible")
            st.caption("⚠️ *E es endógeno por régimen de Tipo de Cambio Flexible.*")
        else:
            st.slider("Tipo de Cambio Nominal ($E$)", min_value=1.0, max_value=30.0, value=float(e_current), step=0.5, key="trade_e_mock")
        st.slider("Arancel a las Importaciones ($\\tau$)", min_value=0.0, max_value=0.50, value=0.0, step=0.05, key="trade_tau_mock")
        st.slider("Controles de Flujos de Capital ($k_c$)", min_value=0.0, max_value=0.90, value=0.0, step=0.1, key="trade_kc_mock")
        
    st.sidebar.divider()
    
    # ── EJECUCIÓN DEL TURNO Y REINICIO ──────────────────────────────────────
    if st.sidebar.button("⏭️ APLICAR POLÍTICAS Y AVANZAR", use_container_width=True, type="primary"):
        # 1. Capturamos los valores de los sliders desde el session_state
        policy_changes = {
            "G_c": st.session_state.get("fiscal_gc_mock", 15.0),
            "I_g": st.session_state.get("fiscal_ig_mock", 5.0),
            "t_c": st.session_state.get("fiscal_tc_mock", 0.20),
            "Tr":  st.session_state.get("fiscal_tr_mock", 0.0),
            "M":   st.session_state.get("monetary_m_mock", 40.0),
            "theta": st.session_state.get("monetary_theta_mock", 0.10),
            "E":   st.session_state.get("trade_e_mock", 10.0),
            "tau": st.session_state.get("trade_tau_mock", 0.0),
            "k_c": st.session_state.get("trade_kc_mock", 0.0),
        }
        
        # 2. Le pasamos las políticas al motor y avanzamos el semestre
        mgr.step_forward(policy_changes)
        
        # 3. Recargamos la interfaz para ver los resultados
        st.rerun()

    if st.sidebar.button("🔄 Reiniciar Simulación", use_container_width=True, type="secondary"):
        # Borramos el motor de la memoria para volver al Turno 0
        if "mgr" in st.session_state:
            del st.session_state["mgr"]
        st.rerun()

    # ── DIVISIÓN GLOBAL EN COLUMNA CENTRAL Y DERECHA ────────────────────────
    col_centro, col_derecha = st.columns([7, 3])
    
    # Extract historical/snapshot data for metrics representation
    history = state.get("history", [{}])
    last_snap = history[-1]
    
    pib_val = last_snap.get("Y", 100.0)
    pi_t_val = last_snap.get("pi", 0.03) * 100.0
    pi_nt_val = last_snap.get("pi_e", 0.03) * 100.0 - 0.2  # Mock NT inflation
    u_val = last_snap.get("U", 0.05) * 100.0
    r_val = last_snap.get("R", 50.0)
    score_val = last_snap.get("score", 80)
    
    # ── TAREA 4: SECTOR CENTRAL (Área de Trabajo Analítica) ─────────────────
    with col_centro:
        st.markdown("<h1 style='margin-bottom: 2px;'>Terminal de Control Macroeconómico</h1>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 0.9rem; margin-top: 0; color: #475467;'>Tablero analítico intertemporal de la administración soberana</p>", unsafe_allow_html=True)
        
        # 1. Cabecera Fija (Grid de 6 KPIs - HTML Premium + Evolución de Barras)
        # Metas fijas para cada KPI
        pib_target = 100.0
        pi_t_target = 3.0
        pi_nt_target = 3.0
        u_target = 5.0
        r_target = 50.0
        score_target = 80.0

        pib_html, pib_fig, _ = _render_kpi_card_with_history("PIB Real (Y)", pib_val, pib_target, "MM", history, "Y")
        pi_t_html, pi_t_fig, _ = _render_kpi_card_with_history("Inflación Transable (π_T)", pi_t_val, pi_t_target, "%", history, "pi", is_lower_better=True)
        pi_nt_html, pi_nt_fig, _ = _render_kpi_card_with_history("Inflación No-Transable (π_NT)", pi_nt_val, pi_nt_target, "%", history, "", is_lower_better=True, is_pi_nt=True)
        
        u_html, u_fig, _ = _render_kpi_card_with_history("Desempleo (U)", u_val, u_target, "%", history, "U", is_lower_better=True)
        r_html, r_fig, _ = _render_kpi_card_with_history("Reservas Netas (R)", r_val, r_target, "MM", history, "R")
        score_html, score_fig, _ = _render_kpi_card_with_history("Score Presidencial", score_val, score_target, "PTS", history, "score")

        row1 = st.columns(3)
        with row1[0]:
            st.markdown(pib_html, unsafe_allow_html=True)
            st.plotly_chart(pib_fig, use_container_width=True, theme=None)
        with row1[1]:
            st.markdown(pi_t_html, unsafe_allow_html=True)
            st.plotly_chart(pi_t_fig, use_container_width=True, theme=None)
        with row1[2]:
            st.markdown(pi_nt_html, unsafe_allow_html=True)
            st.plotly_chart(pi_nt_fig, use_container_width=True, theme=None)

        st.write("")

        row2 = st.columns(3)
        with row2[0]:
            st.markdown(u_html, unsafe_allow_html=True)
            st.plotly_chart(u_fig, use_container_width=True, theme=None)
        with row2[1]:
            st.markdown(r_html, unsafe_allow_html=True)
            st.plotly_chart(r_fig, use_container_width=True, theme=None)
        with row2[2]:
            st.markdown(score_html, unsafe_allow_html=True)
            st.plotly_chart(score_fig, use_container_width=True, theme=None)
        
        # 2. Sistema de Pestañas (Tabs)
        tab1, tab2, tab3, tab4 = st.tabs([
            "🧱 Economía Real",
            "💱 Sector Externo",
            "📈 Mercados Financieros",
            "📚 Historial & Decisiones"
        ])
        
        with tab1:
            st.markdown("### 🧱 Panel de Actividad Física y Producción")
            col_t1a, col_t1b = st.columns(2)
            with col_t1a:
                fig_gdp = plot_gdp_decomposition(history)
                st.plotly_chart(fig_gdp, use_container_width=True, theme=None)
            with col_t1b:
                fig_sectoral = plot_sectoral_composition(history)
                st.plotly_chart(fig_sectoral, use_container_width=True, theme=None)
            fig_fiscal = plot_fiscal_odometer(last_snap)
            st.plotly_chart(fig_fiscal, use_container_width=True, theme=None)

        with tab2:
            st.markdown("### 💱 Relaciones Comerciales y Tipo de Cambio")
            fig_butterfly = plot_butterfly_trade(history)
            st.plotly_chart(fig_butterfly, use_container_width=True, theme=None)
            col_t2a, col_t2b = st.columns(2)
            with col_t2a:
                fig_intervention = plot_exchange_intervention(history)
                st.plotly_chart(fig_intervention, use_container_width=True, theme=None)
            with col_t2b:
                fig_salter = plot_salter_swan(last_snap, mgr.state["structural"])
                st.plotly_chart(fig_salter, use_container_width=True, theme=None)

        with tab3:
            st.markdown("### 📈 Mercados Financieros y Deuda Soberana")
            fig_islm = plot_islm_bp_dynamic(last_snap, mgr.state["structural"])
            st.plotly_chart(fig_islm, use_container_width=True, theme=None)
            col_t3a, col_t3b = st.columns(2)
            with col_t3a:
                fig_trilemma = plot_trilemma_ternary(last_snap)
                st.plotly_chart(fig_trilemma, use_container_width=True, theme=None)
            with col_t3b:
                fig_deuda = plot_debt_snowball(history, last_snap)
                st.plotly_chart(fig_deuda, use_container_width=True, theme=None)

        with tab4:
            st.markdown("### 📚 Libro de Gestión Histórica y Decisiones")
            col_t4a, col_t4b = st.columns(2)
            with col_t4a:
                fig_clock = plot_business_cycle_clock(history)
                st.plotly_chart(fig_clock, use_container_width=True, theme=None)
            with col_t4b:
                fig_radar = plot_reelection_radar(history)
                st.plotly_chart(fig_radar, use_container_width=True, theme=None)

            # Libro Mayor de Decisiones en tiempo real
            st.markdown("#### 📚 Libro Mayor de Políticas Aplicadas")
            decisions_list = []
            for snap in history:
                pol = snap.get("policy_applied", {})
                decisions_list.append({
                    "Semestre (t)": snap["t"],
                    "Régimen": pol.get("regime", "fixed").upper(),
                    "Gasto Corriente (Gc)": pol.get("G_c", 0.0),
                    "Inv. Pública (Ig)": pol.get("I_g", 0.0),
                    "Impuesto (tc)": f"{pol.get('t_c', 0.0)*100:.1f}%" if "t_c" in pol else f"{pol.get('t', 0.0)*100:.1f}%",
                    "Dinero (M)": pol.get("M", 0.0),
                    "Tipo Cambio (E)": pol.get("E", 0.0),
                    "Arancel (tau)": f"{pol.get('tau', 0.0)*100:.1f}%"
                })
            import pandas as pd
            df_decisions = pd.DataFrame(decisions_list)
            st.dataframe(df_decisions, use_container_width=True, hide_index=True)
            
    # ── TAREA 3: SECTOR DERECHO (Gabinete Presidencial) ─────────────────────
    with col_derecha:
        st.markdown("<h2 style='margin-bottom: 12px;'>👥 Gabinete Presidencial</h2>", unsafe_allow_html=True)
        
        # 1. Sello de Calificación Soberana (Moody's Badge)
        # Extraer rating dinámico del snapshot actual
        rating_val = last_snap.get("rating", "BBB")
        
        st.markdown(f"""
        <div class="rating-badge" style="margin-bottom: 20px;">
            <div class="rating-title">Calificación Moody's</div>
            <div class="rating-value">{rating_val}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. Feed de Noticias / Sala de Crisis
        if t_val == 0:
            st.markdown("<h3 style='font-size:1.1rem; margin-bottom: 8px; opacity: 0.65; color: #94a3b8;'>📰 Reporte de Diagnóstico de Inicio</h3>", unsafe_allow_html=True)
            
            # Diagnóstico inicial atenuado en t=0
            st.markdown("""
            <!-- Diagnóstico 1: Reservas y Régimen -->
            <div class="alert-card" style="border-left-color: #3b82f6 !important; opacity: 0.8;">
                <div style="font-weight: 700; font-size: 0.8rem; text-transform: uppercase; color: #3b82f6;">📋 Diagnóstico Cambiario Inicial</div>
                <div style="font-size: 0.75rem; margin-top: 4px; line-height: 1.3; color: #cbd5e1;">Las reservas internacionales se encuentran en su nivel base de inicio. Se sugiere monitorear la balanza comercial y el tipo de cambio para evitar tensiones de balanza de pagos.</div>
            </div>
            
            <!-- Diagnóstico 2: Situación Fiscal -->
            <div class="alert-card" style="border-left-color: #3b82f6 !important; opacity: 0.8;">
                <div style="font-weight: 700; font-size: 0.8rem; text-transform: uppercase; color: #3b82f6;">📋 Diagnóstico Fiscal y de Hacienda</div>
                <div style="font-size: 0.75rem; margin-top: 4px; line-height: 1.3; color: #cbd5e1;">El presupuesto público inicial parte con una proyección de déficit estable. Se recomienda moderar el gasto corriente para sostener la calificación soberana.</div>
            </div>
            
            <!-- Diagnóstico 3: Inflación y Expectativas -->
            <div class="alert-card" style="border-left-color: #3b82f6 !important; opacity: 0.8;">
                <div style="font-weight: 700; font-size: 0.8rem; text-transform: uppercase; color: #3b82f6;">📋 Diagnóstico de Estabilidad de Precios</div>
                <div style="font-size: 0.75rem; margin-top: 4px; line-height: 1.3; color: #cbd5e1;">La inflación y las expectativas adaptativas se encuentran alineadas con los fundamentos iniciales del escenario macroeconómico seleccionado.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("<h3 style='font-size:1.1rem; margin-bottom: 8px;'>📰 Periódicos & Crisis</h3>", unsafe_allow_html=True)
            
            # Si hay alertas del asesor reales, mostrarlas; sino, mostrar mocks premium definidos
            advisor_warnings = state.get("advisor_warnings", [])
            if advisor_warnings:
                for w in advisor_warnings:
                    adv_name = w.get("advisor", "Gabinete")
                    adv_msg = w.get("message", "")
                    st.markdown(f"""
                    <div class="alert-card-critical">
                        <div style="font-weight: 700; font-size: 0.8rem; text-transform: uppercase;">⚠️ Alerta del Gabinete</div>
                        <div style="font-size: 0.75rem; font-weight: 700; color: #DC2626; margin-top: 2px;">{adv_name.upper()}</div>
                        <div style="font-size: 0.75rem; margin-top: 4px; line-height: 1.3;">{adv_msg}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # Sala de Crisis con alertas mock Premium de transmisión
                st.markdown("""
                <!-- Alerta 1: Crisis Cambiaria -->
                <div class="alert-card-critical">
                    <div style="font-weight: 700; font-size: 0.8rem; text-transform: uppercase;">🚨 Riesgo Cambiario Elevado</div>
                    <div style="font-size: 0.75rem; margin-top: 4px; line-height: 1.3;">Las reservas internacionales netas se encuentran en niveles críticos. Se proyecta que el banco central deba abandonar el tipo de cambio fijo o inyectar divisas vendiendo dólares.</div>
                </div>
                
                <!-- Alerta 2: Crowding Out -->
                <div class="alert-card">
                    <div style="font-weight: 700; font-size: 0.8rem; text-transform: uppercase;">⚠️ Alerta de Crowding Out</div>
                    <div style="font-size: 0.75rem; margin-top: 4px; line-height: 1.3;">El elevado gasto público corriente ($G_c$) está presionando al alza la tasa de interés real doméstica, contrayendo marginalmente la inversión productiva privada.</div>
                </div>
                
                <!-- Alerta 3: Asesor de Hacienda -->
                <div class="alert-card" style="border-left-color: #38BDF8 !important;">
                    <div style="font-weight: 700; font-size: 0.8rem; text-transform: uppercase; color: #38BDF8;">⚖️ Asesor de Hacienda</div>
                    <div style="font-size: 0.75rem; margin-top: 4px; line-height: 1.3;">El odómetro fiscal proyecta un déficit presupuestario del 4.2% del PIB para el próximo semestre debido al incremento en el pago de intereses de la deuda pública.</div>
                </div>
                """, unsafe_allow_html=True)
            
        st.divider()
        
        # 3. Asistente IA (Contenedor Futuro)
        st.markdown("<h3 style='font-size:1.1rem; margin-bottom: 8px;'>🤖 Asistente IA</h3>", unsafe_allow_html=True)
        
        st.markdown("""
        <div class="macro-card" style="border-style: dotted; padding: 20px; text-align: center;">
            <div style="font-size: 1.8rem; margin-bottom: 4px;">🧠</div>
            <div style="font-weight: 700; font-size: 0.85rem; color: #38BDF8;">Gabinete Analítico IA</div>
            <div style="font-size: 0.7rem; margin-top: 4px; line-height: 1.3;">
                [Próximamente]<br>Recomendaciones en tiempo real basadas en teoría macroeconómica pura y optimización de bienestar social.
            </div>
        </div>
        """, unsafe_allow_html=True)
