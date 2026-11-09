"""
ui_simple/explanation_panel.py
===============================
Panel narrativo: Gabinete Económico, Brújula Salter-Swan y Periódico del Día (Columna Derecha: ~25%).
Edición: The Economic War Room (V1.3 SIMPLE — Realismo y Experiencia Didáctica).

Incluye:
- Periódico El Observador Macroeconómico con titulares dinámicos adaptados a la coyuntura.
- Tarjetas llamativas de los 3 Asesores Ministeriales con tipografía visible y banners de alerta temprana:
  1. 🏛️ Banco Central (Monetario, Cambiario e Inflación) — Azul Marino
  2. 💼 Ministerio de Hacienda (Fiscal, Presupuesto y Deuda) — Dorado / Ámbar
  3. 📈 Ministerio de Trabajo y Comercio (Empleo, Crecimiento y Sector Externo) — Verde Esmeralda
- Brújula Salter-Swan con prescripciones canónicas claras.
"""

from __future__ import annotations

import re
import streamlit as st
from config_simple.parameters import TurnSnapshot
from engine_simple.advisor import CabinetAdvice
from engine_simple.state_manager import StateManager


def _format_advisor_text(text: str) -> str:
    """Convierte marcas markdown básicas (**bold**, *italic*) a HTML seguro."""
    if not text:
        return ""
    # Convertir **texto** a <b>texto</b>
    formatted = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Convertir *texto* a <i>texto</i>
    formatted = re.sub(r"\*(.*?)\*", r"<i>\1</i>", formatted)
    return formatted


_md_to_html_bold = _format_advisor_text


def _build_advisor_card(card_class: str, title: str, body_text: str, alert_html: str = "") -> str:
    """
    Construye el HTML continuo de una tarjeta de asesor sin sangrías iniciales
    ni saltos de línea vacíos para evitar que Streamlit lo interprete como bloque de código Markdown.
    """
    parts = [
        f'<div class="advisor-card {card_class}">',
        f'<div class="advisor-title">{title}</div>',
    ]
    if alert_html:
        parts.append(alert_html)
    parts.append(f'<div class="advisor-body">{_format_advisor_text(body_text)}</div>')
    parts.append('</div>')
    return "".join(parts)


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
    # 2. DICTAMEN SOCRÁTICO DEL GABINETE ECONÓMICO (TARJETAS INSTITUCIONALES)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("#### 🗣️ Asesores de Gabinete")

    pi_pct = float(curr_snap["pi"]) * 100.0
    reserves_val = float(curr_snap["R"])
    debt_nominal_pct = float(curr_snap.get("debt_to_gdp_nominal", 0.20)) * 100.0
    deficit_val = float(curr_snap.get("deficit", 0.0))
    U_pct = float(curr_snap["U"]) * 100.0
    nx_val = float(curr_snap["NX"])

    # Detección de banderas de alerta temprana para ministros
    cb_alert = ""
    if pi_pct > 8.0 or reserves_val < 10.0:
        cb_alert = '<div class="advisor-alert-banner">⚠️ ALERTA: TENSIÓN EN PRECIOS O RESERVAS</div>'

    treasury_alert = ""
    if deficit_val > 5.0 or debt_nominal_pct > 80.0:
        treasury_alert = '<div class="advisor-alert-banner">⚠️ ALERTA: DÉFICIT FISCAL O ENDEUDAMIENTO</div>'

    labor_alert = ""
    if U_pct > 10.0 or nx_val < -3.0:
        labor_alert = '<div class="advisor-alert-banner">⚠️ ALERTA: TENSIÓN LABORAL O DÉFICIT EXTERNO</div>'

    with st.container():
        # 1. Banco Central
        st.markdown(
            _build_advisor_card(
                card_class="advisor-cb",
                title="🏛️ Banco Central (Monetario & Cambiario)",
                body_text=advice["central_bank"],
                alert_html=cb_alert,
            ),
            unsafe_allow_html=True,
        )

        # 2. Ministerio de Hacienda
        st.markdown(
            _build_advisor_card(
                card_class="advisor-treasury",
                title="💼 Ministerio de Hacienda (Fiscal & Deuda)",
                body_text=advice["treasury"],
                alert_html=treasury_alert,
            ),
            unsafe_allow_html=True,
        )

        # 3. Ministerio de Trabajo y Comercio
        st.markdown(
            _build_advisor_card(
                card_class="advisor-labor",
                title="📈 Trabajo y Comercio (Empleo & Sector Externo)",
                body_text=advice["labor_growth"],
                alert_html=labor_alert,
            ),
            unsafe_allow_html=True,
        )

        # 4. Diagnóstico Salter-Swan
        st.markdown(
            _build_advisor_card(
                card_class="advisor-ss",
                title="⚖️ Brújula Salter-Swan (Balance Interno/Externo)",
                body_text=advice["salter_swan"],
            ),
            unsafe_allow_html=True,
        )


def _render_newspaper(snapshot: TurnSnapshot, advice: CabinetAdvice) -> None:
    """Renderiza la caja visual del periódico con titulares dinámicos de alto impacto."""
    turn_num = snapshot["t"]
    gY_pct = float(snapshot["gY"]) * 100.0
    pi_pct = float(snapshot["pi"]) * 100.0
    U_pct = float(snapshot["U"]) * 100.0
    debt_nominal_pct = float(snapshot.get("debt_to_gdp_nominal", 0.20)) * 100.0
    reserves_val = float(snapshot["R"])
    score = float(snapshot["score"])

    if turn_num == 0:
        headline = "🏛️ NUEVO GABINETE ECONÓMICO ASUME LA CONDUCCIÓN DEL PAÍS"
        body = (
            "El recién investido Ministro toma las riendas de la política económica nacional. "
            "El país inicia su programa de gobierno bajo la atenta mirada de los mercados financieros y la ciudadanía."
        )
    else:
        # Priorización de noticias por impacto macroeconómico
        if snapshot.get("events_triggered"):
            ev_name = ", ".join(snapshot["events_triggered"])
            headline = f"⚡ SHOCK ECONÓMICO: {ev_name.upper()}"
        elif pi_pct > 35.0:
            headline = "🔥 ALERTA MÁXIMA: ESPIRAL DE PRECIOS SACUDE LA ECONOMÍA"
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
            f"En este período, el PIB real varió un <b>{gY_pct:+.1f}%</b>. "
            f"La inflación se registró en <b>{pi_pct:.1f}%</b> anual, el desempleo en <b>{U_pct:.1f}%</b> "
            f"y las reservas se sitúan en <b>{reserves_val:.1f} MUSD</b>. "
            f"El índice de percepción ciudadana se ubica en <b>{score:.1f} / 100 puntos</b>."
        )

    newspaper_html = "".join([
        '<div class="newspaper-box">',
        '<div class="newspaper-header">EL OBSERVADOR MACROECONÓMICO</div>',
        f'<div class="newspaper-date">Turno {turn_num} de 10 — Edición Oficial</div>',
        f'<div class="newspaper-headline">{headline}</div>',
        f'<div class="newspaper-body">{body}</div>',
        '</div>',
    ])
    st.markdown(newspaper_html, unsafe_allow_html=True)
