import streamlit as st
from engine.state_manager import SimStateManager
from ui.calibration_panel import render_calibration_panel
from ui.navigation import render_navigation
from ui.timeline_dashboard import render_timeline_tab
from ui.period_islm import render_period_islm_tab
from ui.data_table import render_data_tab
import pandas as pd
from ui.score_dashboard import render_score_gauge
import plotly.io as pio

pio.renderers.default = "notebook_connected"

def main():
    st.set_page_config(page_title="Simulador Macroeconómico Abierto", layout="wide")
    
    st.markdown("""
    <style>
      .main { background-color: #0B1120; color: #f8fafc; }
      .stTabs [data-baseweb="tab-list"] { gap: 8px; }
      .stTabs [data-baseweb="tab"] { height: 40px; white-space: nowrap; background-color: #1e293b; border-radius: 6px; padding: 6px 12px; }
      .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #f59e0b; color: #0B1120; font-weight: 600; }
      .metric-card { background: #111827; border: 1px solid #1e293b; border-radius: 10px; padding: 14px; margin-bottom: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.3); }
      .metric-label { font-size: 0.85rem; color: #94a3b8; margin-bottom: 4px; }
      .metric-value { font-size: 1.4rem; font-weight: 700; color: #f8fafc; }
      .unit { font-size: 0.75rem; color: #cbd5e1; font-weight: 400; }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("📈 Simulador Macroeconómico Abierto - FASE 2")
    
    mgr = SimStateManager()
    
    if mgr.status == "init":
        render_calibration_panel()
    else:
        render_navigation()
        if mgr.status == "calibrated":
            render_calibration_panel()
        else:
            # Running state
            st.sidebar.divider()
            st.sidebar.subheader("Puntuación Global")
            df_hist = pd.DataFrame(mgr.state["history"])
            if not df_hist.empty:
                score_accum = df_hist["score"].mean()
                st.sidebar.metric("Score Acumulado", f"{score_accum:.1f}/100")
                
            if st.sidebar.button("💾 Guardar Estado Actual"):
                st.sidebar.success("Estado guardado (simulado).")

            tab1, tab2, tab3 = st.tabs([
                "📈 Trayectoria Temporal",
                "🏛️ IS-LM por Período", 
                "📊 Datos Completos"
            ])
            
            with tab1:
                render_timeline_tab(mgr, mgr.state["regime"])
                
            with tab2:
                max_t_slider = max(1, mgr.t)
                if max_t_slider < 2:
                    st.info("ℹ️ Avanza al menos un período para analizar trayectorias.")
                    sel_t = 1
                else:
                    sel_t = st.slider("Seleccionar período para análisis IS-LM", 1, max_t_slider, 
                                     min(st.session_state.get("period_selector", max_t_slider), max_t_slider), 
                                     key="period_selector")
                
                render_period_islm_tab(mgr, mgr.state["regime"], sel_t)
                
            with tab3:
                render_data_tab(mgr)
            
if __name__ == "__main__":
    main()
