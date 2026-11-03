"""
ui_simple/explanation_panel.py
===============================
Panel narrativo: Gabinete Económico, Consejo Salter-Swan y Periódico del Día (Columna Derecha: ~25%).
Edición: The Economic War Room (V1.2 SIMPLE).

Incluye:
- Periódico El Observador Macroeconómico con titulares dinámicos adaptados a la coyuntura.
- Tarjetas fijas socráticas de los 3 Asesores Ministeriales:
  1. 🏦 Banco Central (Monetario & Cambiario)
  2. 🏛️ Ministerio de Hacienda (Fiscal & Deuda)
  3. 🏭 Ministerio de Trabajo y Comercio (Empleo & Sector Externo)
- Resumen pedagógico del Diagnóstico Salter-Swan.
"""

from __future__ import annotations

import re
import streamlit as st
from config_simple.parameters import TurnSnapshot
from engine_simple.advisor import CabinetAdvice
from engine_simple.state_manager import StateManager


def _md_to_html_bold(text: str) -> str:
    """Convierte marcas **texto** de markdown a <b>texto</b> para renderizado en HTML seguro."""
    if not text:
        return ""
    return re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)


def render_explanation_panel(state_mgr: StateManager) -> None:
    """
    Renderiza la columna derecha (~25% ancho) con los informes de prensa y dictámenes ministeriales.
    """
    st.markdown("### 📰 Informes y Asesoría")

    history = state_mgr.history
    if not history:
        return

    curr_snap = history[-1]

    # Obtenemos las recomendaciones del Gabinete basadas en los instrumentos actuales
    advice: CabinetAdvice = state_mgr.get_cabinet_advice(curr_snap["policy_applied"])

    # ─────────────────────────────────────────────────────────────────────────
    # 1. PERIÓDICO DEL DÍA: EL OBSERVADOR MACROECONÓMICO
    # ─────────────────────────────────────────────────────────────────────────
    _render_newspaper(curr_snap, advice)

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. DICTAMEN SOCRÁTICO DEL GABINETE ECONÓMICO
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("#### 🗣️ Asesores de Gabinete")

    with st.container():
        # 1. Banco Central
        st.markdown(
            f"""
            <div class="advisor-card advisor-cb">
                <div class="advisor-title">🏦 Banco Central (Monetario & Cambiario)</div>
                <div style="font-size: 0.83rem; line-height: 1.4;">{_md_to_html_bold(advice['central_bank'])}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 2. Ministerio de Hacienda
        st.markdown(
            f"""
            <div class="advisor-card advisor-treasury">
                <div class="advisor-title">🏛️ Ministerio de Hacienda (Fiscal & Deuda)</div>
                <div style="font-size: 0.83rem; line-height: 1.4;">{_md_to_html_bold(advice['treasury'])}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 3. Ministerio de Trabajo y Comercio
        st.markdown(
            f"""
            <div class="advisor-card advisor-labor">
                <div class="advisor-title">🏭 Trabajo y Comercio (Empleo & Competitividad)</div>
                <div style="font-size: 0.83rem; line-height: 1.4;">{_md_to_html_bold(advice['labor_growth'])}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 4. Diagnóstico Salter-Swan
        st.markdown(
            f"""
            <div class="advisor-card advisor-ss">
                <div class="advisor-title">⚖️ Brújula Salter-Swan</div>
                <div style="font-size: 0.83rem; line-height: 1.4;">{_md_to_html_bold(advice['salter_swan'])}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


def _render_newspaper(snapshot: TurnSnapshot, advice: CabinetAdvice) -> None:
    """Renderiza la caja visual del periódico con titulares dinámicos."""
    turn_num = snapshot["t"]
    gY_pct = snapshot["gY"] * 100.0
    pi_pct = snapshot["pi"] * 100.0
    U_pct = snapshot["U"] * 100.0
    debt_nominal_pct = snapshot.get("debt_to_gdp_nominal", 0.20) * 100.0
    reserves_val = snapshot["R"]
    score = snapshot["score"]

    if turn_num == 0:
        headline = "🏛️ NUEVO GABINETE ECONÓMICO ASUME LA CONDUCCIÓN DEL PAÍS"
        body = (
            "El recién investido Ministro toma las riendas del gabinete económico. "
            "El país inicia su programa de desarrollo bajo la estricta mirada de los mercados y la ciudadanía."
        )
    else:
        # Priorización de noticias por impacto
        if snapshot.get("events_triggered"):
            ev_name = ", ".join(snapshot["events_triggered"])
            headline = f"⚡ IMPACTO HISTÓRICO: {ev_name.upper()}"
        elif pi_pct > 35.0:
            headline = "🔥 ALERTA MÁXIMA: ESPIRAL DE PRECIOS SACUDE AL PAÍS"
        elif reserves_val < 8.0:
            headline = "🚨 PELIGRO EXTERNO: LAS RESERVAS DEL BANCO CENTRAL SE AGOTAN"
        elif debt_nominal_pct > 135.0:
            headline = "⚠️ ALARMA FISCAL: LA DEUDA PÚBLICA ROZA NIVELES DE DEFAULT"
        elif U_pct > 15.0:
            headline = "📉 CRISIS LABORAL: EL DESEMPLEO DESATA FUERTE MALESTAR SOCIAL"
        elif gY_pct < -5.0:
            headline = "⚠️ RECESIÓN SEVERA: LA ACTIVIDAD ECONÓMICA SE CONTRAE"
        elif gY_pct > 4.0 and pi_pct < 4.5:
            headline = "🚀 EXPANSIÓN SÓLIDA: EL PIB CRECE CON ESTABILIDAD MONETARIA"
        else:
            headline = f"📰 EDICIÓN DEL TURNO {turn_num}: RUMBO MACROECONÓMICO ESTABLE"

        body = (
            f"En este período, el PIB varió un <b>{gY_pct:+.1f}%</b>. "
            f"La inflación se registró en <b>{pi_pct:.1f}%</b>, el desempleo en <b>{U_pct:.1f}%</b> "
            f"y las reservas se sitúan en <b>{reserves_val:.1f} MUSD</b>. "
            f"La aprobación ciudadana se ubica en <b>{score:.1f} / 100 puntos</b>."
        )

    st.markdown(
        f"""
        <div class="newspaper-box">
            <div class="newspaper-header">EL OBSERVADOR MACROECONÓMICO</div>
            <div class="newspaper-date">Turno {turn_num} de 10 — Edición Oficial</div>
            <div class="newspaper-headline">{headline}</div>
            <div class="newspaper-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
