"""
ui_simple/charts_panel.py
=========================
Gráficos interactivos Plotly del Simulador Macroeconómico (Columna Central).
Edición: The Economic War Room (V1.2 SIMPLE).

Incluye las 4 pestañas requeridas por master_spec.md (Sección 6.2):
1. 📈 Modelo IS-LM-BP (Curvas IS, LM, BP y desplazamientos en vivo).
2. ⚖️ Diagrama Salter-Swan (4 Cuadrantes, curvas IB/EB y trayectoria histórica).
3. 🔺 Trilema de Mundell-Fleming (Visual interactivo de vértices activos y trade-offs).
4. 🕒 Evolución Temporal (Series de tiempo de 10 turnos para variables macroeconómicas).
"""

from __future__ import annotations

from typing import List

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from config_simple.parameters import TurnSnapshot
from engine_simple.core import compute_salter_swan, solve_equilibrium
from engine_simple.state_manager import StateManager


def render_charts_panel(state_mgr: StateManager) -> None:
    """
    Renderiza el sistema de 4 Tabs con gráficos interactivos Plotly.
    """
    tab_islm, tab_ss, tab_trilemma, tab_timeline = st.tabs([
        "📈 Modelo IS-LM-BP",
        "⚖️ Diagrama Salter-Swan",
        "🔺 Trilema Cambiario",
        "🕒 Evolución Temporal"
    ])

    with tab_islm:
        _render_islmbp_chart(state_mgr)

    with tab_ss:
        _render_salter_swan_chart(state_mgr)

    with tab_trilemma:
        _render_trilemma_chart(state_mgr)

    with tab_timeline:
        _render_timeline_chart(state_mgr.history)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: MODELO IS-LM-BP
# ─────────────────────────────────────────────────────────────────────────────

def _render_islmbp_chart(state_mgr: StateManager) -> None:
    """Genera el gráfico IS-LM-BP dinámico con equilibrio actual y proyectado."""
    curr_snap = state_mgr.history[-1]
    sp = state_mgr.current_params
    inst = curr_snap["policy_applied"]

    Y_eq = curr_snap["Y"]
    r_eq = curr_snap["r"]

    # Dominio de Y
    Y_max = max(180.0, Y_eq * 1.6)
    Y_vals = np.linspace(20.0, Y_max, 250)

    # 1. Curva IS:
    # Y = k_m · [c0 + I0 - b(r - r0) - rho_k(tk - tk0) + psi_ci(Ig - Ig0) + G + X - m0 + eps_m(q - 1)]
    # Despejando r: r_IS = r0 + [c0 + I0 - rho_k(tk - tk0) + psi_ci(Ig - Ig0) + G + X - m0 + eps_m(q-1) - Y/km] / b
    km = curr_snap.get("mult", 1.7)
    b_sens = max(sp.get("b", 0.8), 0.1)
    r0 = sp.get("r0", 5.0)

    # Numerador autónomo en IS
    A_auto_IS = (
        sp.get("c0", 12.0)
        + sp.get("I0", 16.0)
        + curr_snap["Gc"]
        + curr_snap["Ig"]
        + curr_snap["X"]
        - sp.get("m0", 6.0)
        + sp.get("epsilon_m", 1.1) * (curr_snap["q_real"] - 1.0)
    )
    r_IS = r0 + (A_auto_IS - (Y_vals / max(km, 0.1))) / b_sens

    # 2. Curva LM (implícita en el mercado monetario):
    # Demanda de dinero: M/P = k·Y - h·r => r_LM = (k·Y - M/P) / h
    k_money = sp.get("k", 0.5)
    h_money = max(sp.get("h", 2.0), 0.5)
    M_P = k_money * Y_eq - h_money * r_eq
    r_LM = (k_money * Y_vals - M_P) / h_money

    # 3. Curva BP:
    # BP: r_BP = r* + rho + (m1·Y - X) / f
    f_mob = max(sp.get("f", 2.0), 0.1)
    r_star = inst.get("r_star", 4.5)
    rho_val = curr_snap.get("rho", 0.5)
    crawl_rate = inst.get("crawl_rate", 0.0) if inst.get("regime") == "crawling_peg" else 0.0
    r_BP = (r_star + crawl_rate * 100.0 + rho_val) + (sp.get("m1", 0.15) * Y_vals - curr_snap["X"]) / f_mob

    # Acotar visualmente para gráfica limpia
    r_IS_clipped = np.clip(r_IS, -5.0, 35.0)
    r_LM_clipped = np.clip(r_LM, -5.0, 35.0)
    r_BP_clipped = np.clip(r_BP, -5.0, 35.0)

    fig = go.Figure()

    # Curva IS
    fig.add_trace(go.Scatter(
        x=Y_vals, y=r_IS_clipped,
        mode="lines",
        name="Curva IS (Bienes)",
        line=dict(color="#2563eb", width=3),
        hovertemplate="PIB: %{x:.1f}<br>Tasa IS: %{y:.2f}%<extra></extra>"
    ))

    # Curva LM
    fig.add_trace(go.Scatter(
        x=Y_vals, y=r_LM_clipped,
        mode="lines",
        name="Curva LM (Dinero)",
        line=dict(color="#16a34a", width=3),
        hovertemplate="PIB: %{x:.1f}<br>Tasa LM: %{y:.2f}%<extra></extra>"
    ))

    # Curva BP
    fig.add_trace(go.Scatter(
        x=Y_vals, y=r_BP_clipped,
        mode="lines",
        name="Curva BP (Sector Externo)",
        line=dict(color="#dc2626", width=2.5, dash="dash"),
        hovertemplate="PIB: %{x:.1f}<br>Tasa BP: %{y:.2f}%<extra></extra>"
    ))

    # Punto de Equilibrio Actual
    fig.add_trace(go.Scatter(
        x=[Y_eq], y=[r_eq],
        mode="markers+text",
        name="Equilibrio Actual",
        text=["  Equilibrio (Y, r)"],
        textposition="top right",
        marker=dict(color="#0f172a", size=11, symbol="circle"),
        hovertemplate=f"Equilibrio Actual<br>PIB (Y): {Y_eq:.1f}<br>Tasa (r): {r_eq:.2f}%<extra></extra>"
    ))

    # Intentar proyectar punto con sliders actuales si hay diferencia
    try:
        dry_snap = state_mgr.get_dry_run_projection(state_mgr.current_instruments)
        if abs(dry_snap["Y"] - Y_eq) > 0.3 or abs(dry_snap["r"] - r_eq) > 0.1:
            fig.add_trace(go.Scatter(
                x=[dry_snap["Y"]], y=[dry_snap["r"]],
                mode="markers+text",
                name="Proyección t+1",
                text=["  Proyectado"],
                textposition="bottom right",
                marker=dict(color="#d97706", size=10, symbol="diamond"),
                hovertemplate=f"Proyección Sliders<br>PIB: {dry_snap['Y']:.1f}<br>Tasa: {dry_snap['r']:.2f}%<extra></extra>"
            ))
    except Exception:
        pass

    fig.update_layout(
        title="Modelo Macroeconómico IS-LM-BP de Economía Abierta",
        xaxis_title="Producto Interno Bruto Real (Y)",
        yaxis_title="Tasa de Interés Doméstica (r %)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=480,
        margin=dict(l=40, r=40, t=60, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "💡 **Interpretación**: La curva **IS** (azul) representa el equilibrio del mercado de bienes, la curva **LM** (verde) "
        "el mercado de saldos reales, y la curva **BP** (roja punteada) el equilibrio de la Balanza de Pagos."
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: DIAGRAMA SALTER-SWAN
# ─────────────────────────────────────────────────────────────────────────────

def _render_salter_swan_chart(state_mgr: StateManager) -> None:
    """Genera el gráfico del Diagrama Salter-Swan de 4 zonas y trayectoria histórica."""
    history = state_mgr.history
    curr = history[-1]
    sp = state_mgr.current_params

    A_curr = curr["A_domestic"]
    q_curr = curr["q_real"]

    A_range = np.linspace(50.0, 160.0, 120)

    # Pendientes derivadas en Salter-Swan
    tc_eff = curr["policy_applied"].get("tc", 0.16)
    slope_num_IB = 1.0 - sp.get("c1", 0.65) * (1.0 - tc_eff) + sp.get("m1", 0.15)
    slope_den = max(sp.get("epsilon_x", 1.2), 0.1)

    scale_factor = 1.0 / 100.0
    slope_IB = (-slope_num_IB / slope_den) * scale_factor
    slope_EB = (sp.get("m1", 0.15) / slope_den) * scale_factor

    q_IB = 1.0 + slope_IB * (A_range - 100.0)
    q_EB = 1.0 + slope_EB * (A_range - 100.0)

    fig = go.Figure()

    # Zonas de fondo sombreadas
    # Zona I: Inflación + Superávit (Arriba derecha)
    # Zona II: Desempleo + Superávit (Arriba izquierda)
    # Zona III: Desempleo + Déficit (Abajo izquierda)
    # Zona IV: Inflación + Déficit (Abajo derecha)

    fig.add_trace(go.Scatter(
        x=A_range, y=q_IB,
        mode="lines",
        name="IB: Balance Interno (Pleno Empleo)",
        line=dict(color="#2563eb", width=2.5),
        hoverinfo="skip"
    ))

    fig.add_trace(go.Scatter(
        x=A_range, y=q_EB,
        mode="lines",
        name="EB: Balance Externo (Cuenta Corriente = 0)",
        line=dict(color="#059669", width=2.5),
        hoverinfo="skip"
    ))

    # Trayectoria histórica de turnos (t=0..actual)
    A_hist = [s["A_domestic"] for s in history]
    q_hist = [s["q_real"] for s in history]
    t_labels = [f"t={s['t']}" for s in history]

    fig.add_trace(go.Scatter(
        x=A_hist, y=q_hist,
        mode="lines+markers",
        name="Trayectoria del País",
        line=dict(color="#64748b", width=2, dash="dot"),
        marker=dict(size=8, color="#0f172a"),
        text=t_labels,
        hovertemplate="Turno: %{text}<br>Absorción (A): %{x:.1f}<br>TCR (q): %{y:.2f}<extra></extra>"
    ))

    # Punto Actual Destacado
    fig.add_trace(go.Scatter(
        x=[A_curr], y=[q_curr],
        mode="markers",
        name="Posición Actual",
        marker=dict(size=14, color="#dc2626", symbol="star"),
        hovertemplate=f"Posición Actual (t={curr['t']})<br>A: {A_curr:.1f}<br>q: {q_curr:.2f}<extra></extra>"
    ))

    # Anotaciones de las 4 Zonas
    fig.add_annotation(x=70, y=1.35, text="<b>ZONA II</b><br>Desempleo + Superávit", showarrow=False, font=dict(color="#047857", size=10))
    fig.add_annotation(x=130, y=1.35, text="<b>ZONA I</b><br>Inflación + Superávit", showarrow=False, font=dict(color="#b45309", size=10))
    fig.add_annotation(x=70, y=0.65, text="<b>ZONA III</b><br>Desempleo + Déficit", showarrow=False, font=dict(color="#b91c1c", size=10))
    fig.add_annotation(x=130, y=0.65, text="<b>ZONA IV</b><br>Inflación + Déficit", showarrow=False, font=dict(color="#6b21a8", size=10))

    fig.update_layout(
        title=f"Diagrama Salter-Swan — Cuadrante Actual: Zona {curr.get('zone_ss', 'I')}",
        xaxis_title="Absorción Doméstica (A = C + I + G)",
        yaxis_title="Tipo de Cambio Real (q)",
        xaxis=dict(range=[55, 145]),
        yaxis=dict(range=[0.50, 1.50]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=480,
        margin=dict(l=40, r=40, t=60, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "⚖️ **Diagnóstico Salter-Swan**: El eje horizontal mide el gasto doméstico total y el eje vertical la competitividad cambiaria. "
        "El objetivo didáctico es converger hacia la intersección central de balance simultáneo interno y externo."
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: TRILEMA DE MUNDELL-FLEMING
# ─────────────────────────────────────────────────────────────────────────────

def _render_trilemma_chart(state_mgr: StateManager) -> None:
    """Genera el gráfico interactivo del Trilema de Mundell-Fleming."""
    curr = state_mgr.history[-1]
    regime = curr["policy_applied"].get("regime", "fixed")

    # Coordenadas de los 3 vértices del triángulo equilátero
    # Vértice A (Superior): Libre Movilidad de Capitales
    # Vértice B (Inferior Izq): Tipo de Cambio Fijo
    # Vértice C (Inferior Der): Autonomía Monetaria
    vx = [0.5, 0.0, 1.0, 0.5]
    vy = [0.866, 0.0, 0.0, 0.866]

    fig = go.Figure()

    # Marco del triángulo base
    fig.add_trace(go.Scatter(
        x=vx, y=vy,
        mode="lines",
        line=dict(color="#cbd5e1", width=3),
        hoverinfo="skip",
        showlegend=False
    ))

    # Determinar qué lado está activo según el régimen
    # Fixed: Libre movilidad + TC Fijo -> Pérdida de Autonomía Monetaria (Lado Izquierdo)
    # Flexible: Libre movilidad + Autonomía Monetaria -> TC Flotante (Lado Derecho)
    # Crawling / Controles: TC Semi-Fijo + Autonomía -> Menor movilidad (Lado Inferior)
    if regime == "fixed":
        active_side_x = [0.5, 0.0]
        active_side_y = [0.866, 0.0]
        active_label = "Lado Activo: TC Fijo + Libre Movilidad"
        sacrificed = "Sacrificio: Autonomía Monetaria (TPM subordinada a defender el tipo de cambio)"
        active_color = "#2563eb"
    elif regime == "flexible":
        active_side_x = [0.5, 1.0]
        active_side_y = [0.866, 0.0]
        active_label = "Lado Activo: Autonomía Monetaria + Libre Movilidad"
        sacrificed = "Sacrificio: Estabilidad Cambiaria Nominal (el tipo de cambio flota según el mercado)"
        active_color = "#059669"
    else:  # crawling_peg
        active_side_x = [0.0, 1.0]
        active_side_y = [0.0, 0.0]
        active_label = "Lado Activo: TC Regulado + Autonomía Parcial"
        sacrificed = "Sacrificio: Autonomía Parcial (requiere intervenir reservas y coordinar crawl)"
        active_color = "#d97706"

    # Dibujar arista activa iluminada
    fig.add_trace(go.Scatter(
        x=active_side_x, y=active_side_y,
        mode="lines",
        name=active_label,
        line=dict(color=active_color, width=6),
        hoverinfo="skip"
    ))

    # Puntos de los vértices
    v_colors = [
        "#0f172a",  # Libre Movilidad
        active_color if regime in ("fixed", "crawling_peg") else "#94a3b8",
        active_color if regime in ("flexible", "crawling_peg") else "#94a3b8",
    ]

    fig.add_trace(go.Scatter(
        x=[0.5, 0.0, 1.0],
        y=[0.866, 0.0, 0.0],
        mode="markers+text",
        marker=dict(size=[18, 18, 18], color=v_colors),
        text=[
            "<b>1. Libre Movilidad de Capitales</b>",
            "<b>2. Tipo de Cambio Fijo</b>",
            "<b>3. Autonomía Monetaria (TPM)</b>"
        ],
        textposition=["top center", "bottom center", "bottom center"],
        hoverinfo="skip",
        showlegend=False
    ))

    fig.update_layout(
        title="Trilema de Mundell-Fleming — Régimen Actual: " + regime.upper(),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.2, 1.2]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.2, 1.05]),
        template="plotly_white",
        height=440,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f"""
        <div style="background-color: #f1f5f9; border-radius: 6px; padding: 12px 16px; margin-top: -10px;">
            <strong>Principio del Trilema Imposible:</strong><br>
            Una economía solo puede escoger <strong>dos de los tres vértices</strong> simultáneamente.<br>
            <span style="color: {active_color}; font-weight: bold;">• Vértices Activos:</span> {active_label}.<br>
            <span style="color: #dc2626; font-weight: bold;">• Trade-off Ineludible:</span> {sacrificed}.
        </div>
        """,
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: EVOLUCIÓN TEMPORAL (10 TURNOS)
# ─────────────────────────────────────────────────────────────────────────────

def _render_timeline_chart(history: List[TurnSnapshot]) -> None:
    """Genera series temporales interactivas de los 10 turnos jugados."""
    if len(history) < 1:
        st.info("Avanza al menos un turno para observar la serie histórica.")
        return

    turns = [s["t"] for s in history]
    Y_vals = [s["Y"] for s in history]
    Y_pot_vals = [s["Y_pot"] for s in history]
    pi_vals = [s["pi"] * 100.0 for s in history]
    U_vals = [s["U"] * 100.0 for s in history]
    debt_vals = [s["debt_to_gdp_nominal"] * 100.0 for s in history]
    reserves_vals = [s["R"] for s in history]

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "PIB Real vs. PIB Potencial",
            "Inflación vs. Meta (3.0%)",
            "Tasa de Desempleo vs. NAIRU",
            "Deuda / PIB Nominal (%) y Reservas (MUSD)"
        )
    )

    # 1. PIB Real vs Potencial
    fig.add_trace(go.Scatter(x=turns, y=Y_vals, name="PIB Real (Y)", line=dict(color="#2563eb", width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=turns, y=Y_pot_vals, name="PIB Potencial", line=dict(color="#64748b", dash="dash")), row=1, col=1)

    # 2. Inflación vs Meta
    fig.add_trace(go.Scatter(x=turns, y=pi_vals, name="Inflación (%)", line=dict(color="#dc2626", width=2.5)), row=1, col=2)
    fig.add_trace(go.Scatter(x=turns, y=[3.0]*len(turns), name="Meta Central (3%)", line=dict(color="#16a34a", dash="dot")), row=1, col=2)

    # 3. Desempleo vs NAIRU
    fig.add_trace(go.Scatter(x=turns, y=U_vals, name="Desempleo (%)", line=dict(color="#d97706", width=2.5)), row=2, col=1)

    # 4. Deuda y Reservas
    fig.add_trace(go.Scatter(x=turns, y=debt_vals, name="Deuda/PIB Nom (%)", line=dict(color="#7c3aed", width=2.5)), row=2, col=2)
    fig.add_trace(go.Scatter(x=turns, y=reserves_vals, name="Reservas (MUSD)", line=dict(color="#059669", dash="dash")), row=2, col=2)

    fig.update_layout(
        height=500,
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=70, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)
