"""
ui/charts_v2.py
===============
Gráficos interactivos Plotly macroeconómicos avanzados V2.0 (Fase 4).
Rediseñados para la Consistencia y Estilo Bloomberg Terminal (Modo Claro de Alto Contraste).
"""

from __future__ import annotations

import math
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from engine.core_v2 import compute_multiplier, is_curve_v2, lm_curve_v2, compute_NX
from engine.game_state import TurnSnapshot


# ─────────────────────────────────────────────────────────────────────────────
# PALETAS DE COLORES BLOOMBERG TERMINAL (CLARO)
# ─────────────────────────────────────────────────────────────────────────────
EXECUTIVE_COLORS = {
    "C": "#0068ff",             # Consumo (Azul Bloomberg)
    "I": "#0d9488",             # Inversión (Turquesa / Dark Teal)
    "G": "#7A5AF8",             # Gasto (Púrpura)
    "NX": "#fb8b1e",            # Net Exports (Naranja)
    "Y_pot": "#ff433d",         # PIB Potencial (Rojo Bloomberg)
    "T_recaudacion": "#0d9488", # Recaudación (Turquesa / Teal)
    "X": "#0d9488",             # Exportaciones (Turquesa)
    "M": "#ff433d",             # Importaciones (Rojo)
    "E": "#0068ff",             # Tipo de cambio (Azul)
    "E_band": "#98A2B3",        # Banda superior (Gris)
    "intervention": "#ff433d",  # Intervención (Rojo)
    "grid": "#E2E8F0",          # Gris ultra-tenue
    "text": "#000000"           # Negro Puro
}

STRATEGY_COLORS = {
    "C": "#38bdf8",             # Consumo (Cielo brillante)
    "I": "#4af6c3",             # Inversión (Turquesa brillante)
    "G": "#a78bfa",             # Gasto (Púrpura brillante)
    "NX": "#fb923c",            # Net Exports (Naranja brillante)
    "Y_pot": "#f87171",         # PIB Potencial (Rojo brillante)
    "T_recaudacion": "#2dd4bf", # Recaudación
    "X": "#2dd4bf",             # Exportaciones
    "M": "#f87171",             # Importaciones
    "E": "#38bdf8",             # Tipo de cambio
    "E_band": "#94a3b8",        # Banda superior
    "intervention": "#ef4444",  # Intervención (Rojo)
    "grid": "#334155",          # Gris oscuro para grilla nocturna
    "text": "#f8fafc"           # Blanco para textos en modo estrategia
}


def apply_chart_theme(fig: go.Figure, theme: str) -> go.Figure:
    """
    Aplica tipografías Bloomberg, colores de grilla ultra-tenue y fondos transparentes
    a un gráfico garantizando el 100% de legibilidad en Modo Claro/Oscuro según el tema.
    """
    font_family = "Inter, sans-serif" if theme == "executive" else "Manrope, sans-serif"
    title_font_family = "Space Grotesk, sans-serif" if theme == "executive" else "Rajdhani, sans-serif"
    
    if theme == "strategy":
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family=font_family,
                color="#f8fafc",
                size=11
            ),
            title=dict(
                font=dict(
                    family=title_font_family,
                    size=14,
                    weight="bold",
                    color="#f8fafc"
                )
            ),
            xaxis=dict(
                gridcolor="#334155",
                zerolinecolor="#cbd5e1",
                title_font=dict(size=12, color="#f8fafc", family=title_font_family, weight="bold"),
                tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#cbd5e1")
            ),
            yaxis=dict(
                gridcolor="#334155",
                zerolinecolor="#cbd5e1",
                title_font=dict(size=12, color="#f8fafc", family=title_font_family, weight="bold"),
                tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#cbd5e1")
            ),
            legend=dict(
                font=dict(size=11, color="#f8fafc"),
                bgcolor="rgba(15,23,42,0.85)"
            )
        )
    else:
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family=font_family,
                color="#000000",
                size=11
            ),
            title=dict(
                font=dict(
                    family=title_font_family,
                    size=14,
                    weight="bold",
                    color="#000000"
                )
            ),
            xaxis=dict(
                gridcolor="#E2E8F0",
                zerolinecolor="#CBD5E1",
                title_font=dict(size=12, color="#000000", family=title_font_family, weight="bold"),
                tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#1E293B")
            ),
            yaxis=dict(
                gridcolor="#E2E8F0",
                zerolinecolor="#CBD5E1",
                title_font=dict(size=12, color="#000000", family=title_font_family, weight="bold"),
                tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#1E293B")
            ),
            legend=dict(
                font=dict(size=11, color="#000000"),
                bgcolor="rgba(255,255,255,0.8)"
            )
        )
    return fig


def get_trade_details(snap: dict, sp: dict) -> tuple[float, float]:
    """
    Calcula Exportaciones (X) e Importaciones (M_imp) brutas para un snapshot.
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


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY / COMPATIBILIDAD CHARTS (REDISEÑADOS DINÁMICOS)
# ─────────────────────────────────────────────────────────────────────────────

_HASH_FUNCS = {list: lambda x: hash(str(x)), dict: lambda x: hash(str(x))}

@st.cache_data(hash_funcs=_HASH_FUNCS)
def plot_pib_decomposition(history: list[TurnSnapshot]) -> go.Figure:
    """
    PIB por componentes (barras apiladas) + Y_pot (línea).
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS
    fig = go.Figure()

    t_vec = [snap["t"] for snap in history]
    C_vec = [snap["C"] for snap in history]
    I_vec = [snap["I_inv"] for snap in history]
    G_vec = [snap["G"] for snap in history]
    NX_vec = [snap["NX"] for snap in history]
    Y_pot_vec = [snap["Y"] / max(1e-3, 1.0 + snap["gap"]) for snap in history]

    fig.add_trace(go.Bar(
        x=t_vec, y=C_vec, name="Consumo (C)",
        marker_color=colors["C"], opacity=0.85,
        hovertemplate="Consumo (C): %{y:.1f} MM<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=t_vec, y=I_vec, name="Inversión Privada (I)",
        marker_color=colors["I"], opacity=0.85,
        hovertemplate="Inversión (I): %{y:.1f} MM<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=t_vec, y=G_vec, name="Gasto Público (G)",
        marker_color=colors["G"], opacity=0.85,
        hovertemplate="Gasto (G): %{y:.1f} MM<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=t_vec, y=NX_vec, name="Exportaciones Netas (NX)",
        marker_color=colors["NX"], opacity=0.85,
        hovertemplate="Exportaciones Netas (NX): %{y:.1f} MM<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=t_vec, y=Y_pot_vec, name="PIB Potencial (Y_pot)",
        mode="lines+markers",
        line=dict(color=colors["Y_pot"], width=3.5, dash="dash"),
        marker=dict(symbol="circle", size=8),
        hovertemplate="PIB Potencial: %{y:.1f} MM<extra></extra>"
    ))

    fig.update_layout(
        title="Descomposición del PIB y Capacidad Productiva (Crowding-out)",
        xaxis=dict(title="Turno (Período)", tickmode="linear", dtick=1),
        yaxis=dict(title="Valor en MM de USD", showgrid=True),
        barmode="relative",
        legend=dict(orientation="h", y=-0.22, x=0),
        margin=dict(l=40, r=20, t=50, b=80),
    )

    apply_chart_theme(fig, theme)
    return fig


@st.cache_data(hash_funcs=_HASH_FUNCS)
def plot_economic_cycle(history: list[TurnSnapshot]) -> go.Figure:
    """
    Reloj del Ciclo Económico.
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS
    fig = go.Figure()

    u_pct = [snap["U"] * 100 for snap in history]
    pi_pct = [snap["pi"] * 100 for snap in history]
    t_labels = [f"t={snap['t']}" for snap in history]

    marker_sizes = [8 if i < len(history) - 1 else 14 for i in range(len(history))]
    marker_colors = ["#64748b" if i < len(history) - 1 else colors["Y_pot"] for i in range(len(history))]

    fig.add_trace(go.Scatter(
        x=u_pct, y=pi_pct,
        mode="lines+markers+text",
        text=t_labels,
        textposition="top right",
        name="Trayectoria del Ciclo",
        marker=dict(size=marker_sizes, color=marker_colors, line=dict(color="#000000", width=1.2)),
        line=dict(color=colors["C"], width=3.5),
        hovertemplate="Turno %{text}<br>Desempleo (U): %{x:.2f}%<br>Inflación (π): %{y:.2f}%<extra></extra>"
    ))

    pi_obj = 3.0
    U_n = history[0]["policy_applied"].get("U_n", 0.05) * 100 if history else 5.0

    fig.add_hline(y=pi_obj, line_dash="dash", line_color="#475569", line_width=1.5)
    fig.add_vline(x=U_n, line_dash="dash", line_color="#475569", line_width=1.5)

    fig.update_xaxes(autorange="reversed")

    fig.add_annotation(x=U_n + 4.0, y=pi_obj + 8.0, text="<b>ESTANFLACIÓN</b><br>Alta Inflación / Recesión", showarrow=False, font=dict(size=9, color="#ff433d"), bgcolor="rgba(255,255,255,0.9)", bordercolor="#ff433d", borderpad=4)
    fig.add_annotation(x=U_n - 2.5, y=pi_obj + 8.0, text="<b>RECALENTAMIENTO</b><br>Boom de demanda / Inflación", showarrow=False, font=dict(size=9, color="#fb8b1e"), bgcolor="rgba(255,255,255,0.9)", bordercolor="#fb8b1e", borderpad=4)
    fig.add_annotation(x=U_n + 4.0, y=pi_obj - 2.0, text="<b>RECESIÓN</b><br>Desempleo / Deflación", showarrow=False, font=dict(size=9, color="#0068ff"), bgcolor="rgba(255,255,255,0.9)", bordercolor="#0068ff", borderpad=4)
    fig.add_annotation(x=U_n - 2.5, y=pi_obj - 2.0, text="<b>ZONA IDEAL</b><br>Pleno Empleo / Estabilidad", showarrow=False, font=dict(size=9, color="#0d9488"), bgcolor="rgba(255,255,255,0.9)", bordercolor="#0d9488", borderpad=4)

    fig.update_layout(
        title="Reloj del Ciclo Económico (Fase de Actividad)",
        xaxis=dict(title="Tasa de Desempleo (U) - Escala Invertida [%]", showgrid=True),
        yaxis=dict(title="Tasa de Inflación (π) [%]", showgrid=True),
        margin=dict(l=40, r=20, t=50, b=80),
        showlegend=False
    )

    apply_chart_theme(fig, theme)
    return fig


@st.cache_data
def plot_reserves_thermometer(R_curr: float, R_0: float) -> go.Figure:
    """
    Termómetro de Reservas (Gauge semafórico).
    """
    theme = st.session_state.get("theme", "executive")
    
    if R_curr < R_0 * 0.30:
        color_semaforo = "#ff433d"  # Rojo
    elif R_curr < R_0 * 0.70:
        color_semaforo = "#fb8b1e"  # Naranja
    else:
        color_semaforo = "#0d9488"  # Turquesa/Teal

    max_range = max(R_0 * 1.5, R_curr * 1.1)

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=R_curr,
        delta={'reference': R_0, 'relative': False, 'valueformat': '.1f', 'increasing': {'color': "#0d9488"}, 'decreasing': {'color': "#ff433d"}},
        number={'suffix': " MM", 'font': {'size': 24, 'color': '#000000'}},
        gauge={
            'axis': {'range': [0, max_range], 'tickcolor': '#000000'},
            'bar': {'color': color_semaforo},
            'bgcolor': "#FFFFFF",
            'borderwidth': 1,
            'bordercolor': "#CBD5E1",
            'steps': [
                {'range': [0, R_0 * 0.3], 'color': "rgba(255, 67, 61, 0.1)"},
                {'range': [R_0 * 0.3, R_0 * 0.7], 'color': "rgba(251, 139, 30, 0.1)"},
                {'range': [R_0 * 0.7, max_range], 'color': "rgba(13, 148, 136, 0.1)"}
            ],
            'threshold': {
                'line': {'color': "#ff433d", 'width': 3},
                'thickness': 0.75,
                'value': R_0 * 0.3
            }
        }
    ))

    fig.update_layout(
        title={'text': "Termómetro de Reservas Internacionales", 'x': 0.5, 'xanchor': 'center'},
        height=220,
        margin=dict(l=30, r=30, t=60, b=30),
    )

    apply_chart_theme(fig, theme)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# GRÁFICOS ACTIVOS DE LA INTERFAZ
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(hash_funcs=_HASH_FUNCS)
def plot_gdp_decomposition(history: list[dict]) -> go.Figure:
    """
    PIB por componentes (barras apiladas) + Y_pot (línea).
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
    
    fig.add_trace(go.Scatter(
        x=t_vec, y=Y_pot_vec, name="Capacidad Productiva (Y_pot)",
        mode="lines+markers",
        line=dict(color=colors["Y_pot"], width=3.5, dash="dash"),
        marker=dict(symbol="circle", size=8),
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


@st.cache_data(hash_funcs=_HASH_FUNCS)
def plot_sectoral_composition(history: list[dict]) -> go.Figure:
    """
    Composición productiva sector transable YT vs No-Transable YNT.
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


@st.cache_data
def plot_fiscal_odometer(current_state: dict) -> go.Figure:
    """
     Waterfall del Balance Fiscal.
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS
    
    fig = go.Figure()
    
    recaudacion = current_state.get("recaudacion", 0.0)
    deficit = current_state.get("deficit", 0.0)
    
    policy = current_state.get("policy_applied", {})
    G_c = policy.get("G_c", 15.0)
    I_g = policy.get("I_g", 5.0)
    Tr = policy.get("Tr", 0.0)
    
    gasto_total = G_c + I_g + Tr
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
        0.0
    ]
    
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
        connector=dict(line=dict(color=colors["grid"], width=1.5, dash="dot")),
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


@st.cache_data(hash_funcs=_HASH_FUNCS)
def plot_butterfly_trade(history: list[dict]) -> go.Figure:
    """
    Tornado de Importaciones vs Exportaciones.
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
        M_vec.append(-M_imp)
        
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=t_vec,
        x=M_vec,
        name="Importaciones Brutas (M_imp)",
        orientation="h",
        marker_color=colors["M"],
        customdata=[-v for v in M_vec],
        hovertemplate="Importaciones: %{customdata:.2f} MM USD<extra></extra>"
    ))
    
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


@st.cache_data(hash_funcs=_HASH_FUNCS)
def plot_exchange_intervention(history: list[dict]) -> go.Figure:
    """
    Banda Cambiaria e Intervención.
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
            band = snap["E"] * 1.10
        E_band_vec.append(band)
        intervention_vec.append(snap.get("FX_intervention", 0.0))
        
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(
        x=t_vec, y=E_vec,
        name="Tipo de Cambio (E)",
        mode="lines+markers",
        line=dict(color=colors["E"], width=3.5),
        marker=dict(size=7),
        hovertemplate="Tipo de Cambio E: %{y:.2f}<extra></extra>"
    ), secondary_y=False)
    
    fig.add_trace(go.Scatter(
        x=t_vec, y=E_band_vec,
        name="Techo Cambiario (Banda)",
        mode="lines",
        line=dict(color=colors["E_band"], width=2.0, dash="dash"),
        hovertemplate="Techo Cambiario: %{y:.2f}<extra></extra>"
    ), secondary_y=False)
    
    fig.add_trace(go.Bar(
        x=t_vec, y=intervention_vec,
        name="Venta de Reservas (BC)",
        marker_color=colors["intervention"],
        opacity=0.35,
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
    fig.data[2].opacity = 0.35
    
    return fig


@st.cache_data
def plot_salter_swan(current_state: dict, params: dict) -> go.Figure:
    """
    Diagrama de Salter-Swan.
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS
    
    A_actual = current_state.get("A_domestic", 100.0)
    q_actual = current_state.get("q_real", 1.0)
    
    A_ref = 100.0
    q_ref = 1.0
    
    c1 = params.get("c1", 0.75)
    policy = current_state.get("policy_applied", {})
    t = policy.get("t_c", current_state.get("t_c", params.get("t_c", params.get("t", 0.20))))
    m1 = params.get("m1", 0.15)
    epsilon_x = params.get("epsilon_x", 0.80)
    
    slope_numerator_IB = 1.0 - c1 * (1.0 - t) + m1
    slope_denominator = max(epsilon_x, 1e-6)
    
    real_slope_IB = -slope_numerator_IB / slope_denominator
    real_slope_EB = m1 / slope_denominator
    
    scale_factor = 50.0
    slope_IB = real_slope_IB / scale_factor
    slope_EB = real_slope_EB / scale_factor
    
    A_arr = np.linspace(40.0, 160.0, 100)
    
    q_IB = [q_ref + slope_IB * (a - A_ref) for a in A_arr]
    q_EB = [q_ref + slope_EB * (a - A_ref) for a in A_arr]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=A_arr, y=q_IB,
        name="Balance Interno (IB - Pleno Empleo)",
        mode="lines",
        line=dict(color=colors["C"], width=3.5),
        hovertemplate="IB: A=%{x:.1f}, q=%{y:.2f}<extra></extra>"
    ))
    
    fig.add_trace(go.Scatter(
        x=A_arr, y=q_EB,
        name="Balance Externo (EB - Cta. Corriente)",
        mode="lines",
        line=dict(color=colors["NX"], width=3.5),
        hovertemplate="EB: A=%{x:.1f}, q=%{y:.2f}<extra></extra>"
    ))
    
    fig.add_trace(go.Scatter(
        x=[A_actual], y=[q_actual],
        name="Posición del País",
        mode="markers+text",
        text=["<b>📍 ESTADO ACTUAL</b>"],
        textposition="top center",
        textfont=dict(size=11, color="#FF4B4B"),
        marker=dict(color="#FF4B4B", size=18, symbol="star", line=dict(color="#000000", width=2.0)),
        hovertemplate="<b>Estado Actual</b><br>Absorción Doméstica (A): %{x:.2f}<br>TCR (q): %{y:.2f}<extra></extra>"
    ))
    
    zone = current_state.get("zone_ss", "I")
    
    # Renderizar zonas de Salter-Swan basadas en el punto de intersección (100, 1)
    fig.add_annotation(x=130, y=1.5, text="<b>ZONA I</b><br>Sobreempleo / Superávit", showarrow=False, font=dict(size=9, color="#000000"), bgcolor="rgba(255,255,255,0.95)", bordercolor=colors["I"], borderpad=4)
    fig.add_annotation(x=70, y=1.5, text="<b>ZONA II</b><br>Desempleo / Superávit", showarrow=False, font=dict(size=9, color="#000000"), bgcolor="rgba(255,255,255,0.95)", bordercolor=colors["C"], borderpad=4)
    fig.add_annotation(x=70, y=0.5, text="<b>ZONA III</b><br>Desempleo / Déficit", showarrow=False, font=dict(size=9, color="#000000"), bgcolor="rgba(255,255,255,0.95)", bordercolor=colors["Y_pot"], borderpad=4)
    fig.add_annotation(x=130, y=0.5, text="<b>ZONA IV</b><br>Sobreempleo / Déficit", showarrow=False, font=dict(size=9, color="#000000"), bgcolor="rgba(255,255,255,0.95)", bordercolor=colors["NX"], borderpad=4)
    
    # Calcular rangos dinámicos basados en la posición real del país para evitar recortes (clipping)
    x_min = min(35.0, A_actual - 15.0)
    x_max = max(165.0, A_actual + 15.0)
    y_min = min(0.1, q_actual - 0.25)
    y_max = max(1.9, q_actual + 0.25)

    fig.update_layout(
        title=f"Diagrama de Salter-Swan (Zona de Equilibrio {zone})",
        xaxis=dict(title="Absorción Doméstica (A = C + I + G) [MM USD]", range=[x_min, x_max], showgrid=True),
        yaxis=dict(title="Tipo de Cambio Real (q) [TCR]", range=[y_min, y_max], showgrid=True),
        legend=dict(orientation="h", y=-0.18, x=0),
        margin=dict(l=60, r=40, t=60, b=90),
        height=520,
    )
    
    apply_chart_theme(fig, theme)
    return fig


@st.cache_data(hash_funcs=_HASH_FUNCS)
def plot_debt_snowball(history: list[dict], current_state: dict = None) -> go.Figure:
    """
    Trayectoria intertemporal del Ratio Deuda / PIB Potencial (B / Y_pot).
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

    if t_vec:
        t_min, t_max = min(t_vec), max(t_vec)
        fig.add_shape(
            type="line",
            x0=t_min, x1=t_max,
            y0=1.20, y1=1.20,
            line=dict(color="#ff433d", width=2, dash="dash"),
        )
        fig.add_annotation(
            x=t_max, y=1.22,
            text="⚠️ Umbral de Default Soberano (120% PIB)",
            showarrow=False, xanchor="right",
            font=dict(size=9.5, color="#ff433d"),
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#ff433d", borderpad=3
        )

    fig.add_trace(go.Scatter(
        x=t_vec, y=ratio_vec,
        mode="lines+markers",
        name="Ratio Deuda / PIB Potencial",
        line=dict(color=colors["G"], width=3.5),
        marker=dict(size=8, color=colors["G"], line=dict(color="#000000", width=1)),
        fill="tozeroy",
        fillcolor="rgba(122, 90, 248, 0.06)",
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


@st.cache_data
def plot_islm_bp_dynamic(current_state: dict, params: dict) -> go.Figure:
    """
    Diagrama de Equilibrio General IS-LM-BP.
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS

    Y_eq = float(current_state.get("Y", 100.0))
    r_eq = float(current_state.get("r", 5.0))
    policy = current_state.get("policy_applied", {})
    k_c = float(policy.get("k_c", 0.0))

    span = max(20.0, Y_eq * 0.22)
    Y_arr = np.linspace(max(1.0, Y_eq - span), Y_eq + span, 130)

    b = float(params.get("b", 2.0))
    h = float(params.get("h", 2.0))
    k = float(params.get("k", 0.50))
    m1 = float(params.get("m1", 0.15))
    c1 = float(params.get("c1", 0.75))
    t_tax = float(policy.get("t_c", current_state.get("t_c", params.get("t_c", params.get("t", 0.20)))))

    slope_IS_raw = -(1.0 - c1 * (1.0 - t_tax) + m1) / max(b, 1e-6)
    scale = max(1.0, Y_eq / 100.0)
    slope_IS = max(-0.35, min(-0.04, slope_IS_raw / scale))

    slope_LM_raw = k / max(h, 1e-6)
    slope_LM = max(0.03, min(0.30, slope_LM_raw * 0.10 / scale))

    slope_BP = 0.01 + k_c * 0.17

    r_IS = [max(0.0, r_eq + slope_IS * (y - Y_eq)) for y in Y_arr]
    
    # Determinar si opera bajo rate_targeting en régimen flexible
    monetary_mode = policy.get("monetary_mode", "quantity")
    is_rate_targeting = (monetary_mode == "rate_targeting") and (current_state.get("regime", "fixed") == "flexible")
    if is_rate_targeting:
        r_ref_val = float(policy.get("r_ref", r_eq))
        r_LM = [r_ref_val] * len(Y_arr)
    else:
        r_LM = [r_eq + slope_LM * (y - Y_eq) for y in Y_arr]
        
    r_BP = [r_eq + slope_BP * (y - Y_eq) for y in Y_arr]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=list(Y_arr), y=r_IS, mode="lines", name="Curva IS (Bien-Servicios)",
        line=dict(color=colors["C"], width=3.5),
        hovertemplate="PIB: %{x:.1f} MM<br>Tasa IS: %{y:.2f}%<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=list(Y_arr), y=r_LM, mode="lines", name="Curva LM (Dinero)",
        line=dict(color=colors["I"], width=3.5),
        hovertemplate="PIB: %{x:.1f} MM<br>Tasa LM: %{y:.2f}%<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=list(Y_arr), y=r_BP, mode="lines", name="Curva BP (Balanza de Pagos)",
        line=dict(color=colors["NX"], width=3.5, dash="dash"),
        hovertemplate="PIB: %{x:.1f} MM<br>Tasa BP: %{y:.2f}%<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=[Y_eq], y=[r_eq], mode="markers+text", name="Equilibrio (Y*, r*)",
        text=["<b>📍 EQUILIBRIO</b>"],
        textposition="top center",
        textfont=dict(size=11, color="#FF4B4B"),
        marker=dict(
            color="#FF4B4B", size=18, symbol="star",
            line=dict(color="#000000", width=2.0)
        ),
        hovertemplate="<b>Punto de Equilibrio</b><br>Y*: %{x:.2f} MM<br>r*: %{y:.2f}%<extra></extra>"
    ))

    fig.add_vline(x=Y_eq, line_dash="dash", line_color="#EF4444", line_width=1.5,
                  annotation_text=f"<b>Y* = {Y_eq:.1f}</b>", annotation_position="bottom left",
                  annotation_font_size=10.5, annotation_font_color="#EF4444")
    fig.add_hline(y=r_eq, line_dash="dash", line_color="#EF4444", line_width=1.5,
                  annotation_text=f"<b>r* = {r_eq:.1f}%</b>", annotation_position="top right",
                  annotation_font_size=10.5, annotation_font_color="#EF4444")

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
        legend=dict(orientation="h", y=-0.15, x=0),
        margin=dict(l=60, r=40, t=60, b=90),
        height=560,
        hovermode="closest"
    )

    apply_chart_theme(fig, theme)
    return fig


@st.cache_data
def plot_trilemma_ternary(current_state: dict) -> go.Figure:
    """
    Gráfico ternario del Trilema de Mundell-Fleming.
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS

    regime = current_state.get("regime", "fixed")
    policy = current_state.get("policy_applied", {})
    k_c = float(policy.get("k_c", 0.0))

    # Movilidad de capitales base
    mob_capital = 1.0 - k_c

    if regime == "fixed":
        # Trilema estricto: bajo TC Fijo, no hay Autonomía Monetaria a menos que k_c sea extremo (bloqueo financiero)
        if k_c >= 0.75:
            # Control de capital extremo (bloqueo financiero) -> permite recuperar autonomía monetaria
            indep_mon = k_c
            mob_capital = 1.0 - k_c
            tc_fijo = 0.90
        else:
            # Libre movilidad y TC Fijo -> Autonomía Monetaria cae a niveles mínimos, atraída hacia estabilidad cambiaria y movilidad
            indep_mon = 0.01
            mob_capital = 1.0 - k_c
            tc_fijo = 0.99
    elif regime == "flexible":
        # TC Flexible -> Máxima Autonomía Monetaria, y la Movilidad de Capitales depende de k_c
        tc_fijo = 0.01
        indep_mon = 0.99
        mob_capital = 1.0 - k_c
    else:
        # Crawling peg o flotación sucia (regímenes intermedios)
        tc_fijo = 0.45 if regime == "crawl" else 0.25
        indep_mon = 0.40 if regime == "crawl" else 0.60
        mob_capital = 1.0 - k_c

    # Normalizar a suma = 1
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
            line=dict(color="#000000", width=2)
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
                min=0.0, linewidth=2, ticks="outside",
                tickformat=".0%"
            ),
            baxis=dict(
                title="🏦 Indep. Monetaria",
                min=0.0, linewidth=2, ticks="outside",
                tickformat=".0%"
            ),
            caxis=dict(
                title="🌐 Movilidad Capitales",
                min=0.0, linewidth=2, ticks="outside",
                tickformat=".0%"
            ),
        ),
        showlegend=False,
        margin=dict(l=60, r=60, t=70, b=60),
    )

    apply_chart_theme(fig, theme)
    return fig


@st.cache_data(hash_funcs=_HASH_FUNCS)
def plot_business_cycle_clock(history: list[dict]) -> go.Figure:
    """
    Reloj del Ciclo de Negocios.
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

    fig.add_trace(go.Scatter(
        x=u_pct, y=pi_pct,
        mode="lines+markers+text",
        text=t_labels,
        textposition="top right",
        name="Trayectoria del Ciclo",
        marker=dict(
            size=marker_sizes,
            color=marker_colors_list,
            line=dict(color="#000000", width=1.0)
        ),
        line=dict(color=colors["G"], width=3.5),
        hovertemplate=(
            "Turno %{text}<br>"
            "Desempleo (U): %{x:.2f}%<br>"
            "Inflación (π): %{y:.2f}%<extra></extra>"
        )
    ))

    pi_obj = 3.0
    U_nairu = 5.0
    fig.add_hline(y=pi_obj, line_dash="dash", line_color="#475569", line_width=1.5,
                  annotation_text="Meta de Inflación (3%)", annotation_font_size=8.5)
    fig.add_vline(x=U_nairu, line_dash="dash", line_color="#475569", line_width=1.5,
                  annotation_text="NAIRU (5%)", annotation_font_size=8.5)

    fig.add_annotation(x=U_nairu + 2.5, y=pi_obj + 3.5, text="<b>ESTANFLACIÓN</b>",
                       showarrow=False, font=dict(size=9.5, color="#ff433d"),
                       bgcolor="rgba(255,255,255,0.95)", bordercolor="#ff433d", borderpad=3)
    fig.add_annotation(x=U_nairu - 2.0, y=pi_obj + 3.5, text="<b>RECALENTAMIENTO</b>",
                       showarrow=False, font=dict(size=9.5, color="#fb8b1e"),
                       bgcolor="rgba(255,255,255,0.95)", bordercolor="#fb8b1e", borderpad=3)
    fig.add_annotation(x=U_nairu + 2.5, y=pi_obj - 1.5, text="<b>RECESIÓN</b>",
                       showarrow=False, font=dict(size=9.5, color="#0068ff"),
                       bgcolor="rgba(255,255,255,0.95)", bordercolor="#0068ff", borderpad=3)
    fig.add_annotation(x=U_nairu - 2.0, y=pi_obj - 1.5, text="<b>ZONA IDEAL</b>",
                       showarrow=False, font=dict(size=9.5, color="#0d9488"),
                       bgcolor="rgba(255,255,255,0.95)", bordercolor="#0d9488", borderpad=3)

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


@st.cache_data(hash_funcs=_HASH_FUNCS)
def plot_reelection_radar(history: list[dict]) -> go.Figure:
    """
    Radar de Desempeño Presidencial.
    """
    theme = st.session_state.get("theme", "executive")
    colors = STRATEGY_COLORS if theme == "strategy" else EXECUTIVE_COLORS

    categories = [
        "Crecimiento Económico",
        "Estabilidad de Precios",
        "Pleno Empleo",
        "Solidez Externa",
        "Sostenibilidad Fiscal",
        "Crecimiento Económico",
    ]

    R_base = history[0].get("R", 50.0) if history else 50.0

    def compute_scores(snap: dict) -> list[float]:
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

    scores_0_closed = scores_0 + [scores_0[0]]
    scores_curr_closed = scores_curr + [scores_curr[0]]

    t_curr = snap_curr.get("t", len(history) - 1)

    fill_color = "rgba(255, 67, 61, 0.12)"

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=scores_0_closed,
        theta=categories,
        mode="lines+markers",
        name="Turno 0 (Base)",
        line=dict(color=colors["C"], width=2.0, dash="dash"),
        marker=dict(size=5, color=colors["C"]),
        opacity=0.65,
        hovertemplate="%{theta}: %{r:.0f} / 100<extra>Turno 0 (Base)</extra>"
    ))

    fig.add_trace(go.Scatterpolar(
        r=scores_curr_closed,
        theta=categories,
        mode="lines+markers",
        name=f"Turno {t_curr} (Actual)",
        fill="toself",
        fillcolor=fill_color,
        line=dict(color=colors["Y_pot"], width=3.5),
        marker=dict(size=7, color=colors["Y_pot"]),
        hovertemplate="%{theta}: %{r:.0f} / 100<extra>Turno Actual</extra>"
    ))

    grid_color = "#E5E7EB"
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
