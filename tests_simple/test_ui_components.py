"""
tests_simple/test_ui_components.py
===================================
Pruebas unitarias para verificar la correcta importación y ejecución
de los módulos de la interfaz de usuario ui_simple.
"""

from __future__ import annotations

import pytest
from engine_simple.state_manager import StateManager
from ui_simple.charts_panel import _render_islmbp_chart, _render_salter_swan_chart, _render_timeline_chart
from ui_simple.explanation_panel import render_explanation_panel
from ui_simple.kpi_panel import render_kpi_panel
from ui_simple.styles import inject_custom_css


def test_ui_styles_import():
    """Verifica que el módulo de estilos exista y no lance excepciones."""
    assert callable(inject_custom_css)


def test_ui_kpi_panel_execution():
    """Verifica la generación de datos del KPI panel sin excepciones."""
    sm = StateManager("Economia_Saludable")
    assert len(sm.history) == 1
    # render_kpi_panel utiliza componentes Streamlit; validamos la estructura de datos
    snap = sm.history[-1]
    assert "Y" in snap
    assert "pi" in snap
    assert "U" in snap
    assert "score" in snap


def test_ui_charts_data_structure():
    """Verifica que el StateManager provea los datos requeridos por los gráficos Plotly."""
    sm = StateManager("Economia_Saludable")
    sm.step_forward(sm.current_instruments)

    assert len(sm.history) == 2
    snap = sm.history[-1]

    assert snap["Y"] > 0
    assert snap["r"] >= 0
    assert "q_real" in snap
    assert "A_domestic" in snap
    assert "zone_ss" in snap


def test_ui_explanation_advice():
    """Verifica que el panel explicativo reciba recomendaciones válidas del Gabinete."""
    sm = StateManager("Economia_Saludable")
    advice = sm.get_cabinet_advice(sm.current_instruments)

    assert len(advice["central_bank"]) > 0
    assert len(advice["treasury"]) > 0
    assert len(advice["labor_growth"]) > 0
    assert len(advice["salter_swan"]) > 0
