"""
ui/comparison.py — Modo Comparativo para el Simulador Macroeconómico.
Superpone equilibrios base vs actual en tabla y gráfico diferencial.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engine.core import autonomous_demand, is_curve, lm_curve


# ── Helpers ──────────────────────────────────────────────────────────────────

def _delta_color(val: float) -> str:
    """Retorna 'normal' | 'inverse' para st.metric según dirección del delta."""
    return "normal" if val >= 0 else "inverse"


def _build_delta_df(
    eq_base: dict[str, float],
    eq_curr: dict[str, float],
    regime: str,
) -> pd.DataFrame:
    """Construye DataFrame de deltas con formato legible."""
    if regime == "fixed":
        vars_map = {
            "Y — PIB de Equilibrio":         ("Y",      "unid. PIB"),
            "r — Tasa de Interés":           ("r",      "% anual"),
            "M endógena":                    ("M_endo", "unid. monetarias"),
            "NX — Export. Netas":            ("NX",     "unid. PIB"),
            "C — Consumo":                   ("C",      "unid. PIB"),
            "I — Inversión":                 ("I_inv",  "unid. PIB"),
            "Multiplicador (mult)":          ("mult",   "adimensional"),
        }
    elif regime == "flexible":
        vars_map = {
            "Y — PIB de Equilibrio":         ("Y",      "unid. PIB"),
            "r — Tasa de Interés":           ("r",      "% anual"),
            "E — Tipo de Cambio Endógeno":   ("E_endo", "unid. monetarias"),
            "NX — Export. Netas":            ("NX",     "unid. PIB"),
            "C — Consumo":                   ("C",      "unid. PIB"),
            "I — Inversión":                 ("I_inv",  "unid. PIB"),
            "Multiplicador (mult)":          ("mult",   "adimensional"),
        }
    else:  # salter
        vars_map = {
            "q_IB — Balance Interno":        ("q_IB",  "adimensional"),
            "q_EB — Balance Externo":        ("q_EB",  "adimensional"),
        }

    rows = []
    for label, (key, unit) in vars_map.items():
        v0 = eq_base.get(key, float("nan"))
        v1 = eq_curr.get(key, float("nan"))
        delta = v1 - v0
        pct   = (delta / v0 * 100) if v0 != 0 else float("nan")
        rows.append({
            "Variable":      label,
            "Base":          round(v0, 4),
            "Actual":        round(v1, 4),
            "Δ (absoluto)":  round(delta, 4),
            "Δ (%)":         round(pct, 2),
            "Unidad":        unit,
        })
    return pd.DataFrame(rows)


# ── Modo Comparativo IS-LM ────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def _islm_arrays(
    c0: float, c1: float, T: float, I0: float, G: float, NX0: float,
    b: float, x1: float, k: float, h: float, m1: float,
    E: float, M: float,
    n: int = 120,
) -> tuple[list[float], list[float], list[float]]:
    import numpy as np
    Y_arr = list(map(float, __import__("numpy").linspace(30, 190, n)))
    A = autonomous_demand(c0, c1, T, I0, G, NX0)
    r_IS = [is_curve(y, c1, m1, b, A, x1, E) for y in Y_arr]
    r_LM = [lm_curve(y, k, M, h) for y in Y_arr]
    return Y_arr, r_IS, r_LM


def _overlay_fig(
    params_base: dict,
    params_curr: dict,
    eq_base: dict,
    eq_curr: dict,
    regime: str,
    r_star_base: float,
    r_star_curr: float,
) -> go.Figure:
    """Genera figura con 4 curvas (IS₀/IS₁/LM₀/LM₁) superpuestas."""
    Y0, IS0, LM0 = _islm_arrays(
        params_base["c0"], params_base["c1"], params_base["T"],
        params_base["I0"], params_base["G"], params_base["NX0"],
        params_base["b"], params_base["x1"], params_base["k"],
        params_base["h"], params_base["m1"],
        params_base.get("E", 10.0), params_base.get("M", 40.0),
    )
    Y1, IS1, LM1 = _islm_arrays(
        params_curr["c0"], params_curr["c1"], params_curr["T"],
        params_curr["I0"], params_curr["G"], params_curr["NX0"],
        params_curr["b"], params_curr["x1"], params_curr["k"],
        params_curr["h"], params_curr["m1"],
        params_curr.get("E", 10.0), params_curr.get("M", 40.0),
    )

    fig = go.Figure()
    fig.update_layout(
        title="Comparativo IS₀/IS₁ — LM₀/LM₁ — BP",
        xaxis_title="Ingreso Y", yaxis_title="Tasa de interés r",
        legend=dict(orientation="h", y=-0.25),
        hovermode="x unified",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=50, r=20, t=50, b=90),
    )

    IS_COLOR = "#1f77b4"
    LM_COLOR = "#ff7f0e"

    fig.add_trace(go.Scatter(x=Y0, y=IS0, name="IS₀ (base)",
                             line=dict(color=IS_COLOR, dash="dot", width=1.5)))
    fig.add_trace(go.Scatter(x=Y1, y=IS1, name="IS₁ (actual)",
                             line=dict(color=IS_COLOR, width=2.5)))
    fig.add_trace(go.Scatter(x=Y0, y=LM0, name="LM₀ (base)",
                             line=dict(color=LM_COLOR, dash="dot", width=1.5)))
    fig.add_trace(go.Scatter(x=Y1, y=LM1, name="LM₁ (actual)",
                             line=dict(color=LM_COLOR, width=2.5)))

    fig.add_hline(y=r_star_base, line_dash="dot", line_color="#2ca02c", line_width=1.5,
                  annotation_text=f"BP₀ r*={r_star_base}", annotation_position="right")
    if abs(r_star_curr - r_star_base) > 0.01:
        fig.add_hline(y=r_star_curr, line_color="#2ca02c", line_width=2,
                      annotation_text=f"BP₁ r*={r_star_curr}", annotation_position="right")

    # Puntos de equilibrio
    Y_b = eq_base.get("Y", 100.0)
    Y_c = eq_curr.get("Y", 100.0)
    fig.add_trace(go.Scatter(x=[Y_b], y=[r_star_base], mode="markers",
                             name="Eq. Base",
                             marker=dict(color=IS_COLOR, size=10, symbol="circle-open",
                                         line=dict(width=2))))
    fig.add_trace(go.Scatter(x=[Y_c], y=[r_star_curr], mode="markers",
                             name="Eq. Actual",
                             marker=dict(color="#d62728", size=13, symbol="star")))
    # Flecha de desplazamiento
    if abs(Y_c - Y_b) > 0.5:
        fig.add_annotation(
            ax=Y_b, ay=r_star_base, x=Y_c, y=r_star_curr,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowsize=1.3,
            arrowcolor="#d62728", arrowwidth=2,
        )
    return fig


# ── Modo Comparativo Salter-Swan ─────────────────────────────────────────────

def _salter_overlay_fig(
    A_base: float, q_base: float,
    A_curr: float, q_curr: float,
    zone_base: str, zone_curr: str,
) -> go.Figure:
    import numpy as np
    from engine.salter_swan import q_IB, q_EB

    A_arr = list(map(float, np.linspace(40, 160, 120)))
    ib = [q_IB(a) for a in A_arr]
    eb = [q_EB(a) for a in A_arr]

    _ZONE_COLORS = {"I": "#2ca02c", "II": "#ff7f0e", "III": "#d62728", "IV": "#9467bd"}

    fig = go.Figure()
    fig.update_layout(
        title="Salter-Swan Comparativo — Base vs Actual",
        xaxis_title="Absorción doméstica (A)",
        yaxis_title="Tipo de Cambio Real (q)",
        legend=dict(orientation="h", y=-0.25),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=55, r=20, t=50, b=90),
    )

    fig.add_trace(go.Scatter(x=A_arr, y=ib, name="IB — Balance Interno",
                             line=dict(color="#1f77b4", width=2.5)))
    fig.add_trace(go.Scatter(x=A_arr, y=eb, name="EB — Balance Externo",
                             line=dict(color="#ff7f0e", width=2.5)))
    fig.add_trace(go.Scatter(x=[100.0], y=[1.0], mode="markers+text",
                             name="Bliss", text=["✦ Bliss"],
                             textposition="top right",
                             marker=dict(color="#2ca02c", size=12, symbol="diamond")))
    fig.add_trace(go.Scatter(
        x=[A_base], y=[q_base], mode="markers+text",
        name=f"Base (Zona {zone_base})",
        text=[f"Base·{zone_base}"], textposition="bottom left",
        marker=dict(color=_ZONE_COLORS.get(zone_base, "#7f7f7f"), size=12,
                    symbol="circle-open", line=dict(width=2.5)),
    ))
    fig.add_trace(go.Scatter(
        x=[A_curr], y=[q_curr], mode="markers+text",
        name=f"Actual (Zona {zone_curr})",
        text=[f"Actual·{zone_curr}"], textposition="top right",
        marker=dict(color=_ZONE_COLORS.get(zone_curr, "#7f7f7f"), size=14,
                    symbol="star", line=dict(color="black", width=1)),
    ))

    if abs(A_curr - A_base) > 0.5 or abs(q_curr - q_base) > 0.01:
        fig.add_annotation(
            ax=A_base, ay=q_base, x=A_curr, y=q_curr,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowcolor="#d62728",
            arrowsize=1.3, arrowwidth=2,
        )
    return fig


# ── API pública ───────────────────────────────────────────────────────────────

def render_comparison_mode(
    regime: str,
    params_base: dict[str, float],
    params_curr: dict[str, float],
    eq_base: dict[str, float],
    eq_curr: dict[str, float],
    salter_extra: dict | None = None,
) -> None:
    """
    Renderiza el modo comparativo para el régimen dado.

    Parameters
    ----------
    regime       : "fixed" | "flexible" | "salter"
    params_base  : Parámetros base del modelo.
    params_curr  : Parámetros actuales.
    eq_base      : Equilibrio base (eq_fixed/flexible con params_base).
    eq_curr      : Equilibrio actual.
    salter_extra : Para régimen salter: dict con A_base, q_base, zone_base.
    """
    active = st.toggle("⚖️ Modo Comparativo", key=f"cmp_toggle_{regime}", value=False)
    if not active:
        return

    st.markdown("##### Análisis diferencial: Base → Actual")

    if regime in ("fixed", "flexible"):
        col_fig, col_tbl = st.columns([3, 2])

        r_star_base = params_base.get("r_star", 5.0)
        r_star_curr = params_curr.get("r_star", 5.0)

        with col_fig:
            fig = _overlay_fig(
                params_base, params_curr,
                eq_base, eq_curr, regime,
                r_star_base, r_star_curr,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_tbl:
            df_delta = _build_delta_df(eq_base, eq_curr, regime)

            # Métricas con color
            key_map = {
                "fixed":    [("Y", "Y — PIB"), ("M_endo", "M endógena"), ("NX", "NX")],
                "flexible": [("Y", "Y — PIB"), ("E_endo", "E endógeno"), ("NX", "NX")],
            }
            for key, label in key_map.get(regime, []):
                v0 = eq_base.get(key, 0.0)
                v1 = eq_curr.get(key, 0.0)
                d  = v1 - v0
                st.metric(label, f"{v1:.3f}", delta=f"{d:+.3f}",
                          delta_color=_delta_color(d))

            st.divider()
            st.dataframe(
                df_delta.style.format({
                    "Base": "{:.4f}", "Actual": "{:.4f}",
                    "Δ (absoluto)": "{:+.4f}", "Δ (%)": "{:+.2f}%",
                }),
                use_container_width=True,
                hide_index=True,
            )

    elif regime == "salter" and salter_extra:
        A_base   = salter_extra.get("A_base", 100.0)
        q_base   = salter_extra.get("q_base", 1.0)
        A_curr   = salter_extra.get("A_curr", 100.0)
        q_curr   = salter_extra.get("q_curr", 1.0)
        zone_base = eq_base.get("zone", "?")
        zone_curr = eq_curr.get("zone", "?")

        col_fig2, col_tbl2 = st.columns([3, 2])
        with col_fig2:
            fig_ss = _salter_overlay_fig(A_base, q_base, A_curr, q_curr, zone_base, zone_curr)
            st.plotly_chart(fig_ss, use_container_width=True)

        with col_tbl2:
            st.metric("Zona Base", zone_base)
            st.metric("Zona Actual", zone_curr,
                      delta="sin cambio" if zone_base == zone_curr else f"{zone_base} → {zone_curr}")
            st.metric("ΔA (absorción)", f"{A_curr - A_base:+.1f}")
            st.metric("Δq (tipo de cambio real)", f"{q_curr - q_base:+.3f}")
