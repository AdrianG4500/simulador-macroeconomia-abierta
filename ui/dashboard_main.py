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
from config.scoring_v2 import calc_period_score_v2
from ui.charts_v2 import (
    plot_gdp_decomposition,
    plot_sectoral_composition,
    plot_fiscal_odometer,
    plot_butterfly_trade,
    plot_exchange_intervention,
    plot_salter_swan,
    plot_islm_bp_dynamic,
    plot_debt_snowball,
    plot_business_cycle_clock,
    plot_reelection_radar,
    STRATEGY_COLORS
)

import plotly.graph_objects as go

def _render_kpi_card_with_history(label: str, val_current: float, target: float, unit: str, history_snaps: list, value_key: str, is_lower_better: bool = False, is_pi_nt: bool = False) -> tuple[str, go.Figure, str]:
    import numpy as np
    
    snaps_subset = history_snaps[-5:]
    if not snaps_subset:
        return "", go.Figure(), "#0068ff"
        
    semestres = [f"t={snap.get('t', 0)}" for snap in snaps_subset]
    
    # Valores ABSOLUTOS para las barras
    if is_pi_nt:
        history_values = np.array([snap.get("pi_e", 0.03) for snap in snaps_subset], dtype=float) * 100.0 - 0.2
    else:
        multiplier = 100.0 if value_key in ["pi", "U"] else 1.0
        history_values = np.array([snap.get(value_key, 0.0) for snap in snaps_subset], dtype=float) * multiplier
        
    current_snap = snaps_subset[-1]
    current_t = current_snap.get("t", 0)

    # ── SISTEMA DE 5 COLORES (benevolente) ─────────────────────────────────────
    # Azul=T0 | Verde=excelente | Verde-amarillo=bueno | Amarillo-naranja=regular | Rojo=crítico
    def _get_color_tier(val, tgt, lower_better):
        if lower_better:
            dev_pct = abs(val - tgt) / max(abs(tgt), 1e-6) * 100.0
            if dev_pct <= 25:
                return "#10b981", "#047857", "✅ Excelente"
            elif dev_pct <= 60:
                return "#84cc16", "#4d7c0f", "👍 Bueno"
            elif dev_pct <= 120:
                return "#f59e0b", "#b45309", "⚠️ Regular"
            else:
                return "#ef4444", "#b91c1c", "🔴 Crítico"
        else:
            perf_pct = (val / max(abs(tgt), 1e-6)) * 100.0
            if perf_pct >= 88:
                return "#10b981", "#047857", "✅ Excelente"
            elif perf_pct >= 72:
                return "#84cc16", "#4d7c0f", "👍 Bueno"
            elif perf_pct >= 50:
                return "#f59e0b", "#b45309", "⚠️ Regular"
            else:
                return "#ef4444", "#b91c1c", "🔴 Crítico"

    if current_t == 0:
        color = "#0068ff"
        color_text = "#0068ff"
        delta_str = "Diagnóstico Inicial — Referencia Base (T=0)"
    else:
        color, color_text, tier_label = _get_color_tier(val_current, target, is_lower_better)
        delta_str = f"{tier_label} — {val_current:.2f} {unit}  (Meta: {target:.1f} {unit})"
            
    if unit == "%":
        value_str = f"{val_current:.2f}%"
    elif unit == "PTS":
        value_str = f"{int(val_current)}"
    else:
        value_str = f"{val_current:.2f} {unit}"
        
    theme = st.session_state.get("theme", "executive")
    bg_color = "#111827" if theme == "strategy" else "#FFFFFF"
    text_color = "#f8fafc" if theme == "strategy" else "#000000"
    border_color = "#1e293b" if theme == "strategy" else "#E2E8F0"
    label_color = "#94a3b8" if theme == "strategy" else "#475467"
    shadow = "0 4px 6px rgba(0,0,0,0.15)" if theme == "strategy" else "0 1px 3px rgba(0,0,0,0.02)"

    html_card = f"""
    <div style="background-color: {bg_color}; border-left: 5px solid {color}; padding: 12px; border-radius: 6px; margin-bottom: 5px; min-height: 110px; border-top: 1px solid {border_color}; border-right: 1px solid {border_color}; border-bottom: 1px solid {border_color}; box-shadow: {shadow};">
      <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: {label_color}; letter-spacing: 0.5px;">{label}</div>
      <div style="font-size: 1.8rem; font-weight: 800; color: {text_color}; margin-top: 4px; line-height: 1.1; font-family: 'JetBrains Mono', monospace;">{value_str}</div>
      <div style="font-size: 0.75rem; color: {color_text}; font-weight: 700; margin-top: 6px;">{delta_str}</div>
    </div>
    """
    
    # ── Color individual por barra según desempeño histórico ────────────────
    bar_colors = []
    for snap in snaps_subset:
        t_s = snap.get("t", 0)
        if t_s == 0:
            bar_colors.append("#0068ff")
        else:
            if is_pi_nt:
                v = snap.get("pi_e", 0.03) * 100.0 - 0.2
            else:
                mult = 100.0 if value_key in ["pi", "U"] else 1.0
                v = float(snap.get(value_key, 0.0)) * mult
            c, _, _ = _get_color_tier(v, target, is_lower_better)
            bar_colors.append(c)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=semestres,
        y=history_values.tolist(),
        marker_color=bar_colors,
        width=0.35,
        hovertemplate="Semestre %{x}: %{y:.2f}<extra></extra>"
    ))
    
    fig.update_layout(
        xaxis=dict(
            type='category',
            showgrid=False,
            showline=True,
            linecolor='#CBD5E1',
            tickfont=dict(size=8, color="#1E293B")
        ),
        yaxis=dict(
            zeroline=True,
            zerolinewidth=1.5,
            zerolinecolor='#CBD5E1',
            showgrid=True,
            gridcolor='#E2E8F0',
            tickfont=dict(size=8, color="#1E293B")
        ),
        margin=dict(l=30, r=5, t=5, b=5),
        height=95,
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    
    return html_card, fig, color


def render_pocket_metric(label: str, val_metric: float, val_score: float, unit: str, weight: int, help_text: str):
    theme = st.session_state.get("theme", "executive")
    bg_color = "#111827" if theme == "strategy" else "#FFFFFF"
    text_color = "#f8fafc" if theme == "strategy" else "#000000"
    border_color = "#1e293b" if theme == "strategy" else "#E2E8F0"
    label_color = "#94a3b8" if theme == "strategy" else "#475467"
    shadow = "0 4px 6px rgba(0,0,0,0.15)" if theme == "strategy" else "0 1px 3px rgba(0,0,0,0.02)"
    
    color = "#10b981" if val_score >= 70 else "#f59e0b" if val_score >= 40 else "#ef4444"
    
    st.markdown(f"""
    <div style="background-color: {bg_color}; border-left: 5px solid {color}; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-top: 1px solid {border_color}; border-right: 1px solid {border_color}; border-bottom: 1px solid {border_color}; box-shadow: {shadow};">
      <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: {label_color}; letter-spacing: 0.5px;">{label} (Peso {weight}%)</div>
      <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 4px;">
        <div style="font-size: 1.8rem; font-weight: 800; color: {text_color}; line-height: 1.1; font-family: 'JetBrains Mono', monospace;">{val_metric:.2f}{unit}</div>
        <div style="font-size: 1.1rem; font-weight: 700; color: {color};">Score: {val_score:.1f}/100</div>
      </div>
      <div style="font-size: 0.7rem; color: {label_color}; margin-top: 4px;">{help_text}</div>
    </div>
    """, unsafe_allow_html=True)


def _render_plotly_gauge(title: str, value: float, max_val: float, steps: list, unit: str, threshold: float = None) -> go.Figure:
    theme = st.session_state.get("theme", "executive")
    text_color = "#f8fafc" if theme == "strategy" else "#000000"
    label_color = "#94a3b8" if theme == "strategy" else "#475467"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0.1, 0.9], 'y': [0.0, 0.85]},
        number={'suffix': f" {unit}", 'font': {'size': 20, 'family': 'JetBrains Mono', 'color': text_color}},
        gauge={
            'axis': {'range': [0, max_val], 'tickwidth': 1, 'tickcolor': label_color, 'tickfont': {'size': 10}},
            'bar': {'color': "#0068ff"},
            'bgcolor': "#1e293b" if theme == "strategy" else "white",
            'borderwidth': 1,
            'bordercolor': "#334155" if theme == "strategy" else "#cbd5e1",
            'steps': steps,
            'threshold': {'line': {'color': "red", 'width': 3}, 'thickness': 0.75, 'value': threshold} if threshold is not None else None
        }
    ))
    fig.update_layout(
        title={'text': f"<b>{title}</b>", 'font': {'size': 13, 'color': label_color}, 'x': 0.5, 'xanchor': 'center', 'y': 0.95, 'yanchor': 'top'},
        height=160,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig



def render_game_dashboard(mgr: SimStateManagerV2) -> None:
    """
    Orquesta el layout de 3 sectores y aplica el Theming Dinámico (Executive vs Strategy).
    """
    state = mgr.state
    
    # Sincronización del Turno 0 para evitar lag de información
    st.session_state["history"] = state.get("history", [])
    
    # ── TAREA 1: MOTOR DE THEMING DINÁMICO ──────────────────────────────────
    if "theme" not in st.session_state:
        st.session_state["theme"] = "executive"  # Default theme: Bloomberg Financial Clear
        
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
    if mgr.state.get("status") not in ["game_over", "completed"] and mgr.t < 10:
        t_val = mgr.t
        active_regime = state.get("regime", "fixed")
        regime_ui = active_regime.upper()
        diff_ui = state.get("difficulty", "easy").upper()
        
        st.sidebar.markdown(f"""
        <div class="macro-card" style="padding: 12px; margin-bottom: 15px; border-left: 4px solid #0068ff; color: #000000; background-color: #FFFFFF;">
          <div style="font-size: 0.7rem; font-weight: 700; text-transform: uppercase; color: #000000;">Estado de la Gestión</div>
          <div style="font-size: 1rem; font-weight: 700; margin-top: 4px; color: #000000;">Semestre actual: t = {t_val}/10</div>
          <div style="font-size: 0.75rem; margin-top: 2px; color: #000000;">Régimen Cambiario: <b>{regime_ui}</b></div>
          <div style="font-size: 0.75rem; color: #000000;">Dificultad de Partida: <b>{diff_ui}</b></div>
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
            
        if st.sidebar.button(btn_text, use_container_width=True, type="secondary", help="¡ATENCIÓN! Cambiar el régimen cambiario de emergencia penalizará su credibilidad (Percepción Pública -20 pts) y recalculará la economía actual de inmediato."):
            mgr.emergency_regime_switch(target_regime)
            st.toast("🚨 ¡CAMBIO DE RÉGIMEN APLICADO! Se recalculó la economía y se penalizó la Percepción Pública.", icon="⚠️")
            st.rerun()
            
        # Obtener valores actuales de políticas para pre-población de sliders bloqueados
        history = state.get("history", [{}])
        last_snap = history[-1]
        
        gc_current = float(last_snap.get("policy_applied", {}).get("G_c", last_snap.get("G_c", 15.0)))
        ig_current = float(last_snap.get("policy_applied", {}).get("I_g", last_snap.get("I_g", 5.0)))
        tc_current = float(last_snap.get("policy_applied", {}).get("t_c", last_snap.get("t_c", 0.20)))
        tk_current = float(last_snap.get("policy_applied", {}).get("t_k", last_snap.get("t_k", 0.20)))
        tr_current = float(last_snap.get("policy_applied", {}).get("Tr", last_snap.get("Tr", 0.0)))
        theta_current = float(last_snap.get("policy_applied", {}).get("theta", last_snap.get("theta", 0.10)))
        tau_current = float(last_snap.get("policy_applied", {}).get("tau", last_snap.get("tau", 0.0)))
        kc_current = float(last_snap.get("policy_applied", {}).get("k_c", last_snap.get("k_c", 0.0)))
        sx_current = float(last_snap.get("policy_applied", {}).get("s_x", last_snap.get("s_x", 0.0)))
        m_current = float(last_snap.get("policy_applied", {}).get("M", last_snap.get("M", 40.0)))
        e_current = float(last_snap.get("policy_applied", {}).get("E", last_snap.get("E", 10.0)))

        # Acordeones para simular sliders e inputs de políticas
        with st.sidebar.expander("🏛️ Política Fiscal", expanded=False):
            st.markdown("<p style='font-size:0.75rem; margin-bottom:10px;'>Ajuste la asignación de recursos y estructura impositiva:</p>", unsafe_allow_html=True)
            st.slider(
                "Gasto Corriente (Gc)",
                min_value=0.0, max_value=40.0,
                value=float(gc_current), step=1.0,
                key="fiscal_gc_mock",
                help="Financiación de operaciones y servicios diarios del gobierno (salarios, consumos estatales). Impacto: ↑Gc desplaza la demanda IS a la derecha estimulando el PIB a corto plazo, pero ensancha el déficit fiscal acumulando deuda soberana. Unidad: MM USD."
            )
            st.slider(
                "Inversión Pública (Ig)",
                min_value=0.0, max_value=30.0,
                value=float(ig_current), step=1.0,
                key="fiscal_ig_mock",
                help="Proyectos de infraestructura nacional, energía y desarrollo a largo plazo. Impacto: ↑Ig expande la demanda agregada (IS) hoy, y acumula capital público que expande el PIB potencial (Y_pot) a largo plazo, aunque incrementa el déficit inmediato. Unidad: MM USD."
            )
            st.slider(
                "Tasa de Impuesto al Consumo (tc)",
                min_value=0.0, max_value=0.50,
                value=float(tc_current), step=0.01,
                key="fiscal_tc_mock",
                help="Impuesto directo al consumo doméstico. Impacto: ↑tc contrae la demanda agregada (IS), frenando la inflación y el PIB, pero incrementa sustancialmente la recaudación fiscal y reduce el déficit. Unidad: % (Fracción decimal)."
            )
            st.slider(
                "Impuesto a las Empresas (tk)",
                min_value=0.0, max_value=0.50,
                value=float(tk_current), step=0.01,
                key="fiscal_tk_mock",
                help="Gravamen directo sobre las utilidades empresariales. Impacto: ↑tk desincentiva la inversión privada inicial (crowding-out), pero genera recaudación fiscal para el tesoro nacional. Unidad: % (Fracción decimal)."
            )
            st.slider(
                "Transferencias Directas (Tr)",
                min_value=0.0, max_value=20.0,
                value=float(tr_current), step=1.0,
                key="fiscal_tr_mock",
                help="Redistribución y subsidios directos a los hogares. Impacto: ↑Tr estimula el consumo privado autónomo desplazando la IS a la derecha (aumenta PIB y empleo), pero eleva el déficit del período. Unidad: MM USD."
            )
            
        with st.sidebar.expander("🏦 Política Monetaria", expanded=False):
            st.markdown("<p style='font-size:0.75rem; margin-bottom:10px;'>Gestione el instrumento de tasa o encaje legal:</p>", unsafe_allow_html=True)
            if active_regime in ["fixed", "crawling_peg"]:
                st.markdown("**Tasa de Política Monetaria (r_ref)**", help="Tasa de referencia. Bajo tipo de cambio fijo o deslizamiento, la tasa doméstica r está atada a la paridad externa r = r* + ρ.")
                st.info(f"Tasa de interés de paridad: r = {last_snap.get('r', 5.0):.2f}%")
                st.caption("⚠️ *La TPM está bloqueada: atada a la paridad internacional por el Trilema de la Economía Abierta.*")
                st.slider(
                    "Tasa de Política Monetaria (r_ref)",
                    min_value=0.0, max_value=25.0,
                    value=float(last_snap.get("r", 5.0)), step=0.5,
                    key="monetary_r_ref_mock", disabled=True,
                    help="Tasa de referencia de política monetaria. Bajo tipo de cambio fijo o crawling peg, está bloqueada e indexada por paridad de tasas al exterior (r = r_star + rho). Unidad: % anual."
                )
            else:
                r_ref_current = float(last_snap.get("policy_applied", {}).get("r_ref", 5.0))
                st.slider(
                    "Tasa de Política Monetaria (r_ref) [%]",
                    min_value=0.0, max_value=25.0,
                    value=r_ref_current, step=0.5,
                    key="monetary_r_ref_mock",
                    help="Instrumento de tasa (TC Flexible). Impacto: ↑r_ref contrae la demanda de inversión privada (LM a la izquierda), frena el PIB y la inflación, y atrae capitales apreciando la moneda nacional. Unidad: % anual."
                )
            
            st.slider(
                "Encaje Legal Bancario (theta)",
                min_value=0.0, max_value=0.90,
                value=float(theta_current), step=0.01,
                key="monetary_theta_mock",
                help="Coeficiente de reserva mínimo obligatorio de los bancos comerciales. Impacto: ↑theta reduce el multiplicador monetario doméstico y contrae la creación secundaria de dinero. Unidad: % (Fracción decimal)."
            )
            
        with st.sidebar.expander("⚖️ Comercio Exterior y Cambios", expanded=False):
            st.markdown("<p style='font-size:0.75rem; margin-bottom:10px;'>Ajuste las barreras y la paridad nominal cambiaria:</p>", unsafe_allow_html=True)
            if active_regime == "flexible":
                st.slider(
                    "Tipo de Cambio Nominal (E)",
                    min_value=1.0, max_value=30.0,
                    value=float(e_current), step=0.1,
                    key="trade_e_mock", disabled=True,
                    help="Tipo de cambio nominal (Bs/USD). En régimen flexible es endógeno y se ajusta por libre oferta y demanda de divisas en el mercado BP."
                )
                st.caption("⚠️ *E es endógeno por régimen de Tipo de Cambio Flexible.*")
            else:
                st.slider(
                    "Tipo de Cambio Nominal (E)",
                    min_value=1.0, max_value=30.0,
                    value=float(e_current), step=0.1,
                    key="trade_e_mock",
                    help="Tipo de cambio nominal nominal (Bs/USD). Fijado bajo tipo de cambio fijo o crawling peg. Impacto: devaluar (↑E) estimula la balanza comercial y exportaciones (↑NX) a costa de encarecer importaciones e importar inflación (pass-through). Unidad: Bs/USD."
                )
            
            if active_regime == "crawling_peg":
                crawl_current = float(last_snap.get("policy_applied", {}).get("crawl_rate", last_snap.get("crawl_rate", 0.02)))
                st.slider(
                    "Tasa de Deslizamiento (crawl_rate)",
                    min_value=0.0, max_value=0.10,
                    value=crawl_current, step=0.005,
                    format="%.3f",
                    key="trade_crawl_mock",
                    help="Tasa porcentual a la cual se devalúa programadamente el tipo de cambio nominal en cada período (E_t = E_prev * (1 + crawl_rate)). Impacto: equilibra de forma previsible competitividad y expectativas de inflación. Unidad: % (Fracción decimal)."
                )
                
            st.slider(
                "Arancel a las Importaciones (tau)",
                min_value=0.0, max_value=0.50,
                value=float(tau_current), step=0.01,
                key="trade_tau_mock",
                help="Impuesto aduanero a las importaciones. Impacto: ↑tau reduce las importaciones y mejora la balanza comercial (NX) protegiendo el empleo nacional, pero incrementa el nivel de precios local (inflación). Unidad: % (Fracción decimal)."
            )
            st.slider(
                "Subsidio a las Exportaciones (sx)",
                min_value=0.0, max_value=0.30,
                value=float(sx_current), step=0.01,
                key="trade_sx_mock",
                help="Estímulo fiscal directo a exportaciones brutas. Impacto: ↑sx abarata los productos nacionales en el exterior mejorando las exportaciones netas (↑NX, ↑PIB), con un costo directo sobre el presupuesto del gobierno. Unidad: % (Fracción decimal)."
            )
            st.slider(
                "Controles de Flujos de Capital (kc)",
                min_value=0.0, max_value=0.90,
                value=float(kc_current), step=0.01,
                key="trade_kc_mock",
                help="Restricciones administrativas a la libre movilidad de capitales financieros. Impacto: ↑kc reduce la fuga de divisas en crisis y aísla la tasa doméstica del tipo de cambio, pero penaliza la atracción de inversiones externas. Unidad: % (Fracción decimal)."
            )
            
        st.sidebar.divider()
        
        # ── EJECUCIÓN DEL TURNO Y REINICIO ──────────────────────────────────────
        if st.sidebar.button("⏭️ APLICAR POLÍTICAS Y AVANZAR", use_container_width=True, type="primary"):
            # 1. Capturamos los valores de los sliders desde el session_state
            policy_changes = {
                "G_c": st.session_state.get("fiscal_gc_mock", 15.0),
                "I_g": st.session_state.get("fiscal_ig_mock", 5.0),
                "t_c": st.session_state.get("fiscal_tc_mock", 0.20),
                "t_k": st.session_state.get("fiscal_tk_mock", 0.20),
                "Tr":  st.session_state.get("fiscal_tr_mock", 0.0),
                "monetary_mode": "rate_targeting" if active_regime == "flexible" else "quantity",
                "r_ref": st.session_state.get("monetary_r_ref_mock", 5.0),
                "M": m_current,
                "theta": st.session_state.get("monetary_theta_mock", 0.10),
                "E":   st.session_state.get("trade_e_mock", 10.0),
                "tau": st.session_state.get("trade_tau_mock", 0.0),
                "s_x": st.session_state.get("trade_sx_mock", 0.0),
                "k_c": st.session_state.get("trade_kc_mock", 0.0),
                "crawl_rate": st.session_state.get("trade_crawl_mock", 0.02) if active_regime == "crawling_peg" else 0.0,
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
    else:
        st.sidebar.markdown("### 🏛️ Gestión Concluida")
        if st.sidebar.button("🔄 Reiniciar Partida", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # ── DIVISIÓN GLOBAL EN COLUMNA CENTRAL Y DERECHA ────────────────────────
    col_centro, col_derecha = st.columns([7, 3], gap="medium")
    
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
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
                <h1 style="margin: 0; font-size: 2.5rem;">Tablero de Mando Soberano</h1>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<p style='font-size: 0.9rem; margin-top: 0; color: #475467;'>Tablero analítico intertemporal de la administración soberana</p>", unsafe_allow_html=True)
        
        # 1. Cabecera Fija (Grid de 6 KPIs - HTML Premium + Evolución de Barras)
        # Metas específicas de cada escenario cargado en st.session_state (Fase V3.0)
        scenario_id = st.session_state.get("ob_scenario", "Economia_Saludable")
        
        scenario_targets = {
            "tiger_asia": {"pib": 105.0, "pi_t": 3.0, "pi_nt": 3.0, "u": 4.0, "r": 85.0, "score": 85.0},
            "Economia_Saludable": {"pib": 130.0, "pi_t": 8.0, "pi_nt": 8.0, "u": 4.0, "r": 60.0, "score": 85.0},
            "trade_deficit": {"pib": 100.0, "pi_t": 3.0, "pi_nt": 3.0, "u": 5.0, "r": 120.0, "score": 80.0},
            "latam_crisis": {"pib": 80.0, "pi_t": 15.0, "pi_nt": 15.0, "u": 12.0, "r": 20.0, "score": 50.0},
            "death_spiral": {"pib": 78.0, "pi_t": 35.0, "pi_nt": 35.0, "u": 10.0, "r": 20.0, "score": 50.0},
            "Bolivia_2024_Stagflation": {"pib": 95.0, "pi_t": 8.0, "pi_nt": 8.0, "u": 7.0, "r": 30.0, "score": 75.0},
            "Boom_Exportador": {"pib": 105.0, "pi_t": 3.0, "pi_nt": 3.0, "u": 4.0, "r": 80.0, "score": 80.0},
            "Credit_Crunch": {"pib": 95.0, "pi_t": 4.0, "pi_nt": 4.0, "u": 7.0, "r": 30.0, "score": 75.0}
        }
        
        targets = scenario_targets.get(scenario_id, {"pib": 100.0, "pi_t": 3.0, "pi_nt": 3.0, "u": 5.0, "r": 50.0, "score": 80.0})
        pib_target = targets["pib"]
        pi_t_target = targets["pi_t"]
        pi_nt_target = targets["pi_nt"]
        u_target = targets["u"]
        r_target = targets["r"]
        score_target = targets["score"]

        pib_html, pib_fig, _ = _render_kpi_card_with_history("PIB Real (Y)", pib_val, pib_target, "MM", history, "Y")
        pi_t_html, pi_t_fig, _ = _render_kpi_card_with_history("Inflación Transable (π_T)", pi_t_val, pi_t_target, "%", history, "pi", is_lower_better=True)
        pi_nt_html, pi_nt_fig, _ = _render_kpi_card_with_history("Inflación No-Transable (π_NT)", pi_nt_val, pi_nt_target, "%", history, "", is_lower_better=True, is_pi_nt=True)
        
        u_html, u_fig, _ = _render_kpi_card_with_history("Desempleo (U)", u_val, u_target, "%", history, "U", is_lower_better=True)
        r_html, r_fig, _ = _render_kpi_card_with_history("Reservas Netas (R)", r_val, r_target, "MM", history, "R")
        score_html, score_fig, _ = _render_kpi_card_with_history("🗳️ Percepción Pública", score_val, score_target, "PTS", history, "score")

        row1 = st.columns(3)
        with row1[0]:
            st.markdown(pib_html, unsafe_allow_html=True)
            st.plotly_chart(pib_fig, use_container_width=True, theme=None, key="kpi_pib", config={'displayModeBar': False})
        with row1[1]:
            st.markdown(pi_t_html, unsafe_allow_html=True)
            st.plotly_chart(pi_t_fig, use_container_width=True, theme=None, key="kpi_pi_t", config={'displayModeBar': False})
        with row1[2]:
            st.markdown(pi_nt_html, unsafe_allow_html=True)
            st.plotly_chart(pi_nt_fig, use_container_width=True, theme=None, key="kpi_pi_nt", config={'displayModeBar': False})

        st.write("")

        row2 = st.columns(3)
        with row2[0]:
            st.markdown(u_html, unsafe_allow_html=True)
            st.plotly_chart(u_fig, use_container_width=True, theme=None, key="kpi_u", config={'displayModeBar': False})
        with row2[1]:
            st.markdown(r_html, unsafe_allow_html=True)
            st.plotly_chart(r_fig, use_container_width=True, theme=None, key="kpi_r", config={'displayModeBar': False})
        with row2[2]:
            st.markdown(score_html, unsafe_allow_html=True)
            st.plotly_chart(score_fig, use_container_width=True, theme=None, key="kpi_score", config={'displayModeBar': False})
        
        # 2. Sistema de Pestañas (Tabs) V3.2
        tab1, tab2, tab3 = st.tabs([
            "📊 Economía Real y Mercado Laboral",
            "🏦 Sector Monetario y Canal Cambiario",
            "🏛️ Sostenibilidad Fiscal y Restricciones de Stock"
        ])
        
        # Recalcular sub-scores usando la fórmula exacta del motor V4.7 (config/scoring_v2.py)
        # 1. SCORE DE DESEMPLEO (Peso 40%)
        u_val_raw = last_snap.get("U", 0.05)
        diff_U = max(0.0, u_val_raw - 0.04)
        if diff_U < 0.02:
            penalty_U = 0.0
        else:
            penalty_U = (diff_U - 0.02) * 1000.0
            
        # Si tiene superávit fiscal real (déficit < 0), se reduce a la mitad la penalidad de desempleo
        deficit_val = last_snap.get("deficit", 0.0)
        if deficit_val < 0.0:
            penalty_U *= 0.5
            
        # Ventana de gracia para escenarios con crisis profundas en turnos 1 a 3
        current_turn = last_snap.get("t", 0)
        if scenario_id in ["latam_crisis", "death_spiral"] and 1 <= current_turn <= 3:
            penalty_U *= 0.5

        score_U = max(0.0, 100.0 - penalty_U)

        # 2. SCORE DE INFLACIÓN (Peso 40%)
        pi_val_raw = last_snap.get("pi", 0.03)
        desviacion_pi = pi_val_raw - 0.03
        if desviacion_pi < 0:
            # Deflación: penalidad reducida y con zona de no-castigo hasta -2%
            penalty_pi = max(0.0, abs(desviacion_pi) - 0.04) * 80.0
        else:
            # Inflación: penalidad estricta
            penalty_pi = desviacion_pi * 333.0
            
        if scenario_id in ["latam_crisis", "death_spiral"] and 1 <= current_turn <= 3:
            penalty_pi *= 0.5

        score_pi = max(0.0, 100.0 - penalty_pi)

        # 3. SCORE DE CRECIMIENTO (Peso 20%)
        gY_val_raw = last_snap.get("gY", 0.0)
        score_gY = max(0.0, min(100.0, 50.0 + (gY_val_raw * 1000)))

        score_present = (score_U * 0.40) + (score_pi * 0.40) + (score_gY * 0.20)
        
        # Suavizado por media móvil (60% actual, 40% anterior)
        if len(history) >= 2:
            prev_score = history[-2].get("score", score_present)
            weighted_sum = 0.60 * score_present + 0.40 * prev_score
        else:
            weighted_sum = score_present
            
        weighted_sum = round(weighted_sum, 2)
        
        with tab1:
            st.markdown("### 📊 Economía Real y Mercado Laboral")
            
            # Fila de 3 columnas de bolsillo
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                render_pocket_metric(
                    label="Empleo",
                    val_metric=u_val,
                    val_score=round(score_U, 1),
                    unit="%",
                    weight=40,
                    help_text="Aprobación óptima con desempleo ≤ 4.0%."
                )
            with col_b2:
                render_pocket_metric(
                    label="Precios",
                    val_metric=pi_t_val,
                    val_score=round(score_pi, 1),
                    unit="%",
                    weight=40,
                    help_text="Aprobación óptima con inflación en torno al 3.0%."
                )
            with col_b3:
                render_pocket_metric(
                    label="Crecimiento PIB",
                    val_metric=gY_val_raw * 100.0,
                    val_score=round(score_gY, 1),
                    unit="%",
                    weight=20,
                    help_text="Aprobación neutral a 0%; óptima al 5%."
                )
            
            # Advertencia de penalización si el score no coincide con la suma ponderada (ej. por castigo cambiario)
            diff_score = round(weighted_sum - score_val, 2)
            if diff_score >= 19.5:  # Si hay un castigo por cambio de régimen de emergencia
                st.warning("⚠️ **Penalización por Cambio de Régimen Cambiario de Emergencia:** -20.0 PTS aplicados a la aprobación por shock de credibilidad.")
            
            # Salter-Swan a ancho completo para que el punto del país sea visible
            fig_salter = plot_salter_swan(last_snap, mgr.state["structural"])
            st.plotly_chart(fig_salter, use_container_width=True, theme=None, key="chart_salter", config={'displayModeBar': False})

            # Layout de 2 columnas de gráficos
            col_t1a, col_t1b = st.columns(2)
            with col_t1a:
                fig_gdp = plot_gdp_decomposition(history)
                st.plotly_chart(fig_gdp, use_container_width=True, theme=None, key="chart_gdp", config={'displayModeBar': False})
            with col_t1b:
                fig_clock = plot_business_cycle_clock(history)
                st.plotly_chart(fig_clock, use_container_width=True, theme=None, key="chart_clock", config={'displayModeBar': False})

            fig_radar = plot_reelection_radar(history)
            st.plotly_chart(fig_radar, use_container_width=True, theme=None, key="chart_radar", config={'displayModeBar': False})

        with tab2:
            st.markdown("### 🏦 Sector Monetario y Canal Cambiario")
            
            # Renderizar IS-LM-BP a ancho completo para máxima claridad y detalle
            fig_islm = plot_islm_bp_dynamic(last_snap, mgr.state["structural"])
            st.plotly_chart(fig_islm, use_container_width=True, theme=None, key="chart_islm", config={'displayModeBar': False})
                
            # Gráfica de intervención y balanza comercial / mariposa abajo
            col_t2c, col_t2d = st.columns(2)
            with col_t2c:
                fig_intervention = plot_exchange_intervention(history)
                st.plotly_chart(fig_intervention, use_container_width=True, theme=None, key="chart_intervention", config={'displayModeBar': False})
            with col_t2d:
                fig_butterfly = plot_butterfly_trade(history)
                st.plotly_chart(fig_butterfly, use_container_width=True, theme=None, key="chart_butterfly", config={'displayModeBar': False})

            # Explicación del Trilema y Liquidez
            st.markdown("#### 🏛️ Comportamiento de la Política Monetaria y Cambiaria")
            active_regime = state.get("regime", "fixed")
            if active_regime == "fixed":
                st.info(
                    "**Régimen Cambiario: Tipo de Cambio Fijo (E es exógeno)**\n\n"
                    "La paridad cambiaria está fijada de manera rígida. El Banco Central sacrifica su autonomía monetaria "
                    "para sostener el tipo de cambio. La oferta de dinero ($M$) se vuelve endógena pasiva para acomodar la "
                    "tasa de interés doméstica al nivel de equilibrio externo (paridad internacional): $r = r^* + \\rho$.\n\n"
                    f"**Masa Monetaria de Equilibrio ($M_{{implícita}}$):** {last_snap.get('M', 0.0):.2f} unidades."
                )
            elif active_regime == "crawling_peg":
                st.info(
                    "**Régimen Cambiario: Crawling Peg (Deslizamiento cambiario programado)**\n\n"
                    "El tipo de cambio nominal se deprecia de manera controlada y previsible según la tasa de deslizamiento ($crawl\\_rate$). "
                    "Al igual que en el tipo de cambio fijo, el Banco Central pierde autonomía monetaria directa: "
                    "la tasa de interés queda atada a la paridad externa indexada al deslizamiento ($r = r^* + crawl\\_rate + \\rho$). "
                    "La oferta monetaria ($M$) es endógena pasiva.\n\n"
                    f"**Masa Monetaria de Equilibrio ($M_{{implícita}}$):** {last_snap.get('M', 0.0):.2f} unidades."
                )
            elif active_regime == "flexible":
                # Determinar si r_ref o M está activo
                mon_mode_disp = last_snap.get("policy_applied", {}).get("monetary_mode", "rate_targeting")
                if mon_mode_disp == "rate_targeting":
                    st.success(
                        "**Régimen Cambiario: Tipo de Cambio Flexible (E es endógeno)**\n\n"
                        "El tipo de cambio flota libremente en el mercado. El Banco Central recupera su autonomía monetaria y opera bajo "
                        "el paradigma moderno de **Metas de Inflación / Tasa de Referencia (`rate_targeting`)**. "
                        "La tasa de política monetaria ($r_{ref}$) es el instrumento activo fijado exógenamente. "
                        "La oferta de dinero ($M$) se vuelve endógena para convalidar dicha tasa en el mercado de dinero.\n\n"
                        f"**Masa Monetaria Implícita de Equilibrio ($M_{{implícita}}$):** {last_snap.get('M', 0.0):.2f} unidades."
                    )
                else:
                    st.info(
                        "**Régimen Cambiario: Tipo de Cambio Flexible (E es endógeno)**\n\n"
                        "El tipo de cambio flota libremente en el mercado. El Banco Central utiliza la oferta nominal de dinero ($M$) "
                        "como instrumento exógeno directo para desplazar la LM y determinar la tasa de interés nominal $r$ de equilibrio.\n\n"
                        f"**Masa Monetaria de Turno ($M$):** {last_snap.get('M', 0.0):.2f} unidades."
                    )

        with tab3:
            st.markdown("### 🏛️ Sostenibilidad Fiscal y Restricciones de Stock")
            
            # Fila de 2 columnas de odómetros/gauges interactivos
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                # Reservas Netas (R) Gauge
                R_0 = history[0]["R"]
                steps_r = [
                    {'range': [0.0, R_0 * 0.5], 'color': "#fee2e2"},
                    {'range': [R_0 * 0.5, R_0 * 0.8], 'color': "#fef3c7"},
                    {'range': [R_0 * 0.8, R_0 * 2.5], 'color': "#d1fae5"}
                ]
                fig_r_gauge = _render_plotly_gauge(
                    title="Nivel de Reservas Netas (R)",
                    value=r_val,
                    max_val=R_0 * 2.5,
                    steps=steps_r,
                    unit="MM",
                    threshold=R_0 * 0.5
                )
                st.plotly_chart(fig_r_gauge, use_container_width=True, key="gauge_reservas", config={'displayModeBar': False})
            with col_g2:
                # Déficit Fiscal en % del PIB Gauge
                deficit_pct = (last_snap.get("deficit", 0.0) / max(1.0, last_snap.get("Y", 100.0))) * 100.0
                steps_def = [
                    {'range': [-5.0, 3.0], 'color': "#d1fae5"},
                    {'range': [3.0, 6.0], 'color': "#fef3c7"},
                    {'range': [6.0, 15.0], 'color': "#fee2e2"}
                ]
                fig_def_gauge = _render_plotly_gauge(
                    title="Déficit Fiscal (% PIB)",
                    value=deficit_pct,
                    max_val=15.0,
                    steps=steps_def,
                    unit="%",
                    threshold=8.0
                )
                st.plotly_chart(fig_def_gauge, use_container_width=True, key="gauge_deficit", config={'displayModeBar': False})
            
            # Advertencia crítica si la deuda se acerca al umbral
            B_pct = (last_snap.get("B", 0.0) / max(1.0, last_snap.get("Y", 100.0))) * 100.0
            if B_pct >= 90.0:
                st.error(f"🚨 **ALERTA CRÍTICA DE SOLVENCIA:** La deuda pública acumulada representa el **{B_pct:.1f}%** del PIB. Riesgo de default inminente si se cruza el umbral del **120%-150%**.")
            elif B_pct >= 60.0:
                st.warning(f"⚠️ **RIESGO FISCAL ELEVADO:** La deuda pública acumulada representa el **{B_pct:.1f}%** del PIB. Se recomienda contención fiscal y control del déficit.")
            
            # Layout de 2 columnas de gráficos abajo
            col_t3a, col_t3b = st.columns(2)
            with col_t3a:
                fig_deuda = plot_debt_snowball(history, last_snap)
                st.plotly_chart(fig_deuda, use_container_width=True, theme=None, key="chart_deuda", config={'displayModeBar': False})
            with col_t3b:
                fig_fiscal = plot_fiscal_odometer(last_snap)
                st.plotly_chart(fig_fiscal, use_container_width=True, theme=None, key="chart_fiscal", config={'displayModeBar': False})

        # Collapsible expanders at the bottom of the page (below telemetry tabs)
        st.write("")
        st.divider()
        with st.expander("📚 Libro Mayor de Decisiones e Historial"):
            st.markdown("### 📚 Libro de Gestión Histórica y Decisiones")
            decisions_list = []
            for snap in history:
                pol = snap.get("policy_applied", {})
                decisions_list.append({
                    "Semestre (t)": snap["t"],
                    "Régimen": pol.get("regime", "fixed").upper(),
                    "Gasto Corriente (Gc)": pol.get("G_c", 0.0),
                    "Inv. Pública (Ig)": pol.get("I_g", 0.0),
                    "Impuesto (tc)": f"{pol.get('t_c', 0.20)*100:.1f}%",
                    "TPM (r_ref)": f"{pol.get('r_ref', 5.0):.2f}%" if pol.get("regime", "fixed") == "flexible" else f"{snap.get('r', 5.0):.2f}% (Fijada por Paridad)",
                    "Tipo Cambio (E)": pol.get("E", 0.0),
                    "Arancel (tau)": f"{pol.get('tau', 0.0)*100:.1f}%"
                })
            import pandas as pd
            df_decisions = pd.DataFrame(decisions_list)
            st.dataframe(df_decisions, use_container_width=True, hide_index=True)
            
        with st.expander("🔍 Inspección Técnica de Consistencia Ex-Post (Debug)"):
            st.markdown("### 🔍 Inspección Técnica y Consistencia de Datos (Debug)")
            st.markdown("<p style='font-size: 0.85rem; color: #64748b; margin-top:-10px;'>Auditoría intertemporal completa del equilibrio macroeconómico.</p>", unsafe_allow_html=True)
            
            # Construcción y extracción del DataFrame de consistencia ex-post (Debug)
            debug_rows = []
            sp = state.get("structural", {})
            
            for i, snap in enumerate(history):
                t = snap.get("t", 0)
                pol = snap.get("policy_applied", {})
                
                # 1. Políticas Exógenas (Sliders)
                G_c = pol.get("G_c", snap.get("G_c", 15.0))
                I_g = pol.get("I_g", snap.get("I_g", 5.0))
                t_c = pol.get("t_c", snap.get("t_c", 0.20))
                t_k = pol.get("t_k", snap.get("t_k", 0.20))
                M = snap.get("M", pol.get("M", 40.0))
                E = pol.get("E", pol.get("E", 10.0))
                theta = pol.get("theta", 0.10)
                tau = pol.get("tau", 0.0)
                k_c = pol.get("k_c", 0.0)
                Tr = pol.get("Tr", 0.0)
                regime = pol.get("regime", snap.get("regime", "fixed"))
                
                # 2. Parámetros del Motor
                k_m = snap.get("mult", 1.5)
                rho = snap.get("rho", 0.0)
                velocity_penalty = snap.get("velocity_penalty", 1.0)
                f_eff = max(sp.get("f", 10.0) * (1.0 - k_c), 1e-4)
                
                x0 = sp.get("x0", 0.0)
                x1 = sp.get("x1", 0.0)
                Y_star = sp.get("Y_star", 0.0)
                m0 = sp.get("m0", 0.0)
                use_disaggregated = (x0 != 0.0 or m0 != 0.0 or x1 != 0.0 or Y_star != 0.0)
                ml_ok = (sp.get("epsilon_x", 0.5) + sp.get("epsilon_m", 0.5)) > 1.0
                j_curve_active = snap.get("j_curve_active", False)
                if use_disaggregated:
                    if j_curve_active:
                        eps_x_eff = 0.10
                        eps_m_eff = 0.10
                    elif ml_ok:
                        eps_x_eff = sp.get("epsilon_x", 0.5)
                        eps_m_eff = sp.get("epsilon_m", 0.5)
                    else:
                        eps_x_eff = -(sp.get("epsilon_m", 0.5) - sp.get("epsilon_x", 0.5))
                        eps_m_eff = sp.get("epsilon_m", 0.5)
                else:
                    if j_curve_active:
                        eps_eff = 0.10
                    elif ml_ok:
                        eps_eff = sp.get("epsilon_x", 0.5)
                    else:
                        eps_eff = -(sp.get("epsilon_m", 0.5) - sp.get("epsilon_x", 0.5))
                    eps_x_eff = eps_eff
                    eps_m_eff = sp.get("epsilon_m", 0.5)
                    
                G_total = G_c + I_g
                if use_disaggregated:
                    NX0_eff = x0 + x1 * Y_star - m0
                else:
                    NX0_eff = sp.get("NX0", 0.0)
                rho_k = sp.get("rho_k", 0.0)
                A_auto = sp.get("c0", 50.0) + sp.get("c1", 0.6) * Tr + sp.get("I0", 15.0) - rho_k * t_k + G_total + NX0_eff
                
                # 3. Resultados
                Y = snap.get("Y", 100.0)
                gap = snap.get("gap", 0.0)
                Y_pot = Y / (1.0 + gap) if abs(gap + 1.0) > 1e-5 else 100.0
                U = snap.get("U", 0.05)
                pi = snap.get("pi", 0.03)
                
                if i == 0:
                    pi_core = pi
                else:
                    prev_snap = history[i - 1]
                    E_prev = prev_snap.get("E", 10.0)
                    E_curr = snap.get("E", 10.0)
                    devaluation_rate = (E_curr - E_prev) / max(E_prev, 1e-9)
                    beta_PT = sp.get("beta_PT", 0.4)
                    pi_core = max(-0.015, pi - beta_PT * devaluation_rate)
                    
                R = snap.get("R", 50.0)
                B = snap.get("B", 0.0)
                NX = snap.get("NX", 0.0)
                
                CF = snap.get("capital_flows_eq", 0.0)
                
                s_x = pol.get("s_x", snap.get("s_x", 0.0))
                gY = snap.get("gY", 0.0)
                r_rate = snap.get("r", 5.0)
                P_local = snap.get("P_local", 4.60)
                score = snap.get("score", 90.0)
                events = snap.get("events_triggered", [])
                events_str = ", ".join(events) if events else "--"
                
                # Ratios
                B_Y = B / Y if Y > 0 else 0.0
                nom_GDP = Y * P_local
                R_nomGDP = R / nom_GDP if nom_GDP > 0 else 0.0

                debug_rows.append({
                    "t": f"T{t}",
                    "Regimen": regime.upper(),
                    "G_c": round(G_c, 2),
                    "I_g": round(I_g, 2),
                    "t_c": f"{t_c*100:.1f}%",
                    "t_k": f"{t_k*100:.1f}%",
                    "Tr": round(Tr, 2),
                    "M": round(M, 2) if regime == "flexible" else f"{round(M, 2)} (Endógena)",
                    "E": round(E, 2),
                    "theta": f"{theta*100:.1f}%",
                    "tau": f"{tau*100:.1f}%",
                    "s_x": f"{s_x*100:.1f}%",
                    "k_c": f"{k_c*100:.1f}%",
                    "Y": round(Y, 2),
                    "Y_pot": round(Y_pot, 2),
                    "Gap(%)": f"{gap*100:.2f}%",
                    "U(%)": f"{U*100:.2f}%",
                    "pi(%)": f"{pi*100:.2f}%",
                    "gY(%)": f"{gY*100:.2f}%",
                    "r": round(r_rate, 2),
                    "B": round(B, 2),
                    "R": round(R, 2),
                    "NX": round(NX, 2),
                    "P_local": round(P_local, 4),
                    "B/Y": round(B_Y, 3),
                    "R/nomGDP": round(R_nomGDP, 4),
                    "Score": round(score, 2),
                    "Eventos": events_str
                })
                
            import pandas as pd
            df_debug = pd.DataFrame(debug_rows)
            st.dataframe(df_debug, use_container_width=True, hide_index=True)
            
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
        if t_val == 0:
            st.markdown("<h3 style='font-size:1.1rem; margin-bottom: 8px; font-weight: bold; color: #000000;'>📰 Reporte de Diagnóstico de Inicio</h3>", unsafe_allow_html=True)
            
            # Diagnóstico inicial atenuado en t=0
            st.markdown("""
            <!-- Diagnóstico 1: Reservas y Régimen -->
            <div class="alert-card" style="border-left-color: #0068ff !important; background-color: #FFFFFF; border: 1px solid #E2E8F0;">
                <div style="font-weight: 700; font-size: 0.95rem; text-transform: uppercase; color: #0068ff;">📋 Diagnóstico Cambiario Inicial</div>
                <div style="font-size: 0.85rem; margin-top: 4px; line-height: 1.35; color: #000000;">Las reservas internacionales se encuentran en su nivel base de inicio. Se sugiere monitorear la balanza comercial y el tipo de cambio para evitar tensiones de balanza de pagos.</div>
            </div>
            
            <!-- Diagnóstico 2: Situación Fiscal -->
            <div class="alert-card" style="border-left-color: #0068ff !important; background-color: #FFFFFF; border: 1px solid #E2E8F0;">
                <div style="font-weight: 700; font-size: 0.95rem; text-transform: uppercase; color: #0068ff;">📋 Diagnóstico Fiscal y de Hacienda</div>
                <div style="font-size: 0.85rem; margin-top: 4px; line-height: 1.35; color: #000000;">El presupuesto público inicial parte con una proyección de déficit estable. Se recomienda moderar el gasto corriente para sostener la calificación soberana.</div>
            </div>
            
            <!-- Diagnóstico 3: Inflación y Expectativas -->
            <div class="alert-card" style="border-left-color: #0068ff !important; background-color: #FFFFFF; border: 1px solid #E2E8F0;">
                <div style="font-weight: 700; font-size: 0.95rem; text-transform: uppercase; color: #0068ff;">📋 Diagnóstico de Estabilidad de Precios</div>
                <div style="font-size: 0.85rem; margin-top: 4px; line-height: 1.35; color: #000000;">La inflación y las expectativas adaptativas se encuentran alineadas con los fundamentos iniciales del escenario macroeconómico seleccionado.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("<h3 style='font-size:1.1rem; margin-bottom: 8px;'>📰 CONTEXTO GENERAL Y ALERTAS</h3>", unsafe_allow_html=True)
            
            # Leer los eventos activos del periodo actual
            active_events = state.get("active_events", [])
            if history:
                active_events = list(set(active_events + history[-1].get("events_triggered", [])))
                
            EVENT_METADATA = {
                "commodity_supercycle": {"title": "📈 BOOM EN COMMODITIES", "color": "#10b981", "desc": "Precios de exportación suben drásticamente. Términos de intercambio mejoran de forma sin precedentes (+20 NX0, +10% P*)."},
                "fed_rate_shock": {"title": "🏦 ALZA DE TASAS DE LA FED", "color": "#ef4444", "desc": "La Fed endurece su tasa de referencia en +400 pb. Fuerte drenaje de liquidez global y encarecimiento del crédito."},
                "global_recession": {"title": "📉 RECESIÓN GLOBAL CONTRAE DEMANDA", "color": "#ef4444", "desc": "Gran desaceleración en las potencias mundiales. Caída de exportaciones autónomas y elasticidad de exportación."},
                "tech_productivity": {"title": "💻 REVOLUCIÓN TECNOLÓGICA", "color": "#10b981", "desc": "Adopción masiva de IA y automatización. Tasa de crecimiento potencial anual aumenta +1% permanentemente."},
                "natural_disaster": {"title": "🚨 SEVERO DESASTRE NATURAL AZOTA CAPITAL", "color": "#ef4444", "desc": "Daños severos en infraestructura y redes logísticas. Pérdida del 10% del PIB potencial y gasto forzoso de reconstrucción."},
                "social_unrest": {"title": "💥 DISTURBIOS SOCIALES POR DESEMPLEO", "color": "#ef4444", "desc": "Falta de empleo desata protestas masivas, reduciendo el PIB potencial en 5% y contrayendo la propensión marginal a consumir."},
                "bank_panic": {"title": "🏦 PÁNICO BANCARIO: CORRIDA CONTRA EL PESO", "color": "#ef4444", "desc": "Bajas reservas desatan rumores de devaluación y corralito. Las expectativas de devaluación suben al 20%."},
                "stagflation_trap": {"title": "📈 TRAMPA DE ESTANFLACIÓN INERCIAL", "color": "#ef4444", "desc": "Coexistencia de nulo crecimiento con inflación alta consolida inflación inercial base permanentemente en +5%."},
                "virtuous_circle": {"title": "🌟 CÍRCULO VIRTUOSO MACROECONÓMICO", "color": "#10b981", "desc": "Gran dinamismo y sólido control fiscal despiertan optimismo inversor, reduciendo el efecto crowding-out de las tasas de interés."}
            }
 
            # Mostrar eventos reales por encima
            has_events = False
            for ev_id in active_events:
                if ev_id in EVENT_METADATA:
                    has_events = True
                    meta = EVENT_METADATA[ev_id]
                    st.markdown(f"""
                    <div style="border-left: 5px solid {meta['color']} !important; margin-bottom: 12px; background-color: #FFFFFF; padding: 12px; border-radius: 6px; border-top: 1px solid #E2E8F0; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                        <div style="font-weight: 700; font-size: 0.95rem; text-transform: uppercase; color: {meta['color']};">{meta['title']}</div>
                        <div style="font-size: 0.85rem; margin-top: 4px; line-height: 1.35; color: #000000;">{meta['desc']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Si hay alertas del asesor reales, mostrarlas a continuación
            advisor_warnings = state.get("advisor_warnings", [])
            if advisor_warnings:
                for w in advisor_warnings:
                    adv_name = w.get("advisor", "Gabinete")
                    adv_msg = w.get("message", "")
                    st.markdown(f"""
                    <div class="alert-card-critical">
                        <div style="font-weight: 700; font-size: 0.95rem; text-transform: uppercase;">⚠️ Alerta del Gabinete</div>
                        <div style="font-size: 0.85rem; font-weight: 700; color: #DC2626; margin-top: 2px;">{adv_name.upper()}</div>
                        <div style="font-size: 0.85rem; margin-top: 4px; line-height: 1.35;">{adv_msg}</div>
                    </div>
                    """, unsafe_allow_html=True)
            elif not has_events:
                # Sala de Crisis con alertas mock Premium de transmisión si no hay eventos reales
                show_riesgo = (state.get("regime", "fixed") == "fixed") and (state.get("R", 0.0) < 0.25 * state.get("Y_pot", 100.0))
                riesgo_cambiario_html = """
                <!-- Alerta 1: Crisis Cambiaria -->
                <div class="alert-card-critical">
                    <div style="font-weight: 700; font-size: 0.95rem; text-transform: uppercase;">🚨 Riesgo Cambiario Elevado</div>
                    <div style="font-size: 0.85rem; margin-top: 4px; line-height: 1.35;">Las reservas internacionales netas se encuentran en niveles críticos. Se proyecta que el banco central deba abandonar el tipo de cambio fijo o inyectar divisas vendiendo dólares.</div>
                </div>
                """ if show_riesgo else ""
 
                st.markdown(f"""
                {riesgo_cambiario_html}
                <!-- Alerta 2: Crowding Out -->
                <div class="alert-card">
                    <div style="font-weight: 700; font-size: 0.95rem; text-transform: uppercase;">⚠️ Alerta de Crowding Out</div>
                    <div style="font-size: 0.85rem; margin-top: 4px; line-height: 1.35;">El elevado gasto público corriente ($G_c$) está presionando al alza la tasa de interés real doméstica, contrayendo marginalmente la inversión productiva privada.</div>
                </div>
                
                <!-- Alerta 3: Asesor de Hacienda -->
                <div class="alert-card" style="border-left-color: #38BDF8 !important;">
                    <div style="font-weight: 700; font-size: 0.95rem; text-transform: uppercase; color: #38BDF8;">⚖️ Asesor de Hacienda</div>
                    <div style="font-size: 0.85rem; margin-top: 4px; line-height: 1.35;">El odómetro fiscal proyecta un déficit presupuestario del 4.2% del PIB para el próximo semestre debido al incremento en el pago de intereses de la deuda pública.</div>
                </div>
                """, unsafe_allow_html=True)
            
        st.divider()
        
        # 3. Asistente IA (Contenedor Futuro)
        st.markdown("<h3 style='font-size:1.1rem; margin-bottom: 8px;'>🤖 Asistente IA</h3>", unsafe_allow_html=True)
        
        text_color = "#f8fafc" if st.session_state.get("theme", "executive") == "strategy" else "#000000"
        bg_color = "#111827" if st.session_state.get("theme", "executive") == "strategy" else "#FFFFFF"
        border_color = "#334155" if st.session_state.get("theme", "executive") == "strategy" else "#E2E8F0"
        
        st.markdown(f"""
        <div class="macro-card" style="border: 2px dotted {border_color}; padding: 20px; text-align: center; background-color: {bg_color}; border-radius: 8px;">
            <div style="font-size: 1.8rem; margin-bottom: 4px;">🧠</div>
            <div style="font-weight: 700; font-size: 0.95rem; color: #38BDF8;">Gabinete Analítico IA</div>
            <div style="font-size: 0.85rem; margin-top: 4px; line-height: 1.35; color: {text_color};">
                [Próximamente]<br>Recomendaciones en tiempo real basadas en teoría macroeconómica pura y optimización de bienestar social.
            </div>
        </div>
        """, unsafe_allow_html=True)

