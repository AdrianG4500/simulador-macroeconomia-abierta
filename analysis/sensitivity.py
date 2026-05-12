"""
analysis/sensitivity.py — Análisis de sensibilidad del modelo Mundell-Fleming.

Incluye:
  - Barrido unidimensional (±20% por parámetro)
  - Gráfico Tornado (impacto relativo de cada parámetro sobre Y)
  - Monte Carlo placeholder via sklearn.ParameterSampler
"""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engine.core import eq_fixed, eq_flexible


# ── Configuración ─────────────────────────────────────────────────────────────

STRUCTURAL_PARAMS = ["c1", "m1", "x1", "b", "k", "h"]
POLICY_PARAMS_FIXED    = ["G", "T", "E", "r_star"]
POLICY_PARAMS_FLEXIBLE = ["G", "T", "M", "r_star"]

Regime = Literal["fixed", "flexible"]


# ── Barrido unidimensional ────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def run_parameter_sweep(
    base_params_frozen: str,           # JSON string para compatibilidad con cache_data
    regime: Regime = "fixed",
    param_names: tuple[str, ...] = tuple(STRUCTURAL_PARAMS),
    steps: int = 20,
    variation: float = 0.20,           # ±20% alrededor del valor base
) -> dict[str, pd.DataFrame]:
    """
    Barrido unidimensional: varía cada parámetro ±variation% con `steps` puntos,
    mantiene el resto en valor base, y registra (Y, r, E/M_endo) en cada punto.

    Parameters
    ----------
    base_params_frozen : JSON string de los parámetros base.
    regime             : "fixed" | "flexible".
    param_names        : Tuple de parámetros a variar.
    steps              : Puntos por parámetro.
    variation          : Fracción de variación (0.20 = ±20%).

    Returns
    -------
    dict[str, pd.DataFrame]
        Clave: nombre del parámetro.
        Valor: DataFrame con columnas [param_value, Y, r, E_or_M].
    """
    import json
    base_params = json.loads(base_params_frozen)

    eq_fn = eq_fixed if regime == "fixed" else eq_flexible
    end_key = "M_endo" if regime == "fixed" else "E_endo"

    results: dict[str, pd.DataFrame] = {}

    for param in param_names:
        base_val = base_params.get(param)
        if base_val is None or base_val == 0:
            continue

        lo = base_val * (1 - variation)
        hi = base_val * (1 + variation)
        values = np.linspace(lo, hi, steps)

        rows = []
        for v in values:
            p = dict(base_params)
            p[param] = float(v)
            try:
                eq = eq_fn(p)
                rows.append({
                    "param_value": round(float(v), 6),
                    "Y":           eq["Y"],
                    "r":           eq["r"],
                    end_key:       eq.get(end_key, float("nan")),
                })
            except Exception:
                rows.append({"param_value": float(v), "Y": float("nan"),
                             "r": float("nan"), end_key: float("nan")})

        results[param] = pd.DataFrame(rows)

    return results


# ── Gráfico Tornado ───────────────────────────────────────────────────────────

def plot_tornado_chart(
    sweep_results: dict[str, pd.DataFrame],
    target: str = "Y",
    base_value: float = 100.0,
    regime: str = "fixed",
) -> go.Figure:
    """
    Gráfico de barras horizontales (tornado) mostrando el rango de impacto
    de cada parámetro sobre la variable objetivo.

    Parameters
    ----------
    sweep_results : Output de run_parameter_sweep().
    target        : Variable objetivo ("Y", "r", "M_endo" / "E_endo").
    base_value    : Valor base de la variable objetivo para la línea de referencia.
    regime        : "fixed" | "flexible" (solo para etiquetas).

    Returns
    -------
    go.Figure
    """
    labels, lo_vals, hi_vals, impacts = [], [], [], []

    for param, df in sweep_results.items():
        col = target
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if series.empty:
            continue
        lo = series.min()
        hi = series.max()
        impact = hi - lo
        labels.append(param)
        lo_vals.append(lo)
        hi_vals.append(hi)
        impacts.append(impact)

    if not labels:
        fig = go.Figure()
        fig.update_layout(title=f"Sin datos para '{target}'")
        return fig

    # Ordenar por impacto descendente (más sensible arriba)
    order = sorted(range(len(labels)), key=lambda i: impacts[i], reverse=True)
    labels   = [labels[i]   for i in order]
    lo_vals  = [lo_vals[i]  for i in order]
    hi_vals  = [hi_vals[i]  for i in order]
    impacts  = [impacts[i]  for i in order]

    fig = go.Figure()

    # Barra negativa (caída desde base)
    fig.add_trace(go.Bar(
        name="Valor mínimo (−20%)",
        y=labels,
        x=[base_value - lo for lo in lo_vals],
        base=[lo - base_value for lo in lo_vals],
        orientation="h",
        marker_color="#ef4444",
        hovertemplate="Param: %{y}<br>Mín = %{base:.2f}<extra></extra>",
    ))
    # Barra positiva (subida desde base)
    fig.add_trace(go.Bar(
        name="Valor máximo (+20%)",
        y=labels,
        x=[hi - base_value for hi in hi_vals],
        base=[0] * len(labels),
        orientation="h",
        marker_color="#22c55e",
        hovertemplate="Param: %{y}<br>Máx = %{customdata:.2f}<extra></extra>",
        customdata=hi_vals,
    ))

    # Línea vertical en cero (= valor base)
    fig.add_vline(x=0, line_color="white", line_width=2, line_dash="solid")

    # Etiquetas de impacto
    for i, (label, impact) in enumerate(zip(labels, impacts)):
        fig.add_annotation(
            x=max(hi_vals[i] - base_value, abs(lo_vals[i] - base_value)) + 0.5,
            y=i,
            text=f"Δ={impact:.2f}",
            showarrow=False,
            font=dict(size=10),
            xanchor="left",
        )

    fig.update_layout(
        title=f"Análisis de Sensibilidad — Impacto en {target} ({regime})",
        xaxis=dict(
            title=f"Variación de {target} respecto al valor base ({base_value:.1f})",
            zeroline=True, zerolinecolor="white", zerolinewidth=2,
        ),
        yaxis=dict(title="Parámetro"),
        barmode="overlay",
        legend=dict(orientation="h", y=-0.18),
        margin=dict(l=60, r=120, t=55, b=70),
        plot_bgcolor="#111827",
        paper_bgcolor="#030712",
        font=dict(color="#f8fafc"),
    )
    return fig


# ── Monte Carlo Placeholder ───────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def run_monte_carlo_placeholder(
    base_params_frozen: str,
    regime: Regime = "fixed",
    n: int = 500,
    variation: float = 0.20,
) -> pd.DataFrame:
    """
    Simulación Monte Carlo via sklearn.utils.ParameterSampler.
    Muestrea n combinaciones de parámetros estructurales con distribución uniforme ±20%.

    Returns
    -------
    pd.DataFrame con columnas: Y, r, E_endo/M_endo y percentiles (p5, p50, p95).
    """
    import json
    from sklearn.utils import ParameterSampler

    base = json.loads(base_params_frozen)
    eq_fn   = eq_fixed if regime == "fixed" else eq_flexible
    end_key = "M_endo" if regime == "fixed" else "E_endo"

    param_grid = {
        p: list(map(float, np.linspace(
            base[p] * (1 - variation),
            base[p] * (1 + variation),
            50,
        )))
        for p in STRUCTURAL_PARAMS
        if p in base and base[p] != 0
    }

    sampler = ParameterSampler(param_grid, n_iter=n, random_state=42)

    rows = []
    for sample in sampler:
        p = dict(base)
        p.update({k: float(v) for k, v in sample.items()})
        # Validar que multiplicador sea positivo
        if (1 - p.get("c1", 0.75) + p.get("m1", 0.15)) <= 0:
            continue
        try:
            eq = eq_fn(p)
            rows.append({"Y": eq["Y"], "r": eq["r"], end_key: eq.get(end_key, float("nan"))})
        except Exception:
            pass

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Calcular percentiles
    summary_rows = []
    for col in df.columns:
        q5, q50, q95 = df[col].quantile([0.05, 0.50, 0.95])
        summary_rows.append({
            "Variable":       col,
            "P5 (pesimista)": round(q5,  3),
            "P50 (mediana)":  round(q50, 3),
            "P95 (optimista)":round(q95, 3),
            "Rango (P95−P5)": round(q95 - q5, 3),
        })

    return pd.DataFrame(summary_rows)


# ── Gráfico de línea para un parámetro ───────────────────────────────────────

def plot_sensitivity_line(
    sweep_df: pd.DataFrame,
    param_name: str,
    target: str = "Y",
    base_val: float = 0.0,
    base_y: float = 100.0,
) -> go.Figure:
    """
    Gráfico de línea: param_value en X, target en Y, con punto base marcado.
    """
    fig = go.Figure()
    fig.update_layout(
        title=f"Sensibilidad de {target} a variaciones en {param_name}",
        xaxis_title=param_name,
        yaxis_title=target,
        plot_bgcolor="#111827",
        paper_bgcolor="#030712",
        font=dict(color="#f8fafc"),
        margin=dict(l=50, r=20, t=55, b=60),
    )

    col = target if target in sweep_df.columns else sweep_df.columns[-1]
    fig.add_trace(go.Scatter(
        x=sweep_df["param_value"],
        y=sweep_df[col],
        mode="lines+markers",
        name=f"{target} vs {param_name}",
        line=dict(color="#fcd34d", width=2),
        marker=dict(size=4),
        hovertemplate=f"{param_name}=%{{x:.4f}}<br>{target}=%{{y:.3f}}<extra></extra>",
    ))

    # Punto base
    if base_val > 0:
        fig.add_vline(x=base_val, line_dash="dot", line_color="#94a3b8",
                      annotation_text="base", annotation_position="top right",
                      annotation_font_color="#94a3b8")
    if base_y > 0:
        fig.add_hline(y=base_y, line_dash="dot", line_color="#94a3b8")

    return fig
