"""
ui/onboarding.py
================
Pantalla de inicio / Onboarding para el Simulador Macroeconómico V2.0.

Reemplaza el antiguo panel de calibración de la versión 1.0.
Permite elegir escenario, dificultad y régimen inicial de forma premium e inmersiva.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from config.scenarios_v2 import SCENARIO_PRESETS_V3
from config.validation_rules_v2 import VALIDATION_RULES
from engine.state_manager_v2 import SimStateManagerV2


def render_onboarding_panel(mgr: SimStateManagerV2) -> None:
    """
    Renderiza la interfaz de onboarding prémium en Streamlit.
    """
    # ── ESTILOS CSS PREMUM ─────────────────────────────────────────────────────
    st.markdown("""
    <style>
      .onboarding-title {
          font-size: 2.2rem;
          font-weight: 800;
          color: #f59e0b;
          text-align: center;
          margin-bottom: 2px;
          text-transform: uppercase;
          letter-spacing: 1px;
      }
      .onboarding-subtitle {
          font-size: 1.1rem;
          font-style: italic;
          color: #94a3b8;
          text-align: center;
          margin-bottom: 24px;
      }
      .scenario-card-active {
          border: 2px solid #f59e0b !important;
          box-shadow: 0 0 15px rgba(245, 158, 11, 0.3) !important;
          background: #1e293b !important;
      }
      .scenario-card {
          background: #111827;
          border: 1px solid #1e293b;
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 15px;
          transition: all 0.3s ease;
          height: 100%;
          cursor: pointer;
      }
      .scenario-card:hover {
          border-color: #3b82f6;
          box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
      }
      .difficulty-badge {
          display: inline-block;
          padding: 3px 10px;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 700;
          text-transform: uppercase;
          margin-bottom: 8px;
      }
      .badge-facil { background: #dcfce7; color: #15803d; }
      .badge-medio { background: #fef9c3; color: #a16207; }
      .badge-dificil { background: #fee2e2; color: #b91c1c; }
      .badge-muy-dificil { background: #f3e8ff; color: #6b21a8; }
      
      .bullet-point {
          font-size: 0.85rem;
          color: #cbd5e1;
          margin: 6px 0;
          line-height: 1.4;
      }
      
      .dossier-container {
          background: #0f172a;
          border: 1px solid #1e293b;
          border-radius: 10px;
          padding: 18px;
          margin-top: 15px;
          margin-bottom: 20px;
      }
      .dossier-grid {
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          gap: 10px;
          text-align: center;
      }
      .dossier-item {
          background: #1e293b;
          border-radius: 8px;
          padding: 10px;
          border: 1px solid #334155;
      }
      .dossier-val {
          font-size: 1.4rem;
          font-weight: 800;
          color: #3b82f6;
      }
      .dossier-lbl {
          font-size: 0.75rem;
          color: #94a3b8;
          margin-top: 4px;
      }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='onboarding-title'>🏛️ Bienvenido, Ministro de Economía</div>", unsafe_allow_html=True)
    st.markdown("<div class='onboarding-subtitle'>\"El país lo espera. Las decisiones son suyas.\"</div>", unsafe_allow_html=True)

    # Inicializar estado de onboarding en st.session_state
    if "ob_scenario" not in st.session_state:
        st.session_state["ob_scenario"] = "tiger_asia"
    if "ob_difficulty" not in st.session_state:
        st.session_state["ob_difficulty"] = "easy"
    if "custom_structural_params" not in st.session_state:
        st.session_state["custom_structural_params"] = {}

    # ── COLUMNA IZQUIERDA: TARJETAS DE ESCENARIOS ─────────────────────────────────
    st.subheader("📁 Seleccione su Escenario de Gobierno")
    
    # Grid 2x2 para escenarios
    col1, col2 = st.columns(2)
    
    scenarios = list(SCENARIO_PRESETS_V3.items())
    
    for idx, (sc_id, sc_def) in enumerate(scenarios):
        target_col = col1 if idx % 2 == 0 else col2
        
        # Clase CSS según esté seleccionado o no
        active_class = "scenario-card-active" if st.session_state["ob_scenario"] == sc_id else ""
        
        # Mapear dificultad a badge clase
        diff_lower = sc_def["difficulty"].lower()
        badge_style = "badge-facil"
        if "medio" in diff_lower:
            badge_style = "badge-medio"
        elif "muy" in diff_lower:
            badge_style = "badge-muy-dificil"
        elif "difícil" in diff_lower:
            badge_style = "badge-dificil"
            
        with target_col:
            st.markdown(f"""
            <div class='scenario-card {active_class}'>
              <span class='difficulty-badge {badge_style}'>{sc_def['difficulty']}</span>
              <h3 style='margin: 4px 0 8px 0; color: #f8fafc; font-size: 1.15rem;'>{sc_def['name']}</h3>
              <p style='font-size: 0.85rem; color: #94a3b8; margin-bottom: 12px; line-height: 1.4; height: 75px; overflow: hidden;'>{sc_def['description']}</p>
              <div style='margin-bottom: 14px;'>
                {"".join([f"<div class='bullet-point'>{b}</div>" for b in sc_def['bullets']])}
              </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botón invisible/visible para seleccionar
            if st.button(f"Seleccionar {sc_def['name']}", key=f"select_sc_{sc_id}", use_container_width=True, type="primary" if st.session_state["ob_scenario"] == sc_id else "secondary"):
                st.session_state["ob_scenario"] = sc_id
                # Reiniciar custom structural params al cambiar escenario
                st.session_state["custom_structural_params"] = {}
                st.rerun()

    # ── COLUMNA DERECHA: CONFIGURACIÓN DE GOBIERNO ────────────────────────────────
    st.write("---")
    
    col_setup1, col_setup2 = st.columns([3, 2])
    
    with col_setup2:
        st.subheader("⚙️ Configuración del Gabinete")
        
        # Selector de dificultad
        difficulty_opt = st.radio(
            "Nivel de Dificultad",
            options=["easy", "hard"],
            format_func=lambda x: "🟢 Fácil (Visualización de parámetros + sliders)" if x == "easy" else "🔴 Difícil (Niebla de guerra, parámetros ocultos)",
            key="ob_difficulty_radio"
        )
        st.session_state["ob_difficulty"] = difficulty_opt
        
        # Selector de régimen cambiario
        regime_opt = st.selectbox(
            "Régimen Cambiario Inicial",
            options=["fixed", "flexible", "crawling_peg"],
            format_func=lambda x: "🏛️ Tipo de Cambio Fijo (M endógena)" if x == "fixed" else "🌊 Tipo de Cambio Flexible (E endógena)" if x == "flexible" else "⚙️ Crawling Peg (Deslizamiento Programado)",
            key="ob_regime_select"
        )

    # Dossier del escenario seleccionado
    sel_id = st.session_state["ob_scenario"]
    sel_def = SCENARIO_PRESETS_V3[sel_id]
    init_st = sel_def["initial_state"]
    
    with col_setup1:
        st.subheader("🏛️ Dossier del País — Estado Inicial")
        st.markdown(f"**Escenario:** {sel_def['name']} ({sel_def['difficulty']})")
        st.markdown(f"<p style='font-size: 0.9rem; color: #94a3b8; line-height: 1.5;'>{sel_def['description']}</p>", unsafe_allow_html=True)
        
        # Grid visual del Dossier inicial
        st.markdown(f"""
        <div class='dossier-container'>
          <div class='dossier-grid'>
            <div class='dossier-item'>
              <div class='dossier-val'>{init_st.get('Y_pot', 100.0):.1f}</div>
              <div class='dossier-lbl'>PIB Potencial</div>
            </div>
            <div class='dossier-item'>
              <div class='dossier-val'>{init_st.get('pi_e', 0.03)*100:.1f}%</div>
              <div class='dossier-lbl'>Inflación (π)</div>
            </div>
            <div class='dossier-item'>
              <div class='dossier-val'>{init_st.get('R', 50.0):.1f}</div>
              <div class='dossier-lbl'>Reservas (R)</div>
            </div>
            <div class='dossier-item'>
              <div class='dossier-val'>{init_st.get('B', 60.0):.1f}</div>
              <div class='dossier-lbl'>Deuda (B)</div>
            </div>
            <div class='dossier-item'>
              <div class='dossier-val'>{(sel_def['structural']['U_n'] if 'U_n' in sel_def['structural'] else 0.05)*100:.1f}%</div>
              <div class='dossier-lbl'>NAIRU (U_n)</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── FINE-TUNING AVANZADO DE PARÁMETROS STRUCTURALES ────────────────────────────
    if st.session_state["ob_difficulty"] == "easy":
        with st.expander("🛠️ Fine-tuning avanzado de parámetros estructurales (Solo modo Fácil)"):
            st.info("💡 En dificultad Fácil, usted puede ajustar el punto de partida de los parámetros estructurales de la economía antes de iniciar su mandato.")
            
            # Cargar parámetros base modificados para el escenario
            base_structural = dict(sel_def["structural"])
            customs = st.session_state["custom_structural_params"]
            
            col_ft1, col_ft2 = st.columns(2)
            
            # Agrupar sliders de parámetros estructurales
            structural_keys = [
                ("c1", "Propensión Marginal al Consumo"),
                ("t", "Tasa Impositiva Proporcional"),
                ("epsilon_x", "Elasticidad Exportaciones (M-L)"),
                ("epsilon_m", "Elasticidad Importaciones (M-L)"),
                ("m1", "Propensión Marginal a Importar"),
                ("f", "Movilidad de Capitales (f)"),
                ("beta_PT", "Pass-through Cambiario"),
                ("g_pot", "Crecimiento PIB Potencial estructural"),
            ]
            
            for idx, (key, label) in enumerate(structural_keys):
                target_col = col_ft1 if idx % 2 == 0 else col_ft2
                with target_col:
                    rule = VALIDATION_RULES.get(key, {"min": 0.0, "max": 10.0, "step": 0.05, "rationale": ""})
                    
                    val_init = customs.get(key, base_structural.get(key, rule.get("min", 0.0)))
                    
                    # Asegurar cotas
                    val_init = max(rule["min"], min(rule["max"], float(val_init)))
                    
                    customs[key] = st.slider(
                        label=f"{label} ({key})",
                        min_value=float(rule["min"]),
                        max_value=float(rule["max"]),
                        step=float(rule["step"]),
                        value=float(val_init),
                        help=rule["rationale"],
                        key=f"ob_slider_{key}"
                    )
            st.session_state["custom_structural_params"] = customs

    # ── BOTÓN DE INICIO DE GOBIERNO ──────────────────────────────────────────────
    st.write("---")
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    
    with col_btn2:
        if st.button("🏛️ ¡INICIAR GOBIERNO!", use_container_width=True, type="primary"):
            # Preparar overrides de parámetros estructurales
            custom_params = {}
            if st.session_state["ob_difficulty"] == "easy":
                custom_params = st.session_state["custom_structural_params"]
                
            with st.spinner("Calibrando la economía nacional..."):
                # 1. Calibrar
                mgr.calibrate(
                    scenario_id=st.session_state["ob_scenario"],
                    difficulty=st.session_state["ob_difficulty"],
                    custom_params=custom_params if custom_params else None
                )
                # 2. Iniciar simulación con el régimen seleccionado
                mgr.start_simulation(regime=regime_opt)
                
            st.toast("🟢 ¡Gobierno iniciado! Sus asesores preventivos están listos.", icon="🏛️")
            st.rerun()
