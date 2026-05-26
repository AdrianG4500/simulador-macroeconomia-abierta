"""
ui/difficulty_mode.py
======================
Gestión de visibilidad de parámetros e implementación de "Niebla de Guerra" (Fase 3).

Controla la visualización de los parámetros estructurales según el nivel de dificultad:
  - Fácil: Sliders estructurales visibles para análisis y educación + Botón de Debug disponible.
  - Difícil (Niebla de Guerra): Parámetros estructurales y botón de Debug ocultos.
"""

from __future__ import annotations

import streamlit as st
from config.validation_rules_v2 import VALIDATION_RULES
from engine.game_state import GameState


def render_difficulty_parameters(state: GameState) -> dict[str, float]:
    """
    Renderiza los sliders de parámetros estructurales en la barra lateral
    aplicando las reglas de la Niebla de Guerra.

    Parameters
    ----------
    state : GameState actual

    Returns
    -------
    dict[str, float] : Parámetros modificados por los sliders (si aplica)
    """
    difficulty = state.get("difficulty", "easy")
    sp = state["structural"]
    
    # Inicializar estado de debug y visibilidad
    if "debug_active" not in st.session_state:
        st.session_state["debug_active"] = False
    
    # ── BOTÓN DE DEBUG (Solo visible en Fácil) ─────────────────────────────────
    if difficulty == "easy":
        st.sidebar.subheader("🔍 Panel de Control del Modelo")
        if st.sidebar.button("🔍 Alternar Modo Debug (Mostrar/Ocultar Estructurales)", key="btn_toggle_debug"):
            st.session_state["debug_active"] = not st.session_state["debug_active"]
            st.rerun()
            
        if st.session_state["debug_active"]:
            st.sidebar.caption("🟢 Modo Debug Activo: Parámetros del modelo editables.")
    else:
        # En difícil, forzar debug desactivado
        st.session_state["debug_active"] = False

    # ── DETERMINAR VISIBILIDAD DE LA NIEBLA DE GUERRA ───────────────────────────
    # Los parámetros son visibles si estamos en modo Fácil Y el debug está activo
    # (o si el usuario quiere inspeccionarlos de forma general).
    # La spec dice: "Modo Fácil: todos los sliders son visibles. Modo Difícil: ocultos."
    visible = (difficulty == "easy")
    
    if not visible:
        st.sidebar.markdown("""
        <div style='background-color: #1e1b4b; border-left: 4px solid #818cf8; padding: 10px; border-radius: 6px; margin: 10px 0;'>
          <div style='font-size: 0.8rem; font-weight: 700; color: #c7d2fe;'>🌁 NIEBLA DE GUERRA ACTIVA</div>
          <div style='font-size: 0.75rem; color: #a5b4fc; margin-top: 4px;'>Los parámetros estructurales del país están ocultos. Formule políticas basándose únicamente en los KPIs de salida.</div>
        </div>
        """, unsafe_allow_html=True)
        return {}

    # Si es visible (Modo Fácil), renderizar los sliders en un expander
    updates = {}
    st.sidebar.divider()
    with st.sidebar.expander("🛠️ Estructura Económica (Modo Fácil)", expanded=st.session_state["debug_active"]):
        st.caption("Ajuste los parámetros estructurales para realizar simulaciones de sensibilidad.")
        
        # Parámetros a mostrar
        structural_keys = [
            ("c1", "Propensión Marginal a Consumir"),
            ("t", "Tasa Impositiva Proporcional"),
            ("epsilon_x", "Elasticidad Exportaciones"),
            ("epsilon_m", "Elasticidad Importaciones"),
            ("m1", "Propensión Marginal a Importar"),
            ("f", "Movilidad de Capitales (f)"),
            ("beta_PT", "Pass-through en Inflación"),
            ("g_pot", "Crecimiento PIB Potencial"),
            ("pi_0", "Inflación Estructural Base"),
        ]
        
        for key, name in structural_keys:
            rule = VALIDATION_RULES.get(key, {"min": 0.0, "max": 10.0, "step": 0.05, "rationale": ""})
            
            # Valor actual
            curr_val = sp.get(key, rule["min"])
            curr_val = max(rule["min"], min(rule["max"], float(curr_val)))
            
            slider_key = f"game_sp_{key}_slider"
            
            # Slider interactivo
            new_val = st.slider(
                label=f"{name} ({key})",
                min_value=float(rule["min"]),
                max_value=float(rule["max"]),
                step=float(rule["step"]),
                value=float(curr_val),
                help=rule["rationale"],
                key=slider_key
            )
            
            if new_val != curr_val:
                updates[key] = new_val

    return updates
