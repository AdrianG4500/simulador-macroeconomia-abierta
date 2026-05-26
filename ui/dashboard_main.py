"""
ui/dashboard_main.py
====================
Layout de visualización y juego principal durante los 10 turnos (Fase 4).
Implementa un diseño Bloomberg-style inmersivo de 3 columnas:
  - Sidebar: Controles de política cambiaria, fiscal y monetaria + shock exógeno + botón avanzar.
  - Central Column: KPIs con sparklines + 5 pestañas de análisis gráfico interactivo Plotly.
  - Right Column: Feed de noticias del periódico + Panel del Gabinete de Asesores con alertas preventivas.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from engine.state_manager_v2 import SimStateManagerV2
from ui.kpi_panel import render_kpis_panel
from ui.navigation import render_navigation
from ui.charts_v2 import (
    plot_pib_decomposition,
    plot_economic_cycle,
    plot_reserves_thermometer,
    plot_debt_snowball,
    plot_islm_bp_dynamic
)


def render_news_feed_column(state: dict) -> None:
    """
    Renderiza el feed de periódicos y noticias en una columna regular (Panel Derecho)
    en lugar de saturar la barra lateral.
    """
    st.markdown("### 📰 Diario Oficial de la Nación")
    
    news_feed = state.get("news_feed", [])
    if not news_feed:
        st.info("📰 Aún no hay noticias reportadas en la administración.")
        return
        
    # Invertir para mostrar las más recientes arriba
    reversed_news = list(reversed(news_feed))
    recent = reversed_news[:5]
    older = reversed_news[5:]
    
    # Renderizar tarjetas visuales de noticias con HTML Premium
    for item in recent:
        sev = item.get("severity", "info")
        t = item.get("t", 0)
        msg = item["message"]
        
        # Estilos según severidad
        card_bg = "#111e3b"
        border_color = "#3b82f6"
        hdr_color = "#93c5fd"
        badge = "ℹ️ GENERAL"
        
        if sev == "critical":
            card_bg = "#3b111a"
            border_color = "#ef4444"
            hdr_color = "#fca5a5"
            badge = "🚨 CRÍTICO"
        elif sev == "warning":
            card_bg = "#3b2c11"
            border_color = "#f59e0b"
            hdr_color = "#fde047"
            badge = "⚠️ ADVERTENCIA"
            
        headline = badge
        narrative = msg
        if ": " in msg:
            parts = msg.split(": ", 1)
            headline = parts[0]
            narrative = parts[1]
            
        st.markdown(f"""
        <div style='background-color: {card_bg}; border: 1px solid #1e293b; border-left: 5px solid {border_color}; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px;'>
          <div style='display: flex; justify-content: space-between; font-size: 0.7rem; font-weight: 700; margin-bottom: 2px;'>
            <span style='color: {hdr_color}; text-transform: uppercase;'>{headline}</span>
            <span style='color: #64748b;'>Semestre {t}</span>
          </div>
          <div style='font-size: 0.8rem; color: #cbd5e1; line-height: 1.4;'>{narrative}</div>
        </div>
        """, unsafe_allow_html=True)
        
    if older:
        with st.expander("📁 Historial Completo de Periódicos", expanded=False):
            for item in older:
                t = item.get("t", 0)
                msg = item["message"]
                sev = item.get("severity", "info")
                emoji = "ℹ️"
                if sev == "critical":
                    emoji = "🚨"
                elif sev == "warning":
                    emoji = "⚠️"
                st.markdown(f"<div style='font-size: 0.8rem; margin-bottom: 4px;'><b>{emoji} Semestre {t}:</b> {msg}</div>", unsafe_allow_html=True)


def render_advisors_panel(state: dict) -> None:
    """
    Renderiza las advertencias preventivas del Gabinete de Asesores de forma visual
    en el Panel Derecho.
    """
    st.markdown("### 👥 Gabinete de Asesores")
    
    warnings = state.get("advisor_warnings", [])
    
    if not warnings:
        st.markdown("""
        <div style='background-color: #022c22; border: 1px solid #065f46; border-left: 4px solid #10b981; border-radius: 6px; padding: 12px; text-align: center;'>
          <span style='color: #a7f3d0; font-size: 0.85rem; font-weight: 700;'>✅ GABINETE EN CALMA</span>
          <p style='color: #cbd5e1; font-size: 0.75rem; margin: 4px 0 0 0;'>Las proyecciones del próximo semestre no detectan crisis de liquidez cambiaria o fiscal.</p>
        </div>
        """, unsafe_allow_html=True)
        return
        
    # Renderizar cada alerta del asesor
    for w in warnings:
        advisor = w.get("advisor", "Asesor")
        msg = w.get("message", "")
        
        # Definir color del asesor
        color = "#f59e0b"  # Default
        emoji = "👤"
        if "Banco Central" in advisor:
            color = "#3b82f6"
            emoji = "🏦"
        elif "Hacienda" in advisor:
            color = "#8b5cf6"
            emoji = "⚖️"
        elif "Trabajo" in advisor:
            color = "#10b981"
            emoji = "🔨"
        elif "Cambiario" in advisor:
            color = "#ec4899"
            emoji = "💱"
            
        st.markdown(f"""
        <div style='background-color: #1e293b; border: 1px solid #334155; border-left: 4px solid {color}; border-radius: 6px; padding: 10px; margin-bottom: 8px;'>
          <div style='font-size: 0.75rem; font-weight: 800; color: {color}; display: flex; align-items: center; gap: 4px;'>
            <span>{emoji}</span> <span>{advisor.upper()}</span>
          </div>
          <div style='font-size: 0.75rem; color: #cbd5e1; margin-top: 4px; line-height: 1.3;'>{msg}</div>
        </div>
        """, unsafe_allow_html=True)


def render_game_dashboard(mgr: SimStateManagerV2) -> None:
    """
    Orquesta el layout de 3 columnas del juego principal durante los 10 turnos.
    """
    state = mgr.state
    history = state["history"]
    
    # 1. RENDERIZAR LA COLUMNA IZQUIERDA (Sidebar de Streamlit)
    render_navigation()
    
    # 2. SEPARAR EL PANEL PRINCIPAL EN 2 COLUMNAS (Centro 70%, Derecho 30%)
    col_center, col_right = st.columns([13, 5])
    
    # --- COLUMNA CENTRAL ---
    with col_center:
        # A. Renderizar los 6 KPIs macroeconómicos de alto impacto con sparklines
        render_kpis_panel(history)
        
        # B. Encabezado de Progreso y Marcador de Turno
        current_score = history[-1]["score"]
        progress_pct = float(mgr.t) / 10.0
        
        st.markdown(f"""
        <div style='background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 10px 16px; margin: 15px 0; display: flex; justify-content: space-between; align-items: center;'>
          <div style='font-size: 0.85rem; font-weight: 700; color: #e2e8f0;'>
            Semestre de Gobierno: <span style='color: #f59e0b;'>{mgr.t} / 10</span>
          </div>
          <div style='width: 45%; background-color: #1e293b; border-radius: 8px; height: 8px; overflow: hidden; margin: 0 10px;'>
            <div style='width: {progress_pct*100}%; background: linear-gradient(90deg, #3b82f6 0%, #10b981 100%); height: 100%; border-radius: 8px;'></div>
          </div>
          <div style='font-size: 0.85rem; font-weight: 700; color: #e2e8f0;'>
            Score Turno Actual: <span style='color: #10b981;'>{int(current_score)} / 100</span>
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        # C. Panel de Pestañas con los 5 Gráficos Analíticos
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 PIB Componentes",
            "🕰️ Reloj del Ciclo",
            "🌡️ Termómetro Reservas",
            "❄️ Carga de Deuda",
            "🏛️ IS-LM-BP Dinámico"
        ])
        
        with tab1:
            fig_pib = plot_pib_decomposition(history)
            st.plotly_chart(fig_pib, use_container_width=True, key=f"fig_pib_{mgr.t}")
            st.info(
                "💡 **Análisis de Crowding-out:** Observe las barras de Consumo (C), Inversión (I) y Gasto (G). "
                "Si aumenta G sin financiamiento genuino, puede desplazar a la inversión privada o deteriorar las exportaciones netas (NX)."
            )
            
        with tab2:
            fig_ciclo = plot_economic_cycle(history)
            st.plotly_chart(fig_ciclo, use_container_width=True, key=f"fig_ciclo_{mgr.t}")
            st.info(
                "💡 **Actividad Económica:** La trayectoria mapea Desempleo (U) e Inflación (π). "
                "El cuadrante óptimo es el inferior derecho (Zona Ideal). Evite caer en el cuadrante superior izquierdo (Estanflación)."
            )
            
        with tab3:
            R_curr = history[-1]["R"]
            R_0 = history[0]["R"]
            fig_res = plot_reserves_thermometer(R_curr, R_0)
            st.plotly_chart(fig_res, use_container_width=True, key=f"fig_res_{mgr.t}")
            st.info(
                "💡 **Sostenibilidad Cambiaria:** El indicador marca el nivel actual de reservas líquidas. "
                "Si la aguja cae a la zona roja (<30%), se disparará un bank panic debido a la falta de liquidez externa."
            )
            
        with tab4:
            fig_deuda = plot_debt_snowball(history)
            st.plotly_chart(fig_deuda, use_container_width=True, key=f"fig_deuda_{mgr.t}")
            st.info(
                "💡 **Sostenibilidad Fiscal:** Evalúa el porcentaje del gasto público destinado al servicio de intereses de la deuda. "
                "Si el incremento del ratio supera los 3 puntos porcentuales en un semestre, se activará el cartel de 'Bola de Nieve'."
            )
            
        with tab5:
            # Controles interactivos específicos para la pestaña IS-LM-BP
            col_sel1, col_sel2 = st.columns([2, 1])
            with col_sel1:
                max_t = max(1, mgr.t)
                sel_t = st.slider(
                    "Semestre a Analizar",
                    min_value=1,
                    max_value=max_t,
                    value=max_t,
                    key="islm_slider_t"
                )
            with col_sel2:
                compare_prev = st.checkbox(
                    "Comparar con t-1 (Punteado)",
                    value=True,
                    key="islm_compare_prev"
                )
                
            fig_islm = plot_islm_bp_dynamic(mgr, sel_t, overlay_prev=compare_prev)
            st.plotly_chart(fig_islm, use_container_width=True, key=f"fig_islm_{sel_t}_{compare_prev}")
            st.info(
                "💡 **Equilibrio General IS-LM-BP:** Las curvas determinan la intersección de equilibrio general en la tasa de interés "
                "interna (r) y el PIB (Y). La BP posee una pendiente positiva bajo movilidad imperfecta. Active la comparación "
                "para ver el desplazamiento de las curvas desde el semestre anterior."
            )
            
    # --- COLUMNA DERECHA (Panel Derecho) ---
    with col_right:
        # A. Feed de noticias en tarjetas de periódico
        render_news_feed_column(state)
        
        st.divider()
        
        # B. Advertencias del Gabinete de Asesores
        render_advisors_panel(state)
