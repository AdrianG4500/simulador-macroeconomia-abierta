"""
ui/onboarding.py
================
Pantalla de inicio / Onboarding para el Simulador Macroeconómico V2.0 (Fase V3.2).

Permite elegir escenario, dificultad y régimen inicial de forma premium e inmersiva.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import copy
import math
from config.scenarios_v2 import SCENARIO_PRESETS_V3
from config.validation_rules_v2 import VALIDATION_RULES
from engine.state_manager_v2 import SimStateManagerV2
from engine.core_v2 import solve_equilibrium_v2, compute_salter_swan
from engine.dynamics_v2 import compute_sovereign_risk, compute_output_gap


def render_onboarding_panel(mgr: SimStateManagerV2) -> None:
    """
    Renderiza la interfaz de onboarding premium en Streamlit.
    """
    # 1. Clonar profundamente SCENARIO_PRESETS_V3 para evitar fugas de memoria cruzadas
    local_scenarios = copy.deepcopy(SCENARIO_PRESETS_V3)

    # 2. Definición del Escenario Personalizado
    custom_preset = {
        "name": "⚙️ Escenario Personalizado",
        "difficulty": "Medio (Configurable)",
        "description": "Establezca manualmente todos los parámetros estructurales de la economía para simular un escenario único y a medida.",
        "bullets": [
            "Propensión marginal al consumo ajustable (c1).",
            "Flexibilidad de elasticidades y sensibilidades estructurales.",
            "Régimen cambiario y monetario a elección del Ministro."
        ],
        "structural": {
            "c0": 10.0, "c1": 0.75, "t": 0.20, "I0": 15.0, "b": 2.0, "rho_k": 0.5, "NX0": 5.0,
            "x0": 12.0, "x1": 0.10, "Y_star": 30.0, "m0": 7.0,
            "epsilon_x": 0.80, "epsilon_m": 0.70, "m1": 0.15,
            "k": 0.50, "h": 2.00, "f": 5.0,
            "alpha_PT": 0.40, "beta_PT": 0.20, "P_star": 1.0,
            "Y_pot_0": 100.0, "g_pot": 0.02,
            "U_n": 0.05, "gamma_okun": 0.50, "alpha_inf": 0.50, "pi_0": 0.0, "G_needed": 0.0,
            "lambda_h": 0.8, "psi_ci": 0.15, "psi_co": 0.02, "delta_kg": 0.05, "debt_velocity_threshold": 0.10
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
    
    # Agregar el preset personalizado al diccionario clonado localmente
    local_scenarios["custom"] = custom_preset
    
    # Inicializar estado de onboarding en st.session_state
    if "ob_scenario" not in st.session_state:
        st.session_state["ob_scenario"] = "tiger_asia"
    if "ob_difficulty" not in st.session_state:
        st.session_state["ob_difficulty"] = "easy"
    if "custom_structural_params" not in st.session_state:
        st.session_state["custom_structural_params"] = {}
        
    # Obtener el escenario actual y sus datos
    sel_id = st.session_state["ob_scenario"]
    if sel_id not in local_scenarios:
        sel_id = "tiger_asia"
        st.session_state["ob_scenario"] = "tiger_asia"
        
    sel_def = local_scenarios[sel_id]
    init_st = sel_def["initial_state"]
    
    # Sincronizar el régimen en st.session_state si cambia el escenario
    scenario_default_regime = sel_def["policy"].get("regime", "fixed")
    if "ob_regime" not in st.session_state or st.session_state.get("last_scenario") != sel_id:
        st.session_state["ob_regime"] = scenario_default_regime
        st.session_state["last_scenario"] = sel_id

    # Centrar todo el contenido usando columnas laterales de margen estilo "War Room"
    col_l, col_main, col_r = st.columns([0.2, 11.6, 0.2])
    with col_main:
        # ── ESTILOS CSS PREMIUM ─────────────────────────────────────────────────────
        st.markdown("""
        <style>
          /* Forzar estilo claro base (Bloomberg Executive Style) */
          [data-testid="stAppViewContainer"] {
              background-color: #f8fafc !important;
          }
          [data-testid="stHeader"] {
              background-color: rgba(248, 250, 252, 0.8) !important;
          }
          html, body, [class*="css"] {
              color: #0f172a !important;
              font-family: 'Space Grotesk', 'Inter', sans-serif !important;
          }
          .block-container {
              padding-top: 2rem !important;
              padding-bottom: 2rem !important;
              max-width: 1250px !important;
          }
          /* Forzar color de texto oscuro en todos los encabezados y textos */
          h1, h2, h3, h4, h5, h6, .onboarding-subtitle, .bullet-point {
              color: #0f172a !important;
          }
          .onboarding-title {
              font-size: 2.5rem;
              font-weight: 800;
              color: #d97706 !important;
              text-align: center;
              margin-bottom: 2px;
              text-transform: uppercase;
              letter-spacing: 1.5px;
              margin-top: 20px;
          }
          .onboarding-subtitle {
              font-size: 1.1rem;
              font-style: italic;
              color: #475569 !important;
              text-align: center;
              margin-bottom: 30px;
          }
          .scenario-card-active {
              border: 1px solid #f59e0b !important;
              box-shadow: 0 4px 12px rgba(245, 158, 11, 0.12) !important;
              background: #ffffff !important;
              border-radius: 8px !important;
              padding: 24px !important;
              margin-bottom: 25px;
          }
          .scenario-card-active h3, .scenario-card-active p {
              color: #0f172a !important;
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
              font-size: 0.9rem;
              color: #334155 !important;
              margin: 6px 0;
              line-height: 1.4;
          }
          
          /* Forzar textos en st.metric */
          [data-testid="stMetricValue"] {
              color: #0f172a !important;
          }
          [data-testid="stMetricLabel"] p {
              color: #475569 !important;
          }
          
          /* Sliders: etiquetas, marcas, ticks y valor actual */
          div[data-testid="stSlider"] label, 
          div[data-testid="stSlider"] span, 
          div[data-testid="stSlider"] p, 
          div[data-testid="stSlider"] div,
          [data-testid="stTickBarMin"], 
          [data-testid="stTickBarMax"], 
          [data-testid="stSliderTick"] {
              color: #0f172a !important;
          }
          
          /* Cajas de texto e inputs deshabilitados */
          div[data-testid="stTextInput"] label, 
          div[data-testid="stTextInput"] input {
              color: #0f172a !important;
              background-color: #ffffff !important;
              -webkit-text-fill-color: #0f172a !important;
          }
          
          /* Cuadros de notificaciones st.info / st.warning */
          div[data-testid="stNotification"] p, 
          div[data-testid="stNotification"] div {
              color: #0f172a !important;
          }
          
          [data-testid="stExpander"] {
              background-color: #ffffff !important;
              border: 1px solid #cbd5e1 !important;
              border-radius: 4px !important;
              box-shadow: none !important;
          }
          
          /* Estilos para los botones */
          .stButton button, div[data-testid="stFormSubmitButton"] button {
              border-radius: 4px !important;
              border: 2px solid #f59e0b !important;
              font-weight: 700 !important;
              text-transform: uppercase !important;
              letter-spacing: 0.5px !important;
              transition: all 0.2s ease-in-out !important;
          }
          .stButton button[kind="primary"] {
              background-color: #f59e0b !important;
              color: #ffffff !important;
              border: 2px solid #f59e0b !important;
              font-weight: 800 !important;
          }
          .stButton button[kind="primary"]:hover {
              background-color: #d97706 !important;
              border-color: #d97706 !important;
              box-shadow: 0 0 15px rgba(245, 158, 11, 0.4) !important;
          }
          .stButton button[kind="secondary"] {
              background-color: #ffffff !important;
              color: #334155 !important;
              border: 2px solid #cbd5e1 !important;
          }
          .stButton button[kind="secondary"]:hover {
              background-color: #f8fafc !important;
              color: #0f172a !important;
              border-color: #f59e0b !important;
              box-shadow: 0 0 10px rgba(245, 158, 11, 0.2) !important;
          }
        </style>
        """, unsafe_allow_html=True)

        # ── BLOQUE SUPERIOR (Header & Storytelling) ─────────────────────────────────
        st.title("THE ECONOMIC WAR ROOM")
        st.markdown("<div class='onboarding-subtitle'>\"Bienvenido, Ministro de Economía. El país lo espera. Las decisiones son suyas.\"</div>", unsafe_allow_html=True)

        # Mapear dificultad del escenario actual
        diff_lower = sel_def["difficulty"].lower()
        badge_style = "badge-facil"
        if "medio" in diff_lower:
            badge_style = "badge-medio"
        elif "muy" in diff_lower:
            badge_style = "badge-muy-dificil"
        elif "difícil" in diff_lower:
            badge_style = "badge-dificil"

        # Tarjeta de narrativa de crisis del escenario actual con efecto Glassmorphism
        st.markdown(f"""
        <div class='scenario-card-active'>
          <span class='difficulty-badge {badge_style}'>{sel_def['difficulty']}</span>
          <h3 style='margin: 4px 0 8px 0; color: #f59e0b; font-size: 1.35rem;'>{sel_def['name']}</h3>
          <p style='font-size: 0.95rem; color: #e2e8f0; margin-bottom: 12px; line-height: 1.5;'>{sel_def['description']}</p>
          <div style='margin-top: 10px;'>
            {"".join([f"<div class='bullet-point'>• {b}</div>" for b in sel_def['bullets']])}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── BLOQUE CENTRAL (Tablero de Control de Partida) ──────────────────────────
        st.subheader("⚙️ Configuración del Mandato")
        
        col_c1, col_c2, col_c3 = st.columns([1, 1, 1])
        
        with col_c1:
            # Columna 1: Selector interactivo de escenarios (leyendo de SCENARIO_PRESETS_V3)
            scenario_options = list(local_scenarios.keys())
            scenario_names = {k: v["name"] for k, v in local_scenarios.items()}
            try:
                curr_idx = scenario_options.index(st.session_state["ob_scenario"])
            except ValueError:
                curr_idx = 0
                
            selected_scenario_id = st.selectbox(
                "Escenario de Destino",
                options=scenario_options,
                format_func=lambda x: scenario_names.get(x, x),
                index=curr_idx,
                key="ob_scenario_select"
            )
            
            if selected_scenario_id != st.session_state["ob_scenario"]:
                st.session_state["ob_scenario"] = selected_scenario_id
                st.session_state["custom_structural_params"] = {}
                st.rerun()

        with col_c2:
            # Columna 2: Régimen Cambiario Inicial (Solo Lectura)
            regime_names = {
                "fixed": "🏛️ Tipo de Cambio Fijo (M endógena)",
                "flexible": "🌊 Tipo de Cambio Flexible (E endógena)",
                "crawling_peg": "⚙️ Crawling Peg (Deslizamiento programado)"
            }
            reg_name = regime_names.get(scenario_default_regime, scenario_default_regime)
            st.text_input("Régimen Cambiario Inicial", value=reg_name, disabled=True, key="ob_regime_display")
            st.session_state["ob_regime"] = scenario_default_regime

        with col_c3:
            # Columna 3: Nivel de Dificultad (Solo Lectura)
            st.text_input("Modo de Juego", value="🎮 Modo Único", disabled=True, key="ob_difficulty_display")
            st.session_state["ob_difficulty"] = "easy"

        # ── CONFIGURACIÓN DE PARÁMETROS PERSONALIZADOS (SCENARIO CUSTOM) ──
        if st.session_state["ob_scenario"] == "custom":
            st.divider()
            with st.expander("⚙️ Ajustes Avanzados de Parámetros", expanded=True):
                st.info("Ajuste los parámetros estructurales clave para la calibración del escenario personalizado.")
                customs = st.session_state.get("custom_structural_params", {})
                
                c1_val = customs.get("c1", 0.75)
                t_val = customs.get("t_c", 0.20)
                m1_val = customs.get("m1", 0.15)
                b_val = customs.get("b", 2.0)
                h_val = customs.get("h", 2.0)
                k_val = customs.get("k", 0.50)
                
                c1 = st.number_input("Propensión marginal a consumir (c1)", min_value=0.1, max_value=0.99, value=float(c1_val), step=0.01)
                t_c = st.number_input("Tasa impositiva al consumo/ingreso (t_c)", min_value=0.0, max_value=0.9, value=float(t_val), step=0.01)
                m1 = st.number_input("Propensión a importar (m1)", min_value=0.01, max_value=0.9, value=float(m1_val), step=0.01)
                b = st.number_input("Sensibilidad de la inversión (b)", min_value=0.1, max_value=50.0, value=float(b_val), step=0.1)
                h = st.number_input("Sensibilidad monetaria (h)", min_value=0.1, max_value=50.0, value=float(h_val), step=0.1)
                k = st.number_input("Sensibilidad del ingreso a la demanda de dinero (k)", min_value=0.1, max_value=10.0, value=float(k_val), step=0.05)
                
                customs["c1"] = c1
                customs["t_c"] = t_c
                customs["m1"] = m1
                customs["b"] = b
                customs["h"] = h
                customs["k"] = k
                
                st.session_state["custom_structural_params"] = customs

        # ── CÁLCULO DINÁMICO DEL EQUILIBRIO PREVENTIVO T0 ──
        sp = copy.deepcopy(sel_def["structural"])
        pi = copy.deepcopy(sel_def["policy"])
        init_st = copy.deepcopy(sel_def["initial_state"])
        
        # Asegurar t_c en pi
        if "t_c" not in pi:
            pi["t_c"] = sp.get("t_c", sp.get("t", 0.20))
        if "t_k" not in pi:
            pi["t_k"] = sp.get("t_k", 0.20)
            
        customs = st.session_state.get("custom_structural_params", {})
        if customs:
            for key, val in customs.items():
                if key in sp:
                    sp[key] = val
                elif key in pi:
                    pi[key] = val
                    
        # Forzar régimen seleccionado en el balance preventivo
        pi["regime"] = st.session_state["ob_regime"]
        
        # Sincronizar G total para consistencia del equilibrio preventivo
        pi["G"] = pi.get("G_c", 15.0) + pi.get("I_g", 5.0)
            
        # Extraer variables
        Y_pot_0 = float(init_st.get("Y_pot", sp.get("Y_pot_0", 100.0)))
        P_NT_0  = float(init_st.get("P_NT", 1.0))
        pi_e_0  = float(init_st.get("pi_e", 0.03))
        R_0     = float(init_st.get("R", 50.0))
        B_0     = float(init_st.get("B", 60.0))
        
        # Calcular riesgo soberano preventivo T0
        rho_0, rating_0, rp_0 = compute_sovereign_risk(
            B=B_0,
            Y_pot=Y_pot_0,
            R=R_0,
            G=pi.get("G_c", 15.0) + pi.get("I_g", 5.0),
            M=pi.get("M", 40.0),
            prev_risk_penalty=0.0,
            debt_velocity_threshold=sp.get("debt_velocity_threshold", 0.10)
        )
        
        try:
            # Calcular delta_I0 inicial ex-ante
            from engine.dynamics_v2 import compute_crowding_effect
            K_g_init = float(init_st.get("K_g", pi.get("I_g", 5.0) * 10.0))
            delta_I0_0 = compute_crowding_effect(
                K_g=K_g_init,
                Y_pot=Y_pot_0,
                B=B_0,
                psi_ci=sp.get("psi_ci", 0.0),
                psi_co=sp.get("psi_co", 0.0),
            )
            pi = dict(pi)
            pi["_delta_I0"] = delta_I0_0

            # Bucle de punto fijo ex-ante para la inercia del consumo (C_prev)
            C_prev_val = 0.0
            for _ in range(10):
                pi["_C_prev"] = C_prev_val
                eq0 = solve_equilibrium_v2(
                    sp=sp, pi=pi,
                    Y_pot=Y_pot_0, P_NT=P_NT_0,
                    E_prev=pi["E"],
                    j_curve_active=False,
                    delta_E_expected=0.0,
                    rho=rho_0,
                    prev_velocity_penalty=1.0
                )
                if abs(eq0["C"] - C_prev_val) < 1e-4:
                    break
                C_prev_val = eq0["C"]
            Y_0 = eq0["Y"]
            ss_0 = compute_salter_swan(eq0, sp, pi["G"])
        except Exception as e:
            st.error(f"⚠️ Error en la resolución del equilibrio preventivo: {str(e)}")
            Y_0 = Y_pot_0
            eq0 = {
                "Y": Y_pot_0,
                "A_domestic": Y_pot_0,
                "q_real": 1.0,
                "r": pi.get("r_star", 5.0) + rho_0 * 100.0,
            }
            ss_0 = {
                "zone": "III",
                "diagnosis": f"Falla del equilibrio preventivo: {str(e)}",
                "policy": "Revisar parámetros estructurales"
            }
            
        # Cálculos de indicadores
        gap_0 = ((Y_0 - Y_pot_0) / Y_pot_0) * 100
        pi_e_pct = pi_e_0 * 100.0
        
        r_star = pi.get("r_star", 5.0)
        r_taylor_nominal = r_star + (pi_e_pct - 3.0) * 1.5
        r_real_expected = r_taylor_nominal - pi_e_pct
        
        zone_names = {
            "I": "Zona I: Superávit + Sobreempleo",
            "II": "Zona II: Superávit + Desempleo",
            "III": "Zona III: Déficit + Desempleo",
            "IV": "Zona IV: Déficit + Sobreempleo",
        }
        ss_label = zone_names.get(ss_0["zone"], f"Zona {ss_0['zone']}")
        
        I_g = pi.get("I_g", 5.0)
        G_c = pi.get("G_c", pi.get("G", 20.0) - I_g)

        # ── BLOQUE INFERIOR (Ficha Técnica y Balance Contable T0) ───────────────────
        st.divider()
        st.markdown("<p style='font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-bottom: 12px;'>📊 Ficha Técnica y Balance Contable Inicial (Turno 0)</p>", unsafe_allow_html=True)
        
        # Grid horizontal de 2 filas x 4 columnas
        row1_cols = st.columns(4)
        
        with row1_cols[0]:
            st.metric(
                label="PIB Potencial",
                value=f"{Y_pot_0:.1f} MM",
                help="El nivel de producción de pleno empleo que la economía puede sostener a largo plazo."
            )
            
        with row1_cols[1]:
            gap_label = "Sobrecalentamiento" if gap_0 > 0 else "Brecha Recesiva" if gap_0 < 0 else "Equilibrio"
            gap_help = (
                "Inicia en Sobrecalentamiento inflacionario (gap positivo)" 
                if gap_0 > 0.0 
                else "Inicia en Recesión/Capacidad Ociosa (gap negativo)" 
                if gap_0 < 0.0 
                else "Equilibrio macroeconómico perfecto"
            )
            st.metric(
                label="Output Gap",
                value=f"{gap_0:.2f}%",
                delta=f"{gap_0:.2f}% ({gap_label})",
                delta_color="normal",
                help=gap_help
            )
            
        with row1_cols[2]:
            st.metric(
                label="Inflación Esperada",
                value=f"{pi_e_pct:.1f}%",
                help="Expectativas de inflación iniciales de los agentes económicos."
            )
            
        with row1_cols[3]:
            st.metric(
                label="Salter-Swan",
                value=ss_label,
                help=f"Posición macroeconómica en el diagrama Salter-Swan. Diagnóstico: {ss_0['diagnosis']}"
            )
            
        st.write("")
        row2_cols = st.columns(4)
            
        with row2_cols[0]:
            st.metric(
                label="Deuda Pública (B)",
                value=f"{B_0:.1f} MM",
                help="Stock de deuda nominal pública acumulada de inicio."
            )
            
        with row2_cols[1]:
            st.metric(
                label="Reservas Netas (R)",
                value=f"{R_0:.1f} MM",
                help="Reservas internacionales líquidas netas del Banco Central de inicio."
            )
            
        with row2_cols[2]:
            r_real = eq0["r"] - pi_e_pct
            st.metric(
                label="Tasa Real Fisher",
                value=f"{r_real:.2f}%",
                help=f"Tasa de interés real esperada calculada vía Ecuación de Fisher: Tasa de Equilibrio Inicial ({eq0['r']:.2f}%) - Expectativa de Inflación ({pi_e_pct:.1f}%)."
            )
            
        with row2_cols[3]:
            st.metric(
                label="Presupuesto Inversión Pública (I_g)",
                value=f"{I_g:.1f} MM",
                help="Inversión pública inicial acumulada y asignada al presupuesto de infraestructura."
            )

        # ── MATRIZ DE INSTRUMENTOS HEREDADOS (MANDO FÁCIL) ────────────────────────────
        if st.session_state["ob_difficulty"] == "easy" and st.session_state["ob_scenario"] != "custom":
            with st.expander("🏛️ Matriz de Instrumentos Heredados (Gestión Anterior)", expanded=True):
                st.info("Los deslizadores se han posicionado automáticamente en la ubicación exacta que dejó el gobierno saliente. Modifique estas palancas fiscales y monetarias para corregir los desequilibrios o profundizar la estrategia antes de emitir su primer decreto semestral.")
                
                customs = st.session_state.get("custom_structural_params", {})
                
                col_ft1, col_ft2 = st.columns(2)
                
                # Calcular herencia recibida dinámica
                # 1. Gasto Público Corriente (G_c)
                if sel_id in ["death_spiral", "Bolivia_2024_Stagflation"]:
                    gc_init_base = 22.0
                else:
                    gc_val = pi.get("G_c")
                    if gc_val is None:
                        g_val = pi.get("G", 20.0)
                        ig_val = pi.get("I_g", 5.0)
                        if g_val is None: g_val = 20.0
                        if ig_val is None: ig_val = 5.0
                        gc_val = g_val - ig_val
                    gc_init_base = float(gc_val)
                
                # 2. Inversión Pública (I_g)
                if sel_id in ["death_spiral", "Bolivia_2024_Stagflation"]:
                    ig_init_base = 3.0
                else:
                    ig_val = pi.get("I_g")
                    if ig_val is None:
                        ig_val = 5.0
                    ig_init_base = float(ig_val)
                
                # 3. Tasa Impuesto al Consumo (t_c)
                tc_val = pi.get("t_c")
                if tc_val is None:
                    tc_val = sp.get("t_c", sp.get("t", 0.20))
                if tc_val is None:
                    tc_val = 0.20
                tc_init_base = float(tc_val)
                
                # 4. Tasa de Referencia (r_ref / r_star)
                if pi.get("regime", "fixed") in ["fixed", "crawling_peg"]:
                    r_val = pi.get("r_star")
                else:
                    r_val = pi.get("r_ref")
                if r_val is None:
                    r_val = pi.get("r_star")
                if r_val is None:
                    r_val = 5.0
                r_ref_init_base = float(r_val)
                
                # 5. Tasa Arancelaria (tau)
                tau_val = pi.get("tau")
                if tau_val is None:
                    tau_val = 0.0
                tau_init_base = float(tau_val)
                
                # 5.5. Subsidio a exportaciones (s_x)
                sx_val = pi.get("s_x")
                if sx_val is None:
                    sx_val = 0.0
                sx_init_base = float(sx_val)
                
                # 6. Ritmo de Devaluación (crawl_rate)
                crawl_val = pi.get("crawl_rate")
                if crawl_val is None:
                    crawl_val = 0.02
                crawl_rate_init_base = float(crawl_val)
                
                policy_keys = [
                    ("G_c", "Gasto Público Corriente", 0.0, 40.0, 1.0, gc_init_base, "Gasto de funcionamiento del sector público."),
                    ("I_g", "Inversión Pública", 0.0, 30.0, 1.0, ig_init_base, "Gasto en infraestructura y desarrollo productivo."),
                    ("t_c", "Tasa Impuesto al Consumo/Ingreso", 0.0, 0.50, 0.01, tc_init_base, "Alícuota impositiva proporcional activa."),
                    ("r_ref", "Tasa de Referencia de Política", 0.0, 25.0, 0.5, r_ref_init_base, "Tasa de interés de política monetaria o tasa de interés internacional."),
                    ("tau", "Tasa Arancelaria", 0.0, 0.50, 0.01, tau_init_base, "Arancel sobre las importaciones brutas."),
                    ("s_x", "Subsidio a las Exportaciones", 0.0, 0.30, 0.01, sx_init_base, "Subsidio a exportaciones brutas."),
                    ("crawl_rate", "Ritmo de Devaluación Programada", 0.0, 0.10, 0.005, crawl_rate_init_base, "Tasa de devaluación cambiaria por periodo.")
                ]
                
                for idx, (key, label, p_min, p_max, p_step, base_val, rationale) in enumerate(policy_keys):
                    target_col = col_ft1 if idx % 2 == 0 else col_ft2
                    with target_col:
                        val_init = customs.get(key, base_val)
                        val_init = max(p_min, min(p_max, float(val_init)))
                        
                        slider_key = f"ob_slider_{st.session_state['ob_scenario']}_{key}"
                        
                        val_selected = st.slider(
                            label=f"{label} ({key})",
                            min_value=float(p_min),
                            max_value=float(p_max),
                            step=float(p_step),
                            value=float(val_init),
                            help=rationale,
                            key=slider_key,
                            disabled=True
                        )
                        customs[key] = val_selected
                        if key == "r_ref":
                            customs["r_star"] = val_selected  # Sincronizar r_star para coherencia
                            
                st.session_state["custom_structural_params"] = customs

        # Limpiar customs si se cambia a modo Hard
        if st.session_state["ob_difficulty"] == "hard" and st.session_state["ob_scenario"] != "custom":
            st.session_state["custom_structural_params"] = {}

        # ── VISUALIZADOR DE RESUMEN DE PARÁMETROS SELECCIONADOS ──
        st.divider()
        st.subheader("📊 Resumen de Parámetros del Mandato")
        
        base_structural = dict(sel_def["structural"])
        base_policy = dict(sel_def["policy"])
        customs = st.session_state.get("custom_structural_params", {})
        
        summary_params = []
        param_labels = {
            "G_c": "Gasto Público Corriente (G_c)",
            "I_g": "Inversión Pública (I_g)",
            "t_c": "Tasa Impositiva al Consumo/Ingreso (t_c)",
            "r_ref": "Tasa de Referencia de Política (r_ref)",
            "tau": "Tasa Arancelaria (tau)",
            "s_x": "Subsidio a las Exportaciones (s_x)",
            "crawl_rate": "Tasa de Deslizamiento Cambiario (crawl_rate)",
            "c1": "Propensión Marginal al Consumo (c1)",
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
            if k in customs:
                val = customs[k]
                summary_params.append({"Parámetro": label, "Valor": float(val)})
            elif k in base_policy:
                val = base_policy[k]
                if k == "G_c" and "G_c" not in base_policy:
                    val = base_policy.get("G", 20.0) - base_policy.get("I_g", 5.0)
                summary_params.append({"Parámetro": label, "Valor": float(val)})
            elif k in base_structural:
                val = base_structural[k]
                summary_params.append({"Parámetro": label, "Valor": float(val)})
                
        df_summary = pd.DataFrame(summary_params)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

        # ── BOTÓN DE INICIO DE GOBIERNO ──────────────────────────────────────────────
        st.divider()
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        
        with col_btn2:
            if st.button("🏛️ ¡INICIAR GOBIERNO!", use_container_width=True, type="primary"):
                selected_regime = st.session_state.get("ob_regime", "fixed")
                custom_params = {}
                custom_initial_state = None
                
                if st.session_state["ob_scenario"] == "custom":
                    custom_initial_state = custom_preset["initial_state"]
                    for key, val in custom_preset["structural"].items():
                        custom_params[key] = val
                    for key, val in custom_preset["policy"].items():
                        custom_params[key] = val
                    for key, val in st.session_state["custom_structural_params"].items():
                        custom_params[key] = val
                else:
                    custom_params = dict(st.session_state["custom_structural_params"])
                    # Asegurar la pre-población de la herencia si no se definió en custom_params (por ejemplo, en modo Hard)
                    if "G_c" not in custom_params:
                        if sel_id in ["death_spiral", "Bolivia_2024_Stagflation"]:
                            custom_params["G_c"] = 22.0
                        else:
                            val_gc = pi.get("G_c")
                            if val_gc is None:
                                val_g = pi.get("G", 20.0)
                                val_ig = pi.get("I_g", 5.0)
                                if val_g is None: val_g = 20.0
                                if val_ig is None: val_ig = 5.0
                                val_gc = val_g - val_ig
                            custom_params["G_c"] = float(val_gc) if val_gc is not None else 15.0
                    if "I_g" not in custom_params:
                        if sel_id in ["death_spiral", "Bolivia_2024_Stagflation"]:
                            custom_params["I_g"] = 3.0
                        else:
                            val_ig = pi.get("I_g")
                            custom_params["I_g"] = float(val_ig) if val_ig is not None else 5.0
                    if "t_c" not in custom_params:
                        val_tc = pi.get("t_c")
                        if val_tc is None:
                            val_tc = sp.get("t_c", sp.get("t", 0.20))
                        custom_params["t_c"] = float(val_tc) if val_tc is not None else 0.20
                    if "r_ref" not in custom_params:
                        val_rref = pi.get("r_ref")
                        if val_rref is None:
                            val_rref = pi.get("r_star")
                        if val_rref is None:
                            val_rref = 5.0
                        custom_params["r_ref"] = float(val_rref)
                    if "r_star" not in custom_params:
                        val_rstar = pi.get("r_star")
                        custom_params["r_star"] = float(val_rstar) if val_rstar is not None else 5.0
                    if "tau" not in custom_params:
                        val_tau = pi.get("tau")
                        custom_params["tau"] = float(val_tau) if val_tau is not None else 0.0
                    if "s_x" not in custom_params:
                        val_sx = pi.get("s_x")
                        custom_params["s_x"] = float(val_sx) if val_sx is not None else 0.0
                    if "crawl_rate" not in custom_params:
                        val_crawl = pi.get("crawl_rate")
                        custom_params["crawl_rate"] = float(val_crawl) if val_crawl is not None else 0.02
                    
                # Sincronizar t_c con t para asegurar compatibilidad del motor
                if "t_c" in custom_params:
                    custom_params["t"] = custom_params["t_c"]
                    
                # Sincronizar G total
                if "G_c" in custom_params and "I_g" in custom_params:
                    custom_params["G"] = custom_params["G_c"] + custom_params["I_g"]
                    
                # Forzar régimen cambiario inicial seleccionado
                custom_params["regime"] = selected_regime
                
                with st.spinner("Calibrando la economía nacional..."):
                    # 1. Calibrar
                    mgr.calibrate(
                        scenario_id=st.session_state["ob_scenario"],
                        difficulty=st.session_state["ob_difficulty"],
                        custom_params=custom_params if custom_params else None,
                        custom_initial_state=custom_initial_state
                    )
                    # 2. Iniciar simulación con el régimen seleccionado
                    mgr.start_simulation(regime=selected_regime)
                    
                st.toast("🟢 ¡Gobierno iniciado! Sus asesores preventivos están listos.", icon="🏛️")
                st.rerun()
