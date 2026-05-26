"""
ui/charts_v2.py
===============
Gráficos interactivos Plotly macroeconómicos avanzados V2.0 (Fase 4).

Contiene los 5 gráficos analíticos:
  1. plot_pib_decomposition   : PIB por componentes (barras apiladas) + Y_pot (línea).
  2. plot_economic_cycle      : Reloj del Ciclo Económico (cuadrantes interactivos U-pi).
  3. plot_reserves_gauge      : Termómetro de Reservas (indicador Gauge semafórico).
  4. plot_debt_snowball       : Termómetro "Bola de Nieve de Deuda" (% gasto en intereses).
  5. plot_islm_bp_dynamic     : Curvas IS-LM-BP dinámicas con pendiente BP y overlay t-1.
"""

from __future__ import annotations

import math
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from engine.core_v2 import compute_multiplier, is_curve_v2, lm_curve_v2, compute_NX
from engine.game_state import TurnSnapshot


# ─────────────────────────────────────────────────────────────────────────────
# CHART 1: DESCOMPOSICIÓN DEL PIB (BARRAS APILADAS + PIB POTENCIAL)
# ─────────────────────────────────────────────────────────────────────────────

def plot_pib_decomposition(history: list[TurnSnapshot]) -> go.Figure:
    """
    Rinde un gráfico de barras apiladas relativas con los componentes del PIB:
    Y = C + I + G + NX, con la línea de Y_pot superpuesta.
    """
    fig = go.Figure()

    t_vec = [snap["t"] for snap in history]
    C_vec = [snap["C"] for snap in history]
    I_vec = [snap["I_inv"] for snap in history]
    G_vec = [snap["G"] for snap in history]
    NX_vec = [snap["NX"] for snap in history]
    Y_pot_vec = [snap["Y"] / max(1e-3, 1.0 + snap["gap"]) for snap in history]

    # Barras apiladas (barmode="relative" gestiona NX negativo por debajo del cero)
    fig.add_trace(go.Bar(
        x=t_vec, y=C_vec, name="Consumo (C)",
        marker_color="#3b82f6", opacity=0.85,
        hovertemplate="Consumo (C): %{y:.1f} MM<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=t_vec, y=I_vec, name="Inversión Privada (I)",
        marker_color="#10b981", opacity=0.85,
        hovertemplate="Inversión (I): %{y:.1f} MM<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=t_vec, y=G_vec, name="Gasto Público (G)",
        marker_color="#8b5cf6", opacity=0.85,
        hovertemplate="Gasto (G): %{y:.1f} MM<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=t_vec, y=NX_vec, name="Exportaciones Netas (NX)",
        marker_color="#ef4444", opacity=0.85,
        hovertemplate="Exportaciones Netas (NX): %{y:.1f} MM<extra></extra>"
    ))

    # Línea del PIB Potencial
    fig.add_trace(go.Scatter(
        x=t_vec, y=Y_pot_vec, name="PIB Potencial (Y_pot)",
        mode="lines+markers",
        line=dict(color="#f59e0b", width=2.5, dash="dash"),
        marker=dict(symbol="circle", size=6),
        hovertemplate="PIB Potencial: %{y:.1f} MM<extra></extra>"
    ))

    fig.update_layout(
        title="Descomposición del PIB y Capacidad Productiva (Crowding-out)",
        xaxis=dict(title="Turno (Período)", tickmode="linear", dtick=1),
        yaxis=dict(title="Valor en MM de USD", showgrid=True, gridcolor="#1e293b"),
        barmode="relative",
        template="plotly_dark",
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        legend=dict(orientation="h", y=-0.22, x=0),
        margin=dict(l=40, r=20, t=50, b=80),
    )

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 2: RELOJ DEL CICLO ECONÓMICO (U INTERVERTIDA VS PI)
# ─────────────────────────────────────────────────────────────────────────────

def plot_economic_cycle(history: list[TurnSnapshot]) -> go.Figure:
    """
    Rinde el Reloj del Ciclo Económico.
    Mapea Desempleo U en el eje X (escala invertida: derecha = menos desempleo)
    e Inflación pi en el eje Y. Dibuja los cuadrantes característicos.
    """
    fig = go.Figure()

    u_pct = [snap["U"] * 100 for snap in history]
    pi_pct = [snap["pi"] * 100 for snap in history]
    t_labels = [f"t={snap['t']}" for snap in history]

    # Punto del turno actual es más grande
    marker_sizes = [7 if i < len(history) - 1 else 13 for i in range(len(history))]
    marker_colors = ["#64748b" if i < len(history) - 1 else "#f59e0b" for i in range(len(history))]

    # Trayectoria de puntos conectados
    fig.add_trace(go.Scatter(
        x=u_pct, y=pi_pct,
        mode="lines+markers+text",
        text=t_labels,
        textposition="top right",
        name="Trayectoria del Ciclo",
        marker=dict(size=marker_sizes, color=marker_colors, line=dict(color="#000", width=1)),
        line=dict(color="#818cf8", width=2),
        hovertemplate="Turno %{text}<br>Desempleo (U): %{x:.2f}%<br>Inflación (π): %{y:.2f}%<extra></extra>"
    ))

    # Umbrales objetivos sugeridos (para dividir cuadrantes)
    pi_obj = 3.0  # 3% inflación objetivo
    U_n = history[0]["policy_applied"].get("U_n", 0.05) * 100 if history else 5.0  # 5% NAIRU de referencia

    # Dibujar líneas divisorias de cuadrantes
    fig.add_hline(y=pi_obj, line_dash="dash", line_color="#475569", line_width=1.5)
    fig.add_vline(x=U_n, line_dash="dash", line_color="#475569", line_width=1.5)

    # Invertir eje X (derecha = menos desempleo / pleno empleo)
    fig.update_xaxes(autorange="reversed")

    # Inyectar nombres de los cuadrantes
    # Estanflación (Arriba-Izq: Alto desempleo, Alta inflación)
    fig.add_annotation(x=U_n + 4.0, y=pi_obj + 8.0, text="<b>ESTANFLACIÓN</b><br>Alta Inflación / Recesión", showarrow=False, font=dict(size=9, color="#ef4444"), bgcolor="rgba(69,10,10,0.5)", bordercolor="#ef4444", borderpad=4)
    # Recalentamiento (Arriba-Der: Bajo desempleo, Alta inflación)
    fig.add_annotation(x=U_n - 2.5, y=pi_obj + 8.0, text="<b>RECALENTAMIENTO</b><br>Boom de demanda / Inflación", showarrow=False, font=dict(size=9, color="#f59e0b"), bgcolor="rgba(120,53,4,0.5)", bordercolor="#f59e0b", borderpad=4)
    # Recesión (Abajo-Izq: Alto desempleo, Baja inflación)
    fig.add_annotation(x=U_n + 4.0, y=pi_obj - 2.0, text="<b>RECESIÓN</b><br>Desempleo / Deflación", showarrow=False, font=dict(size=9, color="#3b82f6"), bgcolor="rgba(17,24,39,0.7)", bordercolor="#3b82f6", borderpad=4)
    # Zona Ideal (Abajo-Der: Bajo desempleo, Baja inflación)
    fig.add_annotation(x=U_n - 2.5, y=pi_obj - 2.0, text="<b>ZONA IDEAL</b><br>Pleno Empleo / Estabilidad", showarrow=False, font=dict(size=9, color="#10b981"), bgcolor="rgba(2,44,34,0.6)", bordercolor="#10b981", borderpad=4)

    fig.update_layout(
        title="Reloj del Ciclo Económico (Fase de Actividad)",
        xaxis=dict(title="Tasa de Desempleo (U) - Escala Invertida [%]", showgrid=True, gridcolor="#1e293b"),
        yaxis=dict(title="Tasa de Inflación (π) [%]", showgrid=True, gridcolor="#1e293b"),
        template="plotly_dark",
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        margin=dict(l=40, r=20, t=50, b=80),
        showlegend=False
    )

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 3: TERMÓMETRO DE RESERVAS (GAUGE SEMAFÓRICO)
# ─────────────────────────────────────────────────────────────────────────────

def plot_reserves_thermometer(R_curr: float, R_0: float) -> go.Figure:
    """
    Rinde un gráfico tipo Gauge interactivo para monitorizar las reservas internacionales.
    """
    # Color semafórico según umbrales de reserves
    if R_curr < R_0 * 0.30:
        color_semaforo = "#ef4444"  # Rojo crítico
    elif R_curr < R_0 * 0.70:
        color_semaforo = "#f59e0b"  # Amarillo de alerta
    else:
        color_semaforo = "#10b981"  # Verde seguro

    max_range = max(R_0 * 1.5, R_curr * 1.1)

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=R_curr,
        delta={'reference': R_0, 'relative': False, 'valueformat': '.1f', 'increasing': {'color': "#10b981"}, 'decreasing': {'color': "#ef4444"}},
        number={'suffix': " MM", 'font': {'size': 24, 'color': '#f8fafc'}},
        gauge={
            'axis': {'range': [0, max_range], 'tickcolor': '#94a3b8'},
            'bar': {'color': color_semaforo},
            'bgcolor': "#1e293b",
            'borderwidth': 1,
            'bordercolor': "#334155",
            'steps': [
                {'range': [0, R_0 * 0.3], 'color': "rgba(239, 68, 68, 0.25)"},
                {'range': [R_0 * 0.3, R_0 * 0.7], 'color': "rgba(245, 158, 11, 0.25)"},
                {'range': [R_0 * 0.7, max_range], 'color': "rgba(16, 185, 129, 0.25)"}
            ],
            'threshold': {
                'line': {'color': "#ef4444", 'width': 3},
                'thickness': 0.75,
                'value': R_0 * 0.3
            }
        }
    ))

    fig.update_layout(
        title={'text': "Termómetro de Reservas Internacionales", 'x': 0.5, 'xanchor': 'center'},
        height=220,
        margin=dict(l=30, r=30, t=60, b=30),
        template="plotly_dark",
        paper_bgcolor="#111827",
    )

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 4: GAUGE BOLA DE NIEVE DE LA DEUDA
# ─────────────────────────────────────────────────────────────────────────────

def plot_debt_snowball(history: list[TurnSnapshot]) -> go.Figure:
    """
    Rinde un gráfico tipo Gauge para el ratio del servicio de la deuda:
    ratio = (intereses_deuda / (gasto_público + intereses_deuda)) * 100%
    """
    current_snap = history[-1]
    
    # Extraer variables
    r = current_snap["r"]
    B = current_snap["B"]
    G = current_snap["G"]

    # Calcular carga de intereses y ratio de servicio
    interest_payments = (r / 100.0) * B
    total_spending = G + interest_payments
    
    # Evitar divisiones por cero
    ratio = (interest_payments / max(total_spending, 1e-6)) * 100.0

    # Lógica de color semafórico de deuda service
    if ratio > 30.0:
        color = "#ef4444"  # Rojo
    elif ratio > 15.0:
        color = "#f59e0b"  # Amarillo
    else:
        color = "#10b981"  # Verde

    # Verificar si "Bola de Nieve" se activó (incremento de >3 puntos en este turno)
    snowball_triggered = False
    if len(history) >= 2:
        prev = history[-2]
        prev_interest = (prev["r"] / 100.0) * prev["B"]
        prev_total = prev["G"] + prev_interest
        prev_ratio = (prev_interest / max(prev_total, 1e-6)) * 100.0
        
        if ratio - prev_ratio >= 3.0:
            snowball_triggered = True

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=ratio,
        number={'suffix': "%", 'font': {'size': 24, 'color': '#f8fafc'}, 'valueformat': '.1f'},
        gauge={
            'axis': {'range': [0, 60], 'tickcolor': '#94a3b8'},
            'bar': {'color': color},
            'bgcolor': "#1e293b",
            'borderwidth': 1,
            'bordercolor': "#334155",
            'steps': [
                {'range': [0, 15], 'color': "rgba(16, 185, 129, 0.25)"},
                {'range': [15, 30], 'color': "rgba(245, 158, 11, 0.25)"},
                {'range': [30, 60], 'color': "rgba(239, 68, 68, 0.25)"}
            ]
        }
    ))

    # Anotar Bola de Nieve en caso de dispararse
    if snowball_triggered:
        fig.add_annotation(
            text="🚨 BOLA DE NIEVE ACTIVADA: Carga de intereses creciendo descontroladamente",
            xref="paper", yref="paper",
            x=0.5, y=-0.1,
            showarrow=False,
            font=dict(size=9, color="#fca5a5"),
            bgcolor="rgba(69, 10, 10, 0.8)",
            bordercolor="#ef4444",
            borderpad=4
        )
    elif ratio > 30.0:
        fig.add_annotation(
            text="⚠️ ALTA CARGA FISCAL: Servicio de la deuda insostenible",
            xref="paper", yref="paper",
            x=0.5, y=-0.1,
            showarrow=False,
            font=dict(size=9, color="#fde047"),
            bgcolor="rgba(120, 53, 4, 0.8)",
            bordercolor="#f59e0b",
            borderpad=4
        )

    fig.update_layout(
        title={'text': "Servicio de la Deuda (% del Gasto Total)", 'x': 0.5, 'xanchor': 'center'},
        height=220,
        margin=dict(l=30, r=30, t=60, b=30),
        template="plotly_dark",
        paper_bgcolor="#111827",
    )

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART 5: IS-LM-BP DINÁMICO COMPLETO V2.0
# ─────────────────────────────────────────────────────────────────────────────

def plot_islm_bp_dynamic(mgr: any, sel_t: int, overlay_prev: bool = False) -> go.Figure:
    """
    Rinde las curvas macroeconómicas dinámicas IS-LM-BP del período seleccionado (sel_t).
    Hereda el concepto V1 e incorpora las mejoras teóricas V2.0:
      - Impuesto proporcional.
      - BP con pendiente positiva por movilidad imperfecta (f < 100).
      - Mínimos locales e históricos de referencia.
      - Superpone las curvas de t-1 (overlay_prev) si corresponde.
    """
    history = mgr.state["history"]
    snap = history[sel_t]
    
    # Extraer parámetros aplicados en el turno de equilibrio
    policy = snap["policy_applied"]
    structural = dict(mgr.state["structural"])  # fallback estructural
    
    # Cargar valores históricos del snapshot
    Y_eq = snap["Y"]
    r_eq = snap["r"]
    E_curr = snap["E"]
    M_curr = snap["M"]
    G_curr = snap["G"]
    P_local = snap["P_local"]
    
    # Recuperar PIB Potencial
    Y_pot = snap["Y"] / max(1e-3, 1.0 + snap["gap"])

    # Vectores para trazar curvas (PIB de 20 a 180)
    Y_arr = np.linspace(20.0, 180.0, 150).tolist()
    
    # Multiplicador
    c1 = structural.get("c1", 0.75)
    t = structural.get("t", 0.20)
    m1 = structural.get("m1", 0.15)
    b = structural.get("b", 2.0)
    k = structural.get("k", 0.50)
    h = structural.get("h", 2.0)
    f = structural.get("f", 5.0)
    epsilon_x = structural.get("epsilon_x", 0.80)
    
    q = snap["q_real"]
    
    # Demanda autónoma: A = c0 + I0 + G + NX0
    c0 = structural.get("c0", 10.0)
    I0 = structural.get("I0", 15.0)
    NX0 = structural.get("NX0", 5.0)
    A = c0 + I0 + G_curr + NX0

    # 1. CURVAS DEL PERÍODO ACTUAL (sel_t)
    # IS: r_IS = (A + eps_x * q - Y * slope) / b
    r_IS = [is_curve_v2(y, c1, t, m1, b, A, epsilon_x, q) for y in Y_arr]
    
    # LM: r_LM = (k * Y - M_real) / h
    M_real = M_curr / P_local
    r_LM = [lm_curve_v2(y, k, M_real, h) for y in Y_arr]
    
    # BP: r_BP = r_star + delta_E_e - (NX0 + eps_eff * q - m1 * Y) / f
    r_star = policy.get("r_star", 5.0)
    delta_E_expected = mgr.state.get("delta_E_expected", 0.0) if sel_t == mgr.t else 0.0
    
    # Resolver la pendiente de la BP según movilidad de capitales
    r_BP = []
    for y in Y_arr:
        # Calcular NX provisional en ese ingreso y
        NX_y = compute_NX(NX0, epsilon_x, structural.get("epsilon_m", 0.7), q, m1, y, snap.get("j_curve_active", False))
        r_bp_y = r_star + delta_E_expected - (NX_y / f)
        r_BP.append(r_bp_y)

    # 2. RENDERIZACIÓN DEL GRÁFICO
    fig = go.Figure()

    # Curvas Actuales (Líneas sólidas de colores vivos)
    fig.add_trace(go.Scatter(
        x=Y_arr, y=r_IS, mode="lines", name=f"Curva IS (t={sel_t})",
        line=dict(color="#3b82f6", width=2.5),
        hovertemplate="PIB: %{x:.1f} MM<br>Tasa IS: %{y:.2f}%<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=Y_arr, y=r_LM, mode="lines", name=f"Curva LM (t={sel_t})",
        line=dict(color="#10b981", width=2.5),
        hovertemplate="PIB: %{x:.1f} MM<br>Tasa LM: %{y:.2f}%<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=Y_arr, y=r_BP, mode="lines", name=f"Curva BP (t={sel_t})",
        line=dict(color="#f59e0b", width=2.5),
        hovertemplate="PIB: %{x:.1f} MM<br>Tasa BP: %{y:.2f}%<extra></extra>"
    ))

    # 3. OVERLAY DE CURVAS DEL TURNO ANTERIOR (t-1)
    if overlay_prev and sel_t >= 1:
        prev_snap = history[sel_t - 1]
        prev_policy = prev_snap["policy_applied"]
        
        prev_Y_pot = prev_snap["Y"] / max(1e-3, 1.0 + prev_snap["gap"])
        prev_P_local = prev_snap["P_local"]
        prev_q = prev_snap["q_real"]
        
        prev_A = c0 + I0 + prev_snap["G"] + NX0
        
        # Calcular prev_IS, prev_LM, prev_BP
        r_IS_prev = [is_curve_v2(y, c1, t, m1, b, prev_A, epsilon_x, prev_q) for y in Y_arr]
        
        prev_M_real = prev_snap["M"] / prev_P_local
        r_LM_prev = [lm_curve_v2(y, k, prev_M_real, h) for y in Y_arr]
        
        prev_r_star = prev_policy.get("r_star", 5.0)
        
        r_BP_prev = []
        for y in Y_arr:
            prev_NX_y = compute_NX(NX0, epsilon_x, structural.get("epsilon_m", 0.7), prev_q, m1, y, prev_snap.get("j_curve_active", False))
            r_bp_y = prev_r_star - (prev_NX_y / f)
            r_BP_prev.append(r_bp_y)

        # Añadir al gráfico en colores tenues punteados
        fig.add_trace(go.Scatter(
            x=Y_arr, y=r_IS_prev, mode="lines", name=f"IS (t={sel_t-1})",
            line=dict(color="rgba(59, 130, 246, 0.4)", width=1.5, dash="dash"),
            hoverinfo="skip"
        ))
        fig.add_trace(go.Scatter(
            x=Y_arr, y=r_LM_prev, mode="lines", name=f"LM (t={sel_t-1})",
            line=dict(color="rgba(16, 185, 129, 0.4)", width=1.5, dash="dash"),
            hoverinfo="skip"
        ))
        fig.add_trace(go.Scatter(
            x=Y_arr, y=r_BP_prev, mode="lines", name=f"BP (t={sel_t-1})",
            line=dict(color="rgba(245, 158, 11, 0.4)", width=1.5, dash="dash"),
            hoverinfo="skip"
        ))
        
        # Punto de equilibrio anterior
        fig.add_trace(go.Scatter(
            x=[prev_snap["Y"]], y=[prev_snap["r"]], mode="markers",
            name=f"Eq. Anterior (t={sel_t-1})",
            marker=dict(color="rgba(156, 163, 175, 0.7)", size=9, symbol="circle-open"),
            hovertemplate="PIB Anterior: %{x:.2f} MM<br>Tasa Anterior: %{y:.2f}%<extra></extra>"
        ))

    # Línea vertical del PIB Potencial
    fig.add_vline(
        x=Y_pot, line_dash="dash", line_color="#4b5563", line_width=1.5,
        annotation_text="PIB Potencial (Y_pot)", annotation_position="top left"
    )

    # Punto de equilibrio actual (Marcador en estrella brillante)
    fig.add_trace(go.Scatter(
        x=[Y_eq], y=[r_eq], mode="markers", name=f"Equilibrio Actual (t={sel_t})",
        marker=dict(color="#f43f5e", size=13, symbol="star", line=dict(color="#fff", width=1.5)),
        hovertemplate="<b>Punto de Equilibrio</b><br>PIB (Y): %{x:.2f} MM<br>Tasa de Interés (r): %{y:.2f}%<extra></extra>"
    ))

    # Limitar rango de visualización de tasas de interés de 0% a 25% para evitar que vuele la escala
    max_rate_y = max(15.0, r_eq * 1.5, max(r_BP) * 1.1)
    max_rate_y = min(30.0, max_rate_y)

    fig.update_layout(
        title=f"Diagrama de Equilibrio General IS-LM-BP (Semestre {sel_t})",
        xaxis=dict(title="Producción / PIB Real (Y) [MM USD]", range=[10.0, 190.0], showgrid=True, gridcolor="#1e293b"),
        yaxis=dict(title="Tasa de Interés Interna (r) [%]", range=[-1.0, max_rate_y], showgrid=True, gridcolor="#1e293b"),
        template="plotly_dark",
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        legend=dict(orientation="h", y=-0.22, x=0),
        margin=dict(l=50, r=20, t=55, b=80),
        hovermode="closest"
    )

    return fig
