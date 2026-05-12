"""
ui/charts.py — Gráficos Plotly interactivos para IS-LM-BP y Salter-Swan.
Funciones puras: reciben parámetros, retornan go.Figure.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from engine.core import autonomous_demand, is_curve, lm_curve


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def _compute_islm_curves(
    c0: float, c1: float, T: float, I0: float, G: float, NX0: float,
    b: float, x1: float, k: float, h: float, m1: float,
    E: float, M: float,
    Y_min: float = 30.0, Y_max: float = 190.0, n: int = 120,
) -> tuple[list[float], list[float], list[float]]:
    """
    Calcula vectores de r_IS, r_LM para un rango de Y.
    Cacheado por Streamlit para evitar recalculos innecesarios.
    """
    Y_arr = np.linspace(Y_min, Y_max, n).tolist()
    A = autonomous_demand(c0, c1, T, I0, G, NX0)
    r_IS = [is_curve(y, c1, m1, b, A, x1, E) for y in Y_arr]
    r_LM = [lm_curve(y, k, M, h) for y in Y_arr]
    return Y_arr, r_IS, r_LM


def _base_fig(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title="Ingreso / PIB (Y)", showgrid=True, gridcolor="#e5e5e5"),
        yaxis=dict(title="Tasa de Interés (r)", showgrid=True, gridcolor="#e5e5e5"),
        legend=dict(orientation="h", y=-0.2, x=0),
        hovermode="x unified",
        margin=dict(l=50, r=20, t=55, b=80),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# IS-LM-BP — TIPO DE CAMBIO FIJO
# ─────────────────────────────────────────────────────────────────────────────

def plot_islm_fixed(
    Y_eq: float,
    r_eq: float,
    params_base: dict[str, float],
    params_current: dict[str, float],
) -> go.Figure:
    """
    Gráfico IS-LM-BP para régimen de TC fijo.
    Muestra curvas base (punteadas) y curvas actuales (sólidas).
    """
    # Curvas base
    Y0, r_IS0, r_LM0 = _compute_islm_curves(
        params_base["c0"], params_base["c1"], params_base["T"],
        params_base["I0"], params_base["G"], params_base["NX0"],
        params_base["b"], params_base["x1"], params_base["k"],
        params_base["h"], params_base["m1"],
        params_base["E"], params_base["M"],
    )
    # Curvas actuales (M es endógena en fijo → usamos M base para trazar LM actual)
    Y1, r_IS1, r_LM1 = _compute_islm_curves(
        params_current["c0"], params_current["c1"], params_current["T"],
        params_current["I0"], params_current["G"], params_current["NX0"],
        params_current["b"], params_current["x1"], params_current["k"],
        params_current["h"], params_current["m1"],
        params_current["E"], params_current["M"],
    )

    r_star_base = params_base["r_star"]
    r_star_curr = params_current["r_star"]
    Y_base_eq   = 100.0  # equilibrio analítico base

    fig = _base_fig("IS-LM-BP — Tipo de Cambio Fijo")

    ht_is  = "Y=%{x:.1f}<br>r_IS=%{y:.2f}<extra>%{fullData.name}</extra>"
    ht_lm  = "Y=%{x:.1f}<br>r_LM=%{y:.2f}<extra>%{fullData.name}</extra>"
    ht_pt  = "Y=%{x:.1f}<br>r=%{y:.2f}<extra>%{fullData.name}</extra>"

    # IS base
    fig.add_trace(go.Scatter(x=Y0, y=r_IS0, mode="lines", name="IS₀ (base)",
                             line=dict(color="#1f77b4", dash="dot", width=1.5),
                             hovertemplate=ht_is))
    # IS actual
    fig.add_trace(go.Scatter(x=Y1, y=r_IS1, mode="lines", name="IS₁ (actual)",
                             line=dict(color="#1f77b4", width=2.5),
                             hovertemplate=ht_is))
    # LM base (M endógena en fijo → LM pasa siempre por (Y*, r*))
    fig.add_trace(go.Scatter(x=Y0, y=r_LM0, mode="lines", name="LM₀ (base)",
                             line=dict(color="#ff7f0e", dash="dot", width=1.5),
                             hovertemplate=ht_lm))
    # LM actual
    fig.add_trace(go.Scatter(x=Y1, y=r_LM1, mode="lines", name="LM₁ (actual)",
                             line=dict(color="#ff7f0e", width=2.5),
                             hovertemplate=ht_lm))
    # BP base
    fig.add_hline(y=r_star_base, line_dash="dot", line_color="#2ca02c", line_width=1.5,
                  annotation_text=f"BP₀ (r*={r_star_base})", annotation_position="right")
    # BP actual (puede diferir si r* cambió)
    if abs(r_star_curr - r_star_base) > 0.01:
        fig.add_hline(y=r_star_curr, line_dash="solid", line_color="#2ca02c", line_width=2,
                      annotation_text=f"BP₁ (r*={r_star_curr})", annotation_position="right")

    # Equilibrio base
    fig.add_trace(go.Scatter(
        x=[Y_base_eq], y=[r_star_base], mode="markers", name="Eq. Base",
        marker=dict(color="#1f77b4", size=10, symbol="circle-open", line=dict(width=2)),
        hovertemplate=ht_pt,
    ))
    # Equilibrio actual
    fig.add_trace(go.Scatter(
        x=[Y_eq], y=[r_eq], mode="markers", name="Eq. Actual",
        marker=dict(color="#d62728", size=12, symbol="star"),
        hovertemplate=ht_pt,
    ))

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# IS-LM-BP — TIPO DE CAMBIO FLEXIBLE
# ─────────────────────────────────────────────────────────────────────────────

def plot_islm_flexible(
    Y_eq: float,
    r_eq: float,
    params_base: dict[str, float],
    params_current: dict[str, float],
) -> go.Figure:
    """
    Gráfico IS-LM-BP para régimen de TC flexible.
    En TC flexible, M es exógena → LM se desplaza con M.
    IS se desplaza endógenamente para reflejar E_endo.
    """
    Y0, r_IS0, r_LM0 = _compute_islm_curves(
        params_base["c0"], params_base["c1"], params_base["T"],
        params_base["I0"], params_base["G"], params_base["NX0"],
        params_base["b"], params_base["x1"], params_base["k"],
        params_base["h"], params_base["m1"],
        params_base["E"], params_base["M"],
    )
    Y1, r_IS1, r_LM1 = _compute_islm_curves(
        params_current["c0"], params_current["c1"], params_current["T"],
        params_current["I0"], params_current["G"], params_current["NX0"],
        params_current["b"], params_current["x1"], params_current["k"],
        params_current["h"], params_current["m1"],
        params_current["E"], params_current["M"],
    )

    r_star_base = params_base["r_star"]
    r_star_curr = params_current["r_star"]
    Y_base_eq   = 100.0

    fig = _base_fig("IS-LM-BP — Tipo de Cambio Flexible")

    ht_is = "Y=%{x:.1f}<br>r_IS=%{y:.2f}<extra>%{fullData.name}</extra>"
    ht_lm = "Y=%{x:.1f}<br>r_LM=%{y:.2f}<extra>%{fullData.name}</extra>"
    ht_pt = "Y=%{x:.1f}<br>r=%{y:.2f}<extra>%{fullData.name}</extra>"

    fig.add_trace(go.Scatter(x=Y0, y=r_IS0, mode="lines", name="IS₀ (base)",
                             line=dict(color="#1f77b4", dash="dot", width=1.5),
                             hovertemplate=ht_is))
    fig.add_trace(go.Scatter(x=Y1, y=r_IS1, mode="lines", name="IS₁ (actual)",
                             line=dict(color="#1f77b4", width=2.5),
                             hovertemplate=ht_is))
    fig.add_trace(go.Scatter(x=Y0, y=r_LM0, mode="lines", name="LM₀ (base)",
                             line=dict(color="#ff7f0e", dash="dot", width=1.5),
                             hovertemplate=ht_lm))
    fig.add_trace(go.Scatter(x=Y1, y=r_LM1, mode="lines", name="LM₁ (actual)",
                             line=dict(color="#ff7f0e", width=2.5),
                             hovertemplate=ht_lm))

    fig.add_hline(y=r_star_base, line_dash="dot", line_color="#2ca02c", line_width=1.5,
                  annotation_text=f"BP₀ (r*={r_star_base})", annotation_position="right")
    if abs(r_star_curr - r_star_base) > 0.01:
        fig.add_hline(y=r_star_curr, line_dash="solid", line_color="#2ca02c", line_width=2,
                      annotation_text=f"BP₁ (r*={r_star_curr})", annotation_position="right")

    fig.add_trace(go.Scatter(x=[Y_base_eq], y=[r_star_base], mode="markers",
                             name="Eq. Base",
                             marker=dict(color="#1f77b4", size=10, symbol="circle-open",
                                         line=dict(width=2)),
                             hovertemplate=ht_pt))
    fig.add_trace(go.Scatter(x=[Y_eq], y=[r_eq], mode="markers", name="Eq. Actual",
                             marker=dict(color="#d62728", size=12, symbol="star"),
                             hovertemplate=ht_pt))

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# SALTER-SWAN
# ─────────────────────────────────────────────────────────────────────────────

_ZONE_COLORS = {"I": "#2ca02c", "II": "#ff7f0e", "III": "#d62728", "IV": "#9467bd"}

@st.cache_data(ttl=3600)
def _compute_ss_curves(
    A_min: float = 40.0, A_max: float = 160.0, n: int = 120,
) -> tuple[list[float], list[float], list[float]]:
    from engine.salter_swan import q_IB, q_EB
    A_arr = np.linspace(A_min, A_max, n).tolist()
    ib    = [q_IB(a) for a in A_arr]
    eb    = [q_EB(a) for a in A_arr]
    return A_arr, ib, eb


def plot_salter_swan(A: float, q: float, zone_result: dict) -> go.Figure:
    """
    Gráfico Salter-Swan con curvas IB/EB, punto bliss y punto actual coloreado por zona.
    """
    A_arr, ib, eb = _compute_ss_curves()
    zone = zone_result["zone"]
    color = _ZONE_COLORS.get(zone, "#7f7f7f")

    fig = go.Figure()
    fig.update_layout(
        title=dict(text="Salter-Swan — Equilibrio Interno y Externo", font=dict(size=15)),
        xaxis=dict(title="Absorción doméstica (A)", showgrid=True, gridcolor="#e5e5e5"),
        yaxis=dict(title="Tipo de Cambio Real (q)", showgrid=True, gridcolor="#e5e5e5"),
        legend=dict(orientation="h", y=-0.22, x=0),
        hovermode="x unified",
        margin=dict(l=55, r=20, t=55, b=90),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    ht_ib = "A=%{x:.1f}<br>q_IB=%{y:.3f}<extra>Balance Interno</extra>"
    ht_eb = "A=%{x:.1f}<br>q_EB=%{y:.3f}<extra>Balance Externo</extra>"

    fig.add_trace(go.Scatter(x=A_arr, y=ib, mode="lines", name="IB — Balance Interno",
                             line=dict(color="#1f77b4", width=2.5),
                             hovertemplate=ht_ib))
    fig.add_trace(go.Scatter(x=A_arr, y=eb, mode="lines", name="EB — Balance Externo",
                             line=dict(color="#ff7f0e", width=2.5),
                             hovertemplate=ht_eb))

    # Punto bliss (A=100, q=1)
    fig.add_trace(go.Scatter(
        x=[100.0], y=[1.0], mode="markers+text",
        name="Punto Bliss",
        text=["✦ Bliss"], textposition="top right",
        marker=dict(color="#2ca02c", size=13, symbol="diamond"),
        hovertemplate="A=100<br>q=1.00<extra>Equilibrio ideal</extra>",
    ))

    # Punto actual
    fig.add_trace(go.Scatter(
        x=[A], y=[q], mode="markers+text",
        name=f"Actual — Zona {zone}",
        text=[f"Zona {zone}"], textposition="top right",
        marker=dict(color=color, size=14, symbol="circle",
                    line=dict(color="black", width=1.5)),
        hovertemplate=(
            f"A=%{{x:.1f}}<br>q=%{{y:.3f}}<br>"
            f"q_IB={zone_result['q_IB']:.3f}<br>q_EB={zone_result['q_EB']:.3f}"
            f"<extra>Zona {zone}</extra>"
        ),
    ))

    # Anotaciones de zonas
    fig.add_annotation(x=130, y=1.50, text="Zona I<br>Superávit+Inflación",
                       showarrow=False, font=dict(size=10, color=_ZONE_COLORS["I"]),
                       bgcolor="rgba(255,255,255,0.7)")
    fig.add_annotation(x=70, y=1.50, text="Zona II<br>Superávit+Desempleo",
                       showarrow=False, font=dict(size=10, color=_ZONE_COLORS["II"]),
                       bgcolor="rgba(255,255,255,0.7)")
    fig.add_annotation(x=70, y=0.50, text="Zona III<br>Déficit+Desempleo",
                       showarrow=False, font=dict(size=10, color=_ZONE_COLORS["III"]),
                       bgcolor="rgba(255,255,255,0.7)")
    fig.add_annotation(x=130, y=0.50, text="Zona IV<br>Déficit+Inflación",
                       showarrow=False, font=dict(size=10, color=_ZONE_COLORS["IV"]),
                       bgcolor="rgba(255,255,255,0.7)")

    return fig
