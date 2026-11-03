"""
ui_simple/controls_panel.py
===========================
Panel de controles de política económica (Columna Izquierda: ~25% ancho).
Edición: The Economic War Room (V1.2 SIMPLE).

Características:
- Selector de Escenario con metadatos históricos y dificultad.
- Las 8 Palancas de Política Económica agrupadas por bloques ministeriales.
- Reforma Cambiaria de Emergencia (cambio de régimen en tiempo de ejecución).
- Vista Previa de Impacto en Tiempo Real (Proyección t+1) para Beta-Testing.
- Botón de avance de turno y control de fin de partida.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional

import streamlit as st
from config_simple.parameters import PolicyInstruments
from config_simple.scenarios import SCENARIOS
from engine_simple.state_manager import StateManager


def render_controls_panel(state_mgr: StateManager) -> Dict[str, Any]:
    """
    Renderiza la columna izquierda de controles y palancas.

    Returns
    -------
    Dict[str, Any] : Acción a procesar por el layout principal:
        {
            "action": "none" | "step" | "change_scenario" | "trigger_event" | "switch_regime",
            "new_scenario": str,
            "event_id": str,
            "new_regime": str,
            "new_E": float,
            "new_crawl": float,
            "instruments": PolicyInstruments,
        }
    """
    st.markdown("### 🎛️ Controles de Política")

    action_result: Dict[str, Any] = {
        "action": "none",
        "new_scenario": state_mgr.scenario_id,
        "event_id": "",
        "new_regime": state_mgr.current_instruments["regime"],
        "new_E": state_mgr.current_instruments["E"],
        "new_crawl": state_mgr.current_instruments.get("crawl_rate", 0.0),
        "instruments": copy.deepcopy(state_mgr.current_instruments),
    }

    # ─────────────────────────────────────────────────────────────────────────
    # 1. SELECTOR DE ESCENARIO HISTÓRICO
    # ─────────────────────────────────────────────────────────────────────────
    with st.expander("🏛️ Escenario Histórico", expanded=False):
        # Filtrar solo las 4 claves canónicas para evitar duplicados en el selector
        canonical_keys = ["tiger_asia", "chile_rule", "mexico_tequila", "bolivia_hyper"]
        current_canonical = state_mgr.scenario_id
        if current_canonical not in canonical_keys:
            alias_map = {
                "Economia_Saludable": "chile_rule",
                "latam_crisis": "mexico_tequila",
                "death_spiral": "bolivia_hyper",
            }
            current_canonical = alias_map.get(current_canonical, "tiger_asia")

        current_idx = canonical_keys.index(current_canonical)

        selected_scenario = st.selectbox(
            "Seleccionar Escenario",
            canonical_keys,
            index=current_idx,
            format_func=lambda k: SCENARIOS[k]["name"],
            help="Selecciona una economía real histórica con sus desafíos específicos."
        )

        if selected_scenario != current_canonical:
            if st.button("🔄 Cargar Este Escenario", key="btn_load_scenario", use_container_width=True):
                action_result["action"] = "change_scenario"
                action_result["new_scenario"] = selected_scenario
                return action_result

        scen_info = SCENARIOS[selected_scenario]
        diff_color = {
            "Fácil": "🟢",
            "Normal": "🟡",
            "Difícil": "🟠",
            "Muy Difícil": "🔴"
        }.get(scen_info.get("difficulty", "Normal"), "⚪")

        st.markdown(f"**Dificultad:** {diff_color} {scen_info.get('difficulty', 'Normal')}")
        st.caption(scen_info.get("description", ""))
        if "winning_recipe" in scen_info:
            with st.expander("💡 Pistas del Manual Histórico", expanded=False):
                st.caption(scen_info["winning_recipe"])

    st.markdown("---")

    # Copia mutable de instrumentos actuales para binding
    inst: PolicyInstruments = copy.deepcopy(state_mgr.current_instruments)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. BLOQUE 1: POLÍTICA FISCAL (MINISTERIO DE HACIENDA)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("#### 🏛️ Ministerio de Hacienda (Fiscal)")

    # 1. Gasto Corriente Gc [5.0, 35.0], paso 0.5
    inst["Gc"] = st.slider(
        "Gasto Público Corriente (Gc)",
        min_value=5.0,
        max_value=35.0,
        value=float(inst.get("Gc", 14.0)),
        step=0.5,
        help="Sube la Demanda Agregada (Y) hoy; aumenta el déficit fiscal; no amplía el PIB potencial."
    )

    # 2. Inversión Pública Ig [0.0, 25.0], paso 0.5
    inst["Ig"] = st.slider(
        "Inversión en Infraestructura (Ig)",
        min_value=0.0,
        max_value=25.0,
        value=float(inst.get("Ig", 6.0)),
        step=0.5,
        help="Sube la Demanda Agregada hoy; expande el PIB Potencial futuro (Y_pot) y atrae inversión privada (crowding-in)."
    )

    col_tax1, col_tax2 = st.columns(2)
    with col_tax1:
        # 3. Impuesto a la Renta/Consumo tc [5.0%, 40.0%], paso 0.5%
        tc_pct = st.slider(
            "Impuesto Renta/IVA (tc %)",
            min_value=5.0,
            max_value=40.0,
            value=float(inst.get("tc", 0.16) * 100.0),
            step=0.5,
            help="Reduce el ingreso disponible familiar y achica el multiplicador; recauda fondos fiscales."
        )
        inst["tc"] = tc_pct / 100.0

    with col_tax2:
        # 4. Impuesto Corporativo tk [0.0%, 35.0%], paso 0.5%
        tk_pct = st.slider(
            "Imp. Empresas (tk %)",
            min_value=0.0,
            max_value=35.0,
            value=float(inst.get("tk", 0.10) * 100.0),
            step=0.5,
            help="Reduce la inversión privada empresarial; aumenta recaudación sin tocar consumo familiar."
        )
        inst["tk"] = tk_pct / 100.0

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. BLOQUE 2: POLÍTICA MONETARIA (BANCO CENTRAL)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("#### 🏦 Banco Central (Monetario)")

    # 5. Tasa de Política Monetaria TPM r_ref [1.0%, 30.0%], paso 0.25%
    inst["r_ref"] = st.slider(
        "Tasa de Política Monetaria (TPM r_ref %)",
        min_value=1.0,
        max_value=30.0,
        value=float(inst.get("r_ref", 5.0)),
        step=0.25,
        help="Sube la tasa de interés real, enfría la inversión privada, frena la salida de capitales y ancla expectativas."
    )

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. BLOQUE 3: COMERCIO EXTERIOR Y RÉGIMEN CAMBIARIO
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("#### 🚢 Comercio y Régimen Cambiario")

    col_com1, col_com2 = st.columns(2)
    with col_com1:
        # 6. Arancel a las Importaciones tau [0.0%, 30.0%], paso 0.5%
        tau_pct = st.slider(
            "Arancel Importaciones (τ %)",
            min_value=0.0,
            max_value=30.0,
            value=float(inst.get("tau", 0.05) * 100.0),
            step=0.5,
            help="Frena importaciones y protege reservas, pero encarece precios locales sumando inflación."
        )
        inst["tau"] = tau_pct / 100.0

    with col_com2:
        # 7. Subsidio a las Exportaciones sx [0.0%, 20.0%], paso 0.5%
        sx_pct = st.slider(
            "Subsidio Exportador (sx %)",
            min_value=0.0,
            max_value=20.0,
            value=float(inst.get("sx", 0.00) * 100.0),
            step=0.5,
            help="Impulsa exportaciones y PIB, pero cuesta dinero al fisco aumentando el déficit."
        )
        inst["sx"] = sx_pct / 100.0

    # 8. Instrumento Cambiario según régimen
    current_regime = inst.get("regime", "fixed")
    regime_labels = {
        "fixed": "🔒 Régimen Fijo (TC Fijado)",
        "flexible": "🌊 Régimen Flexible (Flotación limpia)",
        "crawling_peg": "📈 Deslizamiento Programado (Crawling Peg)",
    }
    st.caption(f"**Régimen Vigente:** `{regime_labels.get(current_regime, current_regime)}`")

    if current_regime == "fixed":
        inst["E"] = st.slider(
            "Tipo de Cambio Nominal (E)",
            min_value=5.0,
            max_value=25.0,
            value=float(inst.get("E", 10.0)),
            step=0.1,
            help="El gobierno fija E. Devaluar (E↑) mejora el saldo comercial pero genera inflación por pass-through."
        )
    elif current_regime == "crawling_peg":
        crawl_pct = st.slider(
            "Tasa de Deslizamiento (crawl %)",
            min_value=0.0,
            max_value=25.0,
            value=float(inst.get("crawl_rate", 0.08) * 100.0),
            step=0.5,
            help="Tasa porcentual de depreciación periódica programada por el Banco Central."
        )
        inst["crawl_rate"] = crawl_pct / 100.0
    else:
        st.info(
            "🌊 **Flotación de Mercado**: El tipo de cambio no se controla por slider. "
            "El mercado lo determina automáticamente según la Balanza de Pagos."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # REFORMA CAMBIARIA DE EMERGENCIA (HERRAMIENTA HISTÓRICA)
    # ─────────────────────────────────────────────────────────────────────────
    with st.expander("🚨 Reforma Cambiaria de Emergencia", expanded=False):
        st.caption(
            "Permite decretar una transición institucional del régimen cambiario "
            "(ej. pasar de Fijo a Flexible en México 1994 o unificar el cambio en Bolivia 1985)."
        )
        reform_regime = st.selectbox(
            "Nuevo Régimen a Decretar",
            ["fixed", "flexible", "crawling_peg"],
            index=["fixed", "flexible", "crawling_peg"].index(current_regime),
            format_func=lambda r: regime_labels[r],
            key="reform_regime_select"
        )
        reform_E = float(inst.get("E", 10.0))
        reform_crawl = float(inst.get("crawl_rate", 0.02) * 100.0)

        if reform_regime == "fixed":
            reform_E = st.number_input("Nuevo Tipo de Cambio Anclado (E)", min_value=5.0, max_value=25.0, value=reform_E, step=0.5)
        elif reform_regime == "crawling_peg":
            reform_crawl = st.number_input("Nuevo Crawl Rate (%)", min_value=0.0, max_value=25.0, value=reform_crawl, step=0.5)

        if st.button("⚖️ Promulgar Reforma Cambiaria", type="secondary", use_container_width=True):
            action_result["action"] = "switch_regime"
            action_result["new_regime"] = reform_regime
            action_result["new_E"] = reform_E
            action_result["new_crawl"] = reform_crawl / 100.0
            inst["regime"] = reform_regime
            inst["E"] = reform_E
            inst["crawl_rate"] = reform_crawl / 100.0
            action_result["instruments"] = inst
            return action_result

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. VISTA PREVIA DE IMPACTO EN TIEMPO REAL (PROYECCIÓN t+1) — BETA TESTING
    # ─────────────────────────────────────────────────────────────────────────
    with st.expander("👁️ Vista Previa de Impacto (Proyección t+1)", expanded=True):
        try:
            # Sincronizar compatibilidad para cálculo de dry run
            inst["G"] = inst["Gc"] + inst["Ig"] + inst.get("G_needed", 0.0)
            inst["t"] = inst["tc"]

            dry_snap = state_mgr.get_dry_run_projection(inst)
            curr_snap = state_mgr.history[-1]

            delta_Y = (dry_snap["Y"] - curr_snap["Y"]) / curr_snap["Y"] * 100.0 if curr_snap["Y"] > 0 else 0.0
            delta_U = (dry_snap["U"] - curr_snap["U"]) * 100.0
            delta_pi = (dry_snap["pi"] - curr_snap["pi"]) * 100.0
            delta_debt = (dry_snap["debt_to_gdp_nominal"] - curr_snap["debt_to_gdp_nominal"]) * 100.0
            delta_R = dry_snap["R"] - curr_snap["R"]
            delta_score = dry_snap["score"] - curr_snap["score"]

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.caption(f"**PIB (Y)**: {dry_snap['Y']:.1f} ({delta_Y:+.1f}%)")
                st.caption(f"**Inflación (π)**: {dry_snap['pi']*100:.1f}% ({delta_pi:+.1f} pp)")
                st.caption(f"**Desempleo (U)**: {dry_snap['U']*100:.1f}% ({delta_U:+.1f} pp)")
            with col_p2:
                st.caption(f"**Deuda/PIB**: {dry_snap['debt_to_gdp_nominal']*100:.1f}% ({delta_debt:+.1f} pp)")
                st.caption(f"**Reservas**: {dry_snap['R']:.1f} MUSD ({delta_R:+.1f})")
                st.caption(f"**Aprobación**: {dry_snap['score']:.1f} ({delta_score:+.1f} pts)")

            # Alertas tempranas preventivas
            if dry_snap["pi"] > 0.35:
                st.error("🚨 Alerta: Inflación entrará en zona de Alerta Roja (>35%).")
            elif dry_snap["pi"] > 0.08:
                st.warning("⚠️ Alerta: Presión inflacionaria elevada.")

            if dry_snap["debt_to_gdp_nominal"] > 1.35:
                st.error("🚨 Alerta: Deuda/PIB entrará en zona de Default (>135%).")

            if dry_snap["R"] < 8.0 and inst["regime"] in ("fixed", "crawling_peg"):
                st.error("🚨 Alerta: Reservas en nivel crítico de crisis externa (<8 MUSD).")

            if dry_snap["U"] > 0.22:
                st.error("🚨 Alerta: Desempleo crítico cercano al estallido social (>22%).")

        except Exception as e:
            st.caption(f"Ajuste los controles para recalcular proyección: {e}")

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 6. SIMULADOR DE CHOQUES EXÓGENOS DE PRUEBA
    # ─────────────────────────────────────────────────────────────────────────
    with st.expander("⚡ Simular Choques Exógenos", expanded=False):
        col_ev1, col_ev2 = st.columns(2)
        with col_ev1:
            if st.button("📈 Boom Commodities", key="btn_boom", use_container_width=True):
                action_result["action"] = "trigger_event"
                action_result["event_id"] = "commodity_boom"
                action_result["instruments"] = inst
                return action_result
            if st.button("🏦 Alza Tasa Fed", key="btn_fed", use_container_width=True):
                action_result["action"] = "trigger_event"
                action_result["event_id"] = "fed_rate_shock"
                action_result["instruments"] = inst
                return action_result
        with col_ev2:
            if st.button("📉 Recesión Global", key="btn_recession", use_container_width=True):
                action_result["action"] = "trigger_event"
                action_result["event_id"] = "global_recession"
                action_result["instruments"] = inst
                return action_result

    st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 7. BOTÓN PRINCIPAL DE AVANCE DE TURNO
    # ─────────────────────────────────────────────────────────────────────────
    if state_mgr.is_game_over:
        st.error(f"💀 GAME OVER: {state_mgr.game_over_reason}")
        if st.button("🔄 Reiniciar Partida", type="primary", use_container_width=True):
            action_result["action"] = "change_scenario"
            action_result["new_scenario"] = state_mgr.scenario_id
            return action_result
    elif state_mgr.current_turn >= 10:
        st.success("🎉 ¡Has completado los 10 turnos de la simulación!")
        if st.button("🔄 Jugar Nuevo Escenario", type="primary", use_container_width=True):
            action_result["action"] = "change_scenario"
            action_result["new_scenario"] = state_mgr.scenario_id
            return action_result
    else:
        if st.button(f"⏩ Avanzar al Turno {state_mgr.current_turn + 1}", type="primary", use_container_width=True):
            action_result["action"] = "step"
            action_result["instruments"] = inst
            return action_result

    action_result["instruments"] = inst
    return action_result
