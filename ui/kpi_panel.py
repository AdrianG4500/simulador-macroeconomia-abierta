"""
ui/kpi_panel.py
===============
Panel de KPIs de alto impacto con minigráficos (Sparklines) embebidos (Fase 4).

Rinde 6 KPIs clave: PIB, Inflación, Desempleo, Reservas, Deuda y Score.
Cada KPI se rinde en un card con:
  - Nombre del KPI y valor actual en grande.
  - Variación porcentual o absoluta del turno anterior (delta con flechas ↑/↓).
  - Un minigráfico Plotly (Sparkline) que muestra la tendencia reciente (últimos 5 turnos).
  - Color semafórico (verde, amarillo, rojo) según el estado saludable de la variable.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
from engine.game_state import TurnSnapshot


def get_kpi_status(key: str, val: float, R_0: float = 50.0, prev_snap: TurnSnapshot | None = None) -> tuple[str, str]:
    """
    Retorna el color semafórico y el formato del valor actual para cada KPI.
    
    Returns:
        tuple[color_hex, format_str]
    """
    # Verdes, amarillos y rojos curados (Paleta HSL Premium)
    GREEN = "#10b981"
    YELLOW = "#f59e0b"
    RED = "#ef4444"

    if key == "score":
        if val >= 70:
            return GREEN, f"{int(val)}/100"
        elif val >= 40:
            return YELLOW, f"{int(val)}/100"
        return RED, f"{int(val)}/100"

    elif key == "Y":
        # Se evalúa indirectamente a través del output gap si está disponible
        gap = 0.0
        if prev_snap:
            gap = prev_snap.get("gap", 0.0)
        # gap óptimo: [-1%, +3%] (green), acc: [-3%, +5%] (yellow)
        if -0.01 <= gap <= 0.03:
            return GREEN, f"{val:.1f} MM"
        elif -0.03 <= gap <= 0.05:
            return YELLOW, f"{val:.1f} MM"
        return RED, f"{val:.1f} MM"

    elif key == "pi":
        # pi óptimo: [1%, 4%] (green), acc: [0%, 6%] (yellow)
        if 0.01 <= val <= 0.04:
            return GREEN, f"{val*100:.2f}%"
        elif 0.00 <= val <= 0.06:
            return YELLOW, f"{val*100:.2f}%"
        return RED, f"{val*100:.2f}%"

    elif key == "U":
        # U óptimo: < 5% (green), acc: < 8% (yellow)
        if val <= 0.05:
            return GREEN, f"{val*100:.2f}%"
        elif val <= 0.08:
            return YELLOW, f"{val*100:.2f}%"
        return RED, f"{val*100:.2f}%"

    elif key == "R":
        # R / R_0 óptimo: > 80% (green), acc: > 50% (yellow)
        ratio = val / max(R_0, 1.0)
        if ratio >= 0.80:
            return GREEN, f"{val:.1f} MM"
        elif ratio >= 0.50:
            return YELLOW, f"{val:.1f} MM"
        return RED, f"{val:.1f} MM"

    elif key == "B":
        # Deuda nominal / PIB
        debt_ratio = val / 100.0  # asumiendo PIB inicial ~ 100
        if prev_snap and prev_snap.get("Y", 100.0) > 0:
            debt_ratio = val / prev_snap["Y"]
            
        if debt_ratio <= 0.50:
            return GREEN, f"{val:.1f} MM"
        elif debt_ratio <= 0.80:
            return YELLOW, f"{val:.1f} MM"
        return RED, f"{val:.1f} MM"

    return "#94a3b8", f"{val:.2f}"


def render_kpi_card(
    label: str,
    key: str,
    history_values: list[float],
    R_0: float = 50.0,
    prev_snap: TurnSnapshot | None = None
) -> None:
    """
    Renderiza una tarjeta de KPI con sparkline inline de forma visualmente premium.
    """
    if not history_values:
        st.write("Cargando...")
        return

    val_curr = history_values[-1]
    color, val_str = get_kpi_status(key, val_curr, R_0, prev_snap)

    # Calcular variación (Delta) respecto al turno anterior
    delta_str = ""
    delta_color = "#94a3b8"
    if len(history_values) >= 2:
        val_prev = history_values[-2]
        diff = val_curr - val_prev
        
        # Formatear el delta
        if key in ("pi", "U"):
            pct_diff = diff * 100
            arrow = "↑" if diff > 0 else "↓"
            sign = "+" if diff > 0 else ""
            delta_str = f"{arrow} {sign}{pct_diff:.2f}%"
        else:
            arrow = "↑" if diff > 0 else "↓"
            sign = "+" if diff > 0 else ""
            delta_str = f"{arrow} {sign}{diff:.1f}"

        # Lógica semántica del color del delta
        # Para inflación, desempleo y deuda, subir es malo. Para PIB, reservas y score, subir es bueno.
        subir_es_bueno = key in ("Y", "R", "score")
        if diff > 0.0001:
            delta_color = "#10b981" if subir_es_bueno else "#ef4444"
        elif diff < -0.0001:
            delta_color = "#ef4444" if subir_es_bueno else "#10b981"
    else:
        delta_str = "t=0 Base"
        delta_color = "#94a3b8"

    # Rango reciente del sparkline: últimos min(5, t) turnos
    spark_data = history_values[-5:] if len(history_values) >= 5 else history_values

    # Generar Sparkline con Plotly
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(spark_data))),
        y=spark_data,
        mode="lines+markers",
        line=dict(color=color, width=2.5),
        marker=dict(size=4, color=color),
        hoverinfo="none"
    ))
    
    # Hacer el sparkline extremadamente minimalista y transparente
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        height=48,
        margin=dict(l=4, r=4, t=4, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )

    # Renderizar en dos columnas dentro del card (HTML + CSS inyectado + Sparkline)
    st.markdown(f"""
    <div style='background: #111827; border: 1px solid #1e293b; border-left: 4px solid {color}; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.15);'>
      <div style='display: flex; justify-content: space-between; align-items: center;'>
        <div style='font-size: 0.75rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;'>{label}</div>
        <div style='font-size: 0.75rem; color: {delta_color}; font-weight: 700;'>{delta_str}</div>
      </div>
      <div style='display: flex; justify-content: space-between; align-items: flex-end; margin-top: 4px;'>
        <div style='font-size: 1.4rem; font-weight: 800; color: #f8fafc;'>{val_str}</div>
        <div style='width: 90px; height: 35px; overflow: hidden; padding-bottom: 4px;' id='sparkline_{key}'>
    """, unsafe_allow_html=True)
    
    st.plotly_chart(fig, use_container_width=True, key=f"spark_{key}_{len(history_values)}", config={"displayModeBar": False, "staticPlot": True})
    
    st.markdown("</div></div></div>", unsafe_allow_html=True)


def render_kpis_panel(history: list[TurnSnapshot]) -> None:
    """
    Dibuja el panel completo de 6 KPIs en un grid de 3x2.
    """
    if not history:
        return

    R_0 = history[0]["R"]
    current = history[-1]

    # Extraer vectores de historia
    y_hist = [h["Y"] for h in history]
    pi_hist = [h["pi"] for h in history]
    u_hist = [h["U"] for h in history]
    r_hist = [h["R"] for h in history]
    b_hist = [h["B"] for h in history]
    score_hist = [h["score"] for h in history]

    # Renderizar fila 1: PIB, Inflación, Desempleo
    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi_card("PIB Real (Y)", "Y", y_hist, R_0, current)
    with c2:
        render_kpi_card("Tasa de Inflación (π)", "pi", pi_hist, R_0, current)
    with c3:
        render_kpi_card("Tasa de Desempleo (U)", "U", u_hist, R_0, current)

    # Renderizar fila 2: Reservas, Deuda, Score
    c4, c5, c6 = st.columns(3)
    with c4:
        render_kpi_card("Reservas Internacionales (R)", "R", r_hist, R_0, current)
    with c5:
        render_kpi_card("Deuda Pública Acumulada (B)", "B", b_hist, R_0, current)
    with c6:
        render_kpi_card("Puntuación de Gobierno", "score", score_hist, R_0, current)
