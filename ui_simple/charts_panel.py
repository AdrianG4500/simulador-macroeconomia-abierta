"""
ui_simple/charts_panel.py
=========================
Gráficos interactivos Plotly del Simulador Macroeconómico (Columna Central).
Edición: The Economic War Room (V1.3 SIMPLE — Realismo y Experiencia Didáctica).

Incluye las 4 pestañas requeridas por master_spec.md y v1_3_enhancements_spec.md:
1. 📈 Modelo IS-LM-BP (Curvas IS, MP moderna, BP, equilibrio previo y desplazamientos proyectados en vivo).
2. ⚖️ Diagrama Salter-Swan (4 Cuadrantes Canónicos sombreados, curvas IB/EB, trayectoria histórica y proyección).
3. 🔺 Trilema Cambiario de Mundell-Fleming (Vértices activos y trade-offs estructurales).
4. 🕒 Evolución Temporal (6 paneles: PIB/Potencial, Inflación/Empleo, Balance Fiscal % PIB, Balanza de Pagos NX/KA, Deuda/Rating y Reservas).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from config_simple.parameters import TurnSnapshot
from engine_simple.core import compute_salter_swan
from engine_simple.state_manager import StateManager


def render_charts_panel(state_mgr: StateManager) -> None:
    """
    Renderiza el sistema de 4 Tabs con gráficos interactivos Plotly enriquecidos.
    """
    tab_islm, tab_ss, tab_trilemma, tab_timeline = st.tabs([
        "📈 Modelo IS-LM-BP",
        "⚖️ Diagrama Salter-Swan",
        "🔺 Trilema Cambiario",
        "🕒 Evolución Temporal",
    ])

    with tab_islm:
        _render_islmbp_chart(state_mgr)

    with tab_ss:
        _render_salter_swan_chart(state_mgr)

    with tab_trilemma:
        _render_trilemma_chart(state_mgr)

    with tab_timeline:
        _render_timeline_chart(state_mgr.history, state_mgr)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: MODELO IS-LM-BP (ENFOQUE MONETARIO MODERNO Y DESPLAZAMIENTOS EN VIVO)
# ─────────────────────────────────────────────────────────────────────────────

def _render_islmbp_chart(state_mgr: StateManager) -> None:
    """
    Genera el gráfico IS-LM-BP con enfoque moderno de tasa de interés (Regla MP),
    equilibrio del turno actual, equilibrio del turno anterior y proyección interactiva en vivo.
    """
    history = state_mgr.history
    curr_snap = history[-1]
    sp = state_mgr.current_params
    inst = curr_snap["policy_applied"]

    Y_eq = float(curr_snap["Y"])
    r_eq = float(curr_snap["r"])
    Y_pot = float(curr_snap.get("Y_pot", 100.0))

    # Dominio de producto alrededor del equilibrio
    Y_min = max(20.0, min(Y_eq, Y_pot) - 45.0)
    Y_max = max(Y_eq, Y_pot) + 55.0
    Y_vals = np.linspace(Y_min, Y_max, 250)

    # ── 1. Curva IS (Mercado de Bienes) ──
    # Y = k_m · [A_auto - b·(r - r0)] => r_IS = r0 + (A_auto - Y/km) / b
    km = max(float(curr_snap.get("mult", 1.7)), 0.1)
    b_sens = max(float(sp.get("b", 0.8)), 0.1)
    r0 = float(sp.get("r0", 5.0))

    A_auto_curr = (
        float(sp.get("c0", 12.0))
        + float(sp.get("I0", 16.0))
        + float(curr_snap["Gc"])
        + float(curr_snap["Ig"])
        + float(curr_snap["X"])
        - float(sp.get("m0", 6.0))
        + float(sp.get("epsilon_m", 1.1)) * (float(curr_snap["q_real"]) - 1.0)
    )
    r_IS_curr = r0 + (A_auto_curr - (Y_vals / km)) / b_sens

    # ── 2. Curva MP (Política Monetaria Moderna / Banco Central) ──
    # En macroeconomía moderna, el Banco Central fija la tasa operativa de política r = r_ref
    r_MP_curr = np.full_like(Y_vals, r_eq)

    # ── 3. Curva BP (Sector Externo / Balanza de Pagos) ──
    # r_BP = r* + rho + DeltaE^e + (m1·Y - X) / f
    f_mob = max(float(sp.get("f", 2.0)), 0.1)
    r_star = float(inst.get("r_star", 4.5))
    rho_val = float(curr_snap.get("rho", 0.5))
    crawl_rate = float(inst.get("crawl_rate", 0.0)) if inst.get("regime") == "crawling_peg" else 0.0
    m1_val = float(sp.get("m1", 0.15))
    X_val = float(curr_snap["X"])
    r_BP_curr = (r_star + crawl_rate * 100.0 + rho_val) + (m1_val * Y_vals - X_val) / f_mob

    # Acotar visualmente para mantener escala didáctica legible
    r_IS_plot = np.clip(r_IS_curr, -4.0, 32.0)
    r_BP_plot = np.clip(r_BP_curr, -4.0, 32.0)

    fig = go.Figure()

    # Curva IS Actual
    fig.add_trace(go.Scatter(
        x=Y_vals, y=r_IS_plot,
        mode="lines",
        name="Curva IS (Mercado de Bienes)",
        line=dict(color="#2563eb", width=3),
        hovertemplate="PIB: %{x:.1f}<br>Tasa IS: %{y:.2f}%<extra></extra>",
    ))

    # Curva MP Actual (Política Monetaria)
    fig.add_trace(go.Scatter(
        x=Y_vals, y=r_MP_curr,
        mode="lines",
        name="Regla MP (Tasa Banco Central)",
        line=dict(color="#16a34a", width=3),
        hovertemplate="Tasa de Referencia: %{y:.2f}%<extra></extra>",
    ))

    # Curva BP Actual (Balanza de Pagos)
    fig.add_trace(go.Scatter(
        x=Y_vals, y=r_BP_plot,
        mode="lines",
        name="Curva BP (Sector Externo)",
        line=dict(color="#dc2626", width=2.5, dash="dash"),
        hovertemplate="PIB: %{x:.1f}<br>Tasa BP: %{y:.2f}%<extra></extra>",
    ))

    # ── Equilibrio del Turno Anterior (t-1) si existe ──
    if len(history) > 1:
        prev_snap = history[-2]
        Y_prev = float(prev_snap["Y"])
        r_prev = float(prev_snap["r"])
        fig.add_trace(go.Scatter(
            x=[Y_prev], y=[r_prev],
            mode="markers+text",
            name=f"Equilibrio t={prev_snap['t']}",
            text=[f" t={prev_snap['t']}"],
            textposition="bottom left",
            marker=dict(color="#94a3b8", size=9, symbol="circle-open", line=dict(width=2, color="#64748b")),
            hovertemplate=f"Equilibrio Anterior (t={prev_snap['t']})<br>PIB: {Y_prev:.1f}<br>Tasa: {r_prev:.2f}%<extra></extra>",
        ))

    # ── Equilibrio Actual (Turno t) ──
    fig.add_trace(go.Scatter(
        x=[Y_eq], y=[r_eq],
        mode="markers+text",
        name=f"Equilibrio Actual (t={curr_snap['t']})",
        text=[f"  E_t ({Y_eq:.1f}, {r_eq:.2f}%)"],
        textposition="top right",
        marker=dict(color="#0f172a", size=12, symbol="circle"),
        hovertemplate=f"<b>Equilibrio Actual (t={curr_snap['t']})</b><br>PIB Real (Y): {Y_eq:.1f}<br>Tasa (r): {r_eq:.2f}%<extra></extra>",
    ))

    # ── Proyección Dinámica t+1 según Sliders del Panel Izquierdo ──
    try:
        dry_snap = state_mgr.get_dry_run_projection(state_mgr.current_instruments)
        Y_dry = float(dry_snap["Y"])
        r_dry = float(dry_snap["r"])

        # Si los sliders desplazan el equilibrio, graficar el nuevo punto y curvas proyectadas
        if abs(Y_dry - Y_eq) > 0.15 or abs(r_dry - r_eq) > 0.05:
            # Curva IS Proyectada
            km_dry = max(float(dry_snap.get("mult", 1.7)), 0.1)
            A_auto_dry = (
                float(sp.get("c0", 12.0))
                + float(sp.get("I0", 16.0))
                + float(dry_snap["Gc"])
                + float(dry_snap["Ig"])
                + float(dry_snap["X"])
                - float(sp.get("m0", 6.0))
                + float(sp.get("epsilon_m", 1.1)) * (float(dry_snap["q_real"]) - 1.0)
            )
            r_IS_dry = np.clip(r0 + (A_auto_dry - (Y_vals / km_dry)) / b_sens, -4.0, 32.0)
            fig.add_trace(go.Scatter(
                x=Y_vals, y=r_IS_dry,
                mode="lines",
                name="IS Proyectada (t+1)",
                line=dict(color="#60a5fa", width=2, dash="dot"),
                hoverinfo="skip",
            ))

            # Curva MP Proyectada
            fig.add_trace(go.Scatter(
                x=Y_vals, y=np.full_like(Y_vals, r_dry),
                mode="lines",
                name="MP Proyectada (t+1)",
                line=dict(color="#4ade80", width=2, dash="dot"),
                hoverinfo="skip",
            ))

            # Marcador de Proyección
            fig.add_trace(go.Scatter(
                x=[Y_dry], y=[r_dry],
                mode="markers+text",
                name="Proyección t+1",
                text=[f"  Proyectado ({Y_dry:.1f}, {r_dry:.2f}%)"],
                textposition="bottom right",
                marker=dict(color="#d97706", size=12, symbol="diamond"),
                hovertemplate=f"<b>Proyección con Sliders</b><br>PIB proyectado: {Y_dry:.1f}<br>Tasa proyectada: {r_dry:.2f}%<extra></extra>",
            ))
    except Exception:
        pass

    fig.update_layout(
        title=dict(
            text="<b>Modelo IS-LM-BP de Economía Abierta (Enfoque Tasa de Política)</b>",
            x=0.02,
            y=0.98,
            xanchor="left",
            yanchor="top",
            font=dict(size=14),
        ),
        xaxis_title="Producto Interno Bruto Real (Y)",
        yaxis_title="Tasa de Interés Doméstica (r %)",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            font=dict(size=10),
        ),
        template="plotly_white",
        height=500,
        margin=dict(l=45, r=45, t=50, b=80),
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📖 Guía de Interpretación: Modelo IS-LM-BP", expanded=False):
        st.markdown(
            """
            - **Curva IS (Azul):** Representa el equilibrio en el mercado de bienes ($Y = C + I + G + NX$). Tiene pendiente negativa porque una menor tasa de interés estimula la inversión privada y el consumo. Mover el gasto público ($G_c, I_g$) o los impuestos desplaza la curva horizontalmente.
            - **Regla MP (Verde):** Refleja la conducción moderna del Banco Central, que fija directamente la **Tasa de Política Monetaria (TPM)**. Subir la tasa desplaza esta línea hacia arriba, contrayendo el PIB.
            - **Curva BP (Roja Discontinua):** Representa el equilibrio externo ($NX + KA = 0$). Puntos por encima de la curva implican superávit de balanza de pagos (atracción de divisas); puntos por debajo implican déficit externo.
            - **Punto Diamante (Ámbar):** Muestra el impacto proyectado en tiempo real de los sliders que estás ajustando antes de avanzar el turno.
            """
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: DIAGRAMA SALTER-SWAN (CUADRANTES CANÓNICOS Y TRAYECTORIA HISTÓRICA)
# ─────────────────────────────────────────────────────────────────────────────

def _render_salter_swan_chart(state_mgr: StateManager) -> None:
    """
    Genera el Diagrama Salter-Swan riguroso particionando el espacio (A, q)
    en los 4 cuadrantes canónicos de manual macroeconómico con sombreado semitransparente.
    """
    history = state_mgr.history
    curr = history[-1]
    sp = state_mgr.current_params

    A_curr = float(curr["A_domestic"])
    q_curr = float(curr["q_real"])
    A_ref = float(curr.get("Y_pot", 100.0))
    q_ref = 1.0

    # Pendientes analíticas rigurosas derivadas en core.py
    tc_eff = float(curr["policy_applied"].get("tc", 0.16))
    c1 = float(sp.get("c1", 0.65))
    m1 = float(sp.get("m1", 0.15))
    eps_sum = max(float(sp.get("epsilon_x", 1.2)) + float(sp.get("epsilon_m", 1.0)), 1e-4)

    slope_num_IB = 1.0 - c1 * (1.0 - tc_eff) + m1
    scale_factor = q_ref / max(A_ref, 1.0)
    slope_IB = (-slope_num_IB / eps_sum) * scale_factor
    slope_EB = (m1 / eps_sum) * scale_factor

    # Dominio proporcional centrado en (A_ref, q_ref)
    A_min = max(25.0, A_ref - 55.0)
    A_max = A_ref + 55.0
    q_min = 0.42
    q_max = 1.58

    A_vals = np.linspace(A_min, A_max, 120)
    q_IB_vals = q_ref + slope_IB * (A_vals - A_ref)
    q_EB_vals = q_ref + slope_EB * (A_vals - A_ref)

    fig = go.Figure()

    # ── SOMBREADO CANÓNICO DE LOS 4 CUADRANTES MEDIANTE POLÍGONOS EXACTOS ──

    # 1. ZONA I: Inflación + Superávit (Arriba de IB y arriba de EB)
    # q > q_IB y q > q_EB (Región superior)
    poly_I_x = [A_min, A_ref, A_max, A_max, A_min]
    poly_I_y = [
        q_ref + slope_IB * (A_min - A_ref),
        q_ref,
        q_ref + slope_EB * (A_max - A_ref),
        q_max,
        q_max,
    ]
    fig.add_trace(go.Scatter(
        x=poly_I_x, y=poly_I_y,
        fill="toself",
        fillcolor="rgba(245, 158, 11, 0.12)",  # Ámbar suave
        line=dict(width=0),
        name="Zona I: Inflación + Superávit",
        hoverinfo="skip",
    ))

    # 2. ZONA II: Desempleo + Superávit (Abajo de IB y arriba de EB, cuadrante izquierdo)
    # Para A < A_ref: q_EB < q < q_IB
    poly_II_x = [A_min, A_ref, A_min]
    poly_II_y = [
        q_ref + slope_EB * (A_min - A_ref),
        q_ref,
        q_ref + slope_IB * (A_min - A_ref),
    ]
    fig.add_trace(go.Scatter(
        x=poly_II_x, y=poly_II_y,
        fill="toself",
        fillcolor="rgba(16, 185, 129, 0.12)",  # Verde esmeralda suave
        line=dict(width=0),
        name="Zona II: Desempleo + Superávit",
        hoverinfo="skip",
    ))

    # 3. ZONA III: Desempleo + Déficit (Abajo de IB y abajo de EB, región inferior de crisis)
    poly_III_x = [A_min, A_ref, A_max, A_max, A_min]
    poly_III_y = [
        q_ref + slope_EB * (A_min - A_ref),
        q_ref,
        q_ref + slope_IB * (A_max - A_ref),
        q_min,
        q_min,
    ]
    fig.add_trace(go.Scatter(
        x=poly_III_x, y=poly_III_y,
        fill="toself",
        fillcolor="rgba(239, 68, 68, 0.13)",  # Rojo coral suave
        line=dict(width=0),
        name="Zona III: Desempleo + Déficit (Crisis)",
        hoverinfo="skip",
    ))

    # 4. ZONA IV: Inflación + Déficit (Arriba de IB y abajo de EB, cuadrante derecho)
    # Para A > A_ref: q_IB < q < q_EB
    poly_IV_x = [A_ref, A_max, A_max]
    poly_IV_y = [
        q_ref,
        q_ref + slope_EB * (A_max - A_ref),
        q_ref + slope_IB * (A_max - A_ref),
    ]
    fig.add_trace(go.Scatter(
        x=poly_IV_x, y=poly_IV_y,
        fill="toself",
        fillcolor="rgba(139, 92, 246, 0.12)",  # Púrpura suave
        line=dict(width=0),
        name="Zona IV: Inflación + Déficit",
        hoverinfo="skip",
    ))

    # ── CURVAS ESTRUCTURALES IB Y EB ──
    fig.add_trace(go.Scatter(
        x=A_vals, y=q_IB_vals,
        mode="lines",
        name="IB: Balance Interno (Y = Y_pot)",
        line=dict(color="#1e40af", width=3),
        hovertemplate="Absorción (A): %{x:.1f}<br>TCR IB: %{y:.2f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=A_vals, y=q_EB_vals,
        mode="lines",
        name="EB: Balance Externo (NX = 0)",
        line=dict(color="#047857", width=3),
        hovertemplate="Absorción (A): %{x:.1f}<br>TCR EB: %{y:.2f}<extra></extra>",
    ))

    # ── TRAYECTORIA HISTÓRICA DEL PAÍS (t=0..actual) ──
    A_hist = [float(s["A_domestic"]) for s in history]
    q_hist = [float(s["q_real"]) for s in history]
    t_labels = [f"t={s['t']}" for s in history]

    fig.add_trace(go.Scatter(
        x=A_hist, y=q_hist,
        mode="lines+markers",
        name="Trayectoria del País",
        line=dict(color="#475569", width=2.5, dash="dashdot"),
        marker=dict(size=7, color="#1e293b"),
        text=t_labels,
        hovertemplate="<b>Turno %{text}</b><br>Absorción (A): %{x:.1f}<br>TCR (q): %{y:.2f}<extra></extra>",
    ))

    # ── POSICIÓN ACTUAL DESTACADA ──
    fig.add_trace(go.Scatter(
        x=[A_curr], y=[q_curr],
        mode="markers+text",
        name=f"Posición Actual (t={curr['t']})",
        text=[f"  Actual (t={curr['t']})"],
        textposition="top right",
        marker=dict(size=14, color="#b91c1c", symbol="star", line=dict(width=1.5, color="#7f1d1d")),
        hovertemplate=f"<b>Posición Actual (t={curr['t']})</b><br>Absorción A: {A_curr:.1f}<br>Tipo de Cambio Real q: {q_curr:.2f}<extra></extra>",
    ))

    # ── PROYECCIÓN t+1 CON SLIDERS ──
    try:
        dry_snap = state_mgr.get_dry_run_projection(state_mgr.current_instruments)
        A_dry = float(dry_snap["A_domestic"])
        q_dry = float(dry_snap["q_real"])
        if abs(A_dry - A_curr) > 0.3 or abs(q_dry - q_curr) > 0.02:
            fig.add_trace(go.Scatter(
                x=[A_dry], y=[q_dry],
                mode="markers+text",
                name="Proyección t+1",
                text=[f"  Proyectado t={curr['t']+1}"],
                textposition="bottom right",
                marker=dict(size=11, color="#d97706", symbol="diamond"),
                hovertemplate=f"<b>Proyección con Sliders (t={curr['t']+1})</b><br>A: {A_dry:.1f}<br>q: {q_dry:.2f}<extra></extra>",
            ))
    except Exception:
        pass

    # ── ANOTACIONES DIDÁCTICAS EN CADA CUADRANTE ──
    fig.add_annotation(
        x=A_ref, y=q_max - 0.10,
        text="<b>ZONA I</b><br>Inflación + Superávit",
        showarrow=False,
        font=dict(color="#b45309", size=10, family="sans-serif"),
    )
    fig.add_annotation(
        x=A_min + 15.0, y=q_ref + 0.02,
        text="<b>ZONA II</b><br>Desempleo + Superávit",
        showarrow=False,
        font=dict(color="#047857", size=10, family="sans-serif"),
    )
    fig.add_annotation(
        x=A_ref, y=q_min + 0.10,
        text="<b>ZONA III</b><br>Desempleo + Déficit (Crisis)",
        showarrow=False,
        font=dict(color="#b91c1c", size=10, family="sans-serif"),
    )
    fig.add_annotation(
        x=A_max - 15.0, y=q_ref - 0.02,
        text="<b>ZONA IV</b><br>Inflación + Déficit",
        showarrow=False,
        font=dict(color="#6b21a8", size=10, family="sans-serif"),
    )

    fig.update_layout(
        title=dict(
            text=f"<b>Diagrama Salter-Swan Canónico — Posición Actual: Zona {curr.get('zone_ss', 'I')}</b>",
            x=0.02,
            y=0.98,
            xanchor="left",
            yanchor="top",
            font=dict(size=14),
        ),
        xaxis_title="Absorción Doméstica Total (A = C + I_priv + G)",
        yaxis_title="Tipo de Cambio Real (q)",
        xaxis=dict(range=[A_min, A_max]),
        yaxis=dict(range=[q_min, q_max]),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            font=dict(size=10),
        ),
        template="plotly_white",
        height=500,
        margin=dict(l=45, r=45, t=50, b=80),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Diagnóstico del cuadrante actual
    ss_diag = compute_salter_swan(curr, sp, curr["G"], Y_pot=A_ref)
    badge_colors = {
        "I": "#fef3c7; color: #92400e; border: 1px solid #f59e0b",
        "II": "#d1fae5; color: #065f46; border: 1px solid #10b981",
        "III": "#fee2e2; color: #991b1b; border: 1px solid #ef4444",
        "IV": "#f3e8ff; color: #6b21a8; border: 1px solid #a855f7",
    }
    b_style = badge_colors.get(ss_diag["zone"], "#f1f5f9; color: #0f172a; border: 1px solid #cbd5e1")

    st.markdown(
        f"""
        <div style="background-color: {b_style}; border-radius: 6px; padding: 10px 16px; margin-top: -6px; margin-bottom: 10px;">
            <strong>Diagnóstico de Cuadrante ({ss_diag['diagnosis']}):</strong><br>
            💡 <em>Recomendación de Política:</em> {ss_diag['policy']}
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📖 Guía de Cuadrantes Salter-Swan", expanded=False):
        st.markdown(
            """
            El **Diagrama de Salter-Swan** analiza simultáneamente el **Equilibrio Interno** (pleno empleo) y el **Equilibrio Externo** (cuenta corriente equilibrada):
            - **Curva IB (Azul, Pendiente Negativa):** Puntos donde el producto iguala al potencial ($Y = Y_{\text{pot}}$). Puntos por encima de IB implican sobrecalentamiento e inflación; por debajo, desempleo y capacidad ociosa.
            - **Curva EB (Verde, Pendiente Positiva):** Puntos donde la balanza comercial está equilibrada ($NX = 0$). Puntos por encima de EB implican superávit en cuenta corriente; por debajo, déficit comercial.
            - **Objetivo Macroeconómico:** Llevar la estrella del país hacia el punto central de intersección, donde coexisten el pleno empleo y el balance de divisas sin crisis.
            """
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: TRILEMA DE MUNDELL-FLEMING
# ─────────────────────────────────────────────────────────────────────────────

def _render_trilemma_chart(state_mgr: StateManager) -> None:
    """Genera el gráfico interactivo del Trilema de Mundell-Fleming."""
    curr = state_mgr.history[-1]
    regime = curr["policy_applied"].get("regime", "fixed")

    vx = [0.5, 0.0, 1.0, 0.5]
    vy = [0.866, 0.0, 0.0, 0.866]

    fig = go.Figure()

    # Marco del triángulo base
    fig.add_trace(go.Scatter(
        x=vx, y=vy,
        mode="lines",
        line=dict(color="#cbd5e1", width=3),
        hoverinfo="skip",
        showlegend=False,
    ))

    # Determinar lado activo según el régimen cambiario
    if regime == "fixed":
        active_side_x = [0.5, 0.0]
        active_side_y = [0.866, 0.0]
        active_label = "Lado Activo: TC Fijo + Libre Movilidad"
        sacrificed = "Sacrificio: Autonomía Monetaria (La tasa de interés debe subordinarse a defender el tipo de cambio)"
        active_color = "#2563eb"
    elif regime == "flexible":
        active_side_x = [0.5, 1.0]
        active_side_y = [0.866, 0.0]
        active_label = "Lado Activo: Autonomía Monetaria + Libre Movilidad"
        sacrificed = "Sacrificio: Estabilidad Cambiaria Nominal (El tipo de cambio absorbe los desbalances externos fluctuando libremente)"
        active_color = "#059669"
    else:  # crawling_peg
        active_side_x = [0.0, 1.0]
        active_side_y = [0.0, 0.0]
        active_label = "Lado Activo: TC Regulado + Autonomía Parcial"
        sacrificed = "Sacrificio: Deslizamiento Cambiario Administrado (Requiere quemar o acumular reservas para sostener la pauta)"
        active_color = "#d97706"

    # Dibujar arista activa iluminada
    fig.add_trace(go.Scatter(
        x=active_side_x, y=active_side_y,
        mode="lines",
        name=active_label,
        line=dict(color=active_color, width=6),
        hoverinfo="skip",
    ))

    # Vértices institucionales
    v_colors = [
        "#0f172a",
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
            "<b>3. Autonomía Monetaria (TPM)</b>",
        ],
        textposition=["top center", "bottom center", "bottom center"],
        hoverinfo="skip",
        showlegend=False,
    ))

    fig.update_layout(
        title=f"<b>Trilema Imposible de Mundell-Fleming — Régimen: {regime.upper()}</b>",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.2, 1.2]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.2, 1.05]),
        template="plotly_white",
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f"""
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px 16px; margin-top: -8px;">
            <strong>Principio del Trilema Macroeconómico:</strong><br>
            Una economía abierta solo puede seleccionar <strong>dos de los tres vértices</strong> al mismo tiempo:<br>
            <span style="color: {active_color}; font-weight: bold;">• Vértices Activos:</span> {active_label}.<br>
            <span style="color: #dc2626; font-weight: bold;">• Costo Ineludible:</span> {sacrificed}.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: EVOLUCIÓN TEMPORAL EXPANDIDA (6 PANELES DIDÁCTICOS)
# ─────────────────────────────────────────────────────────────────────────────

def _render_timeline_chart(history: List[TurnSnapshot], state_mgr: Optional[StateManager] = None) -> None:
    """
    Genera series temporales interactivas completas de 10 turnos (6 paneles en 3 filas):
    1. PIB Real vs PIB Potencial (Brecha).
    2. Inflación (%) vs Desempleo (%) con metas centrales.
    3. Balance Fiscal (% del PIB) — Barras de Superávit (Verde) y Déficit (Rojo).
    4. Balanza de Pagos: Cuenta Corriente (NX) y Flujos de Capital (KA).
    5. Deuda Soberana / PIB Nominal (%) con Rating Crediticio y Piso del 10%.
    6. Reservas Internacionales (MUSD) y Umbrales de Seguridad.
    """
    if len(history) < 1:
        st.info("Avanza al menos un turno para observar la serie histórica.")
        return

    turns = [s["t"] for s in history]
    Y_vals = [float(s["Y"]) for s in history]
    Y_pot_vals = [float(s["Y_pot"]) for s in history]
    pi_vals = [float(s["pi"]) * 100.0 for s in history]
    U_vals = [float(s["U"]) * 100.0 for s in history]
    debt_vals = [float(s["debt_to_gdp_nominal"]) * 100.0 for s in history]
    reserves_vals = [float(s["R"]) for s in history]
    nx_vals = [float(s["NX"]) for s in history]
    ka_vals = [float(s["KA"]) for s in history]

    # Balance Fiscal (% PIB) y Balance Primario (% PIB)
    # déficit = Gasto - Recaudación => Balance Fiscal = -déficit
    pib_nom_vals = [max(float(s["PIB_nominal"]), 1.0) for s in history]
    fiscal_balance_pct = [(-float(s["deficit"]) / pib_nom_vals[i]) * 100.0 for i, s in enumerate(history)]
    ratings = [str(s.get("rating", "BBB")) for s in history]

    # Colores de barras fiscales: verde si superávit (>=0), rojo si déficit (<0)
    bar_colors = ["#10b981" if val >= 0 else "#ef4444" for val in fiscal_balance_pct]

    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            "1. PIB Real vs. PIB Potencial",
            "2. Inflación (%) y Desempleo (%)",
            "3. Balance Fiscal (% del PIB)",
            "4. Balanza de Pagos: Cta. Corriente (NX) vs. Capitales (KA)",
            "5. Deuda Soberana / PIB Nominal (%) y Rating",
            "6. Reservas Internacionales (MUSD)",
        ),
        vertical_spacing=0.10,
        horizontal_spacing=0.08,
    )

    # ── Panel 1: PIB Real vs Potencial ──
    fig.add_trace(go.Scatter(
        x=turns, y=Y_vals, name="PIB Real (Y)",
        line=dict(color="#2563eb", width=2.5),
        hovertemplate="Turno %{x}: PIB Real = %{y:.1f}<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=turns, y=Y_pot_vals, name="PIB Potencial",
        line=dict(color="#64748b", dash="dash"),
        hovertemplate="Turno %{x}: Potencial = %{y:.1f}<extra></extra>",
    ), row=1, col=1)

    # ── Panel 2: Inflación y Desempleo ──
    fig.add_trace(go.Scatter(
        x=turns, y=pi_vals, name="Inflación (%)",
        line=dict(color="#dc2626", width=2.5),
        hovertemplate="Turno %{x}: Inflación = %{y:.2f}%<extra></extra>",
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=turns, y=[3.0] * len(turns), name="Meta Inflación (3%)",
        line=dict(color="#16a34a", dash="dot"),
        hoverinfo="skip",
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=turns, y=U_vals, name="Desempleo (%)",
        line=dict(color="#d97706", width=2.5),
        hovertemplate="Turno %{x}: Desempleo = %{y:.2f}%<extra></extra>",
    ), row=1, col=2)

    # ── Panel 3: Balance Fiscal (% PIB) con Barras ──
    fig.add_trace(go.Bar(
        x=turns, y=fiscal_balance_pct,
        name="Balance Fiscal (% PIB)",
        marker=dict(color=bar_colors),
        hovertemplate="Turno %{x}: Balance = %{y:.2f}% del PIB<extra></extra>",
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=turns, y=[0.0] * len(turns), name="Equilibrio Fiscal (0%)",
        line=dict(color="#334155", width=1),
        hoverinfo="skip",
    ), row=2, col=1)

    # ── Panel 4: Balanza de Pagos (NX vs KA) ──
    fig.add_trace(go.Scatter(
        x=turns, y=nx_vals, name="Cuenta Corriente (NX)",
        line=dict(color="#0284c7", width=2.5),
        hovertemplate="Turno %{x}: NX = %{y:.2f} MUSD<extra></extra>",
    ), row=2, col=2)
    fig.add_trace(go.Scatter(
        x=turns, y=ka_vals, name="Flujos de Capital (KA)",
        line=dict(color="#ea580c", width=2.5, dash="dash"),
        hovertemplate="Turno %{x}: KA = %{y:.2f} MUSD<extra></extra>",
    ), row=2, col=2)
    fig.add_trace(go.Scatter(
        x=turns, y=[0.0] * len(turns), name="Equilibrio BP (0)",
        line=dict(color="#94a3b8", width=1),
        hoverinfo="skip",
    ), row=2, col=2)

    # ── Panel 5: Deuda / PIB Nominal (%) y Rating ──
    fig.add_trace(go.Scatter(
        x=turns, y=debt_vals, name="Deuda/PIB Nom (%)",
        mode="lines+markers+text",
        text=ratings,
        textposition="top center",
        textfont=dict(size=9, color="#6b21a8"),
        line=dict(color="#7c3aed", width=2.5),
        marker=dict(size=6, color="#581c87"),
        hovertemplate="Turno %{x}: Deuda = %{y:.1f}% PIB<br>Rating: %{text}<extra></extra>",
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=turns, y=[10.0] * len(turns), name="Piso Estructural Deuda (10%)",
        line=dict(color="#f59e0b", dash="dot"),
        hoverinfo="skip",
    ), row=3, col=1)

    # ── Panel 6: Reservas Internacionales y Umbrales ──
    fig.add_trace(go.Scatter(
        x=turns, y=reserves_vals, name="Reservas (MUSD)",
        line=dict(color="#059669", width=2.5),
        hovertemplate="Turno %{x}: Reservas = %{y:.2f} MUSD<extra></extra>",
    ), row=3, col=2)
    fig.add_trace(go.Scatter(
        x=turns, y=[10.0] * len(turns), name="Alerta Crítica Reservas (10 MUSD)",
        line=dict(color="#dc2626", dash="dot"),
        hoverinfo="skip",
    ), row=3, col=2)

    fig.update_layout(
        height=720,
        template="plotly_white",
        showlegend=False,  # Ocultar leyenda global saturada; hover detallado por traza
        margin=dict(l=45, r=45, t=50, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "💡 **Análisis de Series Históricas**: Superávits fiscales continuos (barras verdes) reducen la deuda hasta su piso del 10% "
        "y acumulan reservas adicionales (FSE). Los desbalances externos ($NX + KA$) determinan la trayectoria de las reservas internacionales."
    )
