"""
ui_simple/main_layout.py
========================
Layout principal de 3 columnas en Streamlit:
- Columna 1 (~25%): Controles de política económica (8 palancas en 3 ministerios).
- Columna 2 (~50%): 8 KPIs macroeconómicos superiores + 4 Pestañas de gráficos Plotly.
- Columna 3 (~25%): Periódico El Observador Macroeconómico y Dictamen de los 3 Asesores de Gabinete.

Menú lateral:
- Serialización JSON (Guardar / Cargar partida para Supabase y Canvas).
- Consola de Auditoría Macroeconómica & Inspector de Bugs (Beta-Testing).
"""

from __future__ import annotations

import json
import streamlit as st
from config_simple.scenarios import SCENARIOS
from engine_simple.state_manager import StateManager
from ui_simple.charts_panel import render_charts_panel
from ui_simple.controls_panel import render_controls_panel
from ui_simple.explanation_panel import render_explanation_panel
from ui_simple.kpi_panel import render_kpi_panel
from ui_simple.styles import inject_custom_css


def render_app() -> None:
    """Punto de entrada de la interfaz de usuario Streamlit."""
    st.set_page_config(
        page_title="The Economic War Room — Edición Educativa V1.2 SIMPLE",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inyectar estilos CSS
    inject_custom_css()

    # Inicializar o recuperar StateManager en Session State
    if "state_mgr" not in st.session_state:
        st.session_state.state_mgr = StateManager("chile_rule")

    state_mgr: StateManager = st.session_state.state_mgr
    curr_snap = state_mgr.history[-1]
    scen_info = SCENARIOS.get(state_mgr.scenario_id, {})
    scen_name = scen_info.get("name", state_mgr.scenario_id)

    # ─────────────────────────────────────────────────────────────────────────
    # BARRA LATERAL (SIDEBAR): PERSISTENCIA JSON Y CONSOLA DE AUDITORÍA
    # ─────────────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Herramientas de Partida")

        # Guardar Partida JSON
        game_json = json.dumps(state_mgr.to_dict(), indent=2)
        st.download_button(
            label="💾 Guardar Partida (JSON)",
            data=game_json,
            file_name=f"partida_{state_mgr.scenario_id}_t{state_mgr.current_turn}.json",
            mime="application/json",
            use_container_width=True,
            help="Descarga el estado completo de la partida en formato JSON para persistencia."
        )

        # Cargar Partida JSON
        uploaded_file = st.file_uploader(
            "📂 Cargar Partida (JSON)",
            type=["json"],
            help="Restaura una partida guardada previamente."
        )
        if uploaded_file is not None:
            if st.button("Restaurar Estado desde Archivo", use_container_width=True):
                try:
                    payload = json.load(uploaded_file)
                    st.session_state.state_mgr = StateManager.from_dict(payload)
                    st.success("¡Partida restaurada con éxito!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al leer JSON: {e}")

        st.markdown("---")

        # ─────────────────────────────────────────────────────────────────────
        # CONSOLA DE AUDITORÍA MACROECONÓMICA & INSPECTOR DE BUGS (BETA-TESTING)
        # ─────────────────────────────────────────────────────────────────────
        with st.expander("🔬 Inspector Macroeconómico & Debug", expanded=False):
            st.caption("Herramienta de verificación en tiempo real para Beta-Testing:")

            # 1. Error de Identidad Contable
            C_val = curr_snap["C"]
            I_val = curr_snap["I_priv"]
            G_val = curr_snap["G"]
            NX_val = curr_snap["NX"]
            Y_calc = C_val + I_val + G_val + NX_val
            identity_err = abs(curr_snap["Y"] - Y_calc)

            if identity_err < 1e-12:
                st.success(f"✅ Identidad Exacta: Error = {identity_err:.2e} (< 10⁻¹²)")
            else:
                st.error(f"❌ Error de Identidad: {identity_err:.4e}")

            # 2. Desglose de Demanda Agregada
            st.markdown("**Desglose de Demanda Agregada:**")
            st.write({
                "Consumo (C)": round(C_val, 2),
                "Inversión Privada (I)": round(I_val, 2),
                "Gasto Corriente (Gc)": round(curr_snap["Gc"], 2),
                "Inversión Pública (Ig)": round(curr_snap["Ig"], 2),
                "Exportaciones (X)": round(curr_snap["X"], 2),
                "Importaciones (M)": round(curr_snap["M_imp"], 2),
                "Exportaciones Netas (NX)": round(NX_val, 2),
                "PIB Real (Y)": round(curr_snap["Y"], 2),
                "PIB Nominal": round(curr_snap["PIB_nominal"], 2),
            })

            # 3. Desglose Fiscal
            st.markdown("**Desglose de Finanzas Públicas:**")
            st.write({
                "Recaudación": round(curr_snap["recaudacion"], 2),
                "Costo Subsidios": round(curr_snap["costo_subsidios"], 2),
                "Intereses Deuda": round(curr_snap["intereses_deuda"], 2),
                "Déficit Total": round(curr_snap["deficit"], 2),
                "Stock Deuda (B)": round(curr_snap["B"], 2),
                "Ratio Deuda/PIB Nom": f"{curr_snap['debt_to_gdp_nominal']*100:.2f}%",
            })

            # 4. Contadores de Peligro Game Over (Regla 2 turnos)
            st.markdown("**Contadores de Peligro Game Over:**")
            st.write(state_mgr.consecutive_danger_turns)

            # 5. Parámetros del Motor
            st.markdown("**Credibilidad y Comercio:**")
            st.write({
                "Credibilidad θ": round(curr_snap.get("theta", 0.40), 2),
                "Expectativas π_e": f"{curr_snap['pi_e']*100:.2f}%",
                "P_local": round(curr_snap["P_local"], 4),
                "TCR (q)": round(curr_snap["q_real"], 4),
                "Condición M-L": (state_mgr.current_params.get("epsilon_x", 1.2) + state_mgr.current_params.get("epsilon_m", 1.1)) > 1.0,
            })

        st.markdown("---")
        if st.button("🔄 Reiniciar Partida Actual", use_container_width=True):
            state_mgr.start_simulation()
            st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # MODAL EMERGENTE PARA EVENTOS MACROECONÓMICOS (V1.3 — FASE C.2)
    # ─────────────────────────────────────────────────────────────────────────
    if state_mgr.pending_modal_event is not None:
        _handle_event_modal(state_mgr)

    # ─────────────────────────────────────────────────────────────────────────
    # ENCABEZADO INSTITUCIONAL
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="background-color: #0f172a; color: white; padding: 12px 20px; border-radius: 8px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 6px rgba(0,0,0,0.12);">
            <div>
                <span style="font-size: 1.25rem; font-weight: 800; letter-spacing: 0.5px;">🏛️ THE ECONOMIC WAR ROOM</span>
                <span style="font-size: 0.85rem; color: #94a3b8; margin-left: 12px;">{scen_name}</span>
            </div>
            <div style="display: flex; gap: 12px; align-items: center;">
                <span style="background-color: #1e293b; color: #38bdf8; border: 1px solid #334155; padding: 4px 14px; border-radius: 14px; font-size: 0.82rem; font-weight: 700;">
                    Turno {state_mgr.current_turn} de 10
                </span>
                <span style="background-color: #1e293b; color: #e2e8f0; border: 1px solid #334155; padding: 4px 14px; border-radius: 14px; font-size: 0.82rem; font-weight: 700;">
                    Aprobación: {curr_snap.get('score', 70.0):.1f}%
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ─────────────────────────────────────────────────────────────────────────
    # EVALUACIÓN DE PANTALLAS DE FIN DE PARTIDA
    # ─────────────────────────────────────────────────────────────────────────
    if state_mgr.is_game_over:
        st.markdown(
            f"""
            <div style="background-color: #fef2f2; border: 2px solid #dc2626; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: #991b1b; margin-top: 0;">💥 DERROTA: COLAPSO MACROECONÓMICO (GAME OVER)</h2>
                <p style="font-size: 1.05rem; color: #7f1d1d; font-weight: 600;">{state_mgr.game_over_reason}</p>
                <hr style="border: 1px solid #fecaca;">
                <p style="font-size: 0.92rem; color: #334155;">
                    <strong>Autopsia Didáctica:</strong> La economía acumuló dos turnos consecutivos en zona crítica.
                    Revise la combinación de política monetaria, régimen cambiario y disciplina fiscal para evitar el colapso.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    elif state_mgr.current_turn >= 10:
        summary = state_mgr.get_endgame_summary()
        st.markdown(
            f"""
            <div style="background-color: #f0fdf4; border: 2px solid #16a34a; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: #166534; margin-top: 0;">🎉 ¡MISIÓN CUMPLIDA! 10 TURNOS COMPLETADOS CON ÉXITO</h2>
                <p style="font-size: 1.05rem; color: #14532d;">Has gobernado exitosamente durante toda la década sin que el país colapse.</p>
                <div style="display: flex; gap: 20px; margin-top: 15px;">
                    <div><strong>Score Promedio:</strong> {summary['avg_score']:.1f} / 100</div>
                    <div><strong>PIB Final:</strong> {summary['final_Y']:.1f}</div>
                    <div><strong>Inflación Final:</strong> {summary['final_inflation']:.1f}%</div>
                    <div><strong>Desempleo Final:</strong> {summary['final_unemployment']:.1f}%</div>
                    <div><strong>Rating Final:</strong> {summary['final_rating']}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    # LAYOUT DE 3 COLUMNAS
    # ─────────────────────────────────────────────────────────────────────────
    col_left, col_center, col_right = st.columns([2.5, 5.0, 2.5])

    # 1. Columna Izquierda: Panel de Controles
    with col_left:
        ctrl_output = render_controls_panel(state_mgr)

    # 2. Columna Central: KPIs y Gráficos
    with col_center:
        render_kpi_panel(state_mgr.history)
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        render_charts_panel(state_mgr)

    # 3. Columna Derecha: Prensa y Gabinete
    with col_right:
        render_explanation_panel(state_mgr)

    # ─────────────────────────────────────────────────────────────────────────
    # PROCESAMIENTO DE ACCIONES RETORNADAS POR EL PANEL DE CONTROLES
    # ─────────────────────────────────────────────────────────────────────────
    action = ctrl_output.get("action", "none")

    if action == "change_scenario":
        new_scen = ctrl_output["new_scenario"]
        state_mgr.start_simulation(new_scen)
        st.rerun()

    elif action == "switch_regime":
        state_mgr.switch_regime(
            new_regime=ctrl_output["new_regime"],
            new_E=ctrl_output.get("new_E"),
            new_crawl=ctrl_output.get("new_crawl")
        )
        st.rerun()

    elif action == "trigger_event":
        event_id = ctrl_output["event_id"]
        state_mgr.trigger_exogenous_event(event_id)
        st.rerun()

    elif action == "step":
        proposed_inst = ctrl_output["instruments"]
        try:
            state_mgr.step_forward(proposed_inst)
        except Exception as err:
            st.error(f"⚠️ Error al avanzar turno: {err}")
        st.rerun()


def _handle_event_modal(state_mgr: StateManager) -> None:
    """
    Despliega el modal emergente institucional si existe un evento programado
    o aleatorio gatillado en el turno actual (Fase C.2).
    """
    modal_data = state_mgr.pending_modal_event
    if modal_data is None:
        return

    # Usar el decorador nativo st.dialog si está disponible en Streamlit
    if hasattr(st, "dialog"):
        @st.dialog("🚨 COMUNICADO MACROECONÓMICO OFICIAL")
        def _render_dialog(data: Dict[str, Any]) -> None:
            st.subheader(f"📰 {data['title']}")
            st.markdown(f"<p style='font-size: 1.05rem; color: #334155; line-height: 1.5;'>{data['description']}</p>", unsafe_allow_html=True)
            st.caption(f"⏱️ **Duración estimada:** {data.get('duration', 2)} turnos")

            if data.get("impact_metrics"):
                st.markdown("##### 📊 Impactos Cuantitativos Inmediatos:")
                st.table(data["impact_metrics"])

            st.info(f"💡 **Dictamen del Gabinete Económico:**\n\n{data['advice_summary']}")

            if st.button("Continuar gobernando 🏛️", type="primary", use_container_width=True, key="btn_dialog_dismiss"):
                state_mgr.dismiss_event_modal()
                st.rerun()

        _render_dialog(modal_data)
    else:
        # Fallback si st.dialog no está soportado en la versión de Streamlit
        st.markdown(
            f"""
            <div style="background-color: #fef2f2; border: 2px solid #b91c1c; border-radius: 8px; padding: 18px 24px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(185, 28, 28, 0.15);">
                <div style="font-size: 1.15rem; font-weight: 800; color: #991b1b; margin-bottom: 6px;">
                    🚨 COMUNICADO MACROECONÓMICO OFICIAL
                </div>
                <h3 style="margin-top: 0; color: #0f172a;">📰 {modal_data['title']}</h3>
                <p style="font-size: 1.05rem; color: #334155; line-height: 1.5;">{modal_data['description']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if modal_data.get("impact_metrics"):
            st.table(modal_data["impact_metrics"])
        st.info(f"💡 **Dictamen del Gabinete:** {modal_data['advice_summary']}")
        if st.button("Continuar gobernando 🏛️", type="primary", use_container_width=True, key="btn_fallback_dismiss"):
            state_mgr.dismiss_event_modal()
            st.rerun()

