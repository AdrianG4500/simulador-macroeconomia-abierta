"""
validation/test_phase4.py
==========================
Suite de verificación de la Fase 4: Gráficos avanzados, KPIs y Pantalla de Endgame.

Para ejecutar:
    python -m pytest validation/test_phase4.py -v --tb=short
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest
import plotly.graph_objects as go
import streamlit as st

# Asegurar que el directorio raíz del proyecto esté en el path
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.state_manager_v2 import SimStateManagerV2
from ui.charts_v2 import (
    plot_pib_decomposition,
    plot_economic_cycle,
    plot_reserves_thermometer,
    plot_debt_snowball,
    plot_islm_bp_dynamic,
    plot_gdp_decomposition,
    plot_sectoral_composition,
    plot_fiscal_odometer,
    plot_butterfly_trade,
    plot_exchange_intervention,
    plot_salter_swan,
    plot_trilemma_ternary,
    plot_business_cycle_clock,
    plot_reelection_radar
)
from ui.endgame_screen import calculate_normalized_metrics, plot_endgame_spider, get_custom_narrative


def test_normalized_metrics_bounds():
    """
    Verifica que la normalización de dimensiones macroeconómicas para el Spider Chart
    se mantenga estrictamente acotada en [0, 1] y sea consistente.
    """
    snap_0 = {
        "t": 0, "Y": 100.0, "r": 5.0, "E": 10.0, "M": 40.0, "NX": 0.0,
        "C": 70.0, "I_inv": 15.0, "G": 20.0, "recaudacion": 20.0, "deficit": 0.0,
        "B": 50.0, "R": 50.0, "pi": 0.03, "pi_e": 0.03, "U": 0.05,
        "gap": 0.0, "gY": 0.0, "q_real": 1.0, "A_domestic": 100.0, "P_local": 1.0,
        "zone_ss": "II", "score": 80, "mult": 1.8, "policy_applied": {},
        "events_triggered": []
    }
    
    # 1. En t=0, el sector externo (R / R_0) debe ser exactamente 1.0
    metrics_0 = calculate_normalized_metrics(snap_0, snap_0, is_final=False)
    assert len(metrics_0) == 5, "Deberían haber exactamente 5 dimensiones"
    assert metrics_0[4] == 1.0, "Reservas en t=0 deben dar 1.0"
    for val in metrics_0:
        assert 0.0 <= val <= 1.0, f"Métrica fuera de rango [0,1]: {val}"

    # 2. Simular un colapso en t=10 para verificar comportamiento límite
    snap_f = dict(snap_0)
    snap_f["t"] = 10
    snap_f["R"] = 5.0      # Caída de reservas del 90%
    snap_f["pi"] = 0.25     # Inflación descontrolada al 25%
    snap_f["deficit"] = 30.0 # Déficit fiscal gigante de 30% del PIB
    
    history = [snap_0, snap_f]
    metrics_f = calculate_normalized_metrics(snap_f, snap_0, history=history, is_final=True)
    
    # El sector externo (R / R_0) debe dar 0.1 (5 / 50)
    assert round(metrics_f[4], 2) == 0.1, "La métrica externa debería reflejar la caída de reservas"
    
    # La estabilidad de precios debería estar penalizada a 0 debido al 25% de inflación
    assert metrics_f[2] == 0.0, "Estabilidad de precios debería dar 0.0 por alta inflación"
    
    # El equilibrio fiscal también debería dar 0.0 debido al déficit del 30%
    assert metrics_f[3] == 0.0, "La métrica fiscal debería dar 0.0 por déficit excesivo"
    
    for val in metrics_f:
        assert 0.0 <= val <= 1.0, f"Métrica final fuera de rango [0,1]: {val}"


def test_spider_chart_rendering():
    """
    Verifica que la función del Spider Chart renderice y retorne la figura Plotly sin fallas.
    """
    snap_0 = {
        "t": 0, "Y": 100.0, "r": 5.0, "E": 10.0, "M": 40.0, "NX": 0.0,
        "C": 70.0, "I_inv": 15.0, "G": 20.0, "recaudacion": 20.0, "deficit": 0.0,
        "B": 50.0, "R": 50.0, "pi": 0.03, "pi_e": 0.03, "U": 0.05,
        "gap": 0.0, "gY": 0.0, "q_real": 1.0, "A_domestic": 100.0, "P_local": 1.0,
        "zone_ss": "II", "score": 80, "mult": 1.8, "policy_applied": {},
        "events_triggered": []
    }
    snap_f = dict(snap_0)
    snap_f["t"] = 10
    
    fig = plot_endgame_spider(snap_0, snap_f, [snap_0, snap_f])
    assert isinstance(fig, go.Figure), "Debe retornar una instancia de go.Figure de Plotly"
    assert len(fig.data) == 2, "La figura del Spider debe tener dos traces (Base vs Gestión)"


def test_charts_v2_compilation():
    """
    Verifica que todos los gráficos analíticos de charts_v2 se compilen con éxito
    y retornen figuras válidas con datos de prueba realistas.
    """
    snap_0 = {
        "t": 0, "Y": 100.0, "r": 5.0, "E": 10.0, "M": 40.0, "NX": 0.0,
        "C": 70.0, "I_inv": 15.0, "G": 20.0, "recaudacion": 20.0, "deficit": 0.0,
        "B": 50.0, "R": 50.0, "pi": 0.03, "pi_e": 0.03, "U": 0.05,
        "gap": 0.0, "gY": 0.0, "q_real": 1.0, "A_domestic": 100.0, "P_local": 1.0,
        "zone_ss": "II", "score": 80, "mult": 1.8, "policy_applied": {},
        "events_triggered": []
    }
    snap_1 = dict(snap_0)
    snap_1["t"] = 1
    snap_1["Y"] = 102.0
    snap_1["gY"] = 0.02
    
    history = [snap_0, snap_1]
    
    # 1. PIB componentes
    fig_pib = plot_pib_decomposition(history)
    assert isinstance(fig_pib, go.Figure)
    assert len(fig_pib.data) == 5, "Debería tener 4 barras de componentes + 1 línea potencial"

    # 2. Reloj del ciclo
    fig_ciclo = plot_economic_cycle(history)
    assert isinstance(fig_ciclo, go.Figure)
    assert fig_ciclo.layout.xaxis.autorange == "reversed", "La escala de desempleo U debe ser invertida"

    # 3. Termómetro de reservas
    fig_res = plot_reserves_thermometer(30.0, 50.0)
    assert isinstance(fig_res, go.Figure)
    assert fig_res.data[0].gauge.bar.color == "#fb8b1e", "Debe ser amarillo si R es menor al 70%"
    
    fig_res_red = plot_reserves_thermometer(10.0, 50.0)
    assert fig_res_red.data[0].gauge.bar.color == "#ff433d", "Debe ser rojo crítico si R < 30%"

    # 4. Bola de nieve de deuda
    fig_deuda = plot_debt_snowball(history)
    assert isinstance(fig_deuda, go.Figure)

    # 5. Nuevo: Descomposición del PIB V2.1
    fig_gdp = plot_gdp_decomposition(history)
    assert isinstance(fig_gdp, go.Figure)
    assert len(fig_gdp.data) == 5, "Debería tener 4 barras + 1 línea"

    # 6. Nuevo: Composición Sectorial (Enfermedad Holandesa)
    fig_sec = plot_sectoral_composition(history)
    assert isinstance(fig_sec, go.Figure)
    assert len(fig_sec.data) == 2, "Debería tener sector transable y no transable"

    # 7. Nuevo: Odómetro Fiscal (Waterfall)
    fig_fisc = plot_fiscal_odometer(snap_1)
    assert isinstance(fig_fisc, go.Figure)

    # 8. Nuevo: Balanza en mariposa (divergente horizontal)
    mgr_mock = SimStateManagerV2()
    mgr_mock.calibrate("Economia_Saludable")
    st.session_state["mgr"] = mgr_mock
    fig_bf = plot_butterfly_trade(history)
    assert isinstance(fig_bf, go.Figure)

    # 9. Nuevo: Intervención cambiaria (Línea + Barras)
    fig_interv = plot_exchange_intervention(history)
    assert isinstance(fig_interv, go.Figure)

    # 10. Nuevo: Salter-Swan (Scatter + X lines)
    fig_ss = plot_salter_swan(snap_1, mgr_mock.state["structural"])
    assert isinstance(fig_ss, go.Figure)

    # 11. Nuevo (5.2b): IS-LM-BP Estático
    fig_islm = plot_islm_bp_dynamic(snap_1, mgr_mock.state["structural"])
    assert isinstance(fig_islm, go.Figure)

    # 12. Nuevo (5.2b): Trilema Ternario
    fig_tri = plot_trilemma_ternary(snap_1)
    assert isinstance(fig_tri, go.Figure)

    # 13. Nuevo (5.2b): Deuda intertemporal
    fig_deuda_v21 = plot_debt_snowball(history, snap_1)
    assert isinstance(fig_deuda_v21, go.Figure)

    # 14. Nuevo (5.2b): Reloj del ciclo (Business Cycle Clock)
    fig_clock_v21 = plot_business_cycle_clock(history)
    assert isinstance(fig_clock_v21, go.Figure)

    # 15. Nuevo (5.2b): Radar de reelección
    fig_radar_v21 = plot_reelection_radar(history)
    assert isinstance(fig_radar_v21, go.Figure)


def test_narrative_feedback():
    """
    Verifica que el veredicto narrativo se adapte correctamente a las variables macro de fin de juego.
    """
    summary_reelected = {
        "verdict": "reelected",
        "delta_score": 100.0
    }
    
    snap_f_debt = {
        "t": 10, "Y": 100.0, "r": 10.0, "E": 10.0, "M": 40.0, "NX": 0.0,
        "C": 70.0, "I_inv": 15.0, "G": 20.0, "recaudacion": 20.0, "deficit": 0.0,
        "B": 150.0, # Deuda muy abultada
        "R": 50.0, "pi": 0.02, "pi_e": 0.03, "U": 0.05,
        "gap": 0.0, "gY": 0.0, "q_real": 1.0, "A_domestic": 100.0, "P_local": 1.0,
        "score": 80,
    }
    snap_0 = dict(snap_f_debt)
    snap_0["B"] = 50.0
    snap_0["score"] = 80
    
    # Bajo alta deuda, debe detonarse advertencia de "Bola de nieve" en la narrativa
    narrative_debt = get_custom_narrative(summary_reelected, snap_f_debt, snap_0)
    assert "Bola de Nieve" in narrative_debt or "deuda" in narrative_debt.lower()
