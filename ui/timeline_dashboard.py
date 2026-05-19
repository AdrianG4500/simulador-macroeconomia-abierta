import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from ui.score_dashboard import render_score_gauge

@st.cache_data
def get_timeline_fig(df, selected_vars):
    fig = go.Figure()

    color_map = {
        "Y": "#1e40af",
        "r": "#f59e0b",
        "E": "#10b981",
        "R": "#ef4444",
        "B": "#8b5cf6",
        "pi": "#ec4899",
        "U": "#06b6d4",
        "gY": "#10b981",
        "def": "#ef4444",
        "score": "#64748b"
    }

    for i, var in enumerate(selected_vars):
        is_secondary = (i > 0)

        unit_str = " MM $" if var in ["Y", "R", "B"] else "%" if var in ["pi", "U", "gY", "def", "r"] else ""
        
        fig.add_trace(go.Scatter(
            x=df['t'],
            y=df[var],
            mode='lines+markers',
            name=var,
            line=dict(color=color_map.get(var, "#000000"), width=2),
            yaxis="y2" if is_secondary else "y",
            customdata=df[['policy', 'shock']],
            hovertemplate=(
                f"<b>{var}</b>: %{{y:.2f}}{unit_str}<br>"
            ) + (
                "Política: %{customdata[0]}<br>"
                "Shock: %{customdata[1]}<br>"
                "<extra></extra>"
            )
        ))

    layout_update = {
        "title": "Evolución Temporal de Variables",
        "xaxis_title": "Semestre (t)",
        "yaxis_title": selected_vars[0] if len(selected_vars) > 0 else "",
        "template": "plotly_dark",
        "plot_bgcolor": "#0B1120",
        "paper_bgcolor": "#0B1120",
        "font": dict(color="#e2e8f0"),
        "xaxis": dict(gridcolor="#1e293b", zerolinecolor="#334155"),
        "yaxis": dict(gridcolor="#1e293b", zerolinecolor="#334155"),
        "hovermode": "x unified",
        "margin": dict(l=40, r=20, t=40, b=40),
        "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(17,24,39,0.85)", bordercolor="#334155")
    }

    if len(selected_vars) > 1:
        layout_update["yaxis2"] = dict(
            title="Otras variables",
            overlaying="y",
            side="right"
        )

    fig.update_layout(**layout_update)
    return fig

def render_timeline_tab(mgr, regime: str):
    history = mgr.state["history"]
    if not history:
        st.warning("No hay datos simulados aún. Calibra e inicia la simulación.")
        return

    df_raw = pd.DataFrame(history)
    if 'params' in df_raw.columns:
        df_raw = df_raw.drop(columns=['params'])
    if 'eq' in df_raw.columns:
        df_raw = df_raw.drop(columns=['eq'])
    if 'policy' in df_raw.columns:
        df_raw['policy'] = df_raw['policy'].astype(str)
    if 'shock' in df_raw.columns:
        df_raw['shock'] = df_raw['shock'].astype(str)

    col_chart, col_kpis = st.columns([3, 1])

    with col_chart:
        options = ["Y", "r", "E", "M", "R", "B", "pi", "U", "gY", "def", "score"]
        selected_vars = st.multiselect("Selecciona hasta 4 variables:", options, default=["Y", "r"], max_selections=4)

        if selected_vars:
            fig = get_timeline_fig(df_raw, selected_vars)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Unidades: MM $, %, adimensional")

        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            st.download_button(
                label="📥 Exportar Trayectoria",
                data=df_raw.to_csv(index=False).encode('utf-8'),
                file_name="trayectoria_macro.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        with col_btn2:
            t = mgr.t
            btn_disabled = (t == 0)
            narrator_clicked = st.button("🎙️ Narrador Chávez", disabled=btn_disabled, help="Avanza al menos un semestre" if btn_disabled else "Generar análisis narrativo con IA", use_container_width=True)
            
        if narrator_clicked:
            with st.spinner("Gonzalo está revisando los números..."):
                import json
                from utils.narrator_ai import call_chavez_narrator
                
                current_data = history[-1]
                prev_data = history[-2] if len(history) > 1 else history[-1]
                
                trend = {}
                for k in ["Y", "R", "score"]:
                    if current_data[k] > prev_data[k]: trend[k] = "↑ Sube"
                    elif current_data[k] < prev_data[k]: trend[k] = "↓ Baja"
                    else: trend[k] = "→ Estable"
                    
                context_dict = {
                    "t": t,
                    "regime": regime,
                    "policy": current_data.get("policy", "Ninguna"),
                    "shock": current_data.get("shock", "Ninguno"),
                    "Y": current_data.get("Y"),
                    "R": current_data.get("R"),
                    "E": current_data.get("E"),
                    "pi": current_data.get("pi"),
                    "U": current_data.get("U"),
                    "score": current_data.get("score"),
                    "trend": trend
                }
                
                narrative = call_chavez_narrator(json.dumps(context_dict, sort_keys=True))
                
                # Render full width outside columns
                st.markdown(f"""
<style>
.narrador-container {{
    width: 100%;
    max-width: 100%;
    margin: 0 auto;
    padding: 10px 0;
}}
.narrador-box {{
    background: #111827;
    border-left: 4px solid #f59e0b;
    border-radius: 8px;
    padding: 24px;
    margin-top: 10px;
    width: 100%;
    text-align: justify;
}}
.narrador-title {{
    color: #f59e0b;
    font-weight: 700;
    margin-bottom: 12px;
    text-align: center;
}}
.narrador-text {{
    color: #e2e8f0;
    line-height: 1.8;
    font-size: 1rem;
}}
</style>
<div class="narrador-container">
    <div class="narrador-box">
        <h4 class="narrador-title">🎙️ Análisis del Narrador</h4>
        <div class="narrador-text">{narrative}</div>
    </div>
</div>
""", unsafe_allow_html=True)

    with col_kpis:
        st.subheader("KPIs Período Actual")
        t = mgr.t
        if t > 0:
            current = history[-1]
            prev = history[-2] if len(history) > 1 else history[-1]

            def _kpi_card(label, value, unit, delta=None):
                delta_html = ""
                if delta is not None:
                    sign = "+" if delta >= 0 else ""
                    color = "#10b981" if delta >= 0 else "#ef4444"
                    delta_html = f'<span style="color:{color};font-size:2.1rem;margin-left:6px;">{sign}{delta:.2f}</span>'
                return f"""
                <div class="metric-card">
                  <div class="metric-label">{label}</div>
                  <div class="metric-value">{value} <span class="unit">{unit}</span>{delta_html}</div>
                </div>"""

            def metric_delta(key, label, format_str="{:.2f}", is_percent=False, unit=""):
                val = current[key]
                delta = val - prev[key] if len(history) > 1 else 0
                if is_percent:
                    st.markdown(_kpi_card(label, format_str.format(val * 100), unit, delta=delta * 100), unsafe_allow_html=True)
                else:
                    st.markdown(_kpi_card(label, format_str.format(val), unit, delta=delta), unsafe_allow_html=True)

            metric_delta("Y", "PIB (Y)", "{:,.1f}", unit="MM $")
            metric_delta("r", "Tasa Interés (r)", "{:.2f}", unit="%")
            metric_delta("E", "Tipo Cambio (E)", "{:.2f}", unit="Bs/USD")
            metric_delta("R", "Reservas (R)", "{:,.1f}", unit="MM $")
            metric_delta("B", "Deuda Pública (B)", "{:,.1f}", unit="MM $")
            metric_delta("pi", "Inflación (π)", "{:.2f}", is_percent=True, unit="%")
            metric_delta("U", "Desempleo (U)", "{:.2f}", is_percent=True, unit="%")
            metric_delta("gY", "Crecimiento (gY)", "{:+.2f}", is_percent=True, unit="%")
            metric_delta("def", "Déficit Fiscal", "{:+.2f}", is_percent=True, unit="% PIB")

            score_period = current["score"]
            score_accum = df_raw["score"].mean()

            st.divider()
            from config.scoring import get_score_color, get_crisis_warning
            st.markdown(_kpi_card("Score", f"{score_period}/100", get_score_color(score_period)), unsafe_allow_html=True)
            
            if score_period < 40:
                warn = get_crisis_warning(current["gY"], current["U"], current["pi"], current["def"], current["R"])
                if warn:
                    st.warning(warn)

            st.divider()
            from ui.score_dashboard import render_score_gauge
            render_score_gauge(score_period, score_accum, t, 10)
