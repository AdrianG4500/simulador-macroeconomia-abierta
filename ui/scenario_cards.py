"""
ui/scenario_cards.py
====================
Tarjetas comparativas de escenarios para Fase 4.
"""
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

# ── CSS de tarjetas ────────────────────────────────────────────────────────────
_CARD_STYLES = """
<style>
.sc-card{
  background:#f8fafc; border:1px solid #e2e8f0;
  border-radius:12px; padding:16px 20px; margin-bottom:12px;
  box-shadow:0 2px 8px rgba(30,64,175,.08);
  transition:box-shadow .2s;
}
.sc-card-base{ border-left:4px solid #1e40af; }
.sc-card-shock{ border-left:4px solid #f59e0b; }
.sc-card-policy{ border-left:4px solid #10b981; }
.sc-card h3{ color:#1e293b; margin:0 0 4px 0; font-size:1.05rem; }
.sc-card .regime-badge{
  display:inline-block; padding:2px 8px; border-radius:20px;
  font-size:.75rem; font-weight:600; margin-bottom:8px;
}
.badge-fixed{background:#dbeafe; color:#1e40af;}
.badge-flexible{background:#cffafe; color:#0891b2;}
.sc-kpi{ display:flex; gap:12px; flex-wrap:wrap; margin-top:8px; }
.sc-kpi-item{ text-align:center; min-width:64px; }
.sc-kpi-item .kpi-val{
  font-size:1.3rem; font-weight:700; color:#1e40af; line-height:1;
}
.sc-kpi-item .kpi-lbl{
  font-size:.7rem; color:#64748b; margin-top:2px;
}
</style>
"""

_ZONE_COLORS = {"I": "#10b981", "II": "#f59e0b", "III": "#ef4444", "IV": "#8b5cf6"}
_REGIME_ICON = {"fixed": "🏛️", "flexible": "🌊", "de_facto_fixed": "⚓", "managed_float": "🎛️"}


def render_scenario_card(
    label: str,
    equilibrium: dict,
    params: dict | None = None,
    regime: str = "fixed",
    is_base: bool = False,
    state_manager=None,
) -> None:
    """
    Renderiza una tarjeta visual con los KPIs de un estado económico.

    Parameters
    ----------
    label       : Nombre del estado
    equilibrium : dict con Y, r, NX, C, mult, etc.
    params      : dict de parámetros del modelo (opcional)
    regime      : "fixed" | "flexible"
    is_base     : True = estilo azul base, False = estilo acento
    state_manager : EconomicStateManager (para botones de acción)
    """
    st.markdown(_CARD_STYLES, unsafe_allow_html=True)

    card_class = "sc-card-base" if is_base else "sc-card-shock"
    badge_class = "badge-fixed" if regime in ("fixed", "de_facto_fixed") else "badge-flexible"
    regime_icon = _REGIME_ICON.get(regime, "📌")
    regime_label = {
        "fixed":         "TC Fijo",
        "flexible":      "TC Flexible",
        "de_facto_fixed":"TC Fijo (de facto)",
        "managed_float": "Flotación administrada",
    }.get(regime, regime)

    # Extraer KPIs
    Y    = equilibrium.get("Y",    equilibrium.get("Y",    float("nan")))
    r    = equilibrium.get("r",    float("nan"))
    NX   = equilibrium.get("NX",   float("nan"))
    mult = equilibrium.get("mult", float("nan"))
    E_val = (equilibrium.get("E",      None) or
             equilibrium.get("E_endo", None) or
             params.get("E", float("nan")) if params else float("nan"))
    G_val = params.get("G", float("nan")) if params else float("nan")

    def _fmt(v, decimals=2):
        try:
            return f"{float(v):.{decimals}f}"
        except (TypeError, ValueError):
            return "—"

    st.markdown(
        f"""<div class='sc-card {card_class}'>
<h3>{'⭐ ' if is_base else '📌 '}{label}</h3>
<span class='regime-badge {badge_class}'>{regime_icon} {regime_label}</span>
<div class='sc-kpi'>
  <div class='sc-kpi-item'><div class='kpi-val'>{_fmt(Y)}</div><div class='kpi-lbl'>PIB (Y)</div></div>
  <div class='sc-kpi-item'><div class='kpi-val'>{_fmt(r)}%</div><div class='kpi-lbl'>r = r*</div></div>
  <div class='sc-kpi-item'><div class='kpi-val'>{_fmt(NX)}</div><div class='kpi-lbl'>NX</div></div>
  <div class='sc-kpi-item'><div class='kpi-val'>{_fmt(mult, 3)}</div><div class='kpi-lbl'>Mult.</div></div>
  <div class='sc-kpi-item'><div class='kpi-val'>{_fmt(E_val, 3)}</div><div class='kpi-lbl'>E</div></div>
  <div class='sc-kpi-item'><div class='kpi-val'>{_fmt(G_val, 1)}</div><div class='kpi-lbl'>G</div></div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    # Botones de acción
    if state_manager is not None:
        col_base, col_del = st.columns([1, 1])
        with col_base:
            if st.button("🔁 Usar como Base", key=f"f4_use_base_{label}",
                          use_container_width=True):
                state = state_manager.load_state(label)
                if state:
                    # Cargar parámetros en session_state de calibración
                    _load_state_into_calibration(state)
                    st.success(f"✅ '{label}' cargado como nueva historia base.")
                    st.rerun()
        with col_del:
            if st.button("🗑️ Eliminar", key=f"f4_del_{label}",
                          use_container_width=True, type="secondary"):
                state_manager.delete_state(label)
                st.rerun()


def render_side_by_side_comparison(
    state_a: dict,
    state_b: dict,
) -> None:
    """
    Comparación visual de dos estados: tarjetas lado a lado + gráfico de barras + narrativa.

    Parameters
    ----------
    state_a, state_b : dict — estados del EconomicStateManager
    """
    st.markdown(_CARD_STYLES, unsafe_allow_html=True)

    label_a = state_a.get("label", "Estado A")
    label_b = state_b.get("label", "Estado B")
    eq_a    = state_a.get("equilibrium", {})
    eq_b    = state_b.get("equilibrium", {})
    par_a   = state_a.get("params", {})
    par_b   = state_b.get("params", {})

    # ── Tarjetas lado a lado ──────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        render_scenario_card(label_a, eq_a, par_a,
                              state_a.get("regime", "fixed"), is_base=True)
    with col_b:
        render_scenario_card(label_b, eq_b, par_b,
                              state_b.get("regime", "fixed"), is_base=False)

    # ── Gráfico de barras comparativo ─────────────────────────────────────────
    vars_to_compare = ["Y", "r", "NX", "C", "mult"]
    merged_a = {**par_a, **eq_a}
    merged_b = {**par_b, **eq_b}

    labels_bar, vals_a, vals_b, deltas = [], [], [], []
    for v in vars_to_compare:
        va = merged_a.get(v, None)
        vb = merged_b.get(v, None)
        if va is None or vb is None:
            continue
        try:
            va, vb = float(va), float(vb)
            labels_bar.append(v)
            vals_a.append(va)
            vals_b.append(vb)
            deltas.append(vb - va)
        except (TypeError, ValueError):
            pass

    if labels_bar:
        fig = go.Figure(data=[
            go.Bar(name=label_a[:20], x=labels_bar, y=vals_a,
                   marker_color="#1e40af", opacity=0.85,
                   hovertemplate="%{x}: %{y:.3g}<extra>"+label_a+"</extra>"),
            go.Bar(name=label_b[:20], x=labels_bar, y=vals_b,
                   marker_color="#f59e0b", opacity=0.85,
                   hovertemplate="%{x}: %{y:.3g}<extra>"+label_b+"</extra>"),
        ])
        fig.update_layout(
            barmode="group",
            title="Comparación de KPIs",
            plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", y=-0.25),
            margin=dict(l=40, r=20, t=50, b=80),
            height=350,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Narrativa automática ──────────────────────────────────────────────────
    _render_auto_narrative(label_a, label_b, merged_a, merged_b, deltas, labels_bar)


def _render_auto_narrative(
    label_a: str,
    label_b: str,
    merged_a: dict,
    merged_b: dict,
    deltas: list[float],
    var_names: list[str],
) -> None:
    """Genera narrativa textual de la comparación entre dos estados."""
    Y_a   = merged_a.get("Y", float("nan"))
    Y_b   = merged_b.get("Y", float("nan"))
    r_a   = merged_a.get("r", float("nan"))
    r_b   = merged_b.get("r", float("nan"))
    NX_a  = merged_a.get("NX", float("nan"))
    NX_b  = merged_b.get("NX", float("nan"))
    G_a   = merged_a.get("G", float("nan"))
    G_b   = merged_b.get("G", float("nan"))
    c1_a  = merged_a.get("c1", float("nan"))
    c1_b  = merged_b.get("c1", float("nan"))

    def _dir(va, vb):
        try:
            d = float(vb) - float(va)
            return ("aumentó ↑", abs(d)) if d > 0 else ("cayó ↓", abs(d))
        except Exception:
            return ("cambió", 0)

    with st.expander("📝 Narrativa automática de la transición", expanded=True):
        lines = [
            f"**De «{label_a}» → «{label_b}»:**",
            "",
        ]
        dir_Y, dY  = _dir(Y_a,  Y_b)
        dir_NX, dNX = _dir(NX_a, NX_b)
        dir_G, dG  = _dir(G_a,  G_b)

        try:
            lines.append(
                f"- El **PIB (Y)** {dir_Y} en {dY:.2f} unidades "
                f"({Y_a:.2f} → {Y_b:.2f})."
            )
        except Exception:
            pass

        try:
            lines.append(
                f"- Las **exportaciones netas (NX)** {dir_NX} en {dNX:.2f} unidades "
                f"({NX_a:.2f} → {NX_b:.2f})."
            )
        except Exception:
            pass

        try:
            lines.append(
                f"- El **gasto público (G)** {dir_G} en {dG:.1f} unidades "
                f"({G_a:.1f} → {G_b:.1f})."
            )
        except Exception:
            pass

        # Mecanismo
        if abs(float(G_b or 0) - float(G_a or 0)) > 0.5:
            regime = merged_b.get("regime", "fixed")
            if regime in ("fixed", "de_facto_fixed"):
                lines.append(
                    "- *Mecanismo (TC fijo)*: el cambio en G desplaza la IS. "
                    "La oferta monetaria se ajusta endógenamente para mantener r = r*."
                )
            else:
                lines.append(
                    "- *Mecanismo (TC flexible)*: el cambio en G es compensado por apreciación "
                    "cambiaria (efecto crowding-out externo), dejando Y inalterado en el modelo MF."
                )

        if abs(float(c1_b or 0) - float(c1_a or 0)) > 0.005:
            dir_c, dc = _dir(c1_a, c1_b)
            lines.append(
                f"- La **PMgC (c₁)** {dir_c} en {dc:.3f}, modificando el multiplicador keynesiano."
            )

        st.markdown("\n".join(lines))


def _load_state_into_calibration(state: dict) -> None:
    """Carga un estado guardado en los widgets de calibración (session_state)."""
    p = state.get("params", {})
    mapping = {
        "f4_c0": "c0", "f4_c1": "c1", "f4_I0": "I0", "f4_NX0": "NX0",
        "f4_b": "b", "f4_m1": "m1", "f4_x1": "x1", "f4_k": "k", "f4_h": "h",
        "f4_G": "G", "f4_T": "T", "f4_E": "E", "f4_r_star": "r_star", "f4_M": "M",
    }
    for sk, pk in mapping.items():
        if pk in p:
            val = float(p[pk])
            st.session_state[sk]        = val
            st.session_state[sk + "_n"] = val
