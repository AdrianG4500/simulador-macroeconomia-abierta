"""
ui_simple/styles.py
===================
Estilos CSS profesionales y didácticos para The Economic War Room (V1.3 SIMPLE).
Diseñado para máxima legibilidad tipográfica, alto contraste y visuales institucionales.
"""

from __future__ import annotations

import streamlit as st


def inject_custom_css() -> None:
    """Inyecta CSS en la sesión de Streamlit para una estética institucional y limpia."""
    css = """
    <style>
    /* Estilos del contenedor principal */
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        padding-left: 1.8rem;
        padding-right: 1.8rem;
        max-width: 100% !important;
    }

    /* Tarjetas de KPIs */
    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .kpi-title {
        font-size: 0.78rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    .kpi-value {
        font-size: 1.35rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 2px;
    }
    .kpi-delta {
        font-size: 0.75rem;
        font-weight: 500;
    }

    /* Badges de Score de Aprobación Ciudadana */
    .score-badge-high {
        background-color: #dcfce7;
        color: #166534;
        border: 1px solid #bbf7d0;
        padding: 3px 10px;
        border-radius: 16px;
        font-weight: 700;
        font-size: 0.82rem;
    }
    .score-badge-med {
        background-color: #fef9c3;
        color: #854d0e;
        border: 1px solid #fef08a;
        padding: 3px 10px;
        border-radius: 16px;
        font-weight: 700;
        font-size: 0.82rem;
    }
    .score-badge-low {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #fecaca;
        padding: 3px 10px;
        border-radius: 16px;
        font-weight: 700;
        font-size: 0.82rem;
    }

    /* Banner de Alerta Roja Crítica */
    .critical-alert-banner {
        background-color: #fef2f2;
        border-left: 5px solid #dc2626;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 14px;
        color: #991b1b;
        font-weight: 600;
        box-shadow: 0 2px 6px rgba(220, 38, 38, 0.1);
    }

    /* Periódico El Observador Macroeconómico (Alta Legibilidad) */
    .newspaper-box {
        background-color: #fdfbf7;
        border: 2px solid #0f172a;
        border-radius: 6px;
        padding: 16px 18px;
        margin-top: 6px;
        margin-bottom: 16px;
        font-family: 'Georgia', serif;
        box-shadow: 0 3px 10px rgba(0,0,0,0.08);
    }
    .newspaper-header {
        font-family: 'Times New Roman', serif;
        font-size: 1.25rem;
        font-weight: 800;
        text-transform: uppercase;
        text-align: center;
        border-bottom: 2px solid #0f172a;
        padding-bottom: 6px;
        margin-bottom: 8px;
        letter-spacing: 1.5px;
        color: #0f172a;
    }
    .newspaper-date {
        font-size: 0.78rem;
        font-style: italic;
        color: #64748b;
        text-align: right;
        margin-bottom: 8px;
    }
    .newspaper-headline {
        font-size: 1.15rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 8px;
        line-height: 1.35;
    }
    .newspaper-body {
        font-size: 0.95rem;
        color: #1e293b;
        line-height: 1.55;
    }

    /* Tarjetas de Asesores de Gabinete (Identidad Visual y Tipografía Aumentada) */
    .advisor-card {
        background-color: #ffffff;
        border-top: 1px solid #e2e8f0;
        border-right: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 14px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .advisor-cb { border-left: 5px solid #1e40af; }        /* Banco Central: Azul Marino */
    .advisor-treasury { border-left: 5px solid #d97706; }  /* Hacienda: Dorado / Ámbar */
    .advisor-labor { border-left: 5px solid #059669; }     /* Trabajo y Comercio: Verde Esmeralda */
    .advisor-ss { border-left: 5px solid #7c3aed; }        /* Salter-Swan: Púrpura Institucional */

    .advisor-title {
        font-size: 1.05rem;
        font-weight: 800;
        margin-bottom: 6px;
        color: #0f172a;
    }
    .advisor-body {
        font-size: 0.95rem;
        line-height: 1.5;
        color: #1e293b;
    }
    .advisor-alert-banner {
        background-color: #fee2e2;
        border: 1px solid #fca5a5;
        color: #991b1b;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.80rem;
        font-weight: 800;
        margin-bottom: 8px;
        display: inline-block;
        letter-spacing: 0.3px;
    }

    /* Inspector Macroeconómico de Beta-Testing */
    .debug-box {
        background-color: #0f172a;
        color: #38bdf8;
        border-radius: 6px;
        padding: 10px 14px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 0.82rem;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
