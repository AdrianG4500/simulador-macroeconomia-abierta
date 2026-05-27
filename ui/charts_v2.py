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

def plot_debt_snowball(history: list[dict], current_state: dict = None) -> go.Figure:
    """
    Trayectoria intertemporal del Ratio Deuda Soberana / PIB Potencial (B / Y_pot).
    Muestra la evolución turno a turno e indica la zona crítica de default al 120%.

    Args:
        history       : Lista de snapshots históricos.
        current_state : Snapshot adicional opcional (para compatibilidad futura).
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS

    t_vec: list[int] = []
    ratio_vec: list[float] = []

    for snap in history:
        t_val = snap.get("t", 0)
        B = snap.get("B", 50.0)
        Y = snap.get("Y", 100.0)
        gap = snap.get("gap", 0.0)
        Y_pot = Y / max(1e-3, 1.0 + gap)
        ratio = B / max(1.0, Y_pot)
        t_vec.append(t_val)
        ratio_vec.append(ratio)

    fig = go.Figure()

    # ── Umbral crítico de default (120%) ─────────────────────────────────────
    if t_vec:
        t_min, t_max = min(t_vec), max(t_vec)
        fig.add_shape(
            type="line",
            x0=t_min, x1=t_max,
            y0=1.20, y1=1.20,
            line=dict(color="#EF4444", width=2, dash="dash"),
        )
        fig.add_annotation(
            x=t_max, y=1.22,
            text="⚠️ Umbral de Default Soberano (120% PIB)",
            showarrow=False, xanchor="right",
            font=dict(size=9, color="#EF4444"),
            bgcolor="rgba(239,68,68,0.10)",
            bordercolor="#EF4444", borderpad=3
        )

    # ── Línea de trayectoria de deuda ─────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=t_vec, y=ratio_vec,
        mode="lines+markers",
        name="Ratio Deuda / PIB Potencial",
        line=dict(color=colors["G"], width=2.5),
        marker=dict(size=7, color=colors["G"], line=dict(color="#FFF", width=1)),
        fill="tozeroy",
        fillcolor="rgba(122, 90, 248, 0.08)" if theme == "strategy" else "rgba(122, 90, 248, 0.06)",
        hovertemplate="Turno %{x}<br>Deuda/PIB: %{y:.1%}<extra></extra>"
    ))

    max_y = max(1.5, (max(ratio_vec) * 1.25 if ratio_vec else 1.5))

    fig.update_layout(
        title="Trayectoria de la Deuda Soberana (B / Y_pot)",
        xaxis=dict(title="Turno (Semestre)", tickmode="linear", dtick=1, showgrid=True),
        yaxis=dict(
            title="Ratio Deuda / PIB Potencial",
            tickformat=".0%",
            showgrid=True,
            range=[0, max_y]
        ),
        legend=dict(orientation="h", y=-0.22, x=0),
        margin=dict(l=55, r=25, t=55, b=80),
    )

    apply_chart_theme(fig, theme)
    return fig

def plot_islm_bp_dynamic(current_state: dict, params: dict) -> go.Figure:
    """
    Diagrama IS-LM-BP estático e ilustrativo del equilibrio del turno actual.
    Las 3 curvas son líneas rectas que se intersectan en (Y_eq, r_eq).
    Las pendientes se derivan de los parámetros estructurales en `params`.

    Args:
        current_state : Snapshot del turno actual (dict con 'Y', 'r', etc.).
        params        : Parámetros estructurales (dict con 'b', 'h', 'k', etc.).
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS

    # ── Punto de equilibrio ──────────────────────────────────────────────────
    Y_eq = float(current_state.get("Y", 100.0))
    r_eq = float(current_state.get("r", 5.0))
    policy = current_state.get("policy_applied", {})
    k_c = float(policy.get("k_c", 0.0))

    # ── Rango del eje X centrado en Y_eq ────────────────────────────────────
    span = max(20.0, Y_eq * 0.22)
    Y_arr = np.linspace(max(1.0, Y_eq - span), Y_eq + span, 130)

    # ── Pendientes derivadas de parámetros estructurales ─────────────────────
    b = float(params.get("b", 2.0))    # Sensibilidad inversión a r
    h = float(params.get("h", 2.0))    # Sensibilidad demanda de dinero a r
    k = float(params.get("k", 0.50))   # Sensibilidad demanda de dinero a Y
    m1 = float(params.get("m1", 0.15)) # Propensión marginal a importar
    c1 = float(params.get("c1", 0.75)) # Propensión marginal a consumir
    t_tax = float(params.get("t", 0.20))

    # IS: dr/dY = -(1 - c1*(1-t) + m1) / b  → negativa
    slope_IS_raw = -(1.0 - c1 * (1.0 - t_tax) + m1) / max(b, 1e-6)
    # Escalar para visualización (la magnitud real sería muy grande en las unidades del juego)
    scale = max(1.0, Y_eq / 100.0)
    slope_IS = max(-0.35, min(-0.04, slope_IS_raw / scale))

    # LM: dr/dY = k / h → positiva
    slope_LM_raw = k / max(h, 1e-6)
    slope_LM = max(0.03, min(0.30, slope_LM_raw * 0.10 / scale))

    # BP: positiva. Más plana si k_c bajo (alta movilidad), más empinada si k_c alto.
    #    k_c = 0 (libre movilidad): BP casi horizontal (pendiente ≈ 0.01)
    #    k_c = 1 (control total):   BP empinada (pendiente ≈ 0.18)
    slope_BP = 0.01 + k_c * 0.17

    r_IS = [max(0.0, r_eq + slope_IS * (y - Y_eq)) for y in Y_arr]
    r_LM = [r_eq + slope_LM * (y - Y_eq) for y in Y_arr]
    r_BP = [r_eq + slope_BP * (y - Y_eq) for y in Y_arr]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=list(Y_arr), y=r_IS, mode="lines", name="Curva IS (Bien-Servicios)",
        line=dict(color=colors["C"], width=2.5),
        hovertemplate="PIB: %{x:.1f} MM<br>Tasa IS: %{y:.2f}%<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=list(Y_arr), y=r_LM, mode="lines", name="Curva LM (Dinero)",
        line=dict(color=colors["I"], width=2.5),
        hovertemplate="PIB: %{x:.1f} MM<br>Tasa LM: %{y:.2f}%<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=list(Y_arr), y=r_BP, mode="lines", name="Curva BP (Balanza de Pagos)",
        line=dict(color=colors["NX"], width=2.5, dash="dash"),
        hovertemplate="PIB: %{x:.1f} MM<br>Tasa BP: %{y:.2f}%<extra></extra>"
    ))

    # Marcador de equilibrio
    fig.add_trace(go.Scatter(
        x=[Y_eq], y=[r_eq], mode="markers", name="Equilibrio (Y*, r*)",
        marker=dict(
            color=colors["Y_pot"], size=14, symbol="star",
            line=dict(color="#FFFFFF", width=1.5)
        ),
        hovertemplate="<b>Punto de Equilibrio</b><br>Y*: %{x:.2f} MM<br>r*: %{y:.2f}%<extra></extra>"
    ))

    # Líneas de referencia cruzadas
    fig.add_vline(x=Y_eq, line_dash="dot", line_color="#6B7280", line_width=1.0,
                  annotation_text=f"Y*={Y_eq:.1f}", annotation_position="top left",
                  annotation_font_size=9)
    fig.add_hline(y=r_eq, line_dash="dot", line_color="#6B7280", line_width=1.0,
                  annotation_text=f"r*={r_eq:.1f}%", annotation_position="top right",
                  annotation_font_size=9)

    max_r = max(r_eq * 2.5, 12.0)
    fig.update_layout(
        title="Diagrama de Equilibrio General IS-LM-BP",
        xaxis=dict(
            title="Producción / PIB Real (Y) [MM USD]",
            showgrid=True,
        ),
        yaxis=dict(
            title="Tasa de Interés Interna (r) [%]",
            range=[0, max_r],
            showgrid=True
        ),
        legend=dict(orientation="h", y=-0.22, x=0),
        margin=dict(l=50, r=20, t=55, b=80),
        hovermode="closest"
    )

    apply_chart_theme(fig, theme)
    return fig


# =============================================================================
# BLOQUE 4: GESTIÓN DE TEMAS DINÁMICOS Y COLORES SALTER-SWAN / SECTOR EXTERNO
# =============================================================================


# Paletas de colores curadas y contrastadas para los dos modos de juego
EXECUTIVE_COLORS = {
    "C": "#1570EF",             # Consumo (Azul Bloomberg)
    "I": "#10B981",             # Inversión (Esmeralda)
    "G": "#7A5AF8",             # Gasto (Púrpura)
    "NX": "#F79009",            # Net Exports (Naranja)
    "Y_pot": "#D92D20",         # PIB Potencial (Rojo Crisis)
    "T_recaudacion": "#12B76A", # Recaudación (Verde)
    "X": "#12B76A",             # Exportaciones (Verde)
    "M": "#F04438",             # Importaciones (Rojo)
    "E": "#1570EF",             # Tipo de cambio (Azul)
    "E_band": "#98A2B3",        # Banda superior (Gris)
    "intervention": "#D92D20",  # Intervención (Rojo)
    "grid": "#E4E7EC",
    "text": "#101828"
}

STRATEGY_COLORS = {
    "C": "#38BDF8",             # Consumo (Celeste Cyber)
    "I": "#34D399",             # Inversión (Verde Neón)
    "G": "#A78BFA",             # Gasto (Violeta Geopolítico)
    "NX": "#FB923C",            # Net Exports (Naranja)
    "Y_pot": "#F43F5E",         # PIB Potencial (Rosa Caliente)
    "T_recaudacion": "#34D399", # Recaudación (Verde Neón)
    "X": "#34D399",             # Exportaciones (Verde Neón)
    "M": "#F43F5E",             # Importaciones (Rosa)
    "E": "#38BDF8",             # Tipo de cambio (Celeste)
    "E_band": "#475569",        # Banda superior (Gris metálico)
    "intervention": "#DC2626",  # Intervención (Rojo Alerta)
    "grid": "#364152",
    "text": "#CBD5E1"
}


def apply_chart_theme(fig: go.Figure, theme: str) -> go.Figure:
    """
    Aplica tipografías, colores de grilla y fondos transparentes a un gráfico
    según el tema seleccionado (executive vs strategy).
    """
    if theme == "strategy":
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family="Manrope, sans-serif",
                color="#F8FAFC"
            ),
            title=dict(
                font=dict(
                    family="Rajdhani, sans-serif",
                    size=16,
                    weight="bold",
                    color="#F8FAFC"
                )
            ),
            xaxis=dict(
                gridcolor="#364152",
                zerolinecolor="#364152",
                tickfont=dict(family="IBM Plex Mono, monospace", size=9)
            ),
            yaxis=dict(
                gridcolor="#364152",
                zerolinecolor="#364152",
                tickfont=dict(family="IBM Plex Mono, monospace", size=9)
            ),
            legend=dict(
                font=dict(size=9),
                bgcolor="rgba(0,0,0,0)"
            )
        )
    else:
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family="Inter, sans-serif",
                color="#101828"
            ),
            title=dict(
                font=dict(
                    family="Space Grotesk, sans-serif",
                    size=16,
                    weight="bold",
                    color="#101828"
                )
            ),
            xaxis=dict(
                gridcolor="#E4E7EC",
                zerolinecolor="#D0D5DD",
                tickfont=dict(family="JetBrains Mono, monospace", size=9)
            ),
            yaxis=dict(
                gridcolor="#E4E7EC",
                zerolinecolor="#D0D5DD",
                tickfont=dict(family="JetBrains Mono, monospace", size=9)
            ),
            legend=dict(
                font=dict(size=9),
                bgcolor="rgba(0,0,0,0)"
            )
        )
    return fig


def get_trade_details(snap: dict, sp: dict) -> tuple[float, float]:
    """
    Calcula Exportaciones (X) e Importaciones (M_imp) brutas para un snapshot
    utilizando la función compute_NX del motor.
    """
    from engine.core_v2 import compute_NX
    
    Y = snap.get("Y", 100.0)
    q = snap.get("q_real", 1.0)
    j_curve_active = snap.get("j_curve_active", False)
    
    policy = snap.get("policy_applied", {})
    tau = policy.get("tau", 0.0)
    s_x = policy.get("s_x", 0.0)
    
    # Parámetros estructurales
    NX0 = sp.get("NX0", 5.0)
    epsilon_x = sp.get("epsilon_x", 0.80)
    epsilon_m = sp.get("epsilon_m", 0.70)
    m1 = sp.get("m1", 0.15)
    
    x0 = sp.get("x0", 0.0)
    x1 = sp.get("x1", 0.0)
    Y_star = sp.get("Y_star", 0.0)
    m0 = sp.get("m0", 0.0)
    
    _, X, M_imp = compute_NX(
        NX0, epsilon_x, epsilon_m, q, m1, Y, j_curve_active,
        x0=x0, x1=x1, Y_star=Y_star, m0=m0, tau=tau, s_x=s_x
    )
    
    return X, M_imp


# =============================================================================
# GRÁFICOS PESTAÑA 1: ECONOMÍA REAL (TAREA 2)
# =============================================================================

def plot_gdp_decomposition(history: list[dict]) -> go.Figure:
    """
    Rinde un gráfico de barras apiladas relativas con los componentes del PIB:
    Y = C + I_inv + G + NX, con la línea de Y_pot superpuesta.
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS
    
    fig = go.Figure()
    
    t_vec = [snap["t"] for snap in history]
    C_vec = [snap["C"] for snap in history]
    I_vec = [snap["I_inv"] for snap in history]
    G_vec = [snap["G"] for snap in history]
    NX_vec = [snap["NX"] for snap in history]
    
    Y_pot_vec = []
    for snap in history:
        gap = snap.get("gap", 0.0)
        Y = snap.get("Y", 100.0)
        Y_pot = Y / max(1e-3, 1.0 + gap)
        Y_pot_vec.append(Y_pot)

    # Añadir trazas de componentes
    fig.add_trace(go.Bar(
        x=t_vec, y=C_vec, name="Consumo Privado (C)",
        marker_color=colors["C"], opacity=0.85,
        hovertemplate="Consumo (C): %{y:.2f} MM USD<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=t_vec, y=I_vec, name="Inversión Privada (I)",
        marker_color=colors["I"], opacity=0.85,
        hovertemplate="Inversión (I): %{y:.2f} MM USD<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=t_vec, y=G_vec, name="Gasto Público (G)",
        marker_color=colors["G"], opacity=0.85,
        hovertemplate="Gasto (G): %{y:.2f} MM USD<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=t_vec, y=NX_vec, name="Exportaciones Netas (NX)",
        marker_color=colors["NX"], opacity=0.85,
        hovertemplate="Exportaciones Netas (NX): %{y:.2f} MM USD<extra></extra>"
    ))
    
    # Línea del PIB Potencial
    fig.add_trace(go.Scatter(
        x=t_vec, y=Y_pot_vec, name="Capacidad Productiva (Y_pot)",
        mode="lines+markers",
        line=dict(color=colors["Y_pot"], width=2.5, dash="dash"),
        marker=dict(symbol="circle", size=7),
        hovertemplate="PIB Potencial: %{y:.2f} MM USD<extra></extra>"
    ))
    
    fig.update_layout(
        title="Descomposición Dinámica del PIB (Evolución de Componentes)",
        xaxis=dict(title="Turno (Semestre)", tickmode="linear", dtick=1),
        yaxis=dict(title="MM USD", showgrid=True),
        barmode="relative",
        legend=dict(orientation="h", y=-0.22, x=0),
        margin=dict(l=40, r=20, t=50, b=80),
    )
    
    apply_chart_theme(fig, theme)
    return fig


def plot_sectoral_composition(history: list[dict]) -> go.Figure:
    """
    Rinde un gráfico de barras apiladas al 100% para mostrar la evolución
    de la Enfermedad Holandesa (composición de sectores Transable YT vs No-Transable YNT).
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS
    
    fig = go.Figure()
    
    t_vec = [snap["t"] for snap in history]
    
    YT_shares = []
    YNT_shares = []
    for snap in history:
        YT = snap.get("Y_T", 50.0)
        YNT = snap.get("Y_NT", 50.0)
        total = max(1e-3, YT + YNT)
        YT_shares.append((YT / total) * 100.0)
        YNT_shares.append((YNT / total) * 100.0)
        
    fig.add_trace(go.Bar(
        x=t_vec, y=YT_shares, name="Sector Industrial Transable (Y_T)",
        marker_color=colors["I"], opacity=0.85,
        hovertemplate="Sector Transable: %{y:.1f}% del PIB<extra></extra>"
    ))
    
    fig.add_trace(go.Bar(
        x=t_vec, y=YNT_shares, name="Sector Servicios No-Transable (Y_NT)",
        marker_color=colors["C"], opacity=0.85,
        hovertemplate="Sector No-Transable: %{y:.1f}% del PIB<extra></extra>"
    ))
    
    fig.update_layout(
        title="Composición Productiva (Enfermedad Holandesa)",
        xaxis=dict(title="Turno (Semestre)", tickmode="linear", dtick=1),
        yaxis=dict(title="Participación de Sector (%)", range=[0, 100], showgrid=True),
        barmode="stack",
        legend=dict(orientation="h", y=-0.22, x=0),
        margin=dict(l=40, r=20, t=50, b=80),
    )
    
    apply_chart_theme(fig, theme)
    return fig


def plot_fiscal_odometer(current_state: dict) -> go.Figure:
    """
    Rinde un gráfico tipo Waterfall (Cascada) del Balance Fiscal en el último turno.
    Muestra: Recaudación (+) vs Gastos (-) e Intereses (-).
    El saldo final es el Déficit (negativo) o Superávit (positivo).
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS
    
    fig = go.Figure()
    
    recaudacion = current_state.get("recaudacion", 0.0)
    deficit = current_state.get("deficit", 0.0)
    
    # Extraer gastos del policy_applied
    policy = current_state.get("policy_applied", {})
    G_c = policy.get("G_c", 15.0)
    I_g = policy.get("I_g", 5.0)
    Tr = policy.get("Tr", 0.0)
    
    gasto_total = G_c + I_g + Tr
    
    # intereses = deficit + recaudacion - gasto_total
    intereses = max(0.0, deficit + recaudacion - gasto_total)
    
    x_labels = [
        "Recaudación (+) ", 
        "Gasto Corriente (-)", 
        "Inversión Pública (-)", 
        "Transferencias (-)", 
        "Intereses Deuda (-)", 
        "Balance Fiscal"
    ]
    
    y_values = [
        recaudacion, 
        -G_c, 
        -I_g, 
        -Tr, 
        -intereses, 
        0.0  # El total es autocalculado por Plotly
    ]
    
    # Determinar colores del waterfall
    decreasing_color = colors["M"]  
    increasing_color = colors["T_recaudacion"]  
    totals_color = colors["E"]  
    
    fig.add_trace(go.Waterfall(
        name="Balance Fiscal",
        orientation="v",
        measure=["relative", "relative", "relative", "relative", "relative", "total"],
        x=x_labels,
        textposition="outside",
        y=y_values,
        connector=dict(line=dict(color=colors["grid"], width=1, dash="dot")),
        decreasing=dict(marker=dict(color=decreasing_color)),
        increasing=dict(marker=dict(color=increasing_color)),
        totals=dict(marker=dict(color=totals_color)),
        hovertemplate="%{x}: %{y:.2f} MM USD<extra></extra>"
    ))
    
    fig.update_layout(
        title="Odómetro Fiscal y Balance de Presupuesto",
        showlegend=False,
        margin=dict(l=40, r=20, t=50, b=80),
        yaxis=dict(title="MM USD", showgrid=True)
    )
    
    apply_chart_theme(fig, theme)
    return fig


# =============================================================================
# GRÁFICOS PESTAÑA 2: SECTOR EXTERNO (TAREA 3)
# =============================================================================

def plot_butterfly_trade(history: list[dict]) -> go.Figure:
    """
    Rinde un gráfico de barras horizontales divergente (Tornado/Mariposa) de comercio exterior:
    Exportaciones (X, verdes, derecha) vs Importaciones (M, rojas, izquierda).
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS
    
    mgr = st.session_state.get("mgr")
    sp = mgr.state.get("structural", {}) if (mgr is not None and mgr.state is not None) else {}
    
    t_vec = [f"Turno {snap['t']}" for snap in history]
    
    X_vec = []
    M_vec = []
    
    for snap in history:
        X, M_imp = get_trade_details(snap, sp)
        X_vec.append(X)
        M_vec.append(-M_imp) # Negativo para ir a la izquierda
        
    fig = go.Figure()
    
    # Añadir Importaciones (Izquierda)
    fig.add_trace(go.Bar(
        y=t_vec,
        x=M_vec,
        name="Importaciones Brutas (M_imp)",
        orientation="h",
        marker_color=colors["M"],
        customdata=[-v for v in M_vec],
        hovertemplate="Importaciones: %{customdata:.2f} MM USD<extra></extra>"
    ))
    
    # Añadir Exportaciones (Derecha)
    fig.add_trace(go.Bar(
        y=t_vec,
        x=X_vec,
        name="Exportaciones Brutas (X)",
        orientation="h",
        marker_color=colors["X"],
        hovertemplate="Exportaciones: %{x:.2f} MM USD<extra></extra>"
    ))
    
    fig.update_layout(
        title="Balanza en Mariposa (Comercio Bruto Bilateral)",
        barmode="relative",
        xaxis=dict(title="MM USD (<- Importaciones | Exportaciones ->)", showgrid=True),
        yaxis=dict(title="Período", showgrid=False),
        legend=dict(orientation="h", y=-0.22, x=0),
        margin=dict(l=70, r=20, t=50, b=80),
    )
    
    apply_chart_theme(fig, theme)
    return fig


def plot_exchange_intervention(history: list[dict]) -> go.Figure:
    """
    Rinde un gráfico combinado (Línea + Barras) de Intervención Cambiaria:
    - Línea 1: Tipo de Cambio Nominal (E)
    - Línea 2 (punteada): Banda Superior Cambiaria (E_band_upper)
    - Barras rojas (Eje Y secundario): Intervención del BC (FX_intervention)
    """
    from plotly.subplots import make_subplots
    
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS
    
    t_vec = [snap["t"] for snap in history]
    E_vec = [snap["E"] for snap in history]
    
    E_band_vec = []
    intervention_vec = []
    
    for snap in history:
        policy = snap.get("policy_applied", {})
        band = policy.get("E_band_upper")
        if band is None:
            # Fallback a un techo del 10%
            band = snap["E"] * 1.10
        E_band_vec.append(band)
        
        intervention_vec.append(snap.get("FX_intervention", 0.0))
        
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Línea E
    fig.add_trace(go.Scatter(
        x=t_vec, y=E_vec,
        name="Tipo de Cambio (E)",
        mode="lines+markers",
        line=dict(color=colors["E"], width=2.5),
        marker=dict(size=6),
        hovertemplate="Tipo de Cambio E: %{y:.2f}<extra></extra>"
    ), secondary_y=False)
    
    # Techo de flotación sucia
    fig.add_trace(go.Scatter(
        x=t_vec, y=E_band_vec,
        name="Techo Cambiario (Banda)",
        mode="lines",
        line=dict(color=colors["E_band"], width=1.5, dash="dash"),
        hovertemplate="Techo Cambiario: %{y:.2f}<extra></extra>"
    ), secondary_y=False)
    
    # Intervención (FX_intervention)
    fig.add_trace(go.Bar(
        x=t_vec, y=intervention_vec,
        name="Venta de Reservas (BC)",
        marker_color=colors["intervention"],
        opacity=0.4,
        hovertemplate="FX Intervención: %{y:.2f} MM USD<extra></extra>"
    ), secondary_y=True)
    
    fig.update_layout(
        title="Banda Cambiaria e Intervención del Banco Central (Flotación Sucia)",
        xaxis=dict(title="Turno (Semestre)", tickmode="linear", dtick=1),
        margin=dict(l=40, r=40, t=50, b=80),
        legend=dict(orientation="h", y=-0.22, x=0),
    )
    
    fig.update_yaxes(title_text="Tipo de Cambio Nominal (E)", secondary_y=False)
    fig.update_yaxes(title_text="Quema de Reservas [MM USD]", secondary_y=True, showgrid=False)
    
    apply_chart_theme(fig, theme)
    fig.data[2].opacity = 0.4
    
    return fig


def plot_salter_swan(current_state: dict, params: dict) -> go.Figure:
    """
    Rinde el Diagrama de Salter-Swan dinámico (TCR vs Absorción Doméstica).
    Muestra las curvas de Balance Interno (IB) y Externo (EB) formando una X,
    e ilustra en cuál de las 4 zonas de actividad se encuentra la economía soberana.
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS
    
    A_actual = current_state.get("A_domestic", 100.0)
    q_actual = current_state.get("q_real", 1.0)
    
    A_ref = 100.0
    q_ref = 1.0
    
    c1 = params.get("c1", 0.75)
    t = params.get("t", 0.20)
    m1 = params.get("m1", 0.15)
    epsilon_x = params.get("epsilon_x", 0.80)
    
    slope_numerator_IB = 1.0 - c1 * (1.0 - t) + m1
    slope_denominator = max(epsilon_x, 1e-6)
    
    real_slope_IB = -slope_numerator_IB / slope_denominator
    real_slope_EB = m1 / slope_denominator
    
    # Escalar para encajar visualmente en la cuadrícula
    scale_factor = 50.0
    slope_IB = real_slope_IB / scale_factor
    slope_EB = real_slope_EB / scale_factor
    
    A_arr = np.linspace(40.0, 160.0, 100)
    
    q_IB = [q_ref + slope_IB * (a - A_ref) for a in A_arr]
    q_EB = [q_ref + slope_EB * (a - A_ref) for a in A_arr]
    
    fig = go.Figure()
    
    # Línea IB
    fig.add_trace(go.Scatter(
        x=A_arr, y=q_IB,
        name="Balance Interno (IB - Pleno Empleo)",
        mode="lines",
        line=dict(color=colors["C"], width=2),
        hovertemplate="IB: A=%{x:.1f}, q=%{y:.2f}<extra></extra>"
    ))
    
    # Línea EB
    fig.add_trace(go.Scatter(
        x=A_arr, y=q_EB,
        name="Balance Externo (EB - Cta. Corriente)",
        mode="lines",
        line=dict(color=colors["NX"], width=2),
        hovertemplate="EB: A=%{x:.1f}, q=%{y:.2f}<extra></extra>"
    ))
    
    # Marcador de la posición actual del país
    fig.add_trace(go.Scatter(
        x=[A_actual], y=[q_actual],
        name="Posición del País",
        mode="markers+text",
        text=["ESTADO ACTUAL"],
        textposition="top right",
        marker=dict(color=colors["Y_pot"], size=13, symbol="hexagon", line=dict(color="#FFF", width=1.5)),
        hovertemplate="<b>Estado Actual</b><br>Absorción Doméstica (A): %{x:.2f}<br>TCR (q): %{y:.2f}<extra></extra>"
    ))
    
    zone = current_state.get("zone_ss", "I")
    
    # Textos de los cuadrantes
    fig.add_annotation(x=130, y=1.5, text="<b>ZONA I</b><br>Sobreempleo / Superávit", showarrow=False, font=dict(size=8.5, color=colors["text"]), bgcolor="rgba(16, 185, 129, 0.12)", bordercolor=colors["T_recaudacion"], borderpad=4)
    fig.add_annotation(x=70, y=1.5, text="<b>ZONA II</b><br>Desempleo / Superávit", showarrow=False, font=dict(size=8.5, color=colors["text"]), bgcolor="rgba(56, 189, 248, 0.12)", bordercolor=colors["C"], borderpad=4)
    fig.add_annotation(x=70, y=0.5, text="<b>ZONA III</b><br>Desempleo / Déficit", showarrow=False, font=dict(size=8.5, color=colors["text"]), bgcolor="rgba(239, 68, 68, 0.12)", bordercolor=colors["Y_pot"], borderpad=4)
    fig.add_annotation(x=130, y=0.5, text="<b>ZONA IV</b><br>Sobreempleo / Déficit", showarrow=False, font=dict(size=8.5, color=colors["text"]), bgcolor="rgba(245, 158, 11, 0.12)", bordercolor=colors["NX"], borderpad=4)
    
    fig.update_layout(
        title=f"Diagrama de Salter-Swan (Zona de Equilibrio {zone})",
        xaxis=dict(title="Absorción Doméstica (A = C + I + G) [MM USD]", range=[40.0, 160.0], showgrid=True),
        yaxis=dict(title="Tipo de Cambio Real (q) [TCR]", range=[0.2, 1.8], showgrid=True),
        legend=dict(orientation="h", y=-0.22, x=0),
        margin=dict(l=40, r=20, t=50, b=80),
    )
    
    apply_chart_theme(fig, theme)
    return fig


# =============================================================================
# GRÁFICOS PESTAÑA 3 y 4: FASE 5.2b — MERCADOS FINANCIEROS E HISTORIAL
# =============================================================================

def plot_trilemma_ternary(current_state: dict) -> go.Figure:
    """
    Gráfico ternario del Trilema de Mundell-Fleming (Triángulo de Imposibilidad).
    Vértices:
      A (eje a) = TC Fijo
      B (eje b) = Independencia Monetaria
      C (eje c) = Libre Movilidad de Capitales

    La posición del marcador refleja el régimen cambiario actual y el grado
    de controles de capital (k_c) fijados por el jugador.
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS

    regime = current_state.get("regime", "fixed")
    policy = current_state.get("policy_applied", {})
    k_c = float(policy.get("k_c", 0.0))

    # ── Movilidad de Capitales: 1 − k_c ──────────────────────────────────────
    mob_capital = max(0.05, 1.0 - k_c)

    # ── TC Fijo y Autonomía Monetaria según régimen ───────────────────────────
    tc_map = {"fixed": 0.85, "crawl": 0.55, "dirty_float": 0.28, "flexible": 0.05}
    im_map = {"fixed": 0.05, "crawl": 0.25, "dirty_float": 0.55, "flexible": 0.85}
    tc_fijo = tc_map.get(regime, 0.50)
    indep_mon = im_map.get(regime, 0.40)

    # ── Normalizar a suma = 1 ─────────────────────────────────────────────────
    total = max(tc_fijo + indep_mon + mob_capital, 1e-6)
    a_coord = tc_fijo / total
    b_coord = indep_mon / total
    c_coord = mob_capital / total

    fig = go.Figure()

    fig.add_trace(go.Scatterternary(
        a=[a_coord],
        b=[b_coord],
        c=[c_coord],
        mode="markers+text",
        text=["Política Actual"],
        textposition="top center",
        marker=dict(
            color=colors["Y_pot"],
            size=22,
            symbol="star",
            line=dict(color="#FFFFFF", width=2)
        ),
        name="Posición de Política",
        hovertemplate=(
            "<b>Política Actual</b><br>"
            f"Régimen: {regime.upper()}<br>"
            f"Control de Capitales (k_c): {k_c:.0%}<br>"
            "TC Fijo (a): %{a:.0%}<br>"
            "Independencia Monetaria (b): %{b:.0%}<br>"
            "Movilidad de Capitales (c): %{c:.0%}<extra></extra>"
        )
    ))

    fig.update_layout(
        title="Trilema de Mundell-Fleming (Triángulo de Imposibilidad)",
        ternary=dict(
            sum=1,
            aaxis=dict(
                title="🔒 TC Fijo",
                min=0.01, linewidth=2, ticks="outside",
                tickformat=".0%"
            ),
            baxis=dict(
                title="🏦 Indep. Monetaria",
                min=0.01, linewidth=2, ticks="outside",
                tickformat=".0%"
            ),
            caxis=dict(
                title="🌐 Movilidad Capitales",
                min=0.01, linewidth=2, ticks="outside",
                tickformat=".0%"
            ),
        ),
        showlegend=False,
        margin=dict(l=60, r=60, t=70, b=60),
    )

    apply_chart_theme(fig, theme)
    return fig


def plot_business_cycle_clock(history: list[dict]) -> go.Figure:
    """
    Reloj del Ciclo de Negocios: trayectoria cronológica Desempleo (U) vs Inflación (π).
    El eje X de Desempleo está INVERTIDO para que "derecha = pleno empleo".
    El último punto de la trayectoria se resalta con un marcador más grande.
    Cuadrantes: Zona Ideal, Recalentamiento, Estanflación, Recesión.
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS

    u_pct = [snap.get("U", 0.05) * 100.0 for snap in history]
    pi_pct = [snap.get("pi", 0.03) * 100.0 for snap in history]
    t_labels = [f"t={snap.get('t', i)}" for i, snap in enumerate(history)]

    n = len(history)
    marker_sizes = [8] * n
    marker_colors_list = [colors["C"]] * n
    if n > 0:
        marker_sizes[-1] = 16
        marker_colors_list[-1] = colors["Y_pot"]

    fig = go.Figure()

    # ── Trayectoria conectada ─────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=u_pct, y=pi_pct,
        mode="lines+markers+text",
        text=t_labels,
        textposition="top right",
        name="Trayectoria del Ciclo",
        marker=dict(
            size=marker_sizes,
            color=marker_colors_list,
            line=dict(color="#000000", width=0.8)
        ),
        line=dict(color=colors["G"], width=2.0),
        hovertemplate=(
            "Turno %{text}<br>"
            "Desempleo (U): %{x:.2f}%<br>"
            "Inflación (π): %{y:.2f}%<extra></extra>"
        )
    ))

    # ── Líneas de cuadrante ───────────────────────────────────────────────────
    pi_obj = 3.0
    U_nairu = 5.0
    fig.add_hline(y=pi_obj, line_dash="dash", line_color="#475569", line_width=1.2,
                  annotation_text="Meta de Inflación (3%)", annotation_font_size=8)
    fig.add_vline(x=U_nairu, line_dash="dash", line_color="#475569", line_width=1.2,
                  annotation_text="NAIRU (5%)", annotation_font_size=8)

    # ── Etiquetas de cuadrante ────────────────────────────────────────────────
    fig.add_annotation(x=U_nairu + 2.5, y=pi_obj + 3.5, text="<b>ESTANFLACIÓN</b>",
                       showarrow=False, font=dict(size=9, color="#EF4444"),
                       bgcolor="rgba(239,68,68,0.08)")
    fig.add_annotation(x=U_nairu - 2.0, y=pi_obj + 3.5, text="<b>RECALENTAMIENTO</b>",
                       showarrow=False, font=dict(size=9, color="#F59E0B"),
                       bgcolor="rgba(245,158,11,0.08)")
    fig.add_annotation(x=U_nairu + 2.5, y=pi_obj - 1.5, text="<b>RECESIÓN</b>",
                       showarrow=False, font=dict(size=9, color="#3B82F6"),
                       bgcolor="rgba(59,130,246,0.08)")
    fig.add_annotation(x=U_nairu - 2.0, y=pi_obj - 1.5, text="<b>ZONA IDEAL</b>",
                       showarrow=False, font=dict(size=9, color="#10B981"),
                       bgcolor="rgba(16,185,129,0.08)")

    # Invertir eje X (derecha = menor desempleo / pleno empleo)
    fig.update_xaxes(autorange="reversed")

    fig.update_layout(
        title="Reloj del Ciclo de Negocios (Trayectoria U–π)",
        xaxis=dict(title="Tasa de Desempleo (U) [%] — Escala Invertida", showgrid=True),
        yaxis=dict(title="Tasa de Inflación (π) [%]", showgrid=True),
        showlegend=False,
        margin=dict(l=50, r=20, t=55, b=60),
    )

    apply_chart_theme(fig, theme)
    return fig


def plot_reelection_radar(history: list[dict]) -> go.Figure:
    """
    Radar polar de Desempeño Presidencial comparando Turno 0 (base) vs Turno Actual.

    Cinco ejes normalizados 0–100:
      1. Crecimiento Económico  (gY en [-10%, +10%] → [0, 100])
      2. Estabilidad de Precios (pi en [0, 20%]     → [100, 0])
      3. Pleno Empleo            (U  en [0, 15%]     → [100, 0])
      4. Solidez Externa         (R  / R₀ inicial    → [0, 100])
      5. Sostenibilidad Fiscal   (|déficit| / Y       → [100, 0])
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS

    categories = [
        "Crecimiento Económico",
        "Estabilidad de Precios",
        "Pleno Empleo",
        "Solidez Externa",
        "Sostenibilidad Fiscal",
        "Crecimiento Económico",  # cierra el polígono
    ]

    R_base = history[0].get("R", 50.0) if history else 50.0

    def compute_scores(snap: dict) -> list[float]:
        """Normaliza las variables clave de un snapshot al rango [0, 100]."""
        gY = snap.get("gY", 0.0)
        crecimiento = float(np.clip((gY + 0.10) / 0.20 * 100.0, 0.0, 100.0))

        pi = snap.get("pi", 0.03)
        estabilidad = float(np.clip((1.0 - pi / 0.20) * 100.0, 0.0, 100.0))

        U = snap.get("U", 0.05)
        empleo = float(np.clip((1.0 - U / 0.15) * 100.0, 0.0, 100.0))

        R = snap.get("R", 50.0)
        externa = float(np.clip((R / max(R_base, 1e-6)) * 100.0, 0.0, 100.0))

        deficit = abs(snap.get("deficit", 0.0))
        Y = snap.get("Y", 100.0)
        fiscal = float(np.clip((1.0 - (deficit / max(Y, 1e-6)) / 0.10) * 100.0, 0.0, 100.0))

        return [crecimiento, estabilidad, empleo, externa, fiscal]

    snap_0 = history[0] if history else {}
    snap_curr = history[-1] if history else {}

    scores_0 = compute_scores(snap_0)
    scores_curr = compute_scores(snap_curr)

    # Cerrar los polígonos
    scores_0_closed = scores_0 + [scores_0[0]]
    scores_curr_closed = scores_curr + [scores_curr[0]]

    t_curr = snap_curr.get("t", len(history) - 1)

    # Colores de relleno derivados de la paleta (sin manipulación de hex dinámica)
    fill_color_exec = "rgba(217, 45, 32, 0.12)"    # Y_pot Executive = #D92D20
    fill_color_strat = "rgba(244, 63, 94, 0.12)"   # Y_pot Strategy  = #F43F5E
    fill_color = fill_color_strat if theme == "strategy" else fill_color_exec

    fig = go.Figure()

    # Trazo de referencia (Turno 0) — sutil, sin relleno
    fig.add_trace(go.Scatterpolar(
        r=scores_0_closed,
        theta=categories,
        mode="lines+markers",
        name="Turno 0 (Base)",
        line=dict(color=colors["C"], width=1.5, dash="dash"),
        marker=dict(size=5, color=colors["C"]),
        opacity=0.65,
        hovertemplate="%{theta}: %{r:.0f} / 100<extra>Turno 0 (Base)</extra>"
    ))

    # Trazo actual — principal, con relleno semi-transparente
    fig.add_trace(go.Scatterpolar(
        r=scores_curr_closed,
        theta=categories,
        mode="lines+markers",
        name=f"Turno {t_curr} (Actual)",
        fill="toself",
        fillcolor=fill_color,
        line=dict(color=colors["Y_pot"], width=2.5),
        marker=dict(size=7, color=colors["Y_pot"]),
        hovertemplate="%{theta}: %{r:.0f} / 100<extra>Turno Actual</extra>"
    ))

    grid_color = "#374151" if theme == "strategy" else "#E5E7EB"
    fig.update_layout(
        title=f"Radar de Desempeño Presidencial (t=0 vs t={t_curr})",
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[20, 40, 60, 80, 100],
                ticksuffix="",
                gridcolor=grid_color,
                linecolor=grid_color,
            ),
            angularaxis=dict(gridcolor=grid_color)
        ),
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
        margin=dict(l=60, r=60, t=70, b=80),
    )

    apply_chart_theme(fig, theme)
    return fig
