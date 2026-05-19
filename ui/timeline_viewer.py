"""
ui/timeline_viewer.py
=====================
Visualizador de trayectorias temporales para Fase 4.
Gráficos Plotly interactivos con marcadores de eventos y tabla comparativa.
"""
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Colores institucionales
_COL_FIXED    = "#1e40af"   # azul profundo — TC fijo
_COL_FLEXIBLE = "#0891b2"   # azul cian — TC flexible
_COL_BASE     = "#94a3b8"   # gris — línea base
_COL_GOLD     = "#f59e0b"   # dorado — acento
_COL_GREEN    = "#10b981"

# Variables principales con etiquetas
_VAR_LABELS: dict[str, str] = {
    "Y":      "PIB (Y)",
    "r":      "Tasa de interés (r) %",
    "NX":     "Exportaciones Netas (NX)",
    "C":      "Consumo (C)",
    "mult":   "Multiplicador keynesiano",
    "G":      "Gasto Gobierno (G)",
    "T":      "Impuestos (T)",
    "c1":     "PMgC (c₁)",
    "m1":     "PMgM (m₁)",
    "x1":     "Elasticidad Export. (x₁)",
    "E":      "Tipo de Cambio (E)",
    "M_endo": "M endógena (TC fijo)",
    "r_star": "Tasa internacional (r*)",
}


def render_trajectory_chart(
    state_manager,
    variables: list[str],
    regime: str = "fixed",
) -> go.Figure:
    """
    Gráfico de trayectoria temporal con marcadores de estados.

    Parameters
    ----------
    state_manager : EconomicStateManager
    variables     : list[str] — variables a graficar (hasta 4)
    regime        : "fixed" | "flexible"

    Returns
    -------
    go.Figure
    """
    if state_manager.is_empty():
        fig = go.Figure()
        fig.update_layout(
            title="Sin estados guardados",
            annotations=[dict(
                text="Guarde al menos un estado en la Fase de Simulación.",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font=dict(size=14, color="#94a3b8"),
            )],
            height=350,
        )
        return fig

    labels = state_manager.list_labels()
    x_vals = list(range(len(labels)))

    # Colores por variable
    palette = [_COL_FIXED, _COL_GOLD, _COL_GREEN, "#8b5cf6"]

    fig = go.Figure()
    use_secondary = len(variables) > 1

    for idx, var in enumerate(variables[:4]):
        traj  = state_manager.get_trajectory(var)
        color = palette[idx % len(palette)]
        label = _VAR_LABELS.get(var, var)

        # Línea principal
        fig.add_trace(go.Scatter(
            x=x_vals, y=traj,
            mode="lines+markers",
            name=label,
            line=dict(color=color, width=2.5),
            marker=dict(size=9, color=color, symbol="circle",
                        line=dict(color="white", width=1.5)),
            hovertemplate=(
                f"<b>{label}</b><br>"
                "Estado: %{customdata}<br>"
                "Valor: %{y:.3g}"
                "<extra></extra>"
            ),
            customdata=labels,
            yaxis="y" if idx == 0 else f"y{idx+1}" if idx > 0 else "y",
        ))

        # Área sombreada bajo la curva (solo primera variable)
        if idx == 0:
            fig.add_trace(go.Scatter(
                x=x_vals + x_vals[::-1],
                y=traj + [min(v for v in traj if v == v)] * len(traj),
                fill="toself",
                fillcolor=f"rgba({_hex_to_rgb(color)},0.08)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False, hoverinfo="skip",
            ))

    # Anotaciones de estados como marcadores en eje X
    ticktext = [f"<b>{i}</b><br><span style='font-size:9px'>{l[:15]}…" if len(l)>15
                else f"<b>{i}</b><br>{l}"
                for i, l in enumerate(labels)]

    # Layout
    fig.update_layout(
        title=dict(
            text=f"🗺️ Trayectoria Económica — {len(labels)} estados",
            font=dict(size=16, color="#1e293b"),
        ),
        xaxis=dict(
            title="Paso de simulación",
            tickmode="array",
            tickvals=x_vals,
            ticktext=[f"{i}: {l[:12]}…" if len(l)>12 else f"{i}: {l}"
                      for i, l in enumerate(labels)],
            tickangle=-30,
            showgrid=True, gridcolor="#f1f5f9",
        ),
        yaxis=dict(
            title=_VAR_LABELS.get(variables[0], variables[0]) if variables else "Valor",
            showgrid=True, gridcolor="#f1f5f9",
            titlefont=dict(color=palette[0]),
        ),
        legend=dict(
            orientation="h", y=-0.28, x=0,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#e2e8f0", borderwidth=1,
        ),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=30, t=60, b=110),
        height=420,
    )

    # Eje Y secundario si hay múltiples variables
    if len(variables) >= 2:
        fig.update_layout(
            yaxis2=dict(
                title=_VAR_LABELS.get(variables[1], variables[1]),
                overlaying="y", side="right",
                showgrid=False,
                titlefont=dict(color=palette[1]),
            )
        )
        for tr in fig.data:
            if tr.name == _VAR_LABELS.get(variables[1], variables[1]):
                tr.update(yaxis="y2")

    return fig


def render_state_comparison_table(state_manager) -> None:
    """
    Renderiza tabla interactiva de todos los estados guardados.
    Permite seleccionar dos estados para comparar deltas.
    """
    if state_manager.is_empty():
        st.info("No hay estados guardados. Vaya a la Fase de Simulación y guarde estados.")
        return

    df = state_manager.get_trajectory_df(
        variables=["Y", "r", "NX", "C", "mult", "G", "T", "c1", "m1"]
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Paso":      st.column_config.NumberColumn("Paso", width="small"),
            "Estado":    st.column_config.TextColumn("Estado", width="medium"),
            "Timestamp": st.column_config.TextColumn("Timestamp", width="medium"),
            "Régimen":   st.column_config.TextColumn("Régimen", width="small"),
            "Y":         st.column_config.NumberColumn("Y (PIB)", format="%.2f"),
            "r":         st.column_config.NumberColumn("r (%)", format="%.2f"),
            "NX":        st.column_config.NumberColumn("NX", format="%.2f"),
            "mult":      st.column_config.NumberColumn("Mult.", format="%.3f"),
            "G":         st.column_config.NumberColumn("G", format="%.1f"),
            "c1":        st.column_config.NumberColumn("c₁", format="%.3f"),
        },
    )

    # ── Selector de comparación ───────────────────────────────────────────────
    labels = state_manager.list_labels()
    if len(labels) >= 2:
        st.markdown("##### 📊 Comparar dos estados")
        col_a, col_b, col_btn = st.columns([2, 2, 1])
        with col_a:
            sel_a = st.selectbox("Estado A (base)", labels,
                                  index=0, key="f4_compare_a")
        with col_b:
            sel_b = st.selectbox("Estado B (comparar)", labels,
                                  index=min(1, len(labels)-1), key="f4_compare_b")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            compare_btn = st.button("🔍 Comparar", key="f4_compare_btn",
                                     use_container_width=True)

        if compare_btn or st.session_state.get("f4_last_compare") == (sel_a, sel_b):
            st.session_state["f4_last_compare"] = (sel_a, sel_b)
            df_cmp = state_manager.compare_states(sel_a, sel_b)
            if not df_cmp.empty:
                # Resaltar deltas significativos
                st.dataframe(
                    df_cmp,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Δ %": st.column_config.NumberColumn("Δ %", format="%.2f"),
                        "Δ Absoluto": st.column_config.NumberColumn("Δ Abs.", format="%.4f"),
                    },
                )


def render_variable_selector(default: list[str] | None = None) -> list[str]:
    """
    Widget para seleccionar variables a graficar en la trayectoria.

    Returns
    -------
    list[str] : Variables seleccionadas (máx. 4)
    """
    default = default or ["Y", "NX"]
    available = list(_VAR_LABELS.keys())
    selected = st.multiselect(
        "Variables a graficar (máx. 4)",
        options=available,
        default=[v for v in default if v in available],
        format_func=lambda v: _VAR_LABELS.get(v, v),
        max_selections=4,
        key="f4_traj_vars",
    )
    return selected if selected else ["Y"]


# ── Helper ─────────────────────────────────────────────────────────────────────
def _hex_to_rgb(hex_color: str) -> str:
    """Convierte #rrggbb a 'r,g,b' para rgba() en Plotly."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"
