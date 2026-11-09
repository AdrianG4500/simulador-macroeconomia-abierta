"""
ui_simple/kpi_panel.py
======================
Panel de tarjetas de indicadores macroeconómicos (KPIs), Aprobación Ciudadana y Alertas.
Edición: The Economic War Room (V1.2 SIMPLE).

Incluye:
- Banner preventivo de Alerta Roja Crítica cuando una variable entra en zona de peligro.
- 8 Tarjetas KPI superiores estructuradas en 2 filas limpias.
- Indicador de Aprobación Ciudadana (Score 0-100) con badge semántico y Rating Crediticio.
"""

from __future__ import annotations

from typing import List

import streamlit as st
from config_simple.parameters import TurnSnapshot


def render_kpi_panel(history: List[TurnSnapshot]) -> None:
    """
    Renderiza la fila superior de tarjetas KPI y avisos de alerta en la Columna Central.
    """
    if not history:
        return

    curr = history[-1]
    prev = history[-2] if len(history) >= 2 else curr

    # ─────────────────────────────────────────────────────────────────────────
    # 0. BANNER DE ALERTA ROJA CRÍTICA (REGLA 1 ANTI-BUCLE)
    # ─────────────────────────────────────────────────────────────────────────
    if curr.get("red_alert_active", False):
        alert_msg = curr.get("red_alert_reason", "Situación macroeconómica en zona crítica.")
        st.markdown(
            f"""
            <div class="critical-alert-banner">
                <span style="font-size: 1.1rem; margin-right: 6px;">⚠️</span>
                <strong>ALERTA ROJA CRÍTICA DE GABINETE:</strong><br>
                <span style="font-size: 0.88rem; font-weight: normal;">{alert_msg}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Cálculo de Deltas y Formatos
    gY_str = f"{curr['gY']*100:+.1f}%" if curr["t"] > 0 else "Base"
    pi_delta_str = f"{(curr['pi'] - prev['pi'])*100:+.1f} pp" if curr["t"] > 0 else f"Meta: {curr['policy_applied'].get('pi_target', 0.03)*100:.1f}%"
    u_delta_str = f"{(curr['U'] - prev['U'])*100:+.1f} pp" if curr["t"] > 0 else f"NAIRU: 5.0%"
    gap_str = f"{curr['gap']*100:+.1f}%"
    debt_nominal_pct = curr.get("debt_to_gdp_nominal", (curr["B"] / curr["PIB_nominal"]) if curr.get("PIB_nominal", 0) > 0 else 0.0) * 100.0
    r_delta_str = f"{(curr['r'] - prev['r']):+.2f} pp" if curr["t"] > 0 else "TPM"
    q_str = f"{curr['q_real']:.2f}"
    reserves_delta = f"{(curr['R'] - prev['R']):+.1f}" if curr["t"] > 0 else "Base"

    st.markdown("### 📊 Indicadores Macroeconómicos Clave")

    # ─────────────────────────────────────────────────────────────────────────
    # FILA 1: PIB, BRECHA, INFLACIÓN, DESEMPLEO Y SCORE
    # ─────────────────────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns([1.1, 1.0, 1.0, 1.0, 1.3])

    with col1:
        st.metric(
            label="PIB Real (Y)",
            value=f"{curr['Y']:.1f}",
            delta=gY_str,
            help="Producto Interno Bruto resuelto analíticamente en forma cerrada (Y = C + I + G + NX)."
        )

    with col2:
        gap_color = "normal" if abs(curr["gap"]) < 0.03 else ("inverse" if curr["gap"] < -0.05 else "off")
        st.metric(
            label="Brecha Producto",
            value=gap_str,
            delta="Sobrecalentada" if curr["gap"] > 0.02 else ("Recesiva" if curr["gap"] < -0.02 else "Equilibrio"),
            help="Brecha entre PIB Real y PIB Potencial: (Y - Y_pot) / Y_pot."
        )

    with col3:
        st.metric(
            label="Inflación (π)",
            value=f"{curr['pi']*100:.1f}%",
            delta=pi_delta_str,
            delta_color="inverse",
            help="Inflación anual de 4 fuerzas (expectativas, demanda, pass-through y aranceles)."
        )

    with col4:
        st.metric(
            label="Desempleo (U)",
            value=f"{curr['U']*100:.1f}%",
            delta=u_delta_str,
            delta_color="inverse",
            help="Tasa de desempleo nacional según la Ley de Okun lineal."
        )

    with col5:
        # Tarjeta de Aprobación Ciudadana
        score_val = curr.get("score", 70.0)
        if score_val >= 70.0:
            badge_class = "score-badge-high"
            status_text = "Favorable"
        elif score_val >= 45.0:
            badge_class = "score-badge-med"
            status_text = "Aceptable"
        else:
            badge_class = "score-badge-low"
            status_text = "Crítico"

        st.markdown(
            f"""
            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px 12px; text-align: center;">
                <div style="font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Aprobación Ciudadana</div>
                <div style="font-size: 1.45rem; font-weight: 800; color: #0f172a; margin: 1px 0;">{score_val:.1f} / 100</div>
                <div style="margin-top: 2px;"><span class="{badge_class}">{status_text}</span></div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # FILA 2: TASA DE INTERÉS, TCR, DEUDA SOBRE PIB NOMINAL, RESERVAS Y RATING
    # ─────────────────────────────────────────────────────────────────────────
    col6, col7, col8, col9, col10 = st.columns([1.1, 1.0, 1.0, 1.0, 1.3])

    with col6:
        st.metric(
            label="💳 Tasa de Crédito en la Calle (r)",
            value=f"{curr['r']:.2f}%",
            delta=r_delta_str,
            help="Esta es la tasa real a la que los bancos comerciales prestan a las empresas y familias en la economía. Es igual a tu Tasa Objetivo del Banco Central (TPM) + el recargo por Riesgo País (ρ) y presiones cambiarias. Esta es la tasa que verdaderamente frena o estimula la inversión privada."
        )

    with col7:
        st.metric(
            label="TCR (q)",
            value=q_str,
            delta="Competitivo" if curr["q_real"] > 1.05 else ("Sobrevaluado" if curr["q_real"] < 0.95 else "Paridad"),
            help="Tipo de cambio real q = (E/10 · P*) / P_local. Normalizado en base E=10."
        )

    with col8:
        st.metric(
            label="Deuda / PIB Nom",
            value=f"{debt_nominal_pct:.1f}%",
            delta="Sostenible" if debt_nominal_pct < 60.0 else "Riesgo",
            delta_color="inverse" if debt_nominal_pct > 60.0 else "normal",
            help="Ratio de Deuda Pública sobre el PIB Nominal (B / (Y · P_local))."
        )

    with col9:
        st.metric(
            label="Reservas (R)",
            value=f"{curr['R']:.1f} MUSD",
            delta=reserves_delta,
            help="Stock de reservas internacionales del Banco Central en millones de dólares."
        )

    with col10:
        rating_val = curr.get("rating", "BBB")
        st.markdown(
            f"""
            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px 12px; text-align: center;">
                <div style="font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Rating Soberano</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #1e3a8a; margin: 2px 0;">{rating_val}</div>
                <div style="font-size: 0.72rem; color: #64748b;">Riesgo ρ: +{curr.get('rho', 0.5):.1f} pp</div>
            </div>
            """,
            unsafe_allow_html=True
        )
