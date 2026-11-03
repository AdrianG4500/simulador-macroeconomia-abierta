"""
ui_simple/styles.py
===================
Estilos CSS profesionales y didácticos para The Economic War Room (V1.2 SIMPLE).
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

    /* Periódico El Observador Macroeconómico */
    .newspaper-box {
        background-color: #fdfbf7;
        border: 2px solid #1e293b;
        border-radius: 4px;
        padding: 14px;
        margin-top: 6px;
        margin-bottom: 14px;
        font-family: 'Georgia', serif;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.06);
    }
    .newspaper-header {
        font-family: 'Times New Roman', serif;
        font-size: 1.15rem;
        font-weight: 800;
        text-transform: uppercase;
        text-align: center;
        border-bottom: 2px solid #1e293b;
        padding-bottom: 5px;
        margin-bottom: 8px;
        letter-spacing: 1.5px;
        color: #0f172a;
    }
    .newspaper-date {
        font-size: 0.72rem;
        font-style: italic;
        color: #64748b;
        text-align: right;
        margin-bottom: 6px;
    }
    .newspaper-headline {
        font-size: 1.0rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 6px;
        line-height: 1.3;
    }
    .newspaper-body {
        font-size: 0.84rem;
        color: #334155;
        line-height: 1.4;
    }

    /* Tarjetas de Asesores de Gabinete */
    .advisor-card {
        background-color: #ffffff;
        border-left: 4px solid #3b82f6;
        border-top: 1px solid #e2e8f0;
        border-right: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 11px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .advisor-cb { border-left-color: #2563eb; }
    .advisor-treasury { border-left-color: #059669; }
    .advisor-labor { border-left-color: #d97706; }
    .advisor-ss { border-left-color: #7c3aed; }

    .advisor-title {
        font-size: 0.86rem;
        font-weight: 700;
        margin-bottom: 5px;
        color: #0f172a;
    }

    /* Inspector Macroeconómico de Beta-Testing */
    .debug-box {
        background-color: #0f172a;
        color: #38bdf8;
        border-radius: 6px;
        padding: 10px 14px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 0.80rem;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
