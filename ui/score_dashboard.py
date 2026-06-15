"""
ui/score_dashboard.py
=====================
Cuadro de mando de puntuación y desempeño macroeconómico V2.0 (Fase 3).

Muestra el puntaje del período actual, el promedio acumulado de la gestión,
y un desglose detallado de las 5 dimensiones clave del score V2.0.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from config.scoring_v2 import get_dimension_scores, get_score_emoji, get_score_label


def render_score_gauge(score_period: int, score_accum: float, t: int, max_t: int) -> None:
    """
    Renderiza las tarjetas del score del período y acumulado, junto a su desglose.
    """
    c1, c2 = st.columns(2)

    def _kpi_card(label, value, extra_html):
        return f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value} {extra_html}</div>
        </div>"""

    # Recuperar el orquestador V2
    if "mgr" not in st.session_state:
        return
    mgr = st.session_state["mgr"]
    history = mgr.state["history"]
    
    if not history:
        return
        
    current_snap = history[-1]
    
    # Calcular el desglose de las 5 dimensiones para el período actual
    R_0_ref = history[0]["R"]
    deficit_pct = current_snap["deficit"] / max(current_snap["Y"], 1e-6)
    
    dimensions = get_dimension_scores(
        gap=current_snap["gap"],
        U=current_snap["U"],
        pi=current_snap["pi"],
        deficit_pct=deficit_pct,
        R=current_snap["R"],
        R_0=R_0_ref,
        gY=current_snap.get("gY", 0.0),
        scenario_id=mgr.state.get("scenario_id", "unknown"),
        current_turn=t,
        has_real_fiscal_surplus=(current_snap["deficit"] < 0.0),
    )

    with c1:
        emoji = get_score_emoji(score_period)
        st.markdown(_kpi_card(f"Score Período Actual (t = {t})", f"{score_period}/100", f"<span style='font-size:1.2rem;'>{emoji}</span>"), unsafe_allow_html=True)
        
        # Desglose de dimensiones en formato premium unificado
        st.markdown("**Desglose de Desempeño (Período):**")
        
        d_cols = st.columns(3)
        d_lbls = [
            ("Empleo (40%)", "U", 40, "💼"),
            ("Precios (40%)", "pi", 40, "📈"),
            ("Crecimiento (20%)", "gY", 20, "🔵")
        ]
        
        for idx, (label, key, max_pts, icon) in enumerate(d_lbls):
            val = dimensions.get(key, 0)
            color = "green" if val >= max_pts * 0.7 else "orange" if val >= max_pts * 0.4 else "red"
            with d_cols[idx]:
                st.markdown(f"""
                <div style='text-align: center; background: #0f172a; padding: 6px; border: 1px solid #1e293b; border-radius: 6px;'>
                  <div style='font-size: 1.1rem;'>{icon}</div>
                  <div style='font-size: 0.75rem; font-weight: 600; color: #94a3b8;'>{label}</div>
                  <div style='font-size: 0.9rem; font-weight: 800; color: {color};'>{val}/{max_pts}</div>
                </div>
                """, unsafe_allow_html=True)
        
    with c2:
        if t > 0:
            emoji_accum = get_score_emoji(int(score_accum))
            st.markdown(_kpi_card("Score Promedio Acumulado", f"{score_accum:.1f}/100", f"<span style='font-size:1.2rem;'>{emoji_accum}</span>"), unsafe_allow_html=True)
            st.progress(score_accum / 100.0)
            
            label_accum = get_score_label(int(score_accum))
            st.markdown(f"Calificación de la gestión del Ministro: **{label_accum}**")


def render_score_history(df_history: pd.DataFrame) -> None:
    """
    Dibuja un gráfico de barras interactivo con el historial de puntuaciones.
    """
    if df_history.empty:
        return
        
    colors = []
    for s in df_history['score']:
        if s >= 70:
            colors.append('#10b981') # green
        elif s >= 40:
            colors.append('#f59e0b') # yellow
        else:
            colors.append('#ef4444') # red
        
    fig = go.Figure(data=[
        go.Bar(
            x=df_history['t'],
            y=df_history['score'],
            marker_color=colors,
            customdata=df_history[['Y', 'pi', 'U', 'policy_applied']],
            hovertemplate=(
                "Semestre: t = %{x}<br>"
                "Puntuación: %{y}/100<br>"
                "PIB: %{customdata[0]:.2f} MM<br>"
                "Inflación: %{customdata[1]:.2%}<br>"
                "Desempleo: %{customdata[2]:.2%}<br>"
                "Políticas: %{customdata[3]}<br>"
                "<extra></extra>"
            )
        )
    ])
    
    fig.add_hline(y=70, line_dash="dash", line_color="green", annotation_text="Excelente (70+)")
    fig.add_hline(y=40, line_dash="dash", line_color="red", annotation_text="Crítico (<40)")
    
    fig.update_layout(
        title="Trayectoria del Desempeño de Gobierno (Score)",
        xaxis_title="Semestre (t)",
        yaxis_title="Puntaje",
        yaxis_range=[0, 105],
        template="plotly_dark",
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#1e293b"),
    )
    
    st.plotly_chart(fig, use_container_width=True)
