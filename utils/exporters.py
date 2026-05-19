"""
utils/exporters.py
==================
Exportación avanzada de sesiones de simulación para Fase 4.

Funciones públicas:
    export_full_session(state_manager, fmt) → bytes
    export_chart_as_png(fig, filename)    → bytes | None
    generate_scenario_summary(state_manager) → str
"""

from __future__ import annotations

import io
import json
from datetime import datetime

import pandas as pd


def export_full_session(state_manager, fmt: str = "csv") -> bytes:
    """
    Exporta la sesión completa de estados del EconomicStateManager.

    Parameters
    ----------
    state_manager : EconomicStateManager
        Instancia con los estados guardados.
    fmt : "csv" | "parquet" | "json"

    Returns
    -------
    bytes : Contenido listo para st.download_button()
    """
    return state_manager.export_trajectory(fmt=fmt)


def export_chart_as_png(fig, filename: str = "chart") -> bytes | None:
    """
    Exporta un gráfico Plotly como PNG usando kaleido.

    Parameters
    ----------
    fig      : go.Figure — gráfico Plotly
    filename : str — nombre base del archivo (sin extensión)

    Returns
    -------
    bytes | None : Bytes PNG, o None si kaleido no está disponible.
    """
    try:
        import plotly.io as pio
        png_bytes = pio.to_image(fig, format="png", width=1200, height=700, scale=2)
        return png_bytes
    except Exception:
        # kaleido no instalado o error de rendering
        return None


def generate_scenario_summary(state_manager) -> str:
    """
    Genera un texto estructurado (Markdown) con el resumen de todos los estados
    de la sesión, listo para copiar/pegar en un informe.

    Parameters
    ----------
    state_manager : EconomicStateManager

    Returns
    -------
    str : Resumen en Markdown.
    """
    states = state_manager.to_summary_dict()
    now    = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Resumen de Análisis — Simulador Macroeconómico Abierto",
        f"*Generado: {now}*",
        "",
        "---",
        "",
        f"## Trayectoria ({len(states)} estados guardados)",
        "",
    ]

    if not states:
        lines.append("*No hay estados guardados en esta sesión.*")
        return "\n".join(lines)

    # Tabla resumen
    lines += [
        "| # | Estado | Régimen | Y | r | NX | Mult. | G | Timestamp |",
        "|---|--------|---------|---|---|----|-------|---|-----------|",
    ]
    for i, s in enumerate(states, 1):
        Y    = f"{s['Y']:.2f}"    if not _isnan(s['Y'])    else "—"
        r    = f"{s['r']:.2f}%"  if not _isnan(s['r'])    else "—"
        NX   = f"{s['NX']:.2f}"  if not _isnan(s['NX'])   else "—"
        mult = f"{s['mult']:.3f}" if not _isnan(s['mult']) else "—"
        G    = f"{s['G']:.1f}"   if not _isnan(s['G'])    else "—"
        ts   = s.get("timestamp", "—")[:16] if s.get("timestamp") else "—"
        lines.append(
            f"| {i} | {s['label']} | {s['regime']} | {Y} | {r} | {NX} | {mult} | {G} | {ts} |"
        )

    # Análisis de trayectoria de Y
    y_values = [s["Y"] for s in states if not _isnan(s["Y"])]
    if len(y_values) >= 2:
        delta_y = y_values[-1] - y_values[0]
        pct_y   = (delta_y / y_values[0] * 100) if abs(y_values[0]) > 1e-9 else float("nan")
        direccion = "aumentó" if delta_y > 0 else "cayó"
        lines += [
            "",
            "---",
            "",
            "## Análisis de Trayectoria",
            "",
            f"- **PIB (Y)**: Pasó de {y_values[0]:.2f} a {y_values[-1]:.2f} "
            f"({direccion} {abs(delta_y):.2f} unidades, {pct_y:+.1f}%)",
        ]

        # Comparación primer vs último estado
        s0, sN = states[0], states[-1]
        lines += [
            f"- **Estado inicial**: {s0['label']} → **Estado final**: {sN['label']}",
        ]

    lines += [
        "",
        "---",
        "",
        "## Nota Metodológica",
        "",
        "Modelo Mundell-Fleming (1962) con movilidad perfecta de capitales.",
        "TC Fijo: política fiscal efectiva, monetaria ineficaz.",
        "TC Flexible: política monetaria efectiva, fiscal ineficaz.",
        "",
        "*Generado por el Simulador Macroeconómico Abierto — Fase 4*",
    ]

    return "\n".join(lines)


def generate_pdf_trajectory_data(state_manager) -> dict:
    """
    Prepara datos estructurados para integrarse con report/generator.py (fpdf2).

    Returns
    -------
    dict con:
        - 'states_df'   : pd.DataFrame con trayectoria completa
        - 'summary_text': str con resumen narrativo
        - 'count'       : int número de estados
    """
    df      = state_manager.get_trajectory_df()
    summary = generate_scenario_summary(state_manager)
    return {
        "states_df":    df,
        "summary_text": summary,
        "count":        state_manager.count(),
    }


# ── Helpers internos ──────────────────────────────────────────────────────────

def _isnan(val) -> bool:
    """Chequeo seguro de NaN para floats."""
    try:
        import math
        return math.isnan(float(val))
    except (TypeError, ValueError):
        return True
