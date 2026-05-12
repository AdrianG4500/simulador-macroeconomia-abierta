"""
main.py — Simulador Macroeconómico Abierto (Fase 3)
=====================================================
Interfaz Streamlit completa: MF Fijo + Flexible + Salter-Swan
+ Sidebar: Comparativo · Sensibilidad · Informe PDF

Ejecución:
    streamlit run main.py
"""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(
    page_title="Simulador Macro Abierta — MF + Salter-Swan",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "**Simulador Macroeconómico Abierto** · Fase 3\n\n"
            "Mundell-Fleming + Salter-Swan\n"
            "Motor validado: mult=2.5, Y=100, M=40, E=10\n"
            "Ingeniería Financiera · Open Macroeconomics"
        )
    },
)

from config.parameters import get_base_params, apply_shocks
from engine.core import eq_fixed, eq_flexible
from engine.salter_swan import get_zone
from ui.controls import render_fixed_controls, render_flexible_controls, render_salter_controls
from ui.charts import plot_islm_fixed, plot_islm_flexible, plot_salter_swan
from ui.narrative import generate_fixed_narrative, generate_flexible_narrative, generate_salter_narrative
from ui.comparison import render_comparison_mode
from utils.export import export_scenario, render_export_button

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — Controles globales Fase 3
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Controles Globales")
    st.caption("Fase 3 — Análisis Avanzado")

    # ── Análisis de Sensibilidad ─────────────────────────────────────────────
    with st.expander("🔍 Análisis de Sensibilidad", expanded=False):
        sens_regime = st.radio(
            "Régimen para sensibilidad",
            ["fixed", "flexible"],
            format_func=lambda x: "TC Fijo" if x == "fixed" else "TC Flexible",
            key="sens_regime",
            horizontal=True,
        )
        sens_target = st.selectbox(
            "Variable objetivo",
            options=["Y", "r", "M_endo"] if sens_regime == "fixed" else ["Y", "r", "E_endo"],
            key="sens_target",
        )
        sens_steps = st.slider("Puntos por parámetro", 10, 40, 20, key="sens_steps")

        run_sens = st.button("▶ Ejecutar barrido", key="run_sens_btn",
                             use_container_width=True)

        if run_sens or st.session_state.get("sens_results") is not None:
            from analysis.sensitivity import (
                run_parameter_sweep, plot_tornado_chart, plot_sensitivity_line,
                STRUCTURAL_PARAMS,
            )
            base_p = get_base_params()
            frozen = json.dumps(base_p, sort_keys=True)

            with st.spinner("Calculando sensibilidad..."):
                sweep = run_parameter_sweep(
                    frozen, sens_regime, tuple(STRUCTURAL_PARAMS), sens_steps
                )
            st.session_state["sens_results"] = sweep
            st.session_state["sens_regime"]  = sens_regime
            st.session_state["sens_target"]  = sens_target

        if st.session_state.get("sens_results"):
            sweep   = st.session_state["sens_results"]
            regime_ = st.session_state.get("sens_regime", "fixed")
            target_ = st.session_state.get("sens_target", "Y")

            fig_tornado = plot_tornado_chart(sweep, target_, base_value=100.0, regime=regime_)
            st.plotly_chart(fig_tornado, use_container_width=True)

            sel_param = st.selectbox("Ver línea de sensibilidad",
                                     options=list(sweep.keys()), key="sens_line_param")
            base_p = get_base_params()
            fig_line = plot_sensitivity_line(
                sweep[sel_param], sel_param, target_,
                base_val=base_p.get(sel_param, 0.0),
                base_y=100.0,
            )
            st.plotly_chart(fig_line, use_container_width=True)

    # ── Monte Carlo ──────────────────────────────────────────────────────────
    with st.expander("🎲 Monte Carlo (n=500)", expanded=False):
        mc_regime = st.radio("Régimen MC", ["fixed", "flexible"],
                             format_func=lambda x: "TC Fijo" if x=="fixed" else "TC Flexible",
                             key="mc_regime", horizontal=True)
        run_mc = st.button("▶ Ejecutar Monte Carlo", key="run_mc_btn",
                           use_container_width=True)
        if run_mc:
            from analysis.sensitivity import run_monte_carlo_placeholder
            base_p = get_base_params()
            with st.spinner("Simulando 500 escenarios..."):
                df_mc = run_monte_carlo_placeholder(
                    json.dumps(base_p, sort_keys=True), mc_regime, n=500
                )
            if not df_mc.empty:
                st.dataframe(df_mc, use_container_width=True, hide_index=True)
                st.caption("P5 = pesimista | P50 = mediana | P95 = optimista (±20% en parámetros estructurales)")
            else:
                st.warning("No se generaron resultados válidos.")

    # ── Generador de Informe PDF ─────────────────────────────────────────────
    with st.expander("📄 Generar Informe PDF", expanded=False):
        st.markdown("Genera una plantilla académica de 5 secciones pre-llenada con los resultados del modelo.")

        pdf_regime = st.radio("Régimen principal del informe",
                              ["fixed", "flexible"],
                              format_func=lambda x: "TC Fijo" if x=="fixed" else "TC Flexible",
                              key="pdf_regime", horizontal=True)

        gen_pdf = st.button("📥 Generar PDF", key="gen_pdf_btn",
                            type="primary", use_container_width=True)

        if gen_pdf:
            from report.generator import generate_academic_pdf
            from config.parameters import CRISIS_PRESETS

            base_p = get_base_params()
            eq_fn  = eq_fixed if pdf_regime == "fixed" else eq_flexible

            # Equilibrios base y Bolivia
            eq_b = dict(eq_fn(base_p))

            bolivia_p = apply_shocks(base_p, "Bolivia_2024_Stagflation")
            eq_biv_fixed = dict(eq_fixed(bolivia_p))
            eq_biv_flex  = dict(eq_flexible(bolivia_p))

            # Salter-Swan Bolivia
            try:
                zone_biv = get_zone(75.0, 0.80)
            except Exception:
                zone_biv = None

            with st.spinner("Generando informe PDF (esto puede tomar unos segundos)..."):
                pdf_bytes = generate_academic_pdf(
                    base_params=base_p,
                    current_params=base_p,
                    equilibrium_base=eq_b,
                    equilibrium_current=eq_b,
                    salter_zone=zone_biv,
                    bolivia_analysis={
                        "TC Fijo":    eq_biv_fixed,
                        "TC Flexible": eq_biv_flex,
                    },
                )

            from datetime import datetime
            date_str = datetime.now().strftime("%Y%m%d_%H%M")
            st.download_button(
                label="⬇️ Descargar Informe PDF",
                data=pdf_bytes,
                file_name=f"Informe_MacroAbierta_{date_str}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            st.success("✅ PDF generado con 5 secciones. Descargue y complete las secciones marcadas.")

    st.divider()
    st.caption("Motor validado · Fase 1-2-3 completas")


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.title("Simulador de Macroeconomía Abierta")
st.caption(
    "Mundell-Fleming (1962) · Movilidad perfecta de capitales · "
    "Salter (1959) — Swan (1960) · Motor validado Sección 3.1"
)

# ─────────────────────────────────────────────────────────────────────────────
# PESTAÑAS PRINCIPALES
# ─────────────────────────────────────────────────────────────────────────────

tab_fixed, tab_flex, tab_ss = st.tabs([
    "🏛️ MF — Tipo de Cambio Fijo",
    "🌊 MF — Tipo de Cambio Flexible",
    "📐 Salter-Swan",
])

base_params = get_base_params()


# ═══════════════════════════════════════════════════════════════════════════
# PESTAÑA 1: TIPO DE CAMBIO FIJO
# ═══════════════════════════════════════════════════════════════════════════

with tab_fixed:
    col_ctrl, col_chart, col_results = st.columns([1, 2, 1])

    with col_ctrl:
        st.subheader("Controles")
        params_fixed = render_fixed_controls()

    try:
        eq_f    = eq_fixed(params_fixed)
        eq_f_base = eq_fixed(base_params)
        fixed_err = None
    except Exception as e:
        eq_f = eq_f_base = None
        fixed_err = str(e)

    with col_chart:
        st.subheader("Diagrama IS-LM-BP")
        if fixed_err:
            st.error(f"Error: {fixed_err}")
        else:
            if eq_f["Y"] <= 0:
                st.warning(f"⚠️ Y = {eq_f['Y']:.2f} ≤ 0. Ajuste los controles.")
            fig_f = plot_islm_fixed(eq_f["Y"], eq_f["r"], base_params, params_fixed)
            st.plotly_chart(fig_f, use_container_width=True)

            # Modo comparativo
            render_comparison_mode(
                regime="fixed",
                params_base=base_params,
                params_curr=params_fixed,
                eq_base=dict(eq_f_base),
                eq_curr=dict(eq_f),
            )

    with col_results:
        st.subheader("Resultados")
        if eq_f:
            st.metric("PIB (Y)", f"{eq_f['Y']:.2f}",
                      delta=f"{eq_f['Y']-100:+.2f} vs base")
            st.metric("r = r*", f"{eq_f['r']:.2f} %")
            st.metric("M endógena", f"{eq_f['M_endo']:.2f}",
                      delta=f"{eq_f['M_endo']-40:+.2f}")
            st.metric("NX", f"{eq_f['NX']:.2f}")
            st.metric("C (consumo)", f"{eq_f['C']:.2f}")
            st.metric("Multiplicador", f"{eq_f['mult']:.3f}")

            st.divider()
            st.markdown("**Narrativa económica**")
            st.markdown(generate_fixed_narrative(
                params_fixed["G"] - base_params["G"],
                params_fixed["T"] - base_params["T"],
                params_fixed["E"] - base_params["E"],
                params_fixed["r_star"] - base_params["r_star"],
                eq_f["Y"], eq_f["M_endo"], eq_f["NX"], eq_f["mult"],
            ))

            st.divider()
            df_exp_f = export_scenario(
                "fixed", base_params, params_fixed,
                dict(eq_f_base), dict(eq_f),
            )
            with st.expander("Vista previa CSV"):
                st.dataframe(df_exp_f, use_container_width=True, hide_index=True)
            render_export_button(df_exp_f, "fixed")


# ═══════════════════════════════════════════════════════════════════════════
# PESTAÑA 2: TIPO DE CAMBIO FLEXIBLE
# ═══════════════════════════════════════════════════════════════════════════

with tab_flex:
    col_ctrl2, col_chart2, col_results2 = st.columns([1, 2, 1])

    with col_ctrl2:
        st.subheader("Controles")
        params_flex = render_flexible_controls()

    try:
        eq_x      = eq_flexible(params_flex)
        eq_x_base = eq_flexible(base_params)
        flex_err  = None
    except Exception as e:
        eq_x = eq_x_base = None
        flex_err = str(e)

    with col_chart2:
        st.subheader("Diagrama IS-LM-BP")
        if flex_err:
            st.error(f"Error: {flex_err}")
        else:
            if eq_x["Y"] <= 0:
                st.warning(f"⚠️ Y = {eq_x['Y']:.2f} ≤ 0. Ajuste los controles.")
            fig_x = plot_islm_flexible(eq_x["Y"], eq_x["r"], base_params, params_flex)
            st.plotly_chart(fig_x, use_container_width=True)

            render_comparison_mode(
                regime="flexible",
                params_base=base_params,
                params_curr=params_flex,
                eq_base=dict(eq_x_base),
                eq_curr=dict(eq_x),
            )

    with col_results2:
        st.subheader("Resultados")
        if eq_x:
            st.metric("PIB (Y)", f"{eq_x['Y']:.2f}",
                      delta=f"{eq_x['Y']-100:+.2f} vs base")
            st.metric("r = r*", f"{eq_x['r']:.2f} %")
            st.metric("E endógeno", f"{eq_x['E_endo']:.3f}",
                      delta=f"{eq_x['E_endo']-10:+.3f}")
            st.metric("NX", f"{eq_x['NX']:.2f}")
            st.metric("C (consumo)", f"{eq_x['C']:.2f}")
            st.metric("Multiplicador", f"{eq_x['mult']:.3f}")

            st.divider()
            st.markdown("**Narrativa económica**")
            st.markdown(generate_flexible_narrative(
                params_flex["G"] - base_params["G"],
                params_flex["T"] - base_params["T"],
                params_flex["M"] - base_params["M"],
                params_flex["r_star"] - base_params["r_star"],
                eq_x["Y"], eq_x["E_endo"], eq_x["NX"], eq_x["mult"],
            ))

            st.divider()
            df_exp_x = export_scenario(
                "flexible", base_params, params_flex,
                dict(eq_x_base), dict(eq_x),
            )
            with st.expander("Vista previa CSV"):
                st.dataframe(df_exp_x, use_container_width=True, hide_index=True)
            render_export_button(df_exp_x, "flexible")


# ═══════════════════════════════════════════════════════════════════════════
# PESTAÑA 3: SALTER-SWAN
# ═══════════════════════════════════════════════════════════════════════════

with tab_ss:
    col_ctrl3, col_chart3, col_results3 = st.columns([1, 2, 1])

    with col_ctrl3:
        st.subheader("Controles")
        A_val, q_val = render_salter_controls()

    try:
        zone_res = get_zone(A_val, q_val)
        zone_base_res = get_zone(100.0, 1.0)
        ss_err = None
    except Exception as e:
        zone_res = zone_base_res = None
        ss_err = str(e)

    with col_chart3:
        st.subheader("Diagrama Salter-Swan")
        if ss_err:
            st.error(f"Error: {ss_err}")
        else:
            fig_ss = plot_salter_swan(A_val, q_val, zone_res)
            st.plotly_chart(fig_ss, use_container_width=True)

            # Modo comparativo Salter-Swan
            render_comparison_mode(
                regime="salter",
                params_base={"A": 100.0, "q": 1.0},
                params_curr={"A": A_val, "q": q_val},
                eq_base={"zone": zone_base_res["zone"],
                         "q_IB": zone_base_res["q_IB"],
                         "q_EB": zone_base_res["q_EB"]},
                eq_curr={"zone": zone_res["zone"],
                         "q_IB": zone_res["q_IB"],
                         "q_EB": zone_res["q_EB"]},
                salter_extra={
                    "A_base": 100.0, "q_base": 1.0,
                    "A_curr": A_val, "q_curr": q_val,
                },
            )

    with col_results3:
        st.subheader("Diagnóstico")
        if zone_res:
            _zcol = {"I": "green", "II": "orange", "III": "red", "IV": "violet"}
            z = zone_res["zone"]
            st.markdown(f"### Zona **:{_zcol.get(z,'gray')}[{z}]**")
            st.metric("A (absorción)", f"{A_val:.1f}")
            st.metric("q (TC real)", f"{q_val:.3f}")
            st.metric("q_IB", f"{zone_res['q_IB']:.3f}")
            st.metric("q_EB", f"{zone_res['q_EB']:.3f}")

            st.divider()
            st.markdown("**Análisis de zona**")
            st.markdown(generate_salter_narrative(
                z, A_val, q_val, zone_res["q_IB"], zone_res["q_EB"]
            ))

            st.divider()
            df_ss = export_scenario(
                "salter",
                {"A": 100.0, "q": 1.0},
                {"A": A_val, "q": q_val},
                {"q_IB": 1.0, "q_EB": 1.0, "zone": "Bliss"},
                {"q_IB": zone_res["q_IB"], "q_EB": zone_res["q_EB"],
                 "zone": zone_res["zone"]},
            )
            render_export_button(df_ss, "salter", "salter_resultado")

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "Simulador Macroeconómico Abierto · Fases 1-2-3 · "
    "mult=2.5 · Y_base=100 · M_endo=40 · E_endo=10 | "
    "Ingeniería Financiera · Open Macroeconomics"
)
