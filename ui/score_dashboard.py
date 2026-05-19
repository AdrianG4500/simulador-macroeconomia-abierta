import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_score_gauge(score_period: int, score_accum: float, t: int, max_t: int):
    c1, c2 = st.columns(2)
    
    def get_emoji(s):
        if s >= 70: return "🟢"
        elif s >= 40: return "🟡"
        return "🔴"
        
    def get_grade(s):
        if s >= 85: return "A (Excelente)"
        elif s >= 70: return "B (Buena)"
        elif s >= 55: return "C (Aceptable)"
        return "D (Requiere ajuste)"
        
    def _kpi_card(label, value, unit):
        return f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value} <span class="unit">{unit}</span></div>
        </div>"""

    with c1:
        st.markdown(_kpi_card(f"Score t={t} (Período)", f"{score_period}/100", get_emoji(score_period)), unsafe_allow_html=True)
        
    with c2:
        if t > 0:
            st.markdown(_kpi_card("Score Acumulado", f"{score_accum:.1f}/100", get_emoji(score_accum)), unsafe_allow_html=True)
            st.progress(score_accum / 100.0)
            st.caption(f"Calificación de gestión: **{get_grade(score_accum)}**")
            
    if score_period < 40 and t > 0:
        from engine.state_manager import SimStateManager
        from config.scoring import get_crisis_warning
        mgr = SimStateManager()
        history = mgr.state["history"]
        if history:
            current = history[-1]
            warn = get_crisis_warning(current["gY"], current["U"], current["pi"], current["def"], current.get("R", 0))
            if warn:
                st.warning("⚠️ Múltiples desequilibrios macroeconómicos. Score = 0 por circuito de crisis.")
            
def render_score_history(df_history: pd.DataFrame):
    if df_history.empty:
        return
        
    colors = []
    for s in df_history['score']:
        if s >= 70: colors.append('#10b981') # green
        elif s >= 40: colors.append('#f59e0b') # yellow
        else: colors.append('#ef4444') # red
        
    fig = go.Figure(data=[
        go.Bar(
            x=df_history['t'],
            y=df_history['score'],
            marker_color=colors,
            customdata=df_history[['Y', 'pi', 'U', 'policy', 'shock']],
            hovertemplate=(
                "t=%{x}<br>"
                "Score: %{y}<br>"
                "Y: %{customdata[0]:.2f}<br>"
                "π: %{customdata[1]:.2%}<br>"
                "U: %{customdata[2]:.2%}<br>"
                "Política: %{customdata[3]}<br>"
                "Shock: %{customdata[4]}<br>"
                "<extra></extra>"
            )
        )
    ])
    
    fig.add_hline(y=70, line_dash="dash", line_color="green", annotation_text="Óptimo")
    fig.add_hline(y=40, line_dash="dash", line_color="red", annotation_text="Crítico")
    
    fig.update_layout(
        title="Historial de Puntuación por Período",
        xaxis_title="Semestre (t)",
        yaxis_title="Score",
        yaxis_range=[0, 105],
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)
