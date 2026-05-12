"""
utils/export.py — Exportación de resultados del simulador.
Genera DataFrame comparativo base vs actual con deltas y botón de descarga.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import streamlit as st

_EXPORT_DIR = Path(__file__).parent.parent / ".scenarios"
_EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Unidades para cada variable del modelo
_UNITS: dict[str, str] = {
    "Y":      "unidades de PIB",
    "r":      "% anual",
    "E":      "unidades monetarias",
    "E_endo": "unidades monetarias",
    "M_endo": "unidades monetarias",
    "M":      "unidades monetarias",
    "NX":     "unidades de PIB",
    "C":      "unidades de PIB",
    "I":      "unidades de PIB",
    "mult":   "adimensional",
    "G":      "unidades de PIB",
    "T":      "unidades de PIB",
    "c1":     "adimensional",
    "m1":     "adimensional",
    "x1":     "adimensional",
    "b":      "adimensional",
    "k":      "adimensional",
    "h":      "adimensional",
}


def export_scenario(
    regime: str,
    params_base: dict[str, float],
    params_current: dict[str, float],
    eq_base: dict[str, float],
    eq_current: dict[str, float],
) -> pd.DataFrame:
    """
    Construye DataFrame comparativo: Variable | Valor_Base | Valor_Actual | Delta | Unidad.

    Parameters
    ----------
    regime        : "fixed" | "flexible"
    params_base   : Parámetros base del modelo.
    params_current: Parámetros actuales (después de sliders/presets).
    eq_base       : Resultado de eq_fixed/flexible con parámetros base.
    eq_current    : Resultado de eq_fixed/flexible con parámetros actuales.

    Returns
    -------
    pd.DataFrame con columnas: Variable, Valor_Base, Valor_Actual, Delta, Unidad.
    """
    # Variables de equilibrio a comparar
    if regime == "fixed":
        eq_vars = {
            "Y (PIB)":              ("Y",      eq_base,     eq_current),
            "r (tasa de interés)":  ("r",      eq_base,     eq_current),
            "E (tipo de cambio)":   ("E",      eq_base,     eq_current),
            "M endógena":           ("M_endo", eq_base,     eq_current),
            "NX (exp. netas)":      ("NX",     eq_base,     eq_current),
            "C (consumo)":          ("C",      eq_base,     eq_current),
            "I (inversión)":        ("I_inv",  eq_base,     eq_current),
            "Multiplicador":        ("mult",   eq_base,     eq_current),
        }
    else:
        eq_vars = {
            "Y (PIB)":              ("Y",      eq_base,     eq_current),
            "r (tasa de interés)":  ("r",      eq_base,     eq_current),
            "E endógeno":           ("E_endo", eq_base,     eq_current),
            "M (oferta monetaria)": ("M",      eq_base,     eq_current),
            "NX (exp. netas)":      ("NX",     eq_base,     eq_current),
            "C (consumo)":          ("C",      eq_base,     eq_current),
            "I (inversión)":        ("I_inv",  eq_base,     eq_current),
            "Multiplicador":        ("mult",   eq_base,     eq_current),
        }

    # Parámetros de política a incluir
    policy_vars = {
        "G (gasto público)":   ("G",  params_base, params_current),
        "T (impuestos)":       ("T",  params_base, params_current),
        "r* (tasa internacc.)": ("r_star", params_base, params_current),
    }
    if regime == "fixed":
        policy_vars["E nominal"] = ("E", params_base, params_current)
    else:
        policy_vars["M exógena"] = ("M", params_base, params_current)

    rows = []

    # Sección: parámetros de política
    for label, (key, d_base, d_curr) in policy_vars.items():
        v_base = d_base.get(key, float("nan"))
        v_curr = d_curr.get(key, float("nan"))
        rows.append({
            "Sección":      "Instrumentos de Política",
            "Variable":     label,
            "Valor_Base":   round(v_base, 4),
            "Valor_Actual": round(v_curr, 4),
            "Delta":        round(v_curr - v_base, 4),
            "Unidad":       _UNITS.get(key, ""),
        })

    # Sección: resultados de equilibrio
    for label, (key, d_base, d_curr) in eq_vars.items():
        v_base = d_base.get(key, float("nan"))
        v_curr = d_curr.get(key, float("nan"))
        rows.append({
            "Sección":      "Equilibrio del Modelo",
            "Variable":     label,
            "Valor_Base":   round(v_base, 4),
            "Valor_Actual": round(v_curr, 4),
            "Delta":        round(v_curr - v_base, 4),
            "Unidad":       _UNITS.get(key, ""),
        })

    df = pd.DataFrame(rows)
    return df


def render_export_button(
    df: pd.DataFrame,
    regime: str,
    file_label: str = "macro_resultado",
) -> None:
    """
    Renderiza el botón de descarga CSV en Streamlit y guarda versión Parquet interna.

    Parameters
    ----------
    df         : DataFrame generado por export_scenario().
    regime     : "fixed" | "flexible".
    file_label : Prefijo del nombre de archivo.
    """
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Descargar Resultados (CSV)",
        data=csv_bytes,
        file_name=f"{file_label}_{regime}.csv",
        mime="text/csv",
        help="Descarga la tabla comparativa base vs actual con deltas.",
    )

    # Guardar versión Parquet interna para trazabilidad
    try:
        parquet_path = _EXPORT_DIR / f"export_{regime}_latest.parquet"
        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, str(parquet_path), compression="snappy")
    except Exception:
        pass  # No bloquear la UI si falla la escritura interna
