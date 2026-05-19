# Reporte del Proyecto: Simulador Macroeconomico

Este documento contiene la estructura del proyecto y el código fuente de todos los archivos relevantes.

## Estructura de Directorios
```text
Simulador Macroeconomico/
    .env.example
    .gitignore
    main.py
    README.md
    requirements.txt
    verify_phase2.py
    analysis/
        sensitivity.py
        __init__.py
    config/
        bolivia_data.py
        parameters.py
        scenarios.py
        validation_rules.py
        __init__.py
    engine/
        cache.py
        core.py
        salter_swan.py
        scenario_builder.py
        state_manager.py
        __init__.py
    report/
        generator.py
        __init__.py
    ui/
        calibration_panel.py
        charts.py
        comparison.py
        controls.py
        narrative.py
        scenario_cards.py
        timeline_viewer.py
        __init__.py
    utils/
        export.py
        exporters.py
        validators.py
        __init__.py
    validation/
        test_equilibrium.py
        __init__.py
```

## Archivos del Proyecto

### Archivo: `.env.example`
```bash
# ============================================================
# Simulador Macroeconómico Abierto — Parámetros Base
# Mundell-Fleming + Salter-Swan
# Sección 3.1 del documento de referencia
# ============================================================

# --- Función de Consumo ---
BASE_C0=10        # Consumo autónomo
BASE_C1=0.75      # Propensión marginal a consumir

# --- Inversión ---
BASE_I0=15        # Inversión autónoma

# --- Exportaciones netas ---
BASE_NX0=5        # Exportaciones netas autónomas

# --- Parámetros de la curva IS ---
BASE_B=2.0        # Sensibilidad de la inversión a la tasa de interés

# --- Parámetros de la curva LM ---
BASE_M1=0.15      # Sensibilidad de la demanda de dinero al ingreso (k)
BASE_X1=1.5       # Sensibilidad de las exportaciones al tipo de cambio
BASE_K_LM=0.5     # Parámetro k de demanda de dinero (alternativo)
BASE_H=2.0        # Sensibilidad de la demanda de dinero a la tasa de interés

# --- Política Fiscal ---
BASE_G=20         # Gasto de gobierno
BASE_T=20         # Impuestos

# --- Tipo de Cambio y Variables Externas ---
BASE_E=10         # Tipo de cambio nominal (régimen fijo)
BASE_RS=5         # Tasa de interés internacional (r*)

# --- Oferta Monetaria ---
BASE_M=40         # Oferta de dinero (régimen flexible)

```

### Archivo: `.gitignore`
```gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual environments
.venv/
venv/
env/
ENV/
env.bak/
venv.bak/

# Environment variables
.env

# Streamlit
.streamlit/credentials.toml

# Reports and exports generated locally
reports/
*.pdf
*.html
*.png
*.csv
*.parquet

# VS Code / IDE settings
.vscode/
.idea/
*.swp

```

### Archivo: `main.py`
```python
"""
main.py — Simulador Macroeconómico Abierto (Fases 1–4)
=======================================================
Fases 1-3: MF Fijo + Flexible + Salter-Swan + Sensibilidad + PDF
Fase 4:    Calibración Bolivia + Trayectoria + Análisis de Políticas

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
    page_title="Simulador Macro Abierta — Fases 1–4",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "**Simulador Macroeconómico Abierto** · Fases 1–4\n\n"
            "Mundell-Fleming + Salter-Swan + Análisis Bolivia\n"
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

# ── Fase 4 ───────────────────────────────────────────────────────────────────
from engine.state_manager import EconomicStateManager
from engine.scenario_builder import PREDEFINED_SHOCKS, apply_temporal_shock
from config.bolivia_data import list_presets, BOLIVIA_PRESETS
from utils.validators import quick_validate
from utils.exporters import export_full_session, generate_scenario_summary
from ui.calibration_panel import render_calibration_panel
from ui.timeline_viewer import render_trajectory_chart, render_state_comparison_table, render_variable_selector
from ui.scenario_cards import render_scenario_card, render_side_by_side_comparison

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

```

### Archivo: `README.md`
```markdown
# Simulador Macroeconómico Abierto

**Mundell-Fleming (IS-LM-BP) + Salter-Swan** — Ingeniería Financiera · Open Macroeconomics

Motor académico verificado contra soluciones analíticas de la Sección 3.1.
Interfaz Streamlit con análisis de sensibilidad, modo comparativo e informe PDF.

---

## Instalación y Ejecución Local

```bash
# 1. Clonar el repositorio
git clone https://github.com/<tu-usuario>/simulador-macro-abierta.git
cd simulador-macro-abierta

# 2. Crear entorno virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Copiar parámetros base
cp .env.example .env        # Opcional: edita .env para personalizar parámetros

# 5. Ejecutar la app
streamlit run main.py
```

La app abre en: `http://localhost:8501`

---

## Estructura del Proyecto

```
Simulador_Macroeconomico/
├── .env.example              # Plantilla de parámetros base
├── .streamlit/
│   └── config.toml           # Tema oscuro + configuración servidor
├── requirements.txt          # Dependencias Python
├── main.py                   # Entry point Streamlit (3 pestañas + sidebar)
│
├── config/                   # Carga de parámetros y escenarios (NO modificar)
│   ├── parameters.py         # dotenv + fallback + CRISIS_PRESETS
│   └── scenarios.py          # Serialización Parquet de escenarios
│
├── engine/                   # Motor matemático puro (NO modificar)
│   ├── core.py               # IS, LM, BP, eq_fixed(), eq_flexible()
│   ├── salter_swan.py        # q_IB(), q_EB(), get_zone()
│   └── cache.py              # Caché joblib
│
├── ui/                       # Interfaz Streamlit
│   ├── controls.py           # Sliders, presets, session_state
│   ├── charts.py             # Gráficos Plotly IS-LM y Salter-Swan
│   ├── narrative.py          # Narrativa económica automática
│   └── comparison.py         # Modo comparativo base vs actual
│
├── analysis/
│   └── sensitivity.py        # Barrido ±20%, tornado chart, Monte Carlo
│
├── report/
│   └── generator.py          # Generador PDF académico (fpdf2)
│
└── validation/
    └── test_equilibrium.py   # Verificación automática del motor
```

---

## Guía de Verificación Numérica

### Verificaciones Base (parámetros Sección 3.1)

| Verificación | Valor esperado | Comando |
|---|---|---|
| Multiplicador (mult) | 2.500 | `python -c "from engine.core import *; p=get_base_params(); print(eq_fixed(p)['mult'])"` |
| Y bajo TC fijo | 100.000 | `eq_fixed(base_params)['Y']` |
| M endógena | 40.000 | `eq_fixed(base_params)['M_endo']` |
| Y bajo TC flexible | 100.000 | `eq_flexible(base_params)['Y']` |
| E endógeno | 10.000 | `eq_flexible(base_params)['E_endo']` |

### Verificaciones de Política

```
G = 30, TC Fijo → Y = 125.00, M_endo = 52.50
  Cálculo: mult × (A + x1×E − b×r*) = 2.5 × (35 + 15×10 − 2×5)... 
  A(G=30) = 10 − 0.75×20 + 15 + 30 + 5 = 45
  Y = 2.5 × (45 + 1.5×10 − 2×5) = 2.5 × 50 = 125 ✓
  M_endo = 0.5×125 − 2×5 = 62.5 − 10 = 52.5 ✓

M = 55, TC Flexible → Y = 130.00, E_endo = 18.00
  Y = (55 + 2×5)/0.5 = 65/0.5 = 130 ✓
  E_endo = (0.40×130 + 2×5 − 35)/1.5 = (52+10−35)/1.5 = 27/1.5 = 18 ✓

Salter-Swan:
  A = 75, q = 0.75 → Zona III (déficit + desempleo) ✓
  A = 115, q = 1.30 → Zona I (superávit + sobreempleo) ✓
```

> **Nota académica:** Este simulador fue diseñado para verificar manualmente los equilibrios  
> *antes* de confiar en la IA. Ver Sección 3.2 del documento original.

---

## Despliegue en Streamlit Community Cloud (3 pasos)

### Requisitos previos
1. Cuenta en [Streamlit Community Cloud](https://streamlit.io/cloud)
2. Repositorio público en GitHub con todos los archivos del proyecto

### Pasos

**Paso 1:** Sube el proyecto a GitHub
```bash
git init
git add .
git commit -m "feat: Simulador Macro Abierta Fase 3"
git remote add origin https://github.com/<tu-usuario>/<repo>.git
git push -u origin main
```

**Paso 2:** En Streamlit Cloud
- Ve a https://share.streamlit.io
- Haz clic en **"New app"**
- Selecciona el repositorio, rama `main` y archivo `main.py`
- Haz clic en **"Deploy!"**

**Paso 3:** Verifica
- La app cargará en `https://<tu-usuario>-<repo>.streamlit.app`
- Verifica que Y=100 en estado base en las 3 pestañas

> `scikit-learn` puede fallar en Python 3.14+ (sin wheel). Si ocurre,  
> Streamlit Cloud usa Python 3.12 por defecto (compatible). Alternativamente,  
> agrega `.python-version` con contenido `3.12` a la raíz del repo.

---

## Funcionalidades por Fase

| Fase | Componentes | Estado |
|------|-------------|--------|
| **Fase 1** | Motor IS-LM-BP, Salter-Swan, validación analítica, caché joblib | ✅ Completo |
| **Fase 2** | Interfaz Streamlit, gráficos Plotly, narrativa, exportación CSV | ✅ Completo |
| **Fase 3** | Modo comparativo, sensibilidad, Monte Carlo, informe PDF | ✅ Completo |

---

## Notas Académicas

- **Motor validado:** Todas las ecuaciones coinciden con la Sección 3.1 (tolerancia < 0.01).
- **Funciones puras:** `engine/core.py` y `engine/salter_swan.py` no tienen efectos laterales.
- **Caché:** `joblib.Memory` + `@st.cache_data` evitan recálculos en reruns de Streamlit.
- **Exportación:** Resultados en CSV y Parquet; informe en PDF académico con 5 secciones.
- **Sensibilidad:** Barrido ±20% con 20 puntos por parámetro; tornado chart de impacto relativo.

```

### Archivo: `requirements.txt`
```text
streamlit>=1.32.0
pandas>=2.2.0
plotly>=5.19.0
joblib>=1.3.2
pyarrow>=15.0.0
python-dotenv>=1.0.1
numpy>=1.26.0
fpdf2>=2.7.9
matplotlib>=3.8.0
kaleido>=0.2.1
scikit-learn>=1.4.0

```

### Archivo: `verify_phase2.py`
```python
"""Script de verificacion numerica completa de Fase 2."""
import sys
sys.path.insert(0, ".")

from config.parameters import get_base_params, CRISIS_PRESETS
from engine.core import eq_fixed, eq_flexible, autonomous_demand, is_curve, lm_curve
from engine.salter_swan import get_zone
from engine.cache import cached_eq_fixed, cached_eq_flexible
from ui.charts import plot_islm_fixed, plot_islm_flexible, plot_salter_swan
from ui.narrative import generate_fixed_narrative, generate_flexible_narrative, generate_salter_narrative
from utils.export import export_scenario

p = get_base_params()
f = eq_fixed(p)
x = eq_flexible(p)

# Base checks
assert abs(f["mult"] - 2.5) < 0.01
assert abs(f["Y"] - 100.0) < 0.01
assert abs(f["M_endo"] - 40.0) < 0.01
assert abs(x["Y"] - 100.0) < 0.01
assert abs(x["E_endo"] - 10.0) < 0.01
print("BASE: OK")

# G=30 fijo -> Y=125, M=52.5
p30 = dict(p); p30["G"] = 30.0
f30 = eq_fixed(p30)
assert abs(f30["Y"] - 125.0) < 0.1, f"Y={f30['Y']}"
assert abs(f30["M_endo"] - 52.5) < 0.1, f"M={f30['M_endo']}"
print(f"G=30 FIJO -> Y={f30['Y']:.2f}, M_endo={f30['M_endo']:.2f}: OK")

# M=55 flexible -> Y=130, E~17.5
p55 = dict(p); p55["M"] = 55.0
x55 = eq_flexible(p55)
assert abs(x55["Y"] - 130.0) < 0.1, f"Y={x55['Y']}"
assert abs(x55["E_endo"] - 18.0) < 0.1, f"E={x55['E_endo']}"  # analitico: (0.40*130+10-35)/1.5=18.0
print(f"M=55 FLEXIBLE -> Y={x55['Y']:.2f}, E_endo={x55['E_endo']:.4f}: OK")

# Salter-Swan zonas
z3 = get_zone(75.0, 0.75)
assert z3["zone"] == "III", f"zona={z3['zone']}"
z1 = get_zone(115.0, 1.3)
assert z1["zone"] == "I", f"zona={z1['zone']}"
z2 = get_zone(88.0, 1.15)
z4 = get_zone(115.0, 0.8)
print(f"Salter zonas -> A=75 q=0.75: {z3['zone']}, A=115 q=1.3: {z1['zone']}")
print(f"               A=88 q=1.15: {z2['zone']}, A=115 q=0.8: {z4['zone']}: OK")

# Narrativas
n = generate_fixed_narrative(10, 0, 0, 0, f30["Y"], f30["M_endo"], f30["NX"], f30["mult"])
assert len(n) > 50
print("Narrativa fijo: OK")

n2 = generate_flexible_narrative(0, 0, 15, 0, x55["Y"], x55["E_endo"], x55["NX"], x55["mult"])
assert len(n2) > 50
print("Narrativa flexible: OK")

# Export
df = export_scenario("fixed", p, p30, dict(f), dict(f30))
assert "Delta" in df.columns
assert len(df) > 5
delta_Y_row = df[df["Variable"].str.contains("PIB")]["Delta"].values
assert abs(delta_Y_row[0] - 25.0) < 0.5, f"Delta Y={delta_Y_row[0]}"
print(f"Export CSV -> Delta Y = {delta_Y_row[0]:.2f}: OK")

# Graficos (sin Streamlit, solo verifica que retorna Figure)
import plotly.graph_objects as go
fig1 = plot_islm_fixed(f30["Y"], f30["r"], p, p30)
fig2 = plot_islm_flexible(x55["Y"], x55["r"], p, p55)
z_bliss = get_zone(100.0, 1.0)
fig3 = plot_salter_swan(100.0, 1.0, z_bliss)
assert all(isinstance(f_, go.Figure) for f_ in [fig1, fig2, fig3])
print("Graficos Plotly: OK")

print("\nALL PHASE 2 VERIFICATIONS PASSED")

```

### Archivo: `analysis\sensitivity.py`
```python
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

```

### Archivo: `analysis\__init__.py`
```python
# analysis package — Fase 3: Análisis de sensibilidad

```

### Archivo: `config\bolivia_data.py`
```python
"""
config/bolivia_data.py
======================
Presets históricos de Bolivia para calibración del modelo Mundell-Fleming.
Fase 4 — Plataforma de Análisis de Políticas.

Fuentes de referencia (aproximadas para calibración académica):
    - INE Bolivia: Indicadores macroeconómicos 2008–2024
    - CEPAL: Anuario estadístico de América Latina y el Caribe
    - BCB: Boletín del Sector Externo

Convención de parámetros (compatibles con engine/core.py):
    c0, c1, I0, NX0, b, m1, x1, k, h, G, T, E, r_star, M
"""

from __future__ import annotations

from typing import Literal

# ── Tipo de régimen cambiario ─────────────────────────────────────────────────
ExchangeRegime = Literal["fixed", "flexible", "managed_float", "de_facto_fixed"]
CapitalMobility = Literal["perfect", "imperfect", "low"]
EconomySize     = Literal["small_open", "large_semi_closed"]


# ── Presets históricos Bolivia ────────────────────────────────────────────────
# Todos los parámetros son compatibles con eq_fixed() y eq_flexible() de core.py
# Los valores son calibraciones académicas basadas en proporciones del PIB.
# El modelo opera en unidades relativas; Y_base≈100 representa el PIB normalizado.

BOLIVIA_PRESETS: dict[str, dict] = {

    # ── 2024: Estanflación y restricción de divisas ───────────────────────────
    "Bolivia_2024_Stagflation": {
        # Metadatos económicos
        "_meta": {
            "label":            "Bolivia 2024 — Estanflación",
            "description":      (
                "Economía bajo presión de reservas internacionales (< 3.2 meses de importaciones), "
                "déficit fiscal persistente (~4.5% PIB), baja inversión privada por incertidumbre "
                "cambiaria, y tipo de cambio de facto fijo ante escasez de divisas."
            ),
            "GDP_nominal_usd":       45e9,
            "GDP_growth_pct":        1.2,
            "unemployment_pct":      3.8,
            "inflation_pct":         3.2,
            "fiscal_balance_pct_gdp": -4.5,
            "reserves_months_imports": 3.2,
            "exchange_regime":       "de_facto_fixed",
            "capital_mobility":      "imperfect",
            "openness_ratio":        0.42,
        },
        # Parámetros del modelo (normalizados, Y_base≈100)
        "c0":    8.0,    # Consumo autónomo bajo (incertidumbre alta)
        "c1":    0.78,   # PMgC relativamente alta (falta de ahorro)
        "I0":   -5.0,    # Inversión autónoma negativa (contracción privada)
        "NX0":  -3.0,    # Déficit estructural de exportaciones netas
        "b":     2.2,    # Sensibilidad inversión a r (moderada)
        "m1":    0.22,   # PMgM alta (dependencia de importaciones)
        "x1":    1.3,    # Elasticidad export–TC reducida (exportaciones primarias inelásticas)
        "k":     0.45,   # Demanda dinero–ingreso (baja dolarización informal)
        "h":     1.8,    # Demanda dinero–tasa (moderada)
        "G":     18.0,   # Gasto público ajustado (presión fiscal)
        "T":     14.0,   # Carga impositiva moderada
        "E":     6.96,   # Tipo de cambio nominal oficial (Bs/USD ≈ 6.96)
        "r_star": 8.0,   # Prima de riesgo país elevada (EMBIG Bolivia)
        "M":     35.0,   # Oferta monetaria reducida (restricción BCB)
    },

    # ── 2019: Precrisis política y desaceleración ─────────────────────────────
    "Bolivia_2019_PreCrisis": {
        "_meta": {
            "label":            "Bolivia 2019 — Precrisis Política",
            "description":      (
                "Año de turbulencia política post-elecciones. Desaceleración del crecimiento "
                "desde niveles del boom, reservas aún aceptables (~7 meses de importaciones), "
                "pero inicio de la caída del precio del gas y presión en la cuenta corriente."
            ),
            "GDP_nominal_usd":       40.9e9,
            "GDP_growth_pct":        2.2,
            "unemployment_pct":      4.0,
            "inflation_pct":         1.8,
            "fiscal_balance_pct_gdp": -7.2,
            "reserves_months_imports": 7.0,
            "exchange_regime":       "de_facto_fixed",
            "capital_mobility":      "imperfect",
            "openness_ratio":        0.45,
        },
        "c0":    10.0,
        "c1":    0.75,
        "I0":     5.0,
        "NX0":    0.5,
        "b":      2.5,
        "m1":     0.20,
        "x1":     1.4,
        "k":      0.48,
        "h":      2.0,
        "G":      22.0,
        "T":      16.0,
        "E":      6.91,
        "r_star":  6.0,
        "M":      42.0,
    },

    # ── 2014: Auge de materias primas ─────────────────────────────────────────
    "Bolivia_2014_Boom": {
        "_meta": {
            "label":            "Bolivia 2014 — Boom de Materias Primas",
            "description":      (
                "Pico del superciclo de materias primas. Superávit fiscal y comercial, "
                "alto precio del gas, reservas internacionales en máximos históricos "
                "(~15 meses de importaciones). Inversión pública masiva y crecimiento > 5%."
            ),
            "GDP_nominal_usd":       33.0e9,
            "GDP_growth_pct":        5.5,
            "unemployment_pct":      3.5,
            "inflation_pct":         5.2,
            "fiscal_balance_pct_gdp": 1.8,
            "reserves_months_imports": 15.0,
            "exchange_regime":       "de_facto_fixed",
            "capital_mobility":      "imperfect",
            "openness_ratio":        0.55,
        },
        "c0":    12.0,
        "c1":    0.72,
        "I0":    12.0,
        "NX0":    8.0,
        "b":      2.8,
        "m1":     0.18,
        "x1":     1.8,
        "k":      0.52,
        "h":      2.2,
        "G":      28.0,
        "T":      20.0,
        "E":      6.87,
        "r_star":  4.0,
        "M":      55.0,
    },

    # ── 2008: Crisis financiera global ────────────────────────────────────────
    "Bolivia_2008_GlobalCrisis": {
        "_meta": {
            "label":            "Bolivia 2008 — Crisis Financiera Global",
            "description":      (
                "Impacto de la crisis financiera global. Caída de exportaciones, "
                "presión sobre el tipo de cambio (Bolivia devalúa levemente), "
                "pero colchón de reservas permite amortiguación. Primer año sin superávit fiscal."
            ),
            "GDP_nominal_usd":       16.7e9,
            "GDP_growth_pct":        6.1,
            "unemployment_pct":      6.7,
            "inflation_pct":        11.8,
            "fiscal_balance_pct_gdp": -0.5,
            "reserves_months_imports": 10.0,
            "exchange_regime":       "managed_float",
            "capital_mobility":      "low",
            "openness_ratio":        0.62,
        },
        "c0":    9.0,
        "c1":    0.70,
        "I0":    8.0,
        "NX0":   5.0,
        "b":     2.0,
        "m1":    0.16,
        "x1":    1.6,
        "k":     0.50,
        "h":     1.5,
        "G":     24.0,
        "T":     18.0,
        "E":     7.07,
        "r_star": 7.5,
        "M":     38.0,
    },

    # ── Hipotético: Ajuste y liberalización ───────────────────────────────────
    "Bolivia_Hypothetical_Reform": {
        "_meta": {
            "label":            "Bolivia Hipotético — Reforma Estructural",
            "description":      (
                "Escenario hipotético de reforma: liberalización parcial del tipo de cambio, "
                "reducción del déficit fiscal, mejora de reservas internacionales y "
                "apertura a inversión extranjera. Sirve como benchmark de política óptima."
            ),
            "GDP_nominal_usd":       50e9,
            "GDP_growth_pct":        4.0,
            "unemployment_pct":      4.5,
            "inflation_pct":         4.0,
            "fiscal_balance_pct_gdp": -2.0,
            "reserves_months_imports": 8.0,
            "exchange_regime":       "managed_float",
            "capital_mobility":      "imperfect",
            "openness_ratio":        0.50,
        },
        "c0":    11.0,
        "c1":    0.73,
        "I0":    10.0,
        "NX0":   2.0,
        "b":     2.5,
        "m1":    0.19,
        "x1":    1.6,
        "k":     0.48,
        "h":     2.0,
        "G":     20.0,
        "T":     17.0,
        "E":     7.50,
        "r_star": 5.5,
        "M":     40.0,
    },
}


# ── Funciones públicas ────────────────────────────────────────────────────────

def get_bolivia_params(key: str) -> dict[str, float]:
    """
    Retorna los parámetros del modelo para un preset boliviano dado.
    Filtra los metadatos (_meta) y retorna solo parámetros numéricos
    compatibles con eq_fixed() y eq_flexible() de engine/core.py.

    Parameters
    ----------
    key : str
        Clave del preset en BOLIVIA_PRESETS.
        Opciones: 'Bolivia_2024_Stagflation', 'Bolivia_2019_PreCrisis',
                  'Bolivia_2014_Boom', 'Bolivia_2008_GlobalCrisis',
                  'Bolivia_Hypothetical_Reform'

    Returns
    -------
    dict[str, float]
        Parámetros listos para pasar a eq_fixed() o eq_flexible().

    Raises
    ------
    KeyError
        Si el key no existe en BOLIVIA_PRESETS.
    """
    if key not in BOLIVIA_PRESETS:
        available = list(BOLIVIA_PRESETS.keys())
        raise KeyError(
            f"Preset '{key}' no encontrado. Disponibles: {available}"
        )
    raw = BOLIVIA_PRESETS[key]
    # Retorna solo claves numéricas (excluye _meta)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def get_bolivia_meta(key: str) -> dict:
    """
    Retorna los metadatos económicos de un preset boliviano.

    Parameters
    ----------
    key : str
        Clave del preset en BOLIVIA_PRESETS.

    Returns
    -------
    dict con GDP_nominal_usd, GDP_growth_pct, unemployment_pct, etc.
    """
    if key not in BOLIVIA_PRESETS:
        return {}
    return BOLIVIA_PRESETS[key].get("_meta", {})


def classify_economy_size(GDP_usd: float, openness_ratio: float) -> EconomySize:
    """
    Clasifica el tamaño relativo de la economía según el PIB nominal
    y el ratio de apertura comercial (exportaciones + importaciones / PIB).

    Criterios (académicos, no oficiales):
        - small_open  : PIB < 100 billion USD Y openness_ratio > 0.35
        - large_semi_closed : PIB >= 100 billion USD O openness_ratio <= 0.35

    Parameters
    ----------
    GDP_usd : float
        PIB nominal en USD.
    openness_ratio : float
        (Exportaciones + Importaciones) / PIB. Rango [0, 1].

    Returns
    -------
    EconomySize : "small_open" | "large_semi_closed"
    """
    if GDP_usd < 100e9 and openness_ratio > 0.35:
        return "small_open"
    return "large_semi_closed"


def list_presets() -> list[dict]:
    """
    Retorna lista de presets con clave, label y descripción para UI.

    Returns
    -------
    list[dict] con keys: 'key', 'label', 'description', 'year_approx'
    """
    result = []
    for key, data in BOLIVIA_PRESETS.items():
        meta = data.get("_meta", {})
        result.append({
            "key":         key,
            "label":       meta.get("label", key),
            "description": meta.get("description", ""),
            "exchange_regime":   meta.get("exchange_regime", "—"),
            "capital_mobility":  meta.get("capital_mobility", "—"),
            "GDP_growth_pct":    meta.get("GDP_growth_pct", float("nan")),
            "inflation_pct":     meta.get("inflation_pct", float("nan")),
        })
    return result

```

### Archivo: `config\parameters.py`
```python
"""
config/parameters.py
====================
Carga de parámetros base del modelo Mundell-Fleming + Salter-Swan.
Fuente: Sección 3.1 del documento de referencia académico.

Responsabilidades:
    - Cargar .env con python-dotenv (fallback a valores hardcoded).
    - Exportar get_base_params() → dict tipado.
    - Definir CRISIS_PRESETS con escenarios de crisis económica.
    - Exportar apply_shocks() → fusiona parámetros base con preset.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# ── Carga del archivo .env (si existe) ──────────────────────────────────────
_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)

# ── Fallback: valores hardcoded de la Sección 3.1 ───────────────────────────
_FALLBACK: dict[str, float] = {
    "c0":     10.0,    # Consumo autónomo
    "c1":     0.75,    # Propensión marginal a consumir
    "I0":     15.0,    # Inversión autónoma
    "NX0":    5.0,     # Exportaciones netas autónomas
    "b":      2.0,     # Sensibilidad inversión–tasa de interés
    "m1":     0.15,    # Sensibilidad demanda dinero–ingreso (también 'k')
    "x1":     1.5,     # Sensibilidad exportaciones–tipo de cambio
    "k":      0.5,     # Parámetro k de la curva LM
    "h":      2.0,     # Sensibilidad demanda dinero–tasa de interés
    "G":      20.0,    # Gasto de gobierno
    "T":      20.0,    # Impuestos lump-sum
    "E":      10.0,    # Tipo de cambio nominal (régimen fijo)
    "r_star": 5.0,     # Tasa de interés internacional
    "M":      40.0,    # Oferta de dinero (régimen flexible)
}

# Mapa de variables de entorno → clave interna del modelo
_ENV_MAP: dict[str, str] = {
    "BASE_C0":   "c0",
    "BASE_C1":   "c1",
    "BASE_I0":   "I0",
    "BASE_NX0":  "NX0",
    "BASE_B":    "b",
    "BASE_M1":   "m1",
    "BASE_X1":   "x1",
    "BASE_K_LM": "k",
    "BASE_H":    "h",
    "BASE_G":    "G",
    "BASE_T":    "T",
    "BASE_E":    "E",
    "BASE_RS":   "r_star",
    "BASE_M":    "M",
}

# ── Presets de crisis económica ──────────────────────────────────────────────
CRISIS_PRESETS: dict[str, dict[str, float]] = {
    # Bolivia 2024 — Estanflación con restricción de divisas y caída de reservas
    "Bolivia_2024_Stagflation": {
        "NX0":    -3.0,   # Déficit de exportaciones netas
        "I0":     -5.0,   # Contracción de inversión privada
        "G":      15.0,   # Ajuste fiscal (reducción del gasto)
        "c1":     0.65,   # Caída en propensión marginal (incertidumbre)
        "r_star":  8.0,   # Prima de riesgo país elevada
        "m1":     0.25,   # Mayor demanda de liquidez preventiva
        "x1":      1.0,   # Menor elasticidad de exportaciones al tipo de cambio
        "h":       1.2,   # Menor sensibilidad de demanda dinero a tasa de interés
    },
    # Shock de demanda externa positivo (escenario de bonanza)
    "Boom_Exportador": {
        "NX0":    15.0,
        "x1":      2.0,
        "r_star":  3.0,
        "G":      22.0,
    },
    # Crisis de liquidez / credit crunch
    "Credit_Crunch": {
        "I0":    -10.0,
        "c1":     0.60,
        "h":      0.8,
        "r_star": 10.0,
        "G":      25.0,
    },
}


def get_base_params() -> dict[str, float]:
    """
    Retorna el diccionario de parámetros base del modelo.

    Prioridad:
        1. Variables de entorno definidas en .env
        2. Valores fallback hardcoded de la Sección 3.1

    Returns
    -------
    dict[str, float]
        Parámetros tipados del modelo macroeconómico.
    """
    params: dict[str, float] = dict(_FALLBACK)  # copia defensiva

    for env_key, param_key in _ENV_MAP.items():
        raw = os.environ.get(env_key)
        if raw is not None:
            try:
                params[param_key] = float(raw)
            except ValueError:
                # Mantiene el fallback si el valor en .env no es numérico
                pass

    return params


def apply_shocks(
    base_params: dict[str, float],
    preset_key: str,
) -> dict[str, float]:
    """
    Fusiona los parámetros base con un preset de crisis.

    Parameters
    ----------
    base_params : dict[str, float]
        Parámetros base obtenidos de get_base_params().
    preset_key : str
        Clave del preset en CRISIS_PRESETS.

    Returns
    -------
    dict[str, float]
        Parámetros fusionados (base + shocks del preset).

    Raises
    ------
    KeyError
        Si el preset_key no existe en CRISIS_PRESETS.
    """
    if preset_key not in CRISIS_PRESETS:
        available = list(CRISIS_PRESETS.keys())
        raise KeyError(
            f"Preset '{preset_key}' no encontrado. "
            f"Opciones disponibles: {available}"
        )

    shocked: dict[str, float] = dict(base_params)
    shocked.update(CRISIS_PRESETS[preset_key])
    return shocked

```

### Archivo: `config\scenarios.py`
```python
"""
config/scenarios.py
===================
Gestión de escenarios macroeconómicos con pandas + pyarrow.

Responsabilidades:
    - Ejecutar el modelo bajo distintos regímenes y presets.
    - Serializar resultados en formato Parquet para lectura eficiente.
    - Proveer load_all_scenarios() para Streamlit/Plotly en Fase 2.

Convención de archivos Parquet:
    .scenarios/{regime}_{preset_key}.parquet
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from config.parameters import apply_shocks, get_base_params
from engine.core import eq_fixed, eq_flexible

# ── Directorio de salida ─────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent
_SCENARIOS_DIR = _PROJECT_ROOT / ".scenarios"
_SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)

# Tipo literal para régimen cambiario
Regime = Literal["fixed", "flexible"]


# ── Schema pyarrow para validación de tipos ──────────────────────────────────
_SCENARIO_SCHEMA = pa.schema([
    pa.field("scenario",  pa.string()),
    pa.field("regime",    pa.string()),
    pa.field("preset",    pa.string()),
    pa.field("Y",         pa.float64()),
    pa.field("r",         pa.float64()),
    pa.field("M_endo",    pa.float64()),   # solo TC fijo
    pa.field("E_endo",    pa.float64()),   # solo TC flexible
    pa.field("E_fixed",   pa.float64()),   # solo TC fijo
    pa.field("M_fixed",   pa.float64()),   # solo TC flexible
    pa.field("NX",        pa.float64()),
    pa.field("C",         pa.float64()),
    pa.field("I_inv",     pa.float64()),
    pa.field("mult",      pa.float64()),
])


# ── Funciones públicas ────────────────────────────────────────────────────────

def run_scenario(
    regime: Regime,
    preset_key: str,
    base_params: dict[str, float] | None = None,
) -> pd.DataFrame:
    """
    Ejecuta el modelo bajo un régimen y preset dados, y persiste en Parquet.

    Parameters
    ----------
    regime : "fixed" | "flexible"
        Régimen cambiario a simular.
    preset_key : str
        Clave del preset en CRISIS_PRESETS, o "base" para usar parámetros base.
    base_params : dict | None
        Parámetros base. Si None, usa get_base_params().

    Returns
    -------
    pd.DataFrame : DataFrame tipado con resultados del equilibrio.
    """
    if base_params is None:
        base_params = get_base_params()

    # Aplicar shocks si no es escenario base
    if preset_key.lower() == "base":
        params = dict(base_params)
    else:
        params = apply_shocks(base_params, preset_key)

    # Calcular equilibrio según régimen
    if regime == "fixed":
        result = eq_fixed(params)
        row = {
            "scenario":  f"{preset_key}_{regime}",
            "regime":    regime,
            "preset":    preset_key,
            "Y":         result["Y"],
            "r":         result["r"],
            "M_endo":    result["M_endo"],
            "E_endo":    float("nan"),           # No aplica en TC fijo
            "E_fixed":   result["E"],
            "M_fixed":   float("nan"),
            "NX":        result["NX"],
            "C":         result["C"],
            "I_inv":     result["I_inv"],
            "mult":      result["mult"],
        }
    else:  # flexible
        result = eq_flexible(params)
        row = {
            "scenario":  f"{preset_key}_{regime}",
            "regime":    regime,
            "preset":    preset_key,
            "Y":         result["Y"],
            "r":         result["r"],
            "M_endo":    float("nan"),
            "E_endo":    result["E_endo"],
            "E_fixed":   float("nan"),
            "M_fixed":   result["M"],
            "NX":        result["NX"],
            "C":         result["C"],
            "I_inv":     result["I_inv"],
            "mult":      result["mult"],
        }

    # Construir DataFrame con tipo pyarrow
    df = pd.DataFrame([row])

    # Serializar a Parquet
    parquet_path = _SCENARIOS_DIR / f"{preset_key}_{regime}.parquet"
    table = pa.Table.from_pandas(df, schema=_SCENARIO_SCHEMA, preserve_index=False)
    pq.write_table(table, str(parquet_path), compression="snappy")

    return df


def load_all_scenarios() -> pd.DataFrame:
    """
    Carga todos los escenarios Parquet disponibles y los concatena.

    Returns
    -------
    pd.DataFrame
        DataFrame unificado con todos los escenarios guardados.
        Retorna DataFrame vacío si no hay archivos Parquet.
    """
    parquet_files = sorted(_SCENARIOS_DIR.glob("*.parquet"))

    if not parquet_files:
        return pd.DataFrame()

    tables = [pq.read_table(str(f)) for f in parquet_files]
    combined = pa.concat_tables(tables)
    return combined.to_pandas()


def run_all_base_scenarios(
    base_params: dict[str, float] | None = None,
) -> pd.DataFrame:
    """
    Ejecuta los 4 escenarios canónicos del modelo:
        - Base × Fijo
        - Base × Flexible
        - Bolivia_2024_Stagflation × Fijo
        - Bolivia_2024_Stagflation × Flexible

    Parameters
    ----------
    base_params : dict | None
        Parámetros base. Si None, usa get_base_params().

    Returns
    -------
    pd.DataFrame : Tabla comparativa de los 4 escenarios.
    """
    if base_params is None:
        base_params = get_base_params()

    frames = []
    for preset in ["base", "Bolivia_2024_Stagflation"]:
        for regime in ("fixed", "flexible"):
            df = run_scenario(regime=regime, preset_key=preset, base_params=base_params)
            frames.append(df)

    return pd.concat(frames, ignore_index=True)

```

### Archivo: `config\validation_rules.py`
```python
"""
config/validation_rules.py
==========================
Reglas de validación por variable del modelo Mundell-Fleming.
Fase 4 — Plataforma de Análisis de Políticas.

Exporta:
    VALIDATION_RULES : dict[str, dict] — reglas por variable
    validate_params(params_dict) → (bool, list[str], list[str])
"""

from __future__ import annotations

# ── Reglas por variable ───────────────────────────────────────────────────────
# Cada entrada: {min, max, step, unit, warning_if_extreme, economic_rationale}

VALIDATION_RULES: dict[str, dict] = {

    # ── Propensión marginal a consumir ────────────────────────────────────────
    "c1": {
        "min":      0.30,
        "max":      0.95,
        "step":     0.01,
        "unit":     "",
        "label":    "Propensión marginal a consumir (c₁)",
        "warning":  "PMgC > 0.90 implica ahorro muy bajo; inestabilidad del multiplicador.",
        "rationale": (
            "Fracción de cada unidad adicional de ingreso disponible que se destina al consumo. "
            "Valores típicos para economías en desarrollo: 0.65–0.85."
        ),
    },

    # ── Propensión marginal a importar ────────────────────────────────────────
    "m1": {
        "min":      0.05,
        "max":      0.50,
        "step":     0.01,
        "unit":     "",
        "label":    "Propensión marginal a importar (m₁)",
        "warning":  "m₁ > 0.40 indica alta dependencia de importaciones; multiplicador muy reducido.",
        "rationale": (
            "Fracción del ingreso adicional que se filtra al exterior vía importaciones. "
            "Para Bolivia, valores históricos: 0.15–0.25."
        ),
    },

    # ── Elasticidad exportaciones–tipo de cambio ──────────────────────────────
    "x1": {
        "min":      0.10,
        "max":      4.00,
        "step":     0.10,
        "unit":     "",
        "label":    "Elasticidad exportaciones al TC (x₁)",
        "warning":  "x₁ < 0.5 sugiere exportaciones muy inelásticas (productos primarios dominantes).",
        "rationale": (
            "Sensibilidad de las exportaciones netas al tipo de cambio nominal. "
            "Bolivia: exportaciones primarias (gas, minerales) tienen baja elasticidad cambiaria."
        ),
    },

    # ── Sensibilidad inversión–tasa de interés ────────────────────────────────
    "b": {
        "min":      0.50,
        "max":      8.00,
        "step":     0.10,
        "unit":     "",
        "label":    "Sensibilidad inversión a r (b)",
        "warning":  "b > 6.0 implica inversión muy sensible a tasas; poco realista para Bolivia.",
        "rationale": (
            "Mide cuánto cae la inversión privada por cada punto porcentual de alza en r. "
            "Valores bajos reflejan predominio de inversión pública poco sensible a tasas."
        ),
    },

    # ── Sensibilidad demanda dinero–ingreso ───────────────────────────────────
    "k": {
        "min":      0.10,
        "max":      1.00,
        "step":     0.01,
        "unit":     "",
        "label":    "Sensibilidad demanda de dinero a Y (k)",
        "warning":  "k > 0.9 implica demanda de dinero excesivamente ligada al ingreso.",
        "rationale": (
            "Determina la pendiente de la curva LM. En economías con dolarización informal, "
            "k tiende a ser menor porque parte de las transacciones usan moneda extranjera."
        ),
    },

    # ── Sensibilidad demanda dinero–tasa de interés ───────────────────────────
    "h": {
        "min":      0.20,
        "max":      8.00,
        "step":     0.10,
        "unit":     "",
        "label":    "Sensibilidad demanda de dinero a r (h)",
        "warning":  "h muy alto → LM casi horizontal (trampa de liquidez). h muy bajo → LM vertical.",
        "rationale": (
            "Controla la pendiente de la curva LM. h alto → política monetaria menos efectiva "
            "en régimen flexible (LM plana). Bolivia: valores moderados (1.5–2.5)."
        ),
    },

    # ── Gasto de Gobierno ─────────────────────────────────────────────────────
    "G": {
        "min":      0.0,
        "max":      60.0,
        "step":     0.5,
        "unit":     "% PIB normalizado",
        "label":    "Gasto de Gobierno (G)",
        "warning":  "G > 40 implica tamaño del Estado muy alto; puede generar crowding-out.",
        "rationale": (
            "Gasto público que desplaza la curva IS a la derecha. "
            "Bajo TC fijo: política fiscal plenamente efectiva (teorema de Mundell-Fleming)."
        ),
    },

    # ── Impuestos ─────────────────────────────────────────────────────────────
    "T": {
        "min":      0.0,
        "max":      60.0,
        "step":     0.5,
        "unit":     "% PIB normalizado",
        "label":    "Impuestos lump-sum (T)",
        "warning":  "T > 35 puede deprimir el consumo privado significativamente.",
        "rationale": (
            "Impuesto de suma alzada que reduce el ingreso disponible: ↑T → ↓C → IS se contrae."
        ),
    },

    # ── Tipo de cambio nominal ────────────────────────────────────────────────
    "E": {
        "min":      1.0,
        "max":      30.0,
        "step":     0.10,
        "unit":     "Bs/USD (o unidades modelo)",
        "label":    "Tipo de Cambio Nominal (E)",
        "warning":  "E < 2 o E > 25 son extremos poco realistas para el modelo académico.",
        "rationale": (
            "Precio de la moneda extranjera. ↑E = depreciación → ↑competitividad → ↑NX. "
            "Bolivia mantiene E≈6.96 Bs/USD de facto desde 2011."
        ),
    },

    # ── Tasa de interés internacional ─────────────────────────────────────────
    "r_star": {
        "min":      0.0,
        "max":      25.0,
        "step":     0.25,
        "unit":     "% anual",
        "label":    "Tasa de interés internacional (r*)",
        "warning":  "r* > 15% puede reflejar crisis de deuda soberana o restricción severa.",
        "rationale": (
            "Bajo movilidad perfecta de capitales (Mundell-Fleming), la tasa doméstica "
            "se iguala a r*. Para Bolivia: r* incluye LIBOR/SOFR + prima de riesgo país."
        ),
    },

    # ── Oferta monetaria (TC flexible) ────────────────────────────────────────
    "M": {
        "min":      5.0,
        "max":      150.0,
        "step":     1.0,
        "unit":     "unidades modelo",
        "label":    "Oferta Monetaria (M)",
        "warning":  "M muy baja puede generar Y negativo en TC flexible. Verifique equilibrio.",
        "rationale": (
            "Exógena bajo TC flexible: el BCB controla M y E se ajusta endógenamente. "
            "Bajo TC fijo: M es endógena (el BCB pierde control de la oferta monetaria)."
        ),
    },

    # ── Consumo autónomo ──────────────────────────────────────────────────────
    "c0": {
        "min":      0.0,
        "max":      30.0,
        "step":     0.5,
        "unit":     "unidades modelo",
        "label":    "Consumo autónomo (c₀)",
        "warning":  "c₀ < 2 implica consumo base muy bajo; posible economía de subsistencia.",
        "rationale": (
            "Componente del consumo independiente del ingreso. Incluye consumo de subsistencia "
            "y gasto financiado con ahorro pasado o crédito."
        ),
    },

    # ── Inversión autónoma ────────────────────────────────────────────────────
    "I0": {
        "min":     -20.0,
        "max":      40.0,
        "step":     0.5,
        "unit":     "unidades modelo",
        "label":    "Inversión autónoma (I₀)",
        "warning":  "I₀ negativo (contracción) puede indicar crisis de confianza o credit crunch.",
        "rationale": (
            "Inversión independiente de la tasa de interés. Valores negativos son válidos "
            "en crisis cuando la inversión cae por debajo del nivel base."
        ),
    },

    # ── Exportaciones netas autónomas ─────────────────────────────────────────
    "NX0": {
        "min":     -20.0,
        "max":      30.0,
        "step":     0.5,
        "unit":     "unidades modelo",
        "label":    "Exportaciones netas autónomas (NX₀)",
        "warning":  "NX₀ < -10 indica déficit estructural severo en balanza comercial.",
        "rationale": (
            "Componente autónomo del saldo de la balanza comercial. "
            "Bolivia 2024: NX₀ negativo por caída de exportaciones de gas y mayor demanda de importaciones."
        ),
    },
}


# ── Función de validación ─────────────────────────────────────────────────────

def validate_params(params: dict) -> tuple[bool, list[str], list[str]]:
    """
    Valida un diccionario de parámetros contra VALIDATION_RULES.

    Parameters
    ----------
    params : dict
        Diccionario con parámetros del modelo (claves como 'c1', 'm1', etc.).

    Returns
    -------
    tuple[bool, list[str], list[str]]
        - is_valid : bool — True si no hay errores (warnings no bloquean)
        - errors   : list[str] — mensajes de error (fuera de rango min/max)
        - warnings : list[str] — mensajes de advertencia (valores extremos)
    """
    errors: list[str] = []
    warnings: list[str] = []

    for var, rule in VALIDATION_RULES.items():
        if var not in params:
            continue  # No validar variables ausentes

        val = params[var]
        label = rule.get("label", var)
        vmin  = rule["min"]
        vmax  = rule["max"]

        # Error: fuera de rango absoluto
        if val < vmin:
            errors.append(
                f"❌ {label}: {val:.4g} < mínimo permitido ({vmin})"
            )
        elif val > vmax:
            errors.append(
                f"❌ {label}: {val:.4g} > máximo permitido ({vmax})"
            )
        else:
            # Warning: valores en zona extrema (25% de los extremos)
            rango = vmax - vmin
            umbral_bajo = vmin + 0.10 * rango
            umbral_alto  = vmax - 0.10 * rango
            if val <= umbral_bajo or val >= umbral_alto:
                warn_msg = rule.get("warning", "")
                if warn_msg:
                    warnings.append(f"⚠️ {label} = {val:.4g}: {warn_msg}")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def get_rule(var: str) -> dict:
    """
    Retorna la regla de validación para una variable específica.
    Retorna dict vacío si no existe.
    """
    return VALIDATION_RULES.get(var, {})

```

### Archivo: `config\__init__.py`
```python
# config package

```

### Archivo: `engine\cache.py`
```python
"""
engine/cache.py
===============
Sistema de caché de equilibrios usando joblib.Memory.

Propósito:
    - Evitar recalcular equilibrios idénticos en reruns de Streamlit.
    - Serializar resultados a disco para persistencia entre sesiones.
    - Proporcionar un decorador @cache_equilibrium listo para Fase 2.

Ruta de caché: .cache/equilibrium_cache
    (relativa al directorio raíz del proyecto)
"""

from __future__ import annotations

import functools
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, TypeVar

import joblib

# ── Configuración del directorio de caché ────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent
_CACHE_DIR = _PROJECT_ROOT / ".cache" / "equilibrium_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Instancia de memoria joblib
memory = joblib.Memory(
    location=str(_CACHE_DIR),
    verbose=0,   # Sin output en consola (Streamlit-friendly)
    backend="local",
)

# ── Tipo genérico para decoradores ───────────────────────────────────────────
F = TypeVar("F", bound=Callable[..., Any])


# ── Funciones cacheadas ──────────────────────────────────────────────────────

@memory.cache
def _cached_eq_fixed(params_frozen: str) -> dict[str, float]:
    """
    Versión cacheada interna de eq_fixed.
    Recibe los parámetros serializados como JSON string (hasheable por joblib).
    """
    from engine.core import eq_fixed  # Import local para evitar circularidad
    params = json.loads(params_frozen)
    return dict(eq_fixed(params))


@memory.cache
def _cached_eq_flexible(params_frozen: str) -> dict[str, float]:
    """
    Versión cacheada interna de eq_flexible.
    Recibe los parámetros serializados como JSON string (hasheable por joblib).
    """
    from engine.core import eq_flexible
    params = json.loads(params_frozen)
    return dict(eq_flexible(params))


def _freeze_params(params: dict[str, float]) -> str:
    """
    Serializa un dict de parámetros a JSON ordenado para uso como clave de caché.

    Parameters
    ----------
    params : dict[str, float]
        Parámetros del modelo.

    Returns
    -------
    str : JSON string ordenado (deterministico).
    """
    return json.dumps(params, sort_keys=True)


# ── API pública ──────────────────────────────────────────────────────────────

def cached_eq_fixed(params: dict[str, float]) -> dict[str, float]:
    """
    Calcula el equilibrio IS-LM-BP bajo tipo de cambio FIJO con caché.

    Si los parámetros ya fueron calculados en una sesión anterior, devuelve
    el resultado desde disco sin re-ejecutar el motor matemático.

    Parameters
    ----------
    params : dict[str, float]
        Parámetros del modelo (ver engine.core.eq_fixed).

    Returns
    -------
    dict[str, float] : Resultado del equilibrio (cacheado o calculado).
    """
    return _cached_eq_fixed(_freeze_params(params))


def cached_eq_flexible(params: dict[str, float]) -> dict[str, float]:
    """
    Calcula el equilibrio IS-LM-BP bajo tipo de cambio FLEXIBLE con caché.

    Parameters
    ----------
    params : dict[str, float]
        Parámetros del modelo (ver engine.core.eq_flexible).

    Returns
    -------
    dict[str, float] : Resultado del equilibrio (cacheado o calculado).
    """
    return _cached_eq_flexible(_freeze_params(params))


def cache_equilibrium(func: F) -> F:
    """
    Decorador para cachear funciones de equilibrio con parámetros dict.

    Uso en Fase 2 (Streamlit):
        @cache_equilibrium
        def mi_calculo_personalizado(params: dict) -> dict:
            ...

    El primer argumento de la función decorada debe ser un dict de parámetros.
    La clave de caché se genera del hash SHA-256 del JSON de los parámetros.

    Parameters
    ----------
    func : Callable
        Función a cachear. Debe aceptar dict como primer argumento.

    Returns
    -------
    Callable : Función envuelta con lógica de caché.
    """
    @functools.wraps(func)
    def wrapper(params: dict[str, float], *args: Any, **kwargs: Any) -> Any:
        # Genera una clave única basada en función + parámetros
        cache_key = hashlib.sha256(
            f"{func.__qualname__}:{_freeze_params(params)}".encode()
        ).hexdigest()[:16]

        cache_file = _CACHE_DIR / f"{func.__name__}_{cache_key}.json"

        # Hit de caché: devuelve resultado guardado
        if cache_file.exists():
            with cache_file.open("r", encoding="utf-8") as f:
                return json.load(f)

        # Miss de caché: calcula y persiste
        result = func(params, *args, **kwargs)
        with cache_file.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        return result

    return wrapper  # type: ignore[return-value]


def clear_cache() -> None:
    """
    Limpia toda la caché de equilibrios.
    Útil al cambiar la versión del modelo o durante desarrollo.
    """
    memory.clear(warn=False)
    # También elimina archivos JSON del decorador manual
    for json_file in _CACHE_DIR.glob("*.json"):
        json_file.unlink()
    print(f"🗑️  Caché limpiada en: {_CACHE_DIR}")

```

### Archivo: `engine\core.py`
```python
"""
engine/core.py
==============
Motor matemático puro del modelo Mundell-Fleming (economía abierta).
Sección 3.1 del documento de referencia académico.

FUNCIONES PURAS — SIN EFECTOS LATERALES NI ESTADO GLOBAL.

Ecuaciones del modelo:
    IS:  r = (A + x1*E - Y*(1 - c1 + m1)) / b
    LM:  r = (k*Y - M) / h
    BP:  r = r*  (movilidad perfecta de capitales)
    A  = c0 - c1*T + I0 + G + NX0
    mult = 1 / (1 - c1 + m1)

Régimen de tipo de cambio FIJO (E exógeno, M endógena):
    Y      = mult * (A + x1*E - b*r*)
    M_endo = k*Y - h*r*

Régimen de tipo de cambio FLEXIBLE (M exógena, E endógena):
    Y      = (M + h*r*) / k
    E_endo = ((1 - c1 + m1)*Y + b*r* - A) / x1
"""

from __future__ import annotations

from typing import TypedDict


# ── Tipos de retorno ─────────────────────────────────────────────────────────

class EquilibriumFixed(TypedDict):
    """Resultado del equilibrio bajo tipo de cambio fijo."""
    Y:      float   # Ingreso/PIB de equilibrio
    r:      float   # Tasa de interés de equilibrio (= r*)
    E:      float   # Tipo de cambio (exógeno, fijo)
    M_endo: float   # Oferta monetaria endógena
    NX:     float   # Exportaciones netas de equilibrio
    C:      float   # Consumo privado de equilibrio
    I_inv:  float   # Inversión de equilibrio
    mult:   float   # Multiplicador keynesiano


class EquilibriumFlexible(TypedDict):
    """Resultado del equilibrio bajo tipo de cambio flexible."""
    Y:      float   # Ingreso/PIB de equilibrio
    r:      float   # Tasa de interés de equilibrio (= r*)
    E_endo: float   # Tipo de cambio endógeno
    M:      float   # Oferta monetaria (exógena)
    NX:     float   # Exportaciones netas de equilibrio
    C:      float   # Consumo privado de equilibrio
    I_inv:  float   # Inversión de equilibrio
    mult:   float   # Multiplicador keynesiano


# ── Componentes del modelo ───────────────────────────────────────────────────

def autonomous_demand(
    c0: float,
    c1: float,
    T: float,
    I0: float,
    G: float,
    NX0: float,
) -> float:
    """
    Calcula la demanda autónoma agregada (A).

    A = c0 - c1*T + I0 + G + NX0

    Parameters
    ----------
    c0  : Consumo autónomo
    c1  : Propensión marginal a consumir
    T   : Impuestos lump-sum
    I0  : Inversión autónoma
    G   : Gasto de gobierno
    NX0 : Exportaciones netas autónomas

    Returns
    -------
    float : Demanda autónoma agregada
    """
    return c0 - c1 * T + I0 + G + NX0


def multiplier(c1: float, m1: float) -> float:
    """
    Calcula el multiplicador keynesiano de economía abierta.

    mult = 1 / (1 - c1 + m1)

    Parameters
    ----------
    c1 : Propensión marginal a consumir
    m1 : Propensión marginal a importar

    Returns
    -------
    float : Multiplicador keynesiano

    Raises
    ------
    ValueError
        Si el denominador es cero o negativo (modelo inestable).
    """
    denominator = 1.0 - c1 + m1
    if denominator <= 0.0:
        raise ValueError(
            f"Multiplicador indefinido: (1 - c1 + m1) = {denominator:.4f}. "
            "El modelo requiere (1 - c1 + m1) > 0."
        )
    return 1.0 / denominator


def is_curve(
    Y: float,
    c1: float,
    m1: float,
    b: float,
    A: float,
    x1: float,
    E: float,
) -> float:
    """
    Curva IS: tasa de interés como función del ingreso.

    r_IS = (A + x1*E - Y*(1 - c1 + m1)) / b

    Parameters
    ----------
    Y   : Nivel de ingreso
    c1  : Propensión marginal a consumir
    m1  : Propensión marginal a importar
    b   : Sensibilidad inversión–tasa de interés
    A   : Demanda autónoma
    x1  : Sensibilidad exportaciones–tipo de cambio
    E   : Tipo de cambio nominal

    Returns
    -------
    float : Tasa de interés sobre la curva IS
    """
    if b <= 0.0:
        raise ValueError(f"Parámetro b debe ser positivo, recibido b={b}")
    return (A + x1 * E - Y * (1.0 - c1 + m1)) / b


def lm_curve(Y: float, k: float, M: float, h: float) -> float:
    """
    Curva LM: tasa de interés como función del ingreso.

    r_LM = (k*Y - M) / h

    Parameters
    ----------
    Y : Nivel de ingreso
    k : Sensibilidad demanda de dinero al ingreso
    M : Oferta monetaria
    h : Sensibilidad demanda de dinero a la tasa de interés

    Returns
    -------
    float : Tasa de interés sobre la curva LM
    """
    if h <= 0.0:
        raise ValueError(f"Parámetro h debe ser positivo, recibido h={h}")
    return (k * Y - M) / h


def bp_curve(r_star: float) -> float:
    """
    Curva BP: condición de movilidad perfecta de capitales.

    r_BP = r*  (la tasa doméstica iguala la tasa internacional)

    Parameters
    ----------
    r_star : Tasa de interés internacional

    Returns
    -------
    float : Tasa de interés de equilibrio externo
    """
    return r_star


# ── Equilibrios del modelo ───────────────────────────────────────────────────

def eq_fixed(p: dict[str, float]) -> EquilibriumFixed:
    """
    Calcula el equilibrio IS-LM-BP bajo tipo de cambio FIJO.

    Bajo TC fijo, el banco central acomoda la oferta monetaria (M endógena)
    para mantener r = r*. El tipo de cambio E es exógeno.

    Ecuaciones de solución:
        Y      = mult * (A + x1*E - b*r*)
        M_endo = k*Y - h*r*

    Parameters
    ----------
    p : dict con claves requeridas:
        c0, c1, T, I0, G, NX0, b, x1, k, h, E, r_star, m1

    Returns
    -------
    EquilibriumFixed : Dict tipado con Y, r, E, M_endo, NX, C, I_inv, mult

    Raises
    ------
    ValueError
        Si los valores de equilibrio están fuera del dominio económico válido.
    """
    # Extraer parámetros
    c0     = p["c0"]
    c1     = p["c1"]
    T      = p["T"]
    I0     = p["I0"]
    G      = p["G"]
    NX0    = p["NX0"]
    b      = p["b"]
    x1     = p["x1"]
    k      = p["k"]
    h      = p["h"]
    E      = p["E"]
    r_star = p["r_star"]
    m1     = p["m1"]

    # Cálculos intermedios
    A    = autonomous_demand(c0, c1, T, I0, G, NX0)
    mult = multiplier(c1, m1)

    # Solución de equilibrio — TC fijo
    r      = bp_curve(r_star)
    Y      = mult * (A + x1 * E - b * r)
    M_endo = k * Y - h * r

    # Variables derivadas
    C     = c0 + c1 * (Y - T)
    I_inv = I0 - b * r          # Inversión neta de la tasa de interés
    NX    = NX0 + x1 * E        # Exportaciones netas en equilibrio

    # Validación de dominio económico (no-estricto: warnings para shocks extremos)
    _validate_equilibrium(Y=Y, r=r, label="TC Fijo", strict=False)

    return EquilibriumFixed(
        Y=round(Y, 6),
        r=round(r, 6),
        E=round(E, 6),
        M_endo=round(M_endo, 6),
        NX=round(NX, 6),
        C=round(C, 6),
        I_inv=round(I_inv, 6),
        mult=round(mult, 6),
    )


def eq_flexible(p: dict[str, float]) -> EquilibriumFlexible:
    """
    Calcula el equilibrio IS-LM-BP bajo tipo de cambio FLEXIBLE.

    Bajo TC flexible, la oferta monetaria M es exógena y el tipo de cambio
    E se ajusta endógenamente para limpiar el mercado externo.

    Ecuaciones de solución:
        Y      = (M + h*r*) / k
        E_endo = ((1 - c1 + m1)*Y + b*r* - A) / x1

    Parameters
    ----------
    p : dict con claves requeridas:
        c0, c1, T, I0, G, NX0, b, x1, k, h, M, r_star, m1

    Returns
    -------
    EquilibriumFlexible : Dict tipado con Y, r, E_endo, M, NX, C, I_inv, mult

    Raises
    ------
    ValueError
        Si los valores de equilibrio están fuera del dominio económico válido.
    """
    # Extraer parámetros
    c0     = p["c0"]
    c1     = p["c1"]
    T      = p["T"]
    I0     = p["I0"]
    G      = p["G"]
    NX0    = p["NX0"]
    b      = p["b"]
    x1     = p["x1"]
    k      = p["k"]
    h      = p["h"]
    M      = p["M"]
    r_star = p["r_star"]
    m1     = p["m1"]

    # Cálculos intermedios
    A    = autonomous_demand(c0, c1, T, I0, G, NX0)
    mult = multiplier(c1, m1)

    # Solución de equilibrio — TC flexible
    r      = bp_curve(r_star)
    Y      = (M + h * r) / k
    E_endo = ((1.0 - c1 + m1) * Y + b * r - A) / x1

    # Variables derivadas
    C     = c0 + c1 * (Y - T)
    I_inv = I0 - b * r
    NX    = NX0 + x1 * E_endo

    # Validación de dominio económico (no-estricto: warnings para shocks extremos)
    _validate_equilibrium(Y=Y, r=r, label="TC Flexible", strict=False)

    return EquilibriumFlexible(
        Y=round(Y, 6),
        r=round(r, 6),
        E_endo=round(E_endo, 6),
        M=round(M, 6),
        NX=round(NX, 6),
        C=round(C, 6),
        I_inv=round(I_inv, 6),
        mult=round(mult, 6),
    )


# ── Validación de dominio ────────────────────────────────────────────────────

def _validate_equilibrium(Y: float, r: float, label: str = "", strict: bool = True) -> None:
    """
    Verifica que los valores de equilibrio sean económicamente válidos.

    Parameters
    ----------
    Y      : Ingreso de equilibrio (debe ser positivo)
    r      : Tasa de interés (debe ser no negativa)
    label  : Etiqueta para mensajes de error
    strict : Si True, lanza ValueError. Si False, imprime advertencia.

    Raises
    ------
    ValueError
        Si Y <= 0 o r < 0 y strict=True.
    """
    prefix = f"[{label}] " if label else ""
    issues = []
    if Y <= 0.0:
        issues.append(
            f"{prefix}Y = {Y:.4f} (ingreso negativo — posible colapso de demanda agregada)"
        )
    if r < 0.0:
        issues.append(
            f"{prefix}r = {r:.4f} (tasa de interes negativa)"
        )
    if issues:
        msg = "Equilibrio fuera de dominio economico valido:\n  " + "\n  ".join(issues)
        if strict:
            raise ValueError(msg)
        else:
            print(f"[ADVERTENCIA] {msg}")

```

### Archivo: `engine\salter_swan.py`
```python
"""
engine/salter_swan.py
=====================
Implementación del modelo Salter-Swan para economía abierta pequeña.

El modelo Salter-Swan analiza el equilibrio simultáneo de:
    - Balance Interno (IB): pleno empleo / estabilidad de precios
    - Balance Externo (EB): equilibrio de cuenta corriente

Instrumentos:
    - Absorción doméstica (A): política fiscal/monetaria
    - Tipo de cambio real (q): política cambiaria

Zonas de desequilibrio (I a IV):
    Zona I   : q > IB  y  q > EB  → Superávit externo + Sobreempleo
    Zona II  : q < IB  y  q > EB  → Superávit externo + Desempleo
    Zona III : q < IB  y  q < EB  → Déficit externo + Desempleo
    Zona IV  : q > IB  y  q < EB  → Déficit externo + Sobreempleo

Nota: q es el tipo de cambio real (↑q = depreciación real = mejora competitividad)
"""

from __future__ import annotations

from typing import TypedDict


# ── Tipos de retorno ─────────────────────────────────────────────────────────

class SalterSwanZone(TypedDict):
    """Resultado del análisis de zona Salter-Swan."""
    zone:      str    # "I", "II", "III" o "IV"
    diagnosis: str    # Descripción del desequilibrio
    policy:    str    # Recomendación de política económica
    q_IB:      float  # Umbral de la curva de Balance Interno
    q_EB:      float  # Umbral de la curva de Balance Externo
    q:         float  # Tipo de cambio real actual
    A:         float  # Absorción doméstica actual


# ── Curvas de equilibrio ─────────────────────────────────────────────────────

def q_IB(A: float) -> float:
    """
    Curva de Balance Interno (IB) en el espacio (A, q).

    Pendiente negativa: mayor absorción requiere menor tipo de cambio real
    (apreciación) para mantener el pleno empleo.

    q_IB(A) = 1.0 - 0.005 * (A - 100)

    Parameters
    ----------
    A : float
        Absorción doméstica (gasto total de la economía)

    Returns
    -------
    float : Tipo de cambio real de Balance Interno
    """
    return 1.0 - 0.005 * (A - 100.0)


def q_EB(A: float) -> float:
    """
    Curva de Balance Externo (EB) en el espacio (A, q).

    Pendiente positiva: mayor absorción requiere mayor tipo de cambio real
    (depreciación) para mantener el equilibrio externo.

    q_EB(A) = 1.0 + 0.005 * (A - 100)

    Parameters
    ----------
    A : float
        Absorción doméstica (gasto total de la economía)

    Returns
    -------
    float : Tipo de cambio real de Balance Externo
    """
    return 1.0 + 0.005 * (A - 100.0)


# ── Diagnóstico y política ───────────────────────────────────────────────────

# Mapa de zona → (diagnóstico económico, recomendación de política)
_ZONE_MAP: dict[str, tuple[str, str]] = {
    "I": (
        "Superávit de cuenta corriente + Sobreempleo (presiones inflacionarias). "
        "La economía está por encima del pleno empleo con saldo externo positivo.",
        "Apreciar el tipo de cambio real (revaluar E) Y/O contraer la absorción "
        "(política fiscal contractiva). Objetivo: enfriar demanda sin comprometer externo.",
    ),
    "II": (
        "Superávit de cuenta corriente + Desempleo (capacidad ociosa). "
        "La economía tiene exceso de oferta con saldo externo favorable.",
        "Expandir la absorción doméstica (política fiscal expansiva) Y mantener "
        "o apreciar moderadamente el tipo de cambio. Objetivo: estimular demanda interna.",
    ),
    "III": (
        "Déficit de cuenta corriente + Desempleo (el peor escenario). "
        "Presión simultánea sobre reservas y empleo — dilema de política.",
        "Depreciar el tipo de cambio real (devaluar E) PARA mejorar competitividad, "
        "con contención fiscal moderada. PRECAUCIÓN: riesgo de espiral inflacionaria.",
    ),
    "IV": (
        "Déficit de cuenta corriente + Sobreempleo (economía recalentada). "
        "Alta demanda presiona precios e importaciones simultáneamente.",
        "Contraer absorción (política fiscal restrictiva) Y depreciar el tipo de "
        "cambio real para reequilibrar la cuenta corriente. Política dual necesaria.",
    ),
}


def get_zone(A: float, q: float) -> SalterSwanZone:
    """
    Determina la zona de desequilibrio Salter-Swan y la política recomendada.

    Clasificación según posición relativa a las curvas IB y EB:
        Zona I   : q > q_IB(A)  y  q > q_EB(A)
        Zona II  : q < q_IB(A)  y  q > q_EB(A)
        Zona III : q < q_IB(A)  y  q < q_EB(A)
        Zona IV  : q > q_IB(A)  y  q < q_EB(A)

    Parameters
    ----------
    A : float
        Absorción doméstica (nivel de gasto agregado de la economía)
    q : float
        Tipo de cambio real actual

    Returns
    -------
    SalterSwanZone : Diccionario tipado con zona, diagnóstico y política

    Raises
    ------
    ValueError
        Si q ≤ 0 (tipo de cambio real debe ser positivo).
    """
    if q <= 0.0:
        raise ValueError(
            f"El tipo de cambio real q debe ser positivo, recibido q={q:.4f}."
        )

    # Umbrales de las curvas en el nivel de absorción A
    threshold_IB = q_IB(A)
    threshold_EB = q_EB(A)

    # Clasificación por zona
    above_IB = q > threshold_IB
    above_EB = q > threshold_EB

    if above_IB and above_EB:
        zone = "I"
    elif (not above_IB) and above_EB:
        zone = "II"
    elif (not above_IB) and (not above_EB):
        zone = "III"
    else:  # above_IB and not above_EB
        zone = "IV"

    diagnosis, policy = _ZONE_MAP[zone]

    return SalterSwanZone(
        zone=zone,
        diagnosis=diagnosis,
        policy=policy,
        q_IB=round(threshold_IB, 6),
        q_EB=round(threshold_EB, 6),
        q=round(q, 6),
        A=round(A, 6),
    )

```

### Archivo: `engine\scenario_builder.py`
```python
"""
engine/scenario_builder.py
==========================
Constructor de "historias económicas" para la Fase 4.
Combina presets base, overrides manuales y secuencias de shocks temporales.

Funciones públicas:
    build_economic_story(base_preset, custom_overrides, policy_shocks) → dict
    generate_narrative_for_story(story_metadata) → str
    apply_temporal_shock(params, shock_dict) → dict
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from config.bolivia_data import BOLIVIA_PRESETS, get_bolivia_params
from config.parameters import get_base_params


# ── Tipos de shocks predefinidos ──────────────────────────────────────────────
# Cada shock_dict tiene la estructura:
#   {
#       "name":        str,          — nombre descriptivo
#       "t":           int,          — paso temporal (t=0, t=1, t=2, ...)
#       "description": str,          — narrativa del shock
#       "overrides":   dict[str,float] — parámetros a sobrescribir
#   }

PREDEFINED_SHOCKS: dict[str, dict] = {
    "caida_exportaciones": {
        "name":        "Caída de Exportaciones (x₁↓)",
        "description": (
            "Reducción de la elasticidad de exportaciones al tipo de cambio, "
            "típica cuando socios comerciales reducen demanda o caen precios de materias primas."
        ),
        "overrides":   {"x1": -0.3, "NX0": -2.0},  # deltas a aplicar
        "is_delta":    True,  # si True, los overrides son deltas (no valores absolutos)
    },
    "fuga_capitales": {
        "name":        "Fuga de Capitales (r*↑)",
        "description": (
            "Aumento de la prima de riesgo país, elevando la tasa de interés internacional "
            "efectiva que enfrenta la economía. Genera salida de capitales."
        ),
        "overrides":   {"r_star": 3.0},
        "is_delta":    True,
    },
    "expansion_fiscal": {
        "name":        "Expansión Fiscal (G↑10)",
        "description": (
            "Aumento del gasto público de 10 unidades. Bajo TC fijo: desplaza IS a la derecha "
            "y el BC acomoda la oferta monetaria (M endógena)."
        ),
        "overrides":   {"G": 10.0},
        "is_delta":    True,
    },
    "contraccion_monetaria": {
        "name":        "Contracción Monetaria (M↓)",
        "description": (
            "Reducción de la oferta monetaria (TC flexible). Desplaza LM a la izquierda, "
            "apreciando el tipo de cambio y reduciendo Y."
        ),
        "overrides":   {"M": -5.0},
        "is_delta":    True,
    },
    "devaluacion": {
        "name":        "Devaluación (E↑15%)",
        "description": (
            "Aumento del tipo de cambio nominal en 15%. Bajo TC fijo: requiere decisión "
            "deliberada del BC. Mejora competitividad pero puede generar presión inflacionaria."
        ),
        "overrides":   {"E": 1.15},  # multiplicador
        "is_delta":    False,        # valor absoluto (multiplica E actual)
        "is_multiplicative": True,
    },
    "subida_impuestos": {
        "name":        "Aumento de Impuestos (T↑5)",
        "description": "Aumento de 5 unidades en impuestos lump-sum. Contrae la demanda agregada.",
        "overrides":   {"T": 5.0},
        "is_delta":    True,
    },
    "mejora_confianza": {
        "name":        "Mejora de Confianza (I₀↑)",
        "description": "Recuperación de la inversión privada autónoma por mejora del clima de negocios.",
        "overrides":   {"I0": 5.0},
        "is_delta":    True,
    },
    "reduccion_consumo": {
        "name":        "Reducción del Consumo (c₁↓)",
        "description": "Caída de la propensión marginal a consumir por incertidumbre o austeridad.",
        "overrides":   {"c1": -0.05},
        "is_delta":    True,
    },
}


# ── Funciones públicas ────────────────────────────────────────────────────────

def build_economic_story(
    base_preset: str,
    custom_overrides: dict[str, float] | None = None,
    policy_shocks: list[dict] | None = None,
) -> tuple[dict[str, float], dict]:
    """
    Construye una "historia económica" combinando preset base, overrides manuales
    y una secuencia de shocks temporales.

    Paso 1: Carga preset base (Bolivia o estándar)
    Paso 2: Aplica overrides manuales del usuario
    Paso 3: Aplica secuencia de shocks (en orden de t)

    Parameters
    ----------
    base_preset : str
        Clave del preset base. Puede ser clave de BOLIVIA_PRESETS
        o "base" para usar get_base_params().
    custom_overrides : dict | None
        Parámetros a sobrescribir manualmente (ej. {"c1": 0.70}).
    policy_shocks : list[dict] | None
        Secuencia de shocks. Cada dict: {"key": str, "t": int}.
        "key" debe ser clave de PREDEFINED_SHOCKS.

    Returns
    -------
    tuple[dict[str, float], dict]
        - params_final : Parámetros finales listos para eq_fixed/eq_flexible
        - story_metadata : Metadatos de la historia para narrativa
    """
    custom_overrides = custom_overrides or {}
    policy_shocks    = policy_shocks or []

    # ── Paso 1: Cargar preset base ────────────────────────────────────────────
    if base_preset in BOLIVIA_PRESETS:
        params = get_bolivia_params(base_preset)
        base_label = BOLIVIA_PRESETS[base_preset].get("_meta", {}).get("label", base_preset)
    elif base_preset == "base":
        params = get_base_params()
        base_label = "Parámetros base (Sección 3.1)"
    else:
        # Intentar como preset de CRISIS_PRESETS (config/parameters.py)
        from config.parameters import apply_shocks, get_base_params as _gbp
        try:
            params = apply_shocks(_gbp(), base_preset)
            base_label = base_preset
        except KeyError:
            params = get_base_params()
            base_label = "Parámetros base"

    params = deepcopy(params)

    # ── Paso 2: Aplicar overrides manuales ───────────────────────────────────
    applied_overrides = {}
    for key, val in custom_overrides.items():
        if key in params:
            applied_overrides[key] = {"antes": params[key], "despues": val}
        params[key] = val

    # ── Paso 3: Aplicar shocks temporales ────────────────────────────────────
    # Ordenar por t (campo "t" opcional; si no existe, usar orden de lista)
    shocks_sorted = sorted(policy_shocks, key=lambda x: x.get("t", 0))
    applied_shocks = []

    for shock_ref in shocks_sorted:
        shock_key = shock_ref.get("key", "")
        shock_def = PREDEFINED_SHOCKS.get(shock_key)
        if shock_def is None:
            # Shock custom inline con "overrides" directo
            if "overrides" in shock_ref:
                shock_def = {
                    "name":        shock_ref.get("name", "Shock personalizado"),
                    "description": shock_ref.get("description", ""),
                    "overrides":   shock_ref["overrides"],
                    "is_delta":    shock_ref.get("is_delta", False),
                    "is_multiplicative": shock_ref.get("is_multiplicative", False),
                }
            else:
                continue

        params = apply_temporal_shock(params, shock_def)
        applied_shocks.append({
            "t":    shock_ref.get("t", len(applied_shocks)),
            "name": shock_def["name"],
            "desc": shock_def["description"],
        })

    # ── Metadatos de la historia ──────────────────────────────────────────────
    story_metadata = {
        "base_preset":       base_preset,
        "base_label":        base_label,
        "custom_overrides":  applied_overrides,
        "applied_shocks":    applied_shocks,
        "params_final":      dict(params),
    }

    return params, story_metadata


def apply_temporal_shock(params: dict[str, float], shock_def: dict) -> dict[str, float]:
    """
    Aplica un shock a un diccionario de parámetros.

    Soporta tres modos:
        is_delta=True         : override_value es un delta (+/-) a sumar al parámetro actual
        is_multiplicative=True: override_value es un multiplicador (* parámetro actual)
        ninguno               : override_value reemplaza directamente el parámetro

    Parameters
    ----------
    params    : dict — parámetros actuales del modelo
    shock_def : dict — definición del shock (de PREDEFINED_SHOCKS o custom)

    Returns
    -------
    dict : Nuevos parámetros con el shock aplicado (copia defensiva)
    """
    result = deepcopy(params)
    overrides  = shock_def.get("overrides", {})
    is_delta   = shock_def.get("is_delta", False)
    is_mult    = shock_def.get("is_multiplicative", False)

    for key, val in overrides.items():
        current = result.get(key, 0.0)
        if is_mult:
            result[key] = current * val
        elif is_delta:
            result[key] = current + val
        else:
            result[key] = val

    return result


def generate_narrative_for_story(story_metadata: dict) -> str:
    """
    Genera un texto explicativo estructurado para una historia económica.

    Parameters
    ----------
    story_metadata : dict — retornado por build_economic_story()

    Returns
    -------
    str : Narrativa en Markdown explicando la configuración de la historia.
    """
    base_label      = story_metadata.get("base_label", "—")
    overrides       = story_metadata.get("custom_overrides", {})
    shocks          = story_metadata.get("applied_shocks", [])
    params_final    = story_metadata.get("params_final", {})

    lines = [
        "### 📖 Narrativa de la Historia Económica",
        "",
        f"**Punto de partida**: {base_label}",
        "",
    ]

    if overrides:
        lines.append("**Ajustes manuales aplicados:**")
        for var, change in overrides.items():
            antes   = change.get("antes", "?")
            despues = change.get("despues", "?")
            lines.append(f"- `{var}`: {antes:.4g} → **{despues:.4g}**")
        lines.append("")

    if shocks:
        lines.append("**Secuencia de shocks de política:**")
        for sh in shocks:
            t    = sh.get("t", "?")
            name = sh.get("name", "—")
            desc = sh.get("desc", "")
            lines.append(f"- t={t}: **{name}** — {desc}")
        lines.append("")

    # Multiplicador resultante
    c1 = params_final.get("c1", float("nan"))
    m1 = params_final.get("m1", float("nan"))
    try:
        mult = 1.0 / (1.0 - c1 + m1)
        lines.append(f"**Multiplicador keynesiano resultante**: `1/(1−{c1:.2f}+{m1:.2f}) = {mult:.3f}`")
    except ZeroDivisionError:
        lines.append("**Multiplicador**: indefinido (denominador = 0)")

    # Resumen de parámetros clave
    lines += [
        "",
        "**Parámetros finales clave:**",
        f"| Variable | Valor |",
        f"|----------|-------|",
        f"| G (Gasto público) | {params_final.get('G', '—'):.2f} |",
        f"| T (Impuestos) | {params_final.get('T', '—'):.2f} |",
        f"| r* (Tasa internacional) | {params_final.get('r_star', '—'):.2f}% |",
        f"| c₁ (PMgC) | {params_final.get('c1', '—'):.3f} |",
        f"| m₁ (PMgM) | {params_final.get('m1', '—'):.3f} |",
        f"| x₁ (Elast. export.) | {params_final.get('x1', '—'):.2f} |",
    ]

    return "\n".join(lines)

```

### Archivo: `engine\state_manager.py`
```python
"""
engine/state_manager.py
=======================
Gestión de estados económicos persistentes para trayectoria de simulación.
Fase 4 — Plataforma de Análisis de Políticas.

La persistencia se implementa en dos capas:
    1. st.session_state["f4_states"] → lista en memoria (persiste entre reruns Streamlit)
    2. Exportación opcional a Parquet/JSON en disco (bajo demanda del usuario)

No se usa base de datos externa.

Uso básico:
    mgr = EconomicStateManager.from_session()
    mgr.save_state("Estado inicial", params, equilibrium)
    traj = mgr.get_trajectory("Y")
    df   = mgr.compare_states("Estado inicial", "Estado 2")
"""

from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

# Clave en st.session_state donde se almacenan los estados
_SESSION_KEY = "f4_states"


class EconomicStateManager:
    """
    Gestiona una lista ordenada de estados económicos (parámetros + equilibrio).

    Cada estado es un dict con la estructura:
        {
            "label":      str,
            "timestamp":  str (ISO 8601),
            "params":     dict[str, float],  # parámetros del modelo
            "equilibrium": dict[str, float], # resultado de eq_fixed / eq_flexible
            "regime":     str,               # "fixed" | "flexible"
            "notes":      str,               # notas opcionales
        }
    """

    def __init__(self) -> None:
        # Inicializar la lista en session_state si no existe
        if _SESSION_KEY not in st.session_state:
            st.session_state[_SESSION_KEY] = []
        # Referencia local (siempre apunta al mismo objeto en session_state)
        self._states: list[dict] = st.session_state[_SESSION_KEY]

    @classmethod
    def from_session(cls) -> "EconomicStateManager":
        """
        Factory method: obtiene o crea el manager desde st.session_state.
        Uso idiomático en Streamlit para evitar reinstanciar en cada rerun.
        """
        return cls()

    # ── Escritura ─────────────────────────────────────────────────────────────

    def save_state(
        self,
        label: str,
        params: dict[str, float],
        equilibrium: dict[str, float],
        regime: str = "fixed",
        notes: str = "",
        timestamp: bool = True,
    ) -> dict:
        """
        Guarda un nuevo estado económico en la lista persistente.

        Parameters
        ----------
        label       : Nombre descriptivo del estado (ej. "Historia: Ajuste Fiscal")
        params      : Parámetros del modelo (dict de engine/core.py)
        equilibrium : Resultado de eq_fixed() o eq_flexible()
        regime      : "fixed" | "flexible"
        notes       : Comentarios opcionales
        timestamp   : Si True, agrega timestamp ISO actual

        Returns
        -------
        dict : El estado guardado
        """
        ts = datetime.now().isoformat(timespec="seconds") if timestamp else ""
        state = {
            "label":      label,
            "timestamp":  ts,
            "params":     dict(params),
            "equilibrium": dict(equilibrium),
            "regime":     regime,
            "notes":      notes,
            "index":      len(self._states),  # índice inmutable
        }
        self._states.append(state)
        # Sincronizar con session_state (puede que se haya reemplazado la referencia)
        st.session_state[_SESSION_KEY] = self._states
        return state

    def update_state(self, label: str, **kwargs) -> bool:
        """
        Actualiza campos de un estado existente por label.
        Retorna True si encontró y actualizó, False si no existe.
        """
        for state in self._states:
            if state["label"] == label:
                for k, v in kwargs.items():
                    state[k] = v
                return True
        return False

    def delete_state(self, label: str) -> bool:
        """
        Elimina un estado por label. Retorna True si eliminó.
        """
        original_len = len(self._states)
        self._states[:] = [s for s in self._states if s["label"] != label]
        st.session_state[_SESSION_KEY] = self._states
        return len(self._states) < original_len

    def clear_all(self) -> None:
        """Elimina todos los estados guardados."""
        self._states.clear()
        st.session_state[_SESSION_KEY] = self._states

    # ── Lectura ───────────────────────────────────────────────────────────────

    def load_state(self, label: str) -> dict | None:
        """
        Carga un estado por su label.

        Returns
        -------
        dict | None : Estado o None si no existe.
        """
        for state in self._states:
            if state["label"] == label:
                return state
        return None

    def get_state_by_index(self, idx: int) -> dict | None:
        """Carga un estado por su índice en la lista."""
        if 0 <= idx < len(self._states):
            return self._states[idx]
        return None

    def list_labels(self) -> list[str]:
        """Retorna lista de labels de todos los estados guardados."""
        return [s["label"] for s in self._states]

    def count(self) -> int:
        """Número de estados guardados."""
        return len(self._states)

    def is_empty(self) -> bool:
        return len(self._states) == 0

    # ── Trayectorias ──────────────────────────────────────────────────────────

    def get_trajectory(self, variable: str) -> list[float]:
        """
        Retorna la trayectoria histórica de una variable a través de todos los estados.

        Si la variable está en 'equilibrium', la toma de ahí.
        Si está en 'params', la toma de parámetros.
        En caso de ausencia, retorna NaN para ese estado.

        Parameters
        ----------
        variable : str
            Nombre de la variable (ej. "Y", "r", "E", "NX", "G", "c1")

        Returns
        -------
        list[float] : Valores en el orden de los estados guardados.
        """
        values = []
        for state in self._states:
            eq  = state.get("equilibrium", {})
            par = state.get("params", {})
            # Prioridad: equilibrium > params
            if variable in eq:
                values.append(float(eq[variable]))
            elif variable in par:
                values.append(float(par[variable]))
            else:
                values.append(float("nan"))
        return values

    def get_trajectory_df(self, variables: list[str] | None = None) -> pd.DataFrame:
        """
        Retorna un DataFrame con la trayectoria de múltiples variables.

        Parameters
        ----------
        variables : list[str] | None
            Variables a incluir. Si None, incluye las principales:
            ['Y', 'r', 'NX', 'C', 'mult', 'G', 'T', 'c1', 'm1']

        Returns
        -------
        pd.DataFrame con columnas: label, timestamp, regime, + variables
        """
        if variables is None:
            variables = ["Y", "r", "NX", "C", "mult", "G", "T", "c1", "m1", "E", "M_endo"]

        rows = []
        for i, state in enumerate(self._states):
            eq  = state.get("equilibrium", {})
            par = state.get("params", {})
            row = {
                "Paso":      i,
                "Estado":    state["label"],
                "Timestamp": state.get("timestamp", ""),
                "Régimen":   state.get("regime", "—"),
                "Notas":     state.get("notes", ""),
            }
            for var in variables:
                if var in eq:
                    row[var] = round(float(eq[var]), 4)
                elif var in par:
                    row[var] = round(float(par[var]), 4)
                else:
                    row[var] = float("nan")
            rows.append(row)

        return pd.DataFrame(rows)

    # ── Comparación ───────────────────────────────────────────────────────────

    def compare_states(self, label_a: str, label_b: str) -> pd.DataFrame:
        """
        Compara dos estados: deltas absolutos y relativos.

        Parameters
        ----------
        label_a, label_b : str
            Labels de los estados a comparar.

        Returns
        -------
        pd.DataFrame con columnas:
            Variable | Valor_A | Valor_B | Delta_Abs | Delta_Pct
        """
        state_a = self.load_state(label_a)
        state_b = self.load_state(label_b)

        if state_a is None or state_b is None:
            return pd.DataFrame()

        # Unir equilibrium y params de ambos estados
        merged_a = {**state_a.get("params", {}), **state_a.get("equilibrium", {})}
        merged_b = {**state_b.get("params", {}), **state_b.get("equilibrium", {})}

        # Variables a comparar (intersección de claves numéricas)
        all_keys = sorted(set(merged_a.keys()) | set(merged_b.keys()))

        rows = []
        for key in all_keys:
            va = merged_a.get(key, float("nan"))
            vb = merged_b.get(key, float("nan"))
            try:
                va = float(va)
                vb = float(vb)
                delta_abs = vb - va
                delta_pct = (delta_abs / va * 100.0) if abs(va) > 1e-9 else float("nan")
            except (TypeError, ValueError):
                delta_abs = delta_pct = float("nan")

            rows.append({
                "Variable":   key,
                f"{label_a}": round(va, 4),
                f"{label_b}": round(vb, 4),
                "Δ Absoluto": round(delta_abs, 4),
                "Δ %":        round(delta_pct, 2) if not (
                    delta_pct != delta_pct  # isnan check
                ) else float("nan"),
            })

        return pd.DataFrame(rows)

    # ── Exportación ───────────────────────────────────────────────────────────

    def export_trajectory(self, fmt: str = "csv") -> bytes:
        """
        Exporta toda la secuencia de estados.

        Parameters
        ----------
        fmt : "csv" | "parquet" | "json"

        Returns
        -------
        bytes : Contenido del archivo exportado.
        """
        df = self.get_trajectory_df()

        if fmt == "csv":
            return df.to_csv(index=False).encode("utf-8")

        elif fmt == "parquet":
            buf = io.BytesIO()
            df.to_parquet(buf, index=False, engine="pyarrow")
            return buf.getvalue()

        elif fmt == "json":
            # Exportar como lista de estados completos (params + equilibrium)
            return json.dumps(
                self._states,
                ensure_ascii=False,
                indent=2,
                default=str,  # maneja datetime si los hubiera
            ).encode("utf-8")

        else:
            raise ValueError(f"Formato '{fmt}' no soportado. Use 'csv', 'parquet' o 'json'.")

    def to_summary_dict(self) -> list[dict]:
        """Retorna representación serializable de todos los estados (para informe PDF)."""
        result = []
        for state in self._states:
            result.append({
                "label":     state["label"],
                "timestamp": state.get("timestamp", ""),
                "regime":    state.get("regime", "—"),
                "notes":     state.get("notes", ""),
                "Y":         state.get("equilibrium", {}).get("Y", float("nan")),
                "r":         state.get("equilibrium", {}).get("r", float("nan")),
                "NX":        state.get("equilibrium", {}).get("NX", float("nan")),
                "mult":      state.get("equilibrium", {}).get("mult", float("nan")),
                "G":         state.get("params", {}).get("G", float("nan")),
                "c1":        state.get("params", {}).get("c1", float("nan")),
            })
        return result

```

### Archivo: `engine\__init__.py`
```python
# engine package

```

### Archivo: `report\generator.py`
```python
"""
report/generator.py - Generador de informe académico PDF con fpdf2.

Estructura del informe (máx. 8 páginas):
  Sección 1: Verificación del modelo (cálculos algebraicos paso a paso)
  Sección 2: Registro de prompts (tabla pre-formateada)
  Sección 3: Errores y correcciones (3 bloques)
  Sección 4: Análisis de política Bolivia 2024 (pre-llenado)
  Sección 5: Reflexión final (espacio en blanco para el estudiante)

Dependencia: fpdf2 (pip install fpdf2)
"""
from __future__ import annotations

import io
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF, XPos, YPos

# ── Configuración de fuentes y colores ────────────────────────────────────────
_DARK_BG   = (3,  9, 18)      # #030712
_AMBER     = (252, 211, 77)   # #fcd34d
_LIGHT_TXT = (248, 250, 252)  # #f8fafc
_GRAY_TXT  = (148, 163, 184)  # #94a3b8
_RED_LIGHT = (252, 165, 165)
_GREEN_LT  = (134, 239, 172)
_SECTION_BG = (17, 24, 39)    # #111827

_REPORT_DIR = Path(__file__).parent.parent / "reports"
_REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ── Clase PDF ─────────────────────────────────────────────────────────────────

class _MacroPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 18, 18)
        self._section_num = 0

    # ── Header ──────────────────────────────────────────────────────────────
    def header(self):
        self.set_fill_color(*_DARK_BG)
        self.rect(0, 0, 210, 12, "F")
        self.set_text_color(*_AMBER)
        self.set_font("Helvetica", "B", 9)
        self.set_y(3)
        self.cell(0, 6, "Simulador Macroeconómico Abierto - Mundell-Fleming + Salter-Swan",
                  align="C")
        self.set_y(14)

    # ── Footer ──────────────────────────────────────────────────────────────
    def footer(self):
        self.set_y(-12)
        self.set_fill_color(*_DARK_BG)
        self.rect(0, self.get_y() - 2, 210, 14, "F")
        self.set_text_color(*_GRAY_TXT)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 8,
                  f"Pág. {self.page_no()} | Ingeniería Financiera - Open Macroeconomics - {datetime.now().year}",
                  align="C")

    # ── Helpers ─────────────────────────────────────────────────────────────
    def section_title(self, num: int, title: str) -> None:
        self.set_fill_color(*_SECTION_BG)
        self.set_text_color(*_AMBER)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 9, f"Sección {num}: {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                  fill=True, border=False)
        self.ln(2)

    def subsection(self, text: str) -> None:
        self.set_text_color(*_AMBER)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*_LIGHT_TXT)
        self.set_font("Helvetica", "", 10)

    def body_text(self, text: str) -> None:
        self.set_text_color(*_LIGHT_TXT)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def key_value_row(self, label: str, value: str, highlight: bool = False) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_AMBER if highlight else _GRAY_TXT)
        self.cell(70, 6, label, border="B")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_LIGHT_TXT)
        self.cell(0, 6, str(value), border="B", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def draw_table(self, headers: list[str], rows: list[list[str]],
                   col_widths: list[float] | None = None) -> None:
        usable = 210 - 36  # A4 - márgenes
        if col_widths is None:
            col_widths = [usable / len(headers)] * len(headers)

        # Header
        self.set_fill_color(*_AMBER)
        self.set_text_color(*_DARK_BG)
        self.set_font("Helvetica", "B", 9)
        for h, w in zip(headers, col_widths):
            self.cell(w, 7, h, border=1, fill=True, align="C")
        self.ln()

        # Rows
        self.set_font("Helvetica", "", 8)
        for i, row in enumerate(rows):
            bg = _SECTION_BG if i % 2 == 0 else _DARK_BG
            self.set_fill_color(*bg)
            self.set_text_color(*_LIGHT_TXT)
            max_lines = 1
            for cell, w in zip(row, col_widths):
                lines = math.ceil(len(str(cell)) / max(1, int(w / 2.2)))
                max_lines = max(max_lines, lines)
            row_h = max(6, max_lines * 5)
            for cell, w in zip(row, col_widths):
                x0, y0 = self.get_x(), self.get_y()
                self.multi_cell(w, 5, str(cell), border=1, fill=True)
                self.set_xy(x0 + w, y0)
            self.ln(row_h)
        self.ln(2)

    def placeholder_box(self, height_mm: float, label: str = "[ Espacio para respuesta del estudiante ]") -> None:
        self.set_fill_color(*_SECTION_BG)
        self.set_draw_color(*_AMBER)
        self.set_line_width(0.3)
        x, y = self.get_x(), self.get_y()
        self.rect(x, y, 174, height_mm, "D")
        self.set_text_color(*_GRAY_TXT)
        self.set_font("Helvetica", "I", 9)
        cy = y + height_mm / 2 - 3
        self.set_xy(x, cy)
        self.cell(174, 6, label, align="C")
        self.set_xy(x, y + height_mm + 2)
        self.ln(2)

    def error_block(self, num: int) -> None:
        self.set_fill_color(*_SECTION_BG)
        self.set_text_color(*_AMBER)
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 6, f"Error #{num}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        for field in ["Error detectado:", "Causa raíz:", "Solución aplicada:"]:
            self.set_text_color(*_GRAY_TXT)
            self.set_font("Helvetica", "B", 8)
            self.cell(0, 5, field, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.placeholder_box(12, "[ Complete aquí ]")
        self.ln(2)


# ── Funciones auxiliares ──────────────────────────────────────────────────────

def export_graph_for_report(fig: Any, filename: str) -> Path | None:
    """
    Exporta una figura Plotly como PNG de alta resolución para incrustar en PDF.

    Parameters
    ----------
    fig      : go.Figure de Plotly.
    filename : Nombre base del archivo (sin extensión).

    Returns
    -------
    Path al PNG generado, o None si falla.
    """
    try:
        out_path = _REPORT_DIR / f"{filename}.png"
        fig.write_image(str(out_path), width=900, height=500, scale=2)
        return out_path
    except Exception as e:
        print(f"[export_graph_for_report] Error: {e}")
        return None


def _fmt(val: float, decimals: int = 4) -> str:
    if val != val:
        return "N/A"
    return f"{val:.{decimals}f}"


# ── Generador principal ───────────────────────────────────────────────────────

def generate_academic_pdf(
    base_params:       dict[str, float],
    current_params:    dict[str, float],
    equilibrium_base:  dict[str, float],
    equilibrium_current: dict[str, float],
    salter_zone:       dict | None = None,
    prompts_used:      list[dict]  | None = None,
    bolivia_analysis:  dict | None = None,
    fig_islm:          Any | None = None,
    fig_salter:        Any | None = None,
) -> bytes:
    """
    Genera un informe académico PDF completo con 5 secciones.

    Parameters
    ----------
    base_params          : Parámetros base del modelo.
    current_params       : Parámetros actuales del simulador.
    equilibrium_base     : Equilibrio base (eq_fixed o eq_flexible).
    equilibrium_current  : Equilibrio con parámetros actuales.
    salter_zone          : Resultado de get_zone() para el análisis Salter-Swan.
    prompts_used         : Lista de dicts con claves: paso, prompt, respuesta, modificacion.
    bolivia_analysis     : Dict con resultados del preset Bolivia_2024_Stagflation.
    fig_islm             : go.Figure IS-LM para exportar (opcional).
    fig_salter           : go.Figure Salter-Swan para exportar (opcional).

    Returns
    -------
    bytes : Contenido del PDF listo para st.download_button.
    """
    pdf = _MacroPDF()
    pdf.set_fill_color(*_DARK_BG)

    # ── Portada ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_DARK_BG)
    pdf.rect(0, 0, 210, 297, "F")

    pdf.set_y(50)
    pdf.set_text_color(*_AMBER)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 12, "INFORME DE EVALUACIÓN", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 12, "Simulador Macroeconómico Abierto", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(6)
    pdf.set_text_color(*_LIGHT_TXT)
    pdf.set_font("Helvetica", "", 13)
    pdf.cell(0, 8, "Mundell-Fleming (IS-LM-BP) + Salter-Swan", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, "Economía Abierta con Movilidad Perfecta de Capitales", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(20)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*_GRAY_TXT)
    pdf.cell(0, 7, "Ingeniería Financiera - Open Macroeconomics", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── SECCIÓN 1: Verificación del Modelo ───────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_DARK_BG)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.section_title(1, "Verificación del Modelo - Cálculos Algebraicos")

    pdf.body_text(
        "Esta sección verifica que el motor matemático reproduce exactamente los equilibrios "
        "analíticos de la Sección 3.1 del documento de referencia. Todos los cálculos se muestran "
        "paso a paso para facilitar la revisión manual."
    )

    # Parámetros base
    pdf.subsection("1.1 Parámetros Base")
    bp = base_params
    param_rows = [
        ["c0 (consumo autónomo)", _fmt(bp.get("c0", 10), 2),
         "c1 (prop. marginal a consumir)", _fmt(bp.get("c1", 0.75), 2)],
        ["I0 (inversión autónoma)", _fmt(bp.get("I0", 15), 2),
         "NX0 (exp. netas autónomas)", _fmt(bp.get("NX0", 5), 2)],
        ["G (gasto gobierno)", _fmt(bp.get("G", 20), 2),
         "T (impuestos)", _fmt(bp.get("T", 20), 2)],
        ["b (IS - sensib. inv.)", _fmt(bp.get("b", 2), 2),
         "x1 (IS - sensib. exp.)", _fmt(bp.get("x1", 1.5), 2)],
        ["k (LM - sensib. ingreso)", _fmt(bp.get("k", 0.5), 2),
         "h (LM - sensib. tasa)", _fmt(bp.get("h", 2), 2)],
        ["m1 (prop. marginal importar)", _fmt(bp.get("m1", 0.15), 2),
         "r* (tasa internacional)", _fmt(bp.get("r_star", 5), 2)],
        ["E (tipo de cambio fijo)", _fmt(bp.get("E", 10), 2),
         "M (oferta monetaria)", _fmt(bp.get("M", 40), 2)],
    ]
    pdf.draw_table(
        ["Parámetro", "Valor", "Parámetro", "Valor"],
        param_rows,
        [65, 22, 65, 22],
    )

    # Cálculo paso a paso
    pdf.subsection("1.2 Cálculo Paso a Paso")

    c0 = bp.get("c0", 10)
    c1 = bp.get("c1", 0.75)
    T  = bp.get("T", 20)
    I0 = bp.get("I0", 15)
    G  = bp.get("G", 20)
    NX0= bp.get("NX0", 5)
    b  = bp.get("b", 2.0)
    x1 = bp.get("x1", 1.5)
    k  = bp.get("k", 0.5)
    h  = bp.get("h", 2.0)
    m1 = bp.get("m1", 0.15)
    E  = bp.get("E", 10.0)
    r_star = bp.get("r_star", 5.0)
    M  = bp.get("M", 40.0)

    A    = c0 - c1*T + I0 + G + NX0
    mult = 1.0 / (1 - c1 + m1)
    Y_fixed   = mult * (A + x1*E - b*r_star)
    M_endo    = k*Y_fixed - h*r_star
    Y_flex    = (M + h*r_star) / k
    E_endo    = ((1 - c1 + m1)*Y_flex + b*r_star - A) / x1

    calc_rows = [
        ["A = c0 - c1-T + I0 + G + NX0",
         f"= {c0} - {c1}-{T} + {I0} + {G} + {NX0}",
         f"= {A:.4f}",
         "OK" if abs(A - 35) < 0.01 else "?"],
        ["mult = 1/(1 - c1 + m1)",
         f"= 1/(1 - {c1} + {m1})",
         f"= {mult:.4f}",
         "OK" if abs(mult - 2.5) < 0.01 else "?"],
        ["Y (fijo) = mult-(A + x1-E - b-r*)",
         f"= {mult:.2f}-({A:.1f} + {x1}-{E} - {b}-{r_star})",
         f"= {Y_fixed:.4f}",
         "OK" if abs(Y_fixed - 100) < 0.1 else "?"],
        ["M_endo = k-Y - h-r*",
         f"= {k}-{Y_fixed:.1f} - {h}-{r_star}",
         f"= {M_endo:.4f}",
         "OK" if abs(M_endo - 40) < 0.1 else "?"],
        ["Y (flexible) = (M + h-r*)/k",
         f"= ({M} + {h}-{r_star})/{k}",
         f"= {Y_flex:.4f}",
         "OK" if abs(Y_flex - 100) < 0.1 else "?"],
        ["E_endo = ((1-c1+m1)-Y + b-r* - A)/x1",
         f"= ({1-c1+m1:.2f}-{Y_flex:.1f} + {b}-{r_star} - {A:.1f})/{x1}",
         f"= {E_endo:.4f}",
         "OK" if abs(E_endo - 10) < 0.1 else "?"],
    ]
    pdf.draw_table(
        ["Ecuación", "Sustitución", "Resultado", "OK"],
        calc_rows,
        [62, 55, 35, 22],
    )

    # Comparación engine vs analítico
    pdf.subsection("1.3 Verificación Engine vs Analítico (tolerancia 0.01)")
    verify_rows = [
        ["Multiplicador (mult)", "2.5000", _fmt(equilibrium_base.get("mult", 0)),
         "OK" if abs(equilibrium_base.get("mult", 0) - 2.5) < 0.01 else "FAIL"],
        ["Y (TC Fijo)", "100.0000", _fmt(equilibrium_base.get("Y", 0)),
         "OK" if abs(equilibrium_base.get("Y", 0) - 100) < 0.01 else "FAIL"],
        ["M endógena", "40.0000", _fmt(equilibrium_base.get("M_endo", 0)),
         "OK" if abs(equilibrium_base.get("M_endo", 0) - 40) < 0.01 else "FAIL"],
    ]
    pdf.draw_table(["Variable", "Esperado", "Engine", "Estado"], verify_rows, [55, 35, 35, 22])

    # ── SECCIÓN 2: Registro de Prompts ────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_DARK_BG)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.section_title(2, "Registro de Prompts Utilizados con IA")

    pdf.body_text(
        "Complete la siguiente tabla con cada interacción significativa con la IA durante el "
        "desarrollo del simulador. Documente el prompt exacto, la respuesta recibida y cualquier "
        "modificación que haya tenido que hacer manualmente."
    )

    prompt_headers = ["#", "Prompt Utilizado", "Respuesta IA (resumen)", "Modificación manual"]
    prompt_widths  = [8, 58, 58, 50]

    # Si hay prompts pre-cargados, los muestra; si no, crea filas vacías
    if prompts_used:
        prompt_rows = [
            [str(i+1), p.get("prompt", ""), p.get("respuesta", ""), p.get("modificacion", "")]
            for i, p in enumerate(prompts_used)
        ]
    else:
        prompt_rows = [[str(i+1), "", "", ""] for i in range(8)]

    pdf.draw_table(prompt_headers, prompt_rows, prompt_widths)

    pdf.body_text(
        "Nota: Documente también los casos donde la IA generó código incorrecto y tuvo que "
        "verificarse manualmente contra la solución analítica (ver Sección 1)."
    )

    # ── SECCIÓN 3: Errores y Correcciones ────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_DARK_BG)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.section_title(3, "Errores Encontrados y Correcciones Aplicadas")

    pdf.body_text(
        "Documente al menos 3 errores significativos encontrados durante el desarrollo. "
        "Incluya el error exacto, su causa raíz y la solución implementada. "
        "Esto demuestra comprensión del modelo y capacidad de debugging."
    )

    for i in range(1, 4):
        pdf.error_block(i)

    # ── SECCIÓN 4: Análisis de Política Bolivia 2024 ──────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_DARK_BG)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.section_title(4, "Análisis de Política Económica - Bolivia 2024")

    pdf.body_text(
        "El preset 'Bolivia_2024_Stagflation' representa el escenario de estanflación que enfrenta "
        "Bolivia en 2024: caída de reservas internacionales, restricción de divisas, contracción "
        "de la inversión privada y presión sobre el tipo de cambio. Se analizan ambos regímenes "
        "cambiarios para evaluar las alternativas de política disponibles."
    )

    # Parámetros del shock Bolivia
    from config.parameters import CRISIS_PRESETS
    bolivia_shock = CRISIS_PRESETS.get("Bolivia_2024_Stagflation", {})
    pdf.subsection("4.1 Shocks Aplicados al Preset Bolivia 2024")
    shock_rows = [[k, _fmt(float(v), 2)] for k, v in bolivia_shock.items()]
    pdf.draw_table(["Parámetro chocado", "Valor"], shock_rows, [80, 40])

    # Resultados Bolivia
    if bolivia_analysis:
        pdf.subsection("4.2 Equilibrios Resultantes")
        bolivia_rows = []
        for regime_label, eq in bolivia_analysis.items():
            if isinstance(eq, dict):
                bolivia_rows.append([
                    regime_label,
                    _fmt(eq.get("Y", float("nan"))),
                    _fmt(eq.get("r", float("nan"))),
                    _fmt(eq.get("M_endo", eq.get("E_endo", float("nan")))),
                    _fmt(eq.get("NX", float("nan"))),
                ])
        if bolivia_rows:
            pdf.draw_table(
                ["Régimen", "Y (PIB)", "r (tasa)", "M_endo / E_endo", "NX"],
                bolivia_rows,
                [45, 28, 28, 42, 28],
            )

    # Interpretación automática (estructurada, el estudiante completa)
    pdf.subsection("4.3 Análisis de Política - Bolivia en la Clasificación Salter-Swan")
    if salter_zone:
        zone = salter_zone.get("zone", "?")
        pdf.body_text(
            f"Zona identificada: {zone} | "
            f"q_IB = {salter_zone.get('q_IB', 0):.4f} | "
            f"q_EB = {salter_zone.get('q_EB', 0):.4f}"
        )
    pdf.body_text(
        "Bajo tipo de cambio FIJO: La política fiscal expansiva es efectiva (IS se desplaza "
        "hacia la derecha), pero Bolivia pierde reservas para mantener el tipo de cambio. "
        "La política monetaria es inefectiva (M es endógena).\n\n"
        "Bajo tipo de cambio FLEXIBLE: La política monetaria sería efectiva "
        "(LM se desplaza -> depreciación ->  up NX ->  up Y), pero el costo es la depreciación "
        "cambiaria con potencial inflación importada."
    )

    pdf.subsection("4.4 Recomendación de Política (complete el estudiante)")
    pdf.placeholder_box(45, "[ Escriba su recomendación de política aquí (máx. 150 palabras) ]")

    # Gráfico IS-LM Bolivia (si se proporciona)
    if fig_islm:
        png_path = export_graph_for_report(fig_islm, "islm_bolivia")
        if png_path and png_path.exists():
            pdf.image(str(png_path), x=18, w=174)
            pdf.ln(3)

    # ── SECCIÓN 5: Reflexión Final ────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_DARK_BG)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.section_title(5, "Reflexión Final")

    pdf.body_text(
        "En máximo media página, reflexione sobre:\n"
        "  a) ¿Qué supuestos del modelo Mundell-Fleming le parecen más irreales para una "
        "economía como Bolivia?\n"
        "  b) ¿Cómo cambiarían los resultados si se relajara el supuesto de movilidad "
        "perfecta de capitales?\n"
        "  c) ¿Qué limitaciones encontró en el uso de IA para construir el simulador y "
        "cómo las superó?\n\n"
        "Importante: Esta sección debe ser escrita completamente por el estudiante. "
        "El uso de texto generado por IA sin análisis propio no se evaluará como reflexión."
    )

    pdf.placeholder_box(100, "[ Reflexión del estudiante - máx. media página ]")

    pdf.ln(4)
    pdf.set_text_color(*_GRAY_TXT)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6,
             "Nota: Este informe fue generado automáticamente como plantilla. "
             "El contenido en [ corchetes ] debe ser completado por el estudiante.",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Exportar ──────────────────────────────────────────────────────────────
    date_str  = datetime.now().strftime("%Y%m%d_%H%M")
    filename  = f"Informe_MacroAbierta_{date_str}.pdf"
    out_path  = _REPORT_DIR / filename

    pdf_bytes = pdf.output()
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)

    return bytes(pdf_bytes)

```

### Archivo: `report\__init__.py`
```python
# report package — Fase 3: Generación de informes PDF

```

### Archivo: `ui\calibration_panel.py`
```python
"""
ui/calibration_panel.py
=======================
Panel profesional de calibración inicial — Fase 4.
Cuatro pestañas: Datos Macro, Parámetros Estructurales, Sector Externo, Política Inicial.
"""
from __future__ import annotations
import streamlit as st
from config.bolivia_data import BOLIVIA_PRESETS, get_bolivia_params, list_presets
from config.validation_rules import VALIDATION_RULES, validate_params
from config.parameters import get_base_params
from utils.validators import validate_macro_consistency, format_validation_message

# ── CSS de tarjetas institucional ─────────────────────────────────────────────
_CARD_CSS = """
<style>
.f4-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;
  padding:14px 18px;margin-bottom:10px;box-shadow:0 1px 4px rgba(30,64,175,.07);}
.f4-card h4{color:#1e40af;margin:0 0 4px 0;font-size:1rem;}
.f4-card p{color:#475569;margin:0;font-size:.85rem;}
.f4-param-ok{color:#10b981;font-weight:600;}
.f4-param-warn{color:#f59e0b;font-weight:600;}
.f4-param-err{color:#ef4444;font-weight:600;}
</style>
"""

# ── Mapa preset → nombre UI ───────────────────────────────────────────────────
_PRESET_LABELS: dict[str, str] = {
    "base": "⚙️ Parámetros base (Sección 3.1)",
    **{p["key"]: f"🇧🇴 {p['label']}" for p in list_presets()},
}


def _sync_slider_input(key_slider: str, key_input: str, default: float,
                        vmin: float, vmax: float, step: float, label: str,
                        help_text: str = "") -> float:
    """
    Renderiza slider + number_input sincronizados mediante callbacks.
    Retorna el valor actual.
    """
    # Inicializar
    if key_slider not in st.session_state:
        st.session_state[key_slider] = float(default)

    def _on_slider():
        st.session_state[key_input] = st.session_state[key_slider]

    def _on_input():
        val = st.session_state[key_input]
        st.session_state[key_slider] = max(vmin, min(vmax, val))

    col1, col2 = st.columns([3, 1])
    with col1:
        st.slider(label, vmin, vmax, key=key_slider, step=step,
                  on_change=_on_slider, help=help_text, format="%.3g")
    with col2:
        st.number_input("", vmin, vmax, key=key_input,
                        step=step, format="%.3g",
                        on_change=_on_input, label_visibility="collapsed")

    return float(st.session_state[key_slider])


def _init_f4_params(preset_key: str = "base") -> None:
    """Inicializa st.session_state con parámetros del preset dado."""
    if preset_key == "base":
        p = get_base_params()
    else:
        p = get_bolivia_params(preset_key)

    defaults = {
        "f4_c0":     p.get("c0",     10.0),
        "f4_c1":     p.get("c1",     0.75),
        "f4_I0":     p.get("I0",     15.0),
        "f4_NX0":    p.get("NX0",    5.0),
        "f4_b":      p.get("b",      2.0),
        "f4_m1":     p.get("m1",     0.15),
        "f4_x1":     p.get("x1",     1.5),
        "f4_k":      p.get("k",      0.5),
        "f4_h":      p.get("h",      2.0),
        "f4_G":      p.get("G",      20.0),
        "f4_T":      p.get("T",      20.0),
        "f4_E":      p.get("E",      10.0),
        "f4_r_star": p.get("r_star", 5.0),
        "f4_M":      p.get("M",      40.0),
        # Widgets espejo para number_input
        "f4_c0_n":     p.get("c0",     10.0),
        "f4_c1_n":     p.get("c1",     0.75),
        "f4_I0_n":     p.get("I0",     15.0),
        "f4_NX0_n":    p.get("NX0",    5.0),
        "f4_b_n":      p.get("b",      2.0),
        "f4_m1_n":     p.get("m1",     0.15),
        "f4_x1_n":     p.get("x1",     1.5),
        "f4_k_n":      p.get("k",      0.5),
        "f4_h_n":      p.get("h",      2.0),
        "f4_G_n":      p.get("G",      20.0),
        "f4_T_n":      p.get("T",      20.0),
        "f4_E_n":      p.get("E",      10.0),
        "f4_r_star_n": p.get("r_star", 5.0),
        "f4_M_n":      p.get("M",      40.0),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = float(v)


def _force_load_preset(preset_key: str) -> None:
    """Fuerza la carga de un preset sobrescribiendo session_state."""
    if preset_key == "base":
        p = get_base_params()
    else:
        p = get_bolivia_params(preset_key)

    mapping = {
        "f4_c0": "c0", "f4_c1": "c1", "f4_I0": "I0", "f4_NX0": "NX0",
        "f4_b": "b", "f4_m1": "m1", "f4_x1": "x1", "f4_k": "k", "f4_h": "h",
        "f4_G": "G", "f4_T": "T", "f4_E": "E", "f4_r_star": "r_star", "f4_M": "M",
    }
    for sk, pk in mapping.items():
        val = float(p.get(pk, st.session_state.get(sk, 0.0)))
        st.session_state[sk]         = val
        st.session_state[sk + "_n"]  = val


def render_calibration_panel(mode: str = "advanced") -> dict[str, float] | None:
    """
    Renderiza el panel de calibración con 4 pestañas.

    Parameters
    ----------
    mode : "quick" | "advanced"

    Returns
    -------
    dict[str, float] | None
        Parámetros calibrados, o None si hay errores de validación bloqueantes.
    """
    st.markdown(_CARD_CSS, unsafe_allow_html=True)

    # ── Selector de preset Bolivia ────────────────────────────────────────────
    st.markdown("#### 🗺️ Carga rápida de preset boliviano")
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        preset_choice = st.selectbox(
            "Seleccionar preset",
            options=list(_PRESET_LABELS.keys()),
            format_func=lambda k: _PRESET_LABELS[k],
            key="f4_preset_choice",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("📥 Cargar", key="f4_load_preset_btn", use_container_width=True):
            _force_load_preset(preset_choice)
            st.rerun()

    # Mostrar descripción del preset seleccionado
    if preset_choice != "base" and preset_choice in BOLIVIA_PRESETS:
        meta = BOLIVIA_PRESETS[preset_choice].get("_meta", {})
        desc = meta.get("description", "")
        if desc:
            with st.expander("📖 Contexto económico del preset", expanded=False):
                st.markdown(f"""
<div class='f4-card'>
<h4>{meta.get('label','')}</h4>
<p>{desc}</p>
</div>
""", unsafe_allow_html=True)
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Crecimiento PIB", f"{meta.get('GDP_growth_pct','—')}%")
                col_m2.metric("Inflación", f"{meta.get('inflation_pct','—')}%")
                col_m3.metric("Reservas (meses imp.)", meta.get('reserves_months_imports','—'))

    st.divider()

    # ── Inicializar con defaults si no existe ─────────────────────────────────
    _init_f4_params("base")

    # ── 4 pestañas de calibración ─────────────────────────────────────────────
    tab_macro, tab_struct, tab_ext, tab_pol = st.tabs([
        "📊 Datos Macro",
        "🔩 Parámetros Estructurales",
        "🌐 Sector Externo",
        "🏛️ Política Inicial",
    ])

    # ═══════════════════════════════════════════════════════════════════
    # PESTAÑA 1: DATOS MACROECONÓMICOS
    # ═══════════════════════════════════════════════════════════════════
    with tab_macro:
        st.markdown("##### Componentes de la demanda agregada")
        with st.expander("ℹ️ Sobre estos parámetros", expanded=False):
            st.info(
                "**Consumo autónomo (c₀)**: consumo independiente del ingreso. "
                "**Inversión autónoma (I₀)**: inversión no ligada a la tasa de interés. "
                "**NX₀**: saldo autónomo de la balanza comercial. "
                "Juntos forman: A = c₀ − c₁·T + I₀ + G + NX₀"
            )

        c0  = _sync_slider_input("f4_c0",  "f4_c0_n",  st.session_state["f4_c0"],
                                  0.0,  30.0, 0.5, "Consumo autónomo (c₀)",
                                  "Gasto de consumo independiente del ingreso disponible.")
        I0  = _sync_slider_input("f4_I0",  "f4_I0_n",  st.session_state["f4_I0"],
                                  -20.0, 40.0, 0.5, "Inversión autónoma (I₀)",
                                  "Inversión privada independiente de r. Puede ser negativa en crisis.")
        NX0 = _sync_slider_input("f4_NX0", "f4_NX0_n", st.session_state["f4_NX0"],
                                  -20.0, 30.0, 0.5, "Exportaciones netas autónomas (NX₀)",
                                  "Saldo comercial estructural. Negativo = déficit comercial crónico.")

        st.markdown("---")
        # Multiplicador preview
        c1_preview = st.session_state.get("f4_c1", 0.75)
        m1_preview = st.session_state.get("f4_m1", 0.15)
        denom = 1 - c1_preview + m1_preview
        if denom > 0:
            mult_preview = 1 / denom
            st.info(f"🔢 **Multiplicador actual**: `1/(1 − {c1_preview:.2f} + {m1_preview:.2f}) = {mult_preview:.3f}`")
        else:
            st.error("❌ Multiplicador indefinido. Ajuste c₁ y m₁.")

    # ═══════════════════════════════════════════════════════════════════
    # PESTAÑA 2: PARÁMETROS ESTRUCTURALES
    # ═══════════════════════════════════════════════════════════════════
    with tab_struct:
        st.markdown("##### Propensiones y sensibilidades del modelo")
        with st.expander("ℹ️ Guía de parámetros estructurales", expanded=False):
            st.markdown("""
**c₁ (PMgC)**: fracción del ingreso adicional que va a consumo.
Multiplicador = 1/(1 − c₁ + m₁). A mayor c₁, mayor multiplicador.

**m₁ (PMgM)**: fracción del ingreso adicional que se gasta en importaciones (fuga).
Reduce el multiplicador keynesiano.

**b**: sensibilidad de la inversión a la tasa de interés (pendiente IS).
Mayor b → IS más plana → política monetaria más potente.

**k, h**: parámetros de la curva LM. k controla la pendiente, h la elasticidad a r.
""")

        c1 = _sync_slider_input("f4_c1", "f4_c1_n", st.session_state["f4_c1"],
                                 0.30, 0.95, 0.01, "Propensión marginal a consumir (c₁)",
                                 "↑c₁ → ↑multiplicador. Bolivia ~0.70–0.80.")
        m1 = _sync_slider_input("f4_m1", "f4_m1_n", st.session_state["f4_m1"],
                                 0.05, 0.50, 0.01, "Propensión marginal a importar (m₁)",
                                 "↑m₁ → ↓multiplicador (fuga al exterior). Bolivia ~0.15–0.25.")
        b  = _sync_slider_input("f4_b",  "f4_b_n",  st.session_state["f4_b"],
                                 0.50, 8.0, 0.10, "Sensibilidad inversión a r (b)",
                                 "b alto → IS plana → política monetaria más efectiva.")
        k  = _sync_slider_input("f4_k",  "f4_k_n",  st.session_state["f4_k"],
                                 0.10, 1.0, 0.01, "Sensibilidad demanda dinero a Y (k)",
                                 "k alto → LM más inclinada.")
        h  = _sync_slider_input("f4_h",  "f4_h_n",  st.session_state["f4_h"],
                                 0.20, 8.0, 0.10, "Sensibilidad demanda dinero a r (h)",
                                 "h alto → LM más plana (mayor elasticidad a la tasa).")

        # Validación en tiempo real c1+m1
        if c1 - m1 >= 1.0:
            st.error(f"❌ c₁ − m₁ = {c1-m1:.3f} ≥ 1. El multiplicador sería negativo o indefinido.")
        elif c1 + m1 > 1.0:
            st.warning(f"⚠️ c₁ + m₁ = {c1+m1:.3f} > 1. Alta propensión al gasto total.")
        else:
            mult_v = 1 / (1 - c1 + m1)
            st.success(f"✅ Multiplicador = {mult_v:.3f}")

    # ═══════════════════════════════════════════════════════════════════
    # PESTAÑA 3: SECTOR EXTERNO Y FINANZAS
    # ═══════════════════════════════════════════════════════════════════
    with tab_ext:
        st.markdown("##### Parámetros del sector externo")
        with st.expander("ℹ️ Régimen cambiario y movilidad de capitales", expanded=False):
            st.markdown("""
**Régimen cambiario** determina qué variable es endógena:
- **Fijo / De facto fijo**: E exógeno, M endógena. Política fiscal efectiva.
- **Flexible**: M exógena, E endógena. Política monetaria efectiva.
- **Administrado**: BCB interviene parcialmente.

**Movilidad de capitales**: el modelo base usa movilidad perfecta (BP horizontal).
Bolivia históricamente tiene movilidad **imperfecta** por controles cambiarios.
""")

        x1 = _sync_slider_input("f4_x1", "f4_x1_n", st.session_state["f4_x1"],
                                  0.10, 4.0, 0.10, "Elasticidad exportaciones al TC (x₁)",
                                  "↑x₁ → IS más sensible a E. Bolivia: exportaciones primarias inelásticas.")

        col_reg, col_mob = st.columns(2)
        with col_reg:
            exchange_regime = st.selectbox(
                "Régimen cambiario",
                ["fixed", "flexible", "managed_float", "de_facto_fixed"],
                format_func=lambda x: {
                    "fixed":          "🏛️ Tipo de cambio fijo",
                    "flexible":       "🌊 Tipo de cambio flexible",
                    "managed_float":  "🎛️ Flotación administrada",
                    "de_facto_fixed": "⚓ Fijo de facto (Bolivia 2011–)",
                }[x],
                index=3,  # Bolivia de facto fixed por defecto
                key="f4_exchange_regime",
            )
        with col_mob:
            capital_mobility = st.selectbox(
                "Movilidad de capitales",
                ["perfect", "imperfect", "low"],
                format_func=lambda x: {
                    "perfect":   "🔓 Perfecta (BP horizontal)",
                    "imperfect": "🔐 Imperfecta (BP inclinada)",
                    "low":       "🔒 Baja (controles estrictos)",
                }[x],
                index=1,  # Bolivia: imperfecta por defecto
                key="f4_capital_mobility",
            )

        # Advertencia de coherencia régimen-modelo
        if exchange_regime in ("flexible", "managed_float"):
            st.info(
                "ℹ️ Con TC flexible, la **simulación usará eq_flexible()**: "
                "M exógena, E endógeno. Ajuste M en la pestaña de Política Inicial."
            )
        else:
            st.info(
                "ℹ️ Con TC fijo/de facto, la **simulación usará eq_fixed()**: "
                "E exógeno, M endógena. Ajuste E en la pestaña de Política Inicial."
            )

    # ═══════════════════════════════════════════════════════════════════
    # PESTAÑA 4: POLÍTICA INICIAL
    # ═══════════════════════════════════════════════════════════════════
    with tab_pol:
        st.markdown("##### Instrumentos de política económica")
        with st.expander("ℹ️ Consistencia de política", expanded=False):
            st.markdown("""
**TC Fijo**: E es el instrumento cambiario. M se ajusta endógenamente.
Modificar M no cambia el equilibrio en régimen fijo (el BCB la acomoda).

**TC Flexible**: M es el instrumento monetario. E se determina endógenamente.
El nivel de E aquí sirve como punto de partida para calibración, no como instrumento.
""")

        G      = _sync_slider_input("f4_G",      "f4_G_n",      st.session_state["f4_G"],
                                     0.0, 60.0, 0.5,  "Gasto de Gobierno (G)",
                                     "TC Fijo: ↑G → ↑Y (política fiscal efectiva).")
        T      = _sync_slider_input("f4_T",      "f4_T_n",      st.session_state["f4_T"],
                                     0.0, 60.0, 0.5,  "Impuestos lump-sum (T)",
                                     "↑T → ↓consumo disponible → IS se contrae.")
        r_star = _sync_slider_input("f4_r_star", "f4_r_star_n", st.session_state["f4_r_star"],
                                     0.0, 25.0, 0.25, "Tasa de interés internacional (r*)",
                                     "Incluye SOFR/LIBOR + prima de riesgo país Bolivia.")
        E      = _sync_slider_input("f4_E",      "f4_E_n",      st.session_state["f4_E"],
                                     1.0, 30.0, 0.10, "Tipo de cambio nominal (E)",
                                     "Instrumento bajo TC fijo. Bs/USD ≈ 6.96 para Bolivia.")
        M      = _sync_slider_input("f4_M",      "f4_M_n",      st.session_state["f4_M"],
                                     5.0, 150.0, 1.0, "Oferta monetaria (M)",
                                     "Instrumento bajo TC flexible. Endógena bajo TC fijo.")

        # Déficit fiscal preview
        deficit = G - T
        color_class = "f4-param-err" if deficit > 10 else ("f4-param-warn" if deficit > 5 else "f4-param-ok")
        st.markdown(
            f"<div class='f4-card'><h4>Balance Fiscal</h4>"
            f"<p>G − T = <span class='{color_class}'>{deficit:+.1f}</span> "
            f"({'déficit' if deficit > 0 else 'superávit'} fiscal)</p></div>",
            unsafe_allow_html=True,
        )

    # ── Recoger todos los parámetros ──────────────────────────────────────────
    params = {
        "c0":     st.session_state["f4_c0"],
        "c1":     st.session_state["f4_c1"],
        "I0":     st.session_state["f4_I0"],
        "NX0":    st.session_state["f4_NX0"],
        "b":      st.session_state["f4_b"],
        "m1":     st.session_state["f4_m1"],
        "x1":     st.session_state["f4_x1"],
        "k":      st.session_state["f4_k"],
        "h":      st.session_state["f4_h"],
        "G":      st.session_state["f4_G"],
        "T":      st.session_state["f4_T"],
        "E":      st.session_state["f4_E"],
        "r_star": st.session_state["f4_r_star"],
        "M":      st.session_state["f4_M"],
    }

    # ── Validación global ─────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### 🔍 Validación de parámetros")
    _, range_errors, range_warnings = validate_params(params)
    cross_errors, cross_warnings    = validate_macro_consistency(params)
    all_errors   = range_errors + cross_errors
    all_warnings = range_warnings + cross_warnings

    if all_errors:
        st.error(format_validation_message(all_errors, []))
    if all_warnings:
        with st.expander(f"⚠️ {len(all_warnings)} advertencia(s) — clic para ver", expanded=False):
            st.warning(format_validation_message([], all_warnings))
    if not all_errors and not all_warnings:
        st.success("✅ Todos los parámetros son consistentes.")

    # Guardar params en session_state para acceso global
    st.session_state["f4_current_params"] = params
    st.session_state["f4_exchange_regime_val"] = st.session_state.get("f4_exchange_regime", "de_facto_fixed")

    return None if all_errors else params

```

### Archivo: `ui\charts.py`
```python
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

```

### Archivo: `ui\comparison.py`
```python
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

```

### Archivo: `ui\controls.py`
```python
"""
ui/controls.py — Widgets de control para el simulador Mundell-Fleming + Salter-Swan.
Solo retorna valores; no llama al motor directamente.
"""
from __future__ import annotations
import streamlit as st
from config.parameters import CRISIS_PRESETS, get_base_params

_PRESET_OPTIONS: dict[str, str] = {
    "Base":                        "base",
    "Bolivia 2024 (Estanflación)": "Bolivia_2024_Stagflation",
    "Boom Exportador":             "Boom_Exportador",
    "Credit Crunch":               "Credit_Crunch",
}
_UI_PRESETS: dict[str, dict] = {"base": {}, **CRISIS_PRESETS}


def _apply_preset(preset_key: str, prefix: str, base: dict) -> None:
    ov = _UI_PRESETS.get(preset_key, {})
    for k in ("G","T","r_star","c1","m1","x1","b","k","h"):
        bk = "r_star" if k == "r_star" else k
        st.session_state[f"{prefix}_{k}"] = float(ov.get(bk, base[bk if bk != "r_star" else "r_star"]))
    if prefix == "fixed":
        st.session_state["fixed_E"] = float(ov.get("E", base["E"]))
    if prefix == "flexible":
        st.session_state["flexible_M"] = float(ov.get("M", base["M"]))


def _init_state(prefix: str, base: dict, regime: str) -> None:
    defaults = {
        f"{prefix}_G": base["G"], f"{prefix}_T": base["T"],
        f"{prefix}_r_star": base["r_star"], f"{prefix}_c1": base["c1"],
        f"{prefix}_m1": base["m1"], f"{prefix}_x1": base["x1"],
        f"{prefix}_b": base["b"], f"{prefix}_k": base["k"],
        f"{prefix}_h": base["h"],
    }
    if regime == "fixed":
        defaults[f"{prefix}_E"] = base["E"]
    if regime == "flexible":
        defaults[f"{prefix}_M"] = base["M"]
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _structural_expander(prefix: str) -> dict[str, float]:
    with st.expander("Parámetros estructurales", expanded=False):
        c1 = st.slider("Propensión marginal a consumir c₁", 0.40, 0.95,
                       st.session_state[f"{prefix}_c1"], 0.05, "%.2f", key=f"{prefix}_c1_slider")
        m1 = st.slider("Propensión marginal a importar m₁", 0.05, 0.40,
                       st.session_state[f"{prefix}_m1"], 0.05, "%.2f", key=f"{prefix}_m1_slider")
        x1 = st.slider("Sensibilidad exportaciones al TC x₁", 0.5, 3.0,
                       st.session_state[f"{prefix}_x1"], 0.1, "%.1f", key=f"{prefix}_x1_slider")
        b  = st.slider("Sensibilidad inversión a r (b)", 0.5, 5.0,
                       st.session_state[f"{prefix}_b"], 0.5, "%.1f", key=f"{prefix}_b_slider")
        k  = st.slider("Sensibilidad demanda dinero a Y (k)", 0.1, 1.0,
                       st.session_state[f"{prefix}_k"], 0.05, "%.2f", key=f"{prefix}_k_slider")
        h  = st.slider("Sensibilidad demanda dinero a r (h)", 0.5, 5.0,
                       st.session_state[f"{prefix}_h"], 0.5, "%.1f", key=f"{prefix}_h_slider")
    return dict(c1=c1, m1=m1, x1=x1, b=b, k=k, h=h)


def render_fixed_controls() -> dict[str, float]:
    base, prefix = get_base_params(), "fixed"
    _init_state(prefix, base, "fixed")

    preset_lbl = st.selectbox("Escenario de crisis", list(_PRESET_OPTIONS),
                              key=f"{prefix}_preset_label")
    if st.button("Cargar preset", key=f"{prefix}_load_preset"):
        _apply_preset(_PRESET_OPTIONS[preset_lbl], prefix, base)
        st.rerun()
    st.divider()

    st.markdown("**Política Fiscal**")
    G = st.slider("Gasto de Gobierno G", 5.0, 50.0, st.session_state["fixed_G"],
                  1.0, "%.0f", key="fixed_G_slider",
                  help="↑G desplaza la IS a la derecha → ↑Y (TC fijo).")
    T = st.slider("Impuestos T", 5.0, 50.0, st.session_state["fixed_T"],
                  1.0, "%.0f", key="fixed_T_slider",
                  help="↑T contrae la IS → ↓Y.")

    st.markdown("**Política Cambiaria**")
    E = st.slider("Tipo de Cambio Nominal E", 5.0, 20.0, st.session_state["fixed_E"],
                  0.5, "%.1f", key="fixed_E_slider",
                  help="↑E = devaluación → ↑NX → IS se desplaza a derecha.")

    st.markdown("**Condición Externa**")
    r_star = st.slider("Tasa de Interés Internacional r*", 1.0, 12.0,
                       st.session_state["fixed_r_star"], 0.5, "%.1f",
                       key="fixed_r_star_slider",
                       help="Bajo movilidad perfecta, r = r* en equilibrio.")

    struct = _structural_expander(prefix)

    for k, v in dict(G=G, T=T, E=E, r_star=r_star, **struct).items():
        st.session_state[f"{prefix}_{k}"] = v

    return {**base, "G": G, "T": T, "E": E, "r_star": r_star, **struct}


def render_flexible_controls() -> dict[str, float]:
    base, prefix = get_base_params(), "flexible"
    _init_state(prefix, base, "flexible")

    preset_lbl = st.selectbox("Escenario de crisis", list(_PRESET_OPTIONS),
                              key=f"{prefix}_preset_label")
    if st.button("Cargar preset", key=f"{prefix}_load_preset"):
        _apply_preset(_PRESET_OPTIONS[preset_lbl], prefix, base)
        st.rerun()
    st.divider()

    st.markdown("**Política Fiscal**")
    G = st.slider("Gasto de Gobierno G", 5.0, 50.0, st.session_state["flexible_G"],
                  1.0, "%.0f", key="flexible_G_slider",
                  help="En TC flexible, ↑G → apreciación cambiaria, Y no cambia.")
    T = st.slider("Impuestos T", 5.0, 50.0, st.session_state["flexible_T"],
                  1.0, "%.0f", key="flexible_T_slider")

    st.markdown("**Política Monetaria**")
    M = st.slider("Oferta Monetaria M", 15.0, 70.0, st.session_state["flexible_M"],
                  1.0, "%.0f", key="flexible_M_slider",
                  help="↑M → LM se desplaza → ↑Y. Política monetaria efectiva en TC flexible.")

    st.markdown("**Condición Externa**")
    r_star = st.slider("Tasa de Interés Internacional r*", 1.0, 12.0,
                       st.session_state["flexible_r_star"], 0.5, "%.1f",
                       key="flexible_r_star_slider")

    struct = _structural_expander(prefix)

    for k, v in dict(G=G, T=T, M=M, r_star=r_star, **struct).items():
        st.session_state[f"{prefix}_{k}"] = v

    return {**base, "G": G, "T": T, "M": M, "r_star": r_star, **struct}


def render_salter_controls() -> tuple[float, float]:
    prefix = "salter"
    if "salter_A" not in st.session_state:
        st.session_state["salter_A"] = 100.0
    if "salter_q" not in st.session_state:
        st.session_state["salter_q"] = 1.0

    _SS_PRESETS = {
        "Equilibrio ideal (punto bliss)":                    (100.0, 1.0),
        "Bolivia 2024 (Zona III — déficit + desempleo)":     (75.0,  0.75),
        "Boom exportador (Zona I — superávit + sobreempleo)":(115.0, 1.30),
        "Ajuste fiscal (Zona II — superávit + desempleo)":   (88.0,  1.15),
    }

    preset_ss = st.selectbox("Escenario ilustrativo", list(_SS_PRESETS), key="salter_preset")
    if st.button("Cargar escenario", key="salter_load"):
        st.session_state["salter_A"], st.session_state["salter_q"] = _SS_PRESETS[preset_ss]
        st.rerun()
    st.divider()

    st.markdown("**Instrumentos de política**")
    A = st.slider("Absorción doméstica A", 40.0, 160.0, st.session_state["salter_A"],
                  1.0, "%.0f", key="salter_A_slider",
                  help="↑A expande demanda interna (política fiscal/monetaria expansiva).")
    q = st.slider("Tipo de Cambio Real q", 0.10, 2.00, st.session_state["salter_q"],
                  0.05, "%.2f", key="salter_q_slider",
                  help="q > 1 → depreciación real (mayor competitividad). q = 1 → equilibrio.")

    st.session_state["salter_A"] = A
    st.session_state["salter_q"] = q
    return A, q

```

### Archivo: `ui\narrative.py`
```python
"""
ui/narrative.py — Narrativa económica automática para cada régimen.
Explica los mecanismos de ajuste en lenguaje académico accesible.
"""
from __future__ import annotations


def generate_fixed_narrative(
    delta_G: float,
    delta_T: float,
    delta_E: float,
    delta_rs: float,
    Y: float,
    M_endo: float,
    NX: float,
    mult: float,
) -> str:
    """
    Genera narrativa para el régimen de tipo de cambio FIJO.

    Mecanismo Mundell-Fleming (TC fijo, movilidad perfecta):
    - Política fiscal es EFECTIVA → ↑G desplaza IS → ↑Y, ↑r → entrada capital → BC interviene → ↑M
    - Política monetaria INEFECTIVA → banco central pierde control de M (endógena)
    - Devaluación → ↑E → IS se desplaza derecha → ↑Y (efecto gasto en exportaciones)
    """
    lines: list[str] = []

    # --- Transmisión del Gasto Público ---
    if abs(delta_G) > 0.5:
        dir_g = "aumentó" if delta_G > 0 else "redujo"
        effect_g = "expansión" if delta_G > 0 else "contracción"
        lines.append(
            f"**Política Fiscal [{'+' if delta_G>0 else ''}{delta_G:.0f} en G]:** "
            f"El gasto público se {dir_g} en {abs(delta_G):.0f} unidades. "
            f"Bajo tipo de cambio fijo con movilidad perfecta de capitales, "
            f"la {effect_g} fiscal es **plenamente efectiva**: la curva IS se desplaza, "
            f"el ingreso sube temporalmente, la presión al alza en r induce "
            f"entrada de capitales, y el banco central debe intervenir vendiendo moneda "
            f"extranjera para mantener E fijo, aumentando la oferta monetaria endógenamente. "
            f"Resultado neto: M endógena = {M_endo:.2f}, Y = {Y:.2f}."
        )

    # --- Transmisión de Impuestos ---
    if abs(delta_T) > 0.5:
        dir_t = "aumentaron" if delta_T > 0 else "redujeron"
        lines.append(
            f"**Política Tributaria [{'+' if delta_T>0 else ''}{delta_T:.0f} en T]:** "
            f"Los impuestos se {dir_t}. Dado que c₁ < 1, el efecto sobre la IS "
            f"es menor que un cambio equivalente en G (multiplicador tributario = −c₁·mult). "
            f"El mecanismo de ajuste es análogo: r → BP → intervención cambiaria → M endógena."
        )

    # --- Transmisión Cambiaria ---
    if abs(delta_E) > 0.1:
        dir_e = "devaluó" if delta_E > 0 else "revaluó"
        lines.append(
            f"**Política Cambiaria [{'+' if delta_E>0 else ''}{delta_E:.1f} en E]:** "
            f"La autoridad {dir_e} el tipo de cambio. "
            f"{'Una devaluación' if delta_E > 0 else 'Una revaluación'} "
            f"{'encarece las importaciones y abarata las exportaciones, desplazando la IS a la derecha.' if delta_E > 0 else 'abarata importaciones y encarece exportaciones, contrayendo la IS.'} "
            f"Exportaciones netas actuales: NX = {NX:.2f}."
        )

    # --- Shock externo ---
    if abs(delta_rs) > 0.1:
        dir_r = "subió" if delta_rs > 0 else "bajó"
        lines.append(
            f"**Shock Externo [{'+' if delta_rs>0 else ''}{delta_rs:.1f} en r*]:** "
            f"La tasa internacional {dir_r}. La curva BP se desplaza "
            f"{'hacia arriba' if delta_rs > 0 else 'hacia abajo'}, "
            f"generando {'salida' if delta_rs > 0 else 'entrada'} de capitales. "
            f"El banco central {'pierde' if delta_rs > 0 else 'acumula'} reservas para mantener E."
        )

    # --- Resultado síntesis ---
    lines.append(
        f"\n**Equilibrio actual:** Y = {Y:.2f} | r = r* | "
        f"M_endo = {M_endo:.2f} | NX = {NX:.2f} | Multiplicador = {mult:.3f}"
    )

    if Y <= 0:
        lines.append(
            "\n⚠️ **Advertencia:** El ingreso de equilibrio es negativo. "
            "Los shocks aplicados exceden la capacidad de ajuste del modelo. "
            "Reduzca la intensidad de los shocks o revise la coherencia de los parámetros."
        )

    return "\n\n".join(lines) if lines else "Ajuste los controles para generar la narrativa."


def generate_flexible_narrative(
    delta_G: float,
    delta_T: float,
    delta_M: float,
    delta_rs: float,
    Y: float,
    E_endo: float,
    NX: float,
    mult: float,
) -> str:
    """
    Genera narrativa para el régimen de tipo de cambio FLEXIBLE.

    Mecanismo Mundell-Fleming (TC flexible, movilidad perfecta):
    - Política fiscal INEFECTIVA → ↑G → ↑r → entrada capital → apreciación de E →
      ↓NX → IS retrocede → crowding-out cambiario completo
    - Política monetaria EFECTIVA → ↑M → LM se desplaza → ↓r → salida capital →
      depreciación de E → ↑NX → IS se desplaza → ↑Y
    """
    lines: list[str] = []

    if abs(delta_G) > 0.5:
        dir_g = "aumentó" if delta_G > 0 else "redujo"
        lines.append(
            f"**Política Fiscal [{'+' if delta_G>0 else ''}{delta_G:.0f} en G]:** "
            f"El gasto público se {dir_g}. Bajo tipo de cambio flexible, "
            f"la política fiscal es **completamente inefectiva** (neutralidad fiscal). "
            f"El mecanismo: ↑G desplaza IS → presión al alza en r → entrada de capitales → "
            f"apreciación cambiaria (↓E_endo) → caída de exportaciones netas → "
            f"la IS retrocede hasta su posición original. "
            f"**Crowding-out cambiario total**: Y no cambia, solo cambia la composición del gasto. "
            f"E_endo actual = {E_endo:.3f}."
        )

    if abs(delta_T) > 0.5:
        lines.append(
            f"**Política Tributaria [{'+' if delta_T>0 else ''}{delta_T:.0f} en T]:** "
            f"Análogo a G: el ajuste en T tampoco modifica Y bajo TC flexible. "
            f"El tipo de cambio absorbe el shock fiscal vía el mecanismo de movilidad de capitales."
        )

    if abs(delta_M) > 0.5:
        dir_m = "expandió" if delta_M > 0 else "contrajo"
        lines.append(
            f"**Política Monetaria [{'+' if delta_M>0 else ''}{delta_M:.0f} en M]:** "
            f"La oferta monetaria se {dir_m}. Bajo TC flexible, la política monetaria "
            f"es **plenamente efectiva**: ↑M desplaza LM → ↓r → salida de capitales → "
            f"depreciación cambiaria (↑E_endo) → ↑NX → IS se desplaza a la derecha → ↑Y. "
            f"Resultado: Y = {Y:.2f}, E_endo = {E_endo:.3f}, NX = {NX:.2f}."
        )

    if abs(delta_rs) > 0.1:
        dir_r = "subió" if delta_rs > 0 else "bajó"
        lines.append(
            f"**Shock Externo [{'+' if delta_rs>0 else ''}{delta_rs:.1f} en r*]:** "
            f"La tasa internacional {dir_r}. La LM determina Y = (M + h·r*)/k, "
            f"por lo que el shock se transmite directamente al ingreso de equilibrio. "
            f"El tipo de cambio se ajusta endógenamente para limpiar el mercado externo."
        )

    lines.append(
        f"\n**Equilibrio actual:** Y = {Y:.2f} | r = r* | "
        f"E_endo = {E_endo:.3f} | NX = {NX:.2f} | Multiplicador = {mult:.3f}"
    )

    if Y <= 0:
        lines.append(
            "\n⚠️ **Advertencia:** Ingreso negativo. Reduzca la intensidad de los shocks."
        )

    return "\n\n".join(lines) if lines else "Ajuste los controles para generar la narrativa."


def generate_salter_narrative(zone: str, A: float, q: float, q_IB: float, q_EB: float) -> str:
    """
    Genera narrativa para el modelo Salter-Swan.

    El espacio (A, q) divide la economía en cuatro zonas de desequilibrio.
    El análisis identifica cuál instrumento (absorción o tipo de cambio real)
    y en qué dirección debe aplicarse la política económica.
    """
    _ZONE_TEXT = {
        "I": {
            "estado": "**Zona I — Superávit Externo + Sobreempleo (Inflación)**",
            "desc": (
                "La economía opera por encima del pleno empleo con un superávit de cuenta corriente. "
                "Hay presiones inflacionarias internas mientras el sector externo acumula divisas. "
                "El tipo de cambio real está **demasiado depreciado** y la absorción "
                "**demasiado alta** para ambos equilibrios simultáneamente."
            ),
            "policy": (
                "**Política recomendada:** Apreciar el tipo de cambio real (revaluar E) "
                "**y/o** contraer la absorción doméstica (política fiscal restrictiva). "
                "El mix óptimo depende de cuánto desequilibrio externo e interno existe. "
                "Si la inflación es el problema dominante, priorice la contracción de A."
            ),
        },
        "II": {
            "estado": "**Zona II — Superávit Externo + Desempleo (Capacidad ociosa)**",
            "desc": (
                "La economía tiene exceso de oferta: hay desempleo y simultáneamente "
                "un saldo positivo de cuenta corriente. Esto es la zona de 'paradoja del ahorro': "
                "el país ahorra demasiado en relación a su demanda interna. "
                "El tipo de cambio real está **demasiado apreciado** para el balance externo "
                "pero la absorción es **insuficiente** para el empleo pleno."
            ),
            "policy": (
                "**Política recomendada:** Expandir la absorción doméstica (política fiscal expansiva) "
                "para estimular la demanda interna. El tipo de cambio puede mantenerse o apreciarse "
                "moderadamente. Esta zona es relativamente 'cómoda': hay espacio de política sin "
                "restricción externa inmediata."
            ),
        },
        "III": {
            "estado": "**Zona III — Déficit Externo + Desempleo (El peor escenario)**",
            "desc": (
                "La economía enfrenta el dilema de política más severo: desempleo interno "
                "y déficit de cuenta corriente simultáneos. Las políticas que estimulan el empleo "
                "empeoran el balance externo, y las que corrigen el externo profundizan el desempleo. "
                "Bolivia en 2024 es un ejemplo paradigmático de esta zona: caída de reservas, "
                "presión sobre el tipo de cambio y capacidad productiva ociosa."
            ),
            "policy": (
                "**Política recomendada (difícil):** Depreciar el tipo de cambio real "
                "(↑q = devaluación) para mejorar la competitividad exportadora, "
                "combinado con contención moderada de la absorción para reducir importaciones. "
                "⚠️ **Riesgo crítico:** la devaluación puede generar inflación importada, "
                "especialmente si hay deuda en moneda extranjera (hoja de balance). "
                "Se requiere secuenciación cuidadosa de reformas."
            ),
        },
        "IV": {
            "estado": "**Zona IV — Déficit Externo + Sobreempleo (Economía recalentada)**",
            "desc": (
                "Alta demanda interna presiona simultáneamente los precios y las importaciones. "
                "La economía está por encima del pleno empleo y tiene un déficit externo. "
                "El tipo de cambio real está **demasiado apreciado** y la absorción "
                "**demasiado alta**."
            ),
            "policy": (
                "**Política recomendada:** Contracción de la absorción (política fiscal restrictiva) "
                "**y** depreciación del tipo de cambio real. La política dual es necesaria: "
                "reducir A corrige la inflación y parte del déficit; depreciar q corrige el resto "
                "del déficit externo. Sin la devaluación, el ajuste solo via contracción sería "
                "excesivamente recesivo."
            ),
        },
    }

    info = _ZONE_TEXT.get(zone, {"estado": f"Zona {zone}", "desc": "", "policy": ""})

    texto = f"""{info['estado']}

**Posición actual:** A = {A:.1f} | q = {q:.3f}
**Umbrales:** q_IB = {q_IB:.3f} | q_EB = {q_EB:.3f}

{info['desc']}

{info['policy']}

---
**Cómo leer el gráfico:** Las curvas IB (azul) y EB (naranja) se cruzan en el punto bliss (A=100, q=1.0), el único punto de equilibrio simultáneo interno y externo. La pendiente de IB es negativa (más absorción requiere moneda más apreciada para el equilibrio interno) y la de EB es positiva (más absorción requiere mayor depreciación para equilibrio externo).
"""
    return texto

```

### Archivo: `ui\scenario_cards.py`
```python
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

```

### Archivo: `ui\timeline_viewer.py`
```python
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

```

### Archivo: `ui\__init__.py`
```python
# ui package — Fase 2: Interfaz Streamlit

```

### Archivo: `utils\export.py`
```python
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

```

### Archivo: `utils\exporters.py`
```python
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

```

### Archivo: `utils\validators.py`
```python
"""
utils/validators.py
===================
Validadores de consistencia macroeconómica para Fase 4.
Complementa config/validation_rules.py con reglas de coherencia cruzada.

Funciones públicas:
    validate_macro_consistency(params) → list[str]
    format_validation_message(errors, warnings) → str
"""

from __future__ import annotations

import math


def validate_macro_consistency(params: dict) -> tuple[list[str], list[str]]:
    """
    Verifica la consistencia macroeconómica interna del conjunto de parámetros.
    Aplica reglas que involucran múltiples variables (no solo rangos individuales).

    Rules:
        1. Multiplicador positivo: (1 - c1 + m1) > 0
        2. Demanda de dinero positiva en equilibrio: k*Y > 0 implícito (k > 0)
        3. Exportaciones elásticas mínimas: x1 > 0 (siempre; error si x1 ≤ 0)
        4. Coherencia fiscal: si G > T*2, déficit fiscal potencialmente insostenible
        5. Coherencia monetaria: M > 0 (si aplica TC flexible)
        6. Sensibilidades positivas: b, k, h > 0

    Parameters
    ----------
    params : dict — parámetros del modelo (del engine/core.py)

    Returns
    -------
    tuple[list[str], list[str]]
        - errors   : condiciones que invalidan el modelo (bloquean simulación)
        - warnings : condiciones preocupantes (no bloquean, solo alertan)
    """
    errors:   list[str] = []
    warnings: list[str] = []

    c1     = params.get("c1",     None)
    m1     = params.get("m1",     None)
    b      = params.get("b",      None)
    k      = params.get("k",      None)
    h      = params.get("h",      None)
    x1     = params.get("x1",     None)
    G      = params.get("G",      None)
    T      = params.get("T",      None)
    M      = params.get("M",      None)
    r_star = params.get("r_star", None)
    NX0    = params.get("NX0",    None)

    # ── Regla 1: Multiplicador positivo ──────────────────────────────────────
    if c1 is not None and m1 is not None:
        denom = 1.0 - c1 + m1
        if denom <= 0:
            errors.append(
                f"❌ Multiplicador indefinido: (1 − c₁ + m₁) = {denom:.4f} ≤ 0. "
                f"El modelo requiere c₁ − m₁ < 1. "
                f"Actual: c₁={c1:.3f}, m₁={m1:.3f}."
            )
        elif denom < 0.05:
            warnings.append(
                f"⚠️ Multiplicador muy alto: 1/(1−c₁+m₁) = {1/denom:.1f}. "
                "Demanda extremadamente elástica; el modelo puede ser inestable."
            )

    # ── Regla 2: Sensibilidades positivas ────────────────────────────────────
    for var_name, val in [("b", b), ("k", k), ("h", h)]:
        if val is not None and val <= 0:
            errors.append(
                f"❌ Parámetro {var_name} = {val:.4f} ≤ 0. "
                "Los parámetros de sensibilidad deben ser estrictamente positivos."
            )

    # ── Regla 3: Elasticidad de exportaciones ────────────────────────────────
    if x1 is not None:
        if x1 <= 0:
            errors.append(
                f"❌ x₁ = {x1:.4f} ≤ 0. La elasticidad de exportaciones debe ser positiva. "
                "Una devaluación debe mejorar la competitividad."
            )
        elif x1 < 0.3:
            warnings.append(
                f"⚠️ x₁ = {x1:.3f} muy bajo. Exportaciones casi inelásticas al tipo de cambio. "
                "La política cambiaria tendrá muy poco impacto sobre NX."
            )

    # ── Regla 4: Coherencia fiscal ────────────────────────────────────────────
    if G is not None and T is not None:
        deficit_ratio = (G - T)
        if deficit_ratio > 15.0:
            warnings.append(
                f"⚠️ Déficit fiscal (G − T) = {deficit_ratio:.1f} es muy elevado. "
                "Puede ser insostenible en el largo plazo. "
                f"G={G:.1f}, T={T:.1f}."
            )
        if T < 0:
            warnings.append(
                f"⚠️ T = {T:.2f} < 0 (subsidio neto). Verifique que este es el escenario deseado."
            )

    # ── Regla 5: Oferta monetaria positiva ───────────────────────────────────
    if M is not None and M <= 0:
        errors.append(
            f"❌ M = {M:.2f} ≤ 0. La oferta monetaria debe ser positiva. "
            "Bajo TC flexible, M = 0 colapsa la demanda agregada."
        )

    # ── Regla 6: Tasa internacional razonable ────────────────────────────────
    if r_star is not None:
        if r_star < 0:
            warnings.append(
                f"⚠️ r* = {r_star:.2f}% < 0 (tasa internacional negativa). "
                "Posible bajo ZIRP/NIRP, pero inusual para economías emergentes."
            )
        if r_star > 20:
            warnings.append(
                f"⚠️ r* = {r_star:.2f}% muy alta. "
                "Refleja situación de crisis de deuda severa o hiperinflación."
            )

    # ── Regla 7: NX autónomo muy negativo ────────────────────────────────────
    if NX0 is not None and NX0 < -10:
        warnings.append(
            f"⚠️ NX₀ = {NX0:.2f} indica déficit comercial estructural muy severo. "
            "Combinado con TC fijo, puede agotar reservas internacionales rápidamente."
        )

    # ── Regla 8: PMgC + PMgM ≥ 1 (implicación del multiplicador) ─────────────
    if c1 is not None and m1 is not None:
        if c1 + m1 > 1.0:
            warnings.append(
                f"⚠️ c₁ + m₁ = {c1+m1:.3f} > 1. "
                "El multiplicador sigue siendo válido (requiere solo c₁ − m₁ < 1), "
                "pero implica que ante un aumento del ingreso, consumo+importaciones "
                "superan el ingreso adicional. Economía de alta propensión al gasto."
            )

    return errors, warnings


def format_validation_message(errors: list[str], warnings: list[str]) -> str:
    """
    Formatea errores y advertencias en un string Markdown legible para st.markdown().

    Parameters
    ----------
    errors   : list[str] — errores (bloquean simulación)
    warnings : list[str] — advertencias (solo informativas)

    Returns
    -------
    str : Mensaje formateado en Markdown.
    """
    parts = []

    if errors:
        parts.append("### ❌ Errores de validación (bloquean simulación)")
        for e in errors:
            parts.append(f"- {e}")

    if warnings:
        parts.append("### ⚠️ Advertencias (no bloquean)")
        for w in warnings:
            parts.append(f"- {w}")

    if not errors and not warnings:
        return "✅ Todos los parámetros son consistentes y están en rango válido."

    return "\n".join(parts)


def quick_validate(params: dict) -> tuple[bool, str]:
    """
    Validación rápida combinada: reglas individuales + consistencia cruzada.
    Útil para mostrar ✅/⚠️/❌ en sidebar.

    Returns
    -------
    tuple[bool, str]
        - is_ok     : True si no hay errores (warnings no cuentan)
        - status_emoji : "✅" | "⚠️" | "❌"
    """
    from config.validation_rules import validate_params as _vp
    _, range_errors, range_warnings = _vp(params)
    cross_errors, cross_warnings    = validate_macro_consistency(params)

    all_errors   = range_errors + cross_errors
    all_warnings = range_warnings + cross_warnings

    if all_errors:
        return False, "❌"
    if all_warnings:
        return True, "⚠️"
    return True, "✅"

```

### Archivo: `utils\__init__.py`
```python
# utils package — Fase 2: Exportación y utilidades

```

### Archivo: `validation\test_equilibrium.py`
```python
"""
validation/test_equilibrium.py
================================
Suite de verificación automática del motor matemático.

Verifica que los equilibrios analíticos de la Sección 3.1 se reproduzcan
exactamente con los parámetros base del modelo.

Valores esperados (parámetros base):
    mult     = 2.5           → 1 / (1 - 0.75 + 0.15) = 1/0.40 = 2.5
    Y_fixed  = 100           → 2.5 * (A + x1*E - b*r*) = 2.5 * (17.5 + 15 - 10) = 55 (revisar)
    M_endo   = 40            → k*Y - h*r* = 0.5*100 - 2*5 = 50 - 10 = 40
    Y_flex   = 100           → (M + h*r*) / k = (40 + 10) / 0.5 = 100
    E_endo   = 10            → ((1-c1+m1)*Y + b*r* - A) / x1

Cálculo explícito de A (base):
    A = c0 - c1*T + I0 + G + NX0
      = 10 - 0.75*20 + 15 + 20 + 5
      = 10 - 15 + 15 + 20 + 5 = 35

Verificación Y_fixed:
    Y = mult * (A + x1*E - b*r*)
      = 2.5 * (35 + 1.5*10 - 2*5)
      = 2.5 * (35 + 15 - 10)
      = 2.5 * 40 = 100  ✓

Verificación E_endo:
    E = ((1-c1+m1)*Y + b*r* - A) / x1
      = (0.40*100 + 2*5 - 35) / 1.5
      = (40 + 10 - 35) / 1.5
      = 15 / 1.5 = 10  ✓
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from config.parameters import get_base_params
from engine.core import (
    autonomous_demand,
    eq_fixed,
    eq_flexible,
    multiplier,
)

# Tolerancia numérica para comparación de floats
_TOLERANCE = 0.01

# Directorio de salida para resultados de validación
_VALIDATION_DIR = Path(__file__).parent.parent / "validation"
_RESULTS_PATH = _VALIDATION_DIR / "results.parquet"


def _step_by_step(p: dict[str, float]) -> None:
    """
    Imprime el cálculo paso a paso del equilibrio base para depuración.

    Parameters
    ----------
    p : dict[str, float]
        Parámetros del modelo.
    """
    A    = autonomous_demand(p["c0"], p["c1"], p["T"], p["I0"], p["G"], p["NX0"])
    mult = multiplier(p["c1"], p["m1"])
    r    = p["r_star"]

    Y_fixed  = mult * (A + p["x1"] * p["E"] - p["b"] * r)
    M_endo   = p["k"] * Y_fixed - p["h"] * r
    Y_flex   = (p["M"] + p["h"] * r) / p["k"]
    E_endo   = ((1 - p["c1"] + p["m1"]) * Y_flex + p["b"] * r - A) / p["x1"]

    print("\n" + "=" * 60)
    print("  CÁLCULO PASO A PASO — PARÁMETROS BASE")
    print("=" * 60)
    print(f"  Parámetros clave:")
    print(f"    c0={p['c0']}, c1={p['c1']}, T={p['T']}, I0={p['I0']}, G={p['G']}, NX0={p['NX0']}")
    print(f"    b={p['b']}, x1={p['x1']}, k={p['k']}, h={p['h']}")
    print(f"    E={p['E']}, r*={p['r_star']}, M={p['M']}, m1={p['m1']}")
    print("-" * 60)
    print(f"  A  = c0 - c1·T + I0 + G + NX0")
    print(f"     = {p['c0']} - {p['c1']}·{p['T']} + {p['I0']} + {p['G']} + {p['NX0']}")
    print(f"     = {A:.4f}")
    print(f"  mult = 1/(1 - c1 + m1) = 1/(1 - {p['c1']} + {p['m1']}) = {mult:.4f}")
    print("-" * 60)
    print(f"  [TC FIJO] Y  = mult·(A + x1·E - b·r*)")
    print(f"               = {mult:.4f}·({A:.4f} + {p['x1']}·{p['E']} - {p['b']}·{r})")
    print(f"               = {Y_fixed:.4f}  (esperado: 100)")
    print(f"  [TC FIJO] M_endo = k·Y - h·r*")
    print(f"                   = {p['k']}·{Y_fixed:.4f} - {p['h']}·{r}")
    print(f"                   = {M_endo:.4f}  (esperado: 40)")
    print("-" * 60)
    print(f"  [TC FLEX] Y  = (M + h·r*) / k")
    print(f"               = ({p['M']} + {p['h']}·{r}) / {p['k']}")
    print(f"               = {Y_flex:.4f}  (esperado: 100)")
    print(f"  [TC FLEX] E_endo = ((1-c1+m1)·Y + b·r* - A) / x1")
    print(f"                   = ({1-p['c1']+p['m1']:.2f}·{Y_flex:.4f} + {p['b']}·{r} - {A:.4f}) / {p['x1']}")
    print(f"                   = {E_endo:.4f}  (esperado: 10)")
    print("=" * 60 + "\n")


def verify_base() -> tuple[dict, dict]:
    """
    Verifica los equilibrios analíticos con los parámetros base.

    Ejecuta eq_fixed y eq_flexible y compara contra valores esperados
    de la Sección 3.1 del documento con tolerancia de 0.01.

    Returns
    -------
    tuple[dict, dict]
        (resultado_fijo, resultado_flexible) si pasa todas las verificaciones.

    Raises
    ------
    ValueError
        Si alguna verificación falla, incluye diagnóstico detallado.
    """
    p = get_base_params()

    # ── Calcular equilibrios ─────────────────────────────────────────────────
    res_fixed    = eq_fixed(p)
    res_flexible = eq_flexible(p)

    # ── Valores esperados según Sección 3.1 ──────────────────────────────────
    expected = {
        "mult":    2.5,
        "Y_fixed": 100.0,
        "M_endo":  40.0,
        "Y_flex":  100.0,
        "E_endo":  10.0,
    }

    # ── Valores calculados ───────────────────────────────────────────────────
    calculated = {
        "mult":    res_fixed["mult"],
        "Y_fixed": res_fixed["Y"],
        "M_endo":  res_fixed["M_endo"],
        "Y_flex":  res_flexible["Y"],
        "E_endo":  res_flexible["E_endo"],
    }

    # ── Verificaciones con tolerancia ────────────────────────────────────────
    failures: list[str] = []

    for key, expected_val in expected.items():
        calc_val = calculated[key]
        diff = abs(calc_val - expected_val)
        if diff > _TOLERANCE:
            failures.append(
                f"  ✗ {key}: calculado={calc_val:.6f}, esperado={expected_val:.6f}, "
                f"diferencia={diff:.6f} > tolerancia={_TOLERANCE}"
            )

    if failures:
        # Imprimir cálculo paso a paso antes de lanzar error
        _step_by_step(p)
        error_msg = (
            "❌ VALIDACIÓN FALLIDA — Motor matemático diverge de solución analítica\n"
            + "\n".join(failures)
            + "\n\nRevise las ecuaciones en engine/core.py contra la Sección 3.1."
        )
        raise ValueError(error_msg)

    # ── Reporte de éxito ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ✅ VALIDACIÓN EXITOSA — Motor matemático verificado")
    print("=" * 60)
    print(f"  mult     = {calculated['mult']:.4f}  (esperado {expected['mult']:.4f})")
    print(f"  Y_fixed  = {calculated['Y_fixed']:.4f}  (esperado {expected['Y_fixed']:.4f})")
    print(f"  M_endo   = {calculated['M_endo']:.4f}  (esperado {expected['M_endo']:.4f})")
    print(f"  Y_flex   = {calculated['Y_flex']:.4f}  (esperado {expected['Y_flex']:.4f})")
    print(f"  E_endo   = {calculated['E_endo']:.4f}  (esperado {expected['E_endo']:.4f})")
    print("=" * 60 + "\n")

    # ── Guardar results.parquet ──────────────────────────────────────────────
    _save_results_parquet(res_fixed, res_flexible)

    return res_fixed, res_flexible


def _save_results_parquet(
    res_fixed: dict,
    res_flexible: dict,
) -> None:
    """
    Serializa los equilibrios base a results.parquet con pyarrow.

    Parameters
    ----------
    res_fixed    : Resultado de eq_fixed con parámetros base.
    res_flexible : Resultado de eq_flexible con parámetros base.
    """
    records = [
        {
            "scenario":  "Base_Fixed",
            "regime":    "fixed",
            "preset":    "base",
            "Y":         res_fixed["Y"],
            "r":         res_fixed["r"],
            "E":         res_fixed["E"],
            "M_endo":    res_fixed["M_endo"],
            "E_endo":    float("nan"),
            "NX":        res_fixed["NX"],
            "C":         res_fixed["C"],
            "I_inv":     res_fixed["I_inv"],
            "mult":      res_fixed["mult"],
        },
        {
            "scenario":  "Base_Flexible",
            "regime":    "flexible",
            "preset":    "base",
            "Y":         res_flexible["Y"],
            "r":         res_flexible["r"],
            "E":         float("nan"),
            "M_endo":    float("nan"),
            "E_endo":    res_flexible["E_endo"],
            "NX":        res_flexible["NX"],
            "C":         res_flexible["C"],
            "I_inv":     res_flexible["I_inv"],
            "mult":      res_flexible["mult"],
        },
    ]

    df = pd.DataFrame(records)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, str(_RESULTS_PATH), compression="snappy")
    print(f"  📄 Resultados base guardados en: {_RESULTS_PATH.name}")

```

### Archivo: `validation\__init__.py`
```python
# validation package

```

