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
    # 1. Definición de Escenario Personalizado
    custom_preset = {
        "name": "⚙️ Escenario Personalizado",
        "difficulty": "Medio (Configurable)",
        "description": "Establezca manualmente todos los parámetros estructurales de la economía para simular un escenario único y a medida.",
        "bullets": [
            "Propensión marginal al consumo ajustable",
            "Flexibilidad de elasticidades y sensibilidades",
            "Régimen cambiario y monetario a elección"
        ],
        "structural": {
            "c0": 10.0, "c1": 0.75, "t": 0.20, "I0": 15.0, "b": 2.0, "rho_k": 0.5, "NX0": 5.0,
            "x0": 0.0, "x1": 0.0, "Y_star": 0.0, "m0": 0.0,
            "epsilon_x": 0.80, "epsilon_m": 0.70, "m1": 0.15,
            "k": 0.50, "h": 2.00, "f": 5.0,
            "alpha_PT": 0.40, "beta_PT": 0.20, "P_star": 1.0,
            "Y_pot_0": 100.0, "g_pot": 0.02,
            "U_n": 0.05, "gamma_okun": 0.50, "alpha_inf": 0.50, "pi_0": 0.0, "G_needed": 0.0
        },
        "policy": {
            "G_c": 15.0, "I_g": 5.0, "Tr": 0.0, "t_c": 0.20, "t_k": 0.20,
            "tau": 0.0, "s_x": 0.0, "k_c": 0.0, "theta": 0.0,
            "E": 10.0, "M": 40.0, "r_star": 5.0, "regime": "fixed", "crawl_rate": 0.02,
            "E_band_upper": None, "G": 20.0
        },
        "initial_state": {
            "Y_pot": 100.0,
            "P_NT": 1.0,
            "pi_e": 0.03,
            "R": 50.0,
            "B": 60.0
        }
    }
    
    # Mutar dinámicamente SCENARIO_PRESETS_V3 en memoria para soportar calibración de escenario "custom"
    SCENARIO_PRESETS_V3["custom"] = custom_preset
    
    local_scenarios = dict(SCENARIO_PRESETS_V3)

    # Centrar todo el contenido usando columnas laterales de margen estilo "War Room"
    col_l, col_main, col_r = st.columns([1, 4, 1])
    with col_main:
        # ── ESTILOS CSS PREMIUM ─────────────────────────────────────────────────────
        st.markdown("""
        <style>
          /* Forzar estilo oscuro base (Strategy Mode) */
          [data-testid="stAppViewContainer"] {
              background-color: #0b0f19 !important;
          }
          [data-testid="stHeader"] {
              background-color: rgba(11, 15, 25, 0.8) !important;
          }
          html, body, [class*="css"] {
              color: #f8fafc !important;
              font-family: 'Space Grotesk', 'Inter', sans-serif !important;
          }
          .block-container {
              padding-top: 4rem !important;
              padding-bottom: 4rem !important;
              max-width: 1200px !important;
          }
          .onboarding-title {
              font-size: 2.5rem;
              font-weight: 800;
              color: #f59e0b;
              text-align: center;
              margin-bottom: 2px;
              text-transform: uppercase;
              letter-spacing: 1.5px;
              margin-top: 60px; /* Margen superior amplio para despegarlo del borde */
          }
          .onboarding-subtitle {
              font-size: 1.1rem;
              font-style: italic;
              color: #94a3b8;
              text-align: center;
              margin-bottom: 30px;
          }
          .scenario-card-active {
              border: 2px solid #f59e0b !important;
              box-shadow: 0 0 15px rgba(245, 158, 11, 0.35) !important;
              background: #1e293b !important;
              border-radius: 4px !important;
          }
          .scenario-card {
              background: #111827;
              border: 1px solid #334155;
              border-radius: 4px;
              padding: 20px;
              margin-bottom: 15px;
              transition: all 0.3s ease;
              height: 100%;
              cursor: pointer;
          }
          .scenario-card:hover {
              border-color: #f59e0b;
              box-shadow: 0 4px 12px rgba(245, 158, 11, 0.15);
          }
          .difficulty-badge {
              display: inline-block;
              padding: 3px 10px;
              border-radius: 4px;
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
              border: 1px solid #334155;
              border-radius: 4px;
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
              border-radius: 4px;
              padding: 10px;
              border: 1px solid #475569;
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
          
          [data-testid="stExpander"] {
              background-color: #111827 !important;
              border: 1px solid #334155 !important;
              border-radius: 4px !important;
              box-shadow: none !important;
          }
          
          /* Estilos War Room para los botones */
          .stButton button, div[data-testid="stFormSubmitButton"] button {
              border-radius: 4px !important;
              border: 2px solid #f59e0b !important;
              font-weight: 700 !important;
              text-transform: uppercase !important;
              letter-spacing: 0.5px !important;
              transition: all 0.2s ease-in-out !important;
          }
          /* Estilo para los botones primarios (War Room) */
          .stButton button[kind="primary"] {
              background-color: #f59e0b !important;
              color: #0b0f19 !important;
              border: 2px solid #f59e0b !important;
              font-weight: 800 !important;
          }
          .stButton button[kind="primary"]:hover {
              background-color: #d97706 !important;
              border-color: #d97706 !important;
              box-shadow: 0 0 15px rgba(245, 158, 11, 0.6) !important;
          }
          /* Estilo para los botones secundarios */
          .stButton button[kind="secondary"] {
              background-color: #1e293b !important;
              color: #cbd5e1 !important;
              border: 2px solid #475569 !important;
          }
          .stButton button[kind="secondary"]:hover {
              background-color: #334155 !important;
              color: #f8fafc !important;
              border-color: #f59e0b !important;
              box-shadow: 0 0 10px rgba(245, 158, 11, 0.3) !important;
          }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("<div class='onboarding-title'>🏛️ The Economic War Room</div>", unsafe_allow_html=True)
        st.markdown("<div class='onboarding-subtitle'>\"Bienvenido, Ministro de Economía. El país lo espera. Las decisiones son suyas.\"</div>", unsafe_allow_html=True)

        # Inicializar estado de onboarding en st.session_state
        if "ob_scenario" not in st.session_state:
            st.session_state["ob_scenario"] = "tiger_asia"
        if "ob_difficulty" not in st.session_state:
            st.session_state["ob_difficulty"] = "easy"
        if "custom_structural_params" not in st.session_state:
            st.session_state["custom_structural_params"] = {}

        # ── SELECCIÓN DE ESCENARIO ─────────────────────────────────
        st.subheader("📁 Seleccione su Escenario de Gobierno")
        
        # Grid 2x2 para escenarios
        col1, col2 = st.columns(2)
        scenarios = list(local_scenarios.items())
        
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
                
                # Botón para seleccionar
                if st.button(f"Seleccionar {sc_def['name']}", key=f"select_sc_{sc_id}", use_container_width=True, type="primary" if st.session_state["ob_scenario"] == sc_id else "secondary"):
                    st.session_state["ob_scenario"] = sc_id
                    # Reiniciar custom structural params al cambiar escenario
                    st.session_state["custom_structural_params"] = {}
                    st.rerun()

        # ── CONFIGURACIÓN DE PARÁMETROS PERSONALIZADOS (MÓDULO DE ESCENARIO PERSONALIZADO) ──
        if st.session_state["ob_scenario"] == "custom":
            st.divider()
            with st.expander("⚙️ Ajustes Avanzados de Parámetros", expanded=True):
                st.info("Ajuste los parámetros estructurales clave para la calibración del escenario personalizado.")
                customs = st.session_state.get("custom_structural_params", {})
                
                # Cargar valores por defecto
                c1_val = customs.get("c1", 0.75)
                t_val = customs.get("t", 0.20)
                m1_val = customs.get("m1", 0.15)
                b_val = customs.get("b", 2.0)
                h_val = customs.get("h", 2.0)
                k_val = customs.get("k", 0.50)
                
                c1 = st.number_input("Propensión marginal a consumir (c1)", min_value=0.1, max_value=0.99, value=float(c1_val), step=0.01)
                t_c = st.number_input("Tasa impositiva (t_c)", min_value=0.0, max_value=0.9, value=float(t_val), step=0.01)
                m1 = st.number_input("Propensión a importar (m1)", min_value=0.01, max_value=0.9, value=float(m1_val), step=0.01)
                b = st.number_input("Sensibilidad de la inversión (b)", min_value=0.1, max_value=50.0, value=float(b_val), step=0.1)
                h = st.number_input("Sensibilidad monetaria (h)", min_value=0.1, max_value=50.0, value=float(h_val), step=0.1)
                k = st.number_input("Sensibilidad del ingreso a la demanda de dinero (k)", min_value=0.1, max_value=10.0, value=float(k_val), step=0.05)
                
                # Guardar en st.session_state
                customs["c1"] = c1
                customs["t"] = t_c
                customs["t_c"] = t_c
                customs["m1"] = m1
                customs["b"] = b
                customs["h"] = h
                customs["k"] = k
                
                st.session_state["custom_structural_params"] = customs

        # ── SECTOR DE CONFIGURACIÓN Y DOSSIER ────────────────────────────────
        st.divider()
        
        col_setup1, col_setup2 = st.columns([3, 2])
        
        # Dossier del escenario seleccionado
        sel_id = st.session_state["ob_scenario"]
        sel_def = local_scenarios[sel_id]
        init_st = sel_def["initial_state"]
        
        with col_setup2:
            st.subheader("⚙️ Configuración del Gabinete")
            
            # Selector de dificultad
            difficulty_opt = st.radio(
                "Nivel de Dificultad",
                options=["easy", "hard"],
                format_func=lambda x: "🟢 Guiado (Visualización de parámetros + sliders)" if x == "easy" else "🔴 Experto Macroeconómico (Niebla de guerra, parámetros ocultos)",
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
        
        with col_setup1:
            st.subheader("🏛️ Dossier del País")
            st.markdown(f"**Escenario:** {sel_def['name']} ({sel_def['difficulty']})")
            st.markdown(f"<p style='font-size: 0.9rem; color: #94a3b8; line-height: 1.5; margin-bottom: 20px;'>{sel_def['description']}</p>", unsafe_allow_html=True)
            
        # Grid visual del Dossier inicial en un contenedor de ancho completo debajo para evitar superposición
        st.write("")
        with st.container():
            st.markdown("<p style='font-size: 1rem; font-weight: 700; color: #f8fafc; margin-bottom: 8px;'>📊 Métricas Iniciales del País — Estado Inicial (t=0)</p>", unsafe_allow_html=True)
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

        # ── FINE-TUNING AVANZADO DE PARÁMETROS STRUCTURALES (MANDO FÁCIL) ────────────────────────────
        if st.session_state["ob_difficulty"] == "easy" and st.session_state["ob_scenario"] != "custom":
            with st.expander("🛠️ Fine-tuning avanzado de parámetros estructurales (Solo modo Fácil)"):
                st.info("💡 En dificultad Fácil, usted puede ajustar el punto de partida de los parámetros estructurales de la economía antes de iniciar su mandato.")
                
                base_structural = dict(sel_def["structural"])
                customs = st.session_state.get("custom_structural_params", {})
                
                col_ft1, col_ft2 = st.columns(2)
                
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

        # ── VISUALIZADOR DE RESUMEN DE PARÁMETROS SELECCIONADOS ──
        st.divider()
        st.subheader("📊 Resumen de Parámetros del Mandato")
        
        # Cargar los parámetros que se usarán en base al escenario y overrides
        base_structural = dict(sel_def["structural"])
        customs = st.session_state.get("custom_structural_params", {})
        
        summary_params = []
        param_labels = {
            "c1": "Propensión Marginal al Consumo (c1)",
            "t": "Tasa Impositiva Consumo/Ingreso (t_c / t)",
            "m1": "Propensión Marginal a Importar (m1)",
            "b": "Sensibilidad de la Inversión (b)",
            "h": "Sensibilidad Monetaria a r (h)",
            "k": "Sensibilidad Monetaria a Y (k)",
            "epsilon_x": "Elasticidad Exportaciones (epsilon_x)",
            "epsilon_m": "Elasticidad Importaciones (epsilon_m)",
            "f": "Movilidad de Capitales (f)",
            "beta_PT": "Pass-through Cambiario (beta_PT)"
        }
        
        for k, label in param_labels.items():
            # Si hay valor personalizado (de custom escenario o fine tuning fácil), usarlo, sino el base del preset
            val = customs.get(k, base_structural.get(k, 0.0))
            summary_params.append({"Parámetro": label, "Valor": float(val)})
            
        df_summary = pd.DataFrame(summary_params)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

        # ── BOTÓN DE INICIO DE GOBIERNO ──────────────────────────────────────────────
        st.divider()
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        
        with col_btn2:
            if st.button("🏛️ ¡INICIAR GOBIERNO!", use_container_width=True, type="primary"):
                # Preparar overrides de parámetros estructurales
                custom_params = {}
                if st.session_state["ob_difficulty"] == "easy" or st.session_state["ob_scenario"] == "custom":
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
