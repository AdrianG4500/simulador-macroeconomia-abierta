"""
main.py
=======
Punto de entrada principal para el Simulador Macroeconómico V2.0 (Fase 3).

Orquesta las tres pantallas del juego: Onboarding, Jugabilidad en curso (Dashboard),
Pantalla de Game Over y Resumen de Fin de Mandato (Endgame).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from engine.state_manager_v2 import SimStateManagerV2
from ui.onboarding import render_onboarding_panel
from ui.navigation import render_navigation
from ui.dashboard_main import render_game_dashboard
from ui.endgame_screen import render_endgame_screen


def main():
    st.set_page_config(
        page_title="Simulador Macroeconómico Abierto V2.0",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # ── ESTILOS CSS PREMUM GLOBAL ──────────────────────────────────────────────
    st.markdown("""
    <style>
      .main { background-color: #0B1120; color: #f8fafc; }
      .stTabs [data-baseweb="tab-list"] { gap: 8px; }
      .stTabs [data-baseweb="tab"] { height: 42px; white-space: nowrap; background-color: #1e293b; border-radius: 6px; padding: 6px 16px; border: 1px solid #334155; }
      .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #f59e0b; color: #0B1120; font-weight: 700; border-color: #f59e0b; }
      
      .metric-card { 
          background: #111827; 
          border: 1px solid #1e293b; 
          border-radius: 10px; 
          padding: 14px 18px; 
          margin-bottom: 12px; 
          box-shadow: 0 4px 10px rgba(0,0,0,0.4); 
          border-left: 4px solid #3b82f6;
      }
      .metric-label { font-size: 0.85rem; color: #94a3b8; margin-bottom: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;}
      .metric-value { font-size: 1.5rem; font-weight: 800; color: #f8fafc; display: flex; justify-content: space-between; align-items: center;}
      .unit { font-size: 0.85rem; color: #a1a1aa; font-weight: 600; }
      
      /* Botones y badges */
      .game-over-box {
          background: #450a0a;
          border: 2px solid #ef4444;
          border-radius: 12px;
          padding: 24px;
          margin-bottom: 20px;
          box-shadow: 0 0 25px rgba(239, 68, 68, 0.25);
      }
      .endgame-box {
          background: #022c22;
          border: 2px solid #10b981;
          border-radius: 12px;
          padding: 24px;
          margin-bottom: 20px;
          box-shadow: 0 0 25px rgba(16, 185, 129, 0.25);
      }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("📈 Simulador Macroeconómico Abierto — V2.0")
    
    # ── RECUPERAR / INSTANCIAR STATE MANAGER V2 EN SESSION STATE ───────────────
    if "mgr" not in st.session_state:
        st.session_state["mgr"] = SimStateManagerV2()
        
    mgr: SimStateManagerV2 = st.session_state["mgr"]
    
    # ── PANTALLA 1: ONBOARDING / CALIBRACIÓN ──────────────────────────────────
    if mgr.status == "init" or mgr.status == "calibrated":
        render_onboarding_panel(mgr)
        
    # ── PANTALLA 2: GAME OVER (COLAPSO MACROECONÓMICO) ────────────────────────
    elif mgr.status == "game_over":
        render_navigation()
        render_endgame_screen(mgr)

    # ── PANTALLA 3: RESUMEN FINAL / MANDATO COMPLETADO (ENDGAME) ───────────────
    elif mgr.status == "endgame":
        render_navigation()
        render_endgame_screen(mgr)

    # ── PANTALLA 4: JUGABILIDAD EN CURSO (RUNNING STATE) ──────────────────────
    elif mgr.status == "running":
        # ── MOSTRAR TOASTS DEL GABINETE PREVENTIVO (Una vez por turno) ─────────
        if "last_warn_t" not in st.session_state:
            st.session_state["last_warn_t"] = -1
            
        if mgr.t > st.session_state["last_warn_t"]:
            warnings = mgr.state.get("advisor_warnings", [])
            for w in warnings:
                st.toast(f"👤 **{w['advisor']}:** {w['message']}", icon="⚠️")
            st.session_state["last_warn_t"] = mgr.t
            
        render_game_dashboard(mgr)


if __name__ == "__main__":
    main()
