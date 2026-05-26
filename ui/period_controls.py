"""
ui/period_controls.py
======================
Panel de control de políticas V2.0 (Fase 3).

Muestra dinámicamente los controles de política económica (G, E, M, crawl_rate)
según el régimen cambiario activo para reflejar el Trilema de la Economía Abierta.
"""

from __future__ import annotations

import streamlit as st


def render_policy_controls(regime: str, current_params: dict) -> dict[str, float]:
    """
    Renderiza los instrumentos de política controlables del turno V2.0.
    Oculta o desactiva sliders según el régimen cambiario.

    Parameters
    ----------
    regime         : Régimen activo ("fixed" | "flexible" | "crawling_peg")
    current_params : Parámetros e instrumentos del turno anterior

    Returns
    -------
    dict[str, float] : Cambios de política aplicados por el jugador.
    """
    st.sidebar.subheader("🏛️ Instrumentos de Política")

    policies: dict[str, float] = {}

    # 1. GASTO PÚBLICO (G) - Siempre Activo
    G_val = current_params.get("G", 20.0)
    G_val = max(5.0, min(60.0, float(G_val)))
    
    st.sidebar.markdown("**Gasto Público (G)** [% PIB]", help="Instrumento fiscal: ↑G desplaza la IS a la derecha. Incrementa la demanda agregada pero ensancha el déficit fiscal.")
    c1, c2 = st.sidebar.columns([3, 1])
    with c1:
        G_slider = st.slider("G_slider_hidden", 5.0, 60.0, float(G_val), step=1.0, label_visibility="collapsed", key="policy_G_slider")
    with c2:
        G_num = st.number_input("G_num_hidden", 5.0, 60.0, float(G_slider), step=1.0, label_visibility="collapsed", key="policy_G_num")
    
    if G_num != G_val:
        policies["G"] = G_num

    # 2. TIPO DE CAMBIO NOMINAL (E) - Solo activo bajo TC Fijo
    E_val = current_params.get("E", 10.0)
    E_val = max(1.0, min(30.0, float(E_val)))
    
    if regime == "fixed":
        st.sidebar.markdown("**Tipo de Cambio Nominal (E)** [Bs/USD]", help="Instrumento cambiario (TC Fijo): ↑E representa una devaluación nominal. Mejora la competitividad cambiaria real (↑q), expandiendo exportaciones netas (↑NX), pero incrementa el nivel de precios local (pass-through).")
        c1, c2 = st.sidebar.columns([3, 1])
        with c1:
            E_slider = st.slider("E_slider_hidden", 1.0, 30.0, float(E_val), step=0.1, label_visibility="collapsed", key="policy_E_slider")
        with c2:
            E_num = st.number_input("E_num_hidden", 1.0, 30.0, float(E_slider), step=0.1, label_visibility="collapsed", key="policy_E_num")
        
        if E_num != E_val:
            policies["E"] = E_num
    else:
        st.sidebar.markdown("**Tipo de Cambio Nominal (E)**", help="Endógeno: El banco central no controla el tipo de cambio bajo este régimen. Se determina por equilibrio IS-LM-BP.")
        st.sidebar.info(f"Tipo de cambio endógeno: E = {E_val:.2f}")

    # 3. OFERTA MONETARIA (M) - Solo activa bajo TC Flexible
    M_val = current_params.get("M", 40.0)
    M_val = max(10.0, min(500.0, float(M_val)))
    
    if regime == "flexible":
        st.sidebar.markdown("**Oferta Monetaria (M)** [Unid. modelo]", help="Instrumento monetario (TC Flexible): ↑M desplaza la LM a la derecha. Reduce la tasa de interés doméstica, estimulando inversión y causando depreciación cambiaria, lo que dinamiza las exportaciones netas.")
        c1, c2 = st.sidebar.columns([3, 1])
        with c1:
            M_slider = st.slider("M_slider_hidden", 10.0, 500.0, float(M_val), step=5.0, label_visibility="collapsed", key="policy_M_slider")
        with c2:
            M_num = st.number_input("M_num_hidden", 10.0, 500.0, float(M_slider), step=5.0, label_visibility="collapsed", key="policy_M_num")
        
        if M_num != M_val:
            policies["M"] = M_num
    else:
        st.sidebar.markdown("**Oferta Monetaria (M)**", help="Endógena: Bajo TC Fijo/Crawling, el banco central debe acomodar la oferta monetaria de forma pasiva para mantener la tasa de interés en el nivel de equilibrio externo (r = r_BP).")
        st.sidebar.info(f"Oferta monetaria endógena: M = {M_val:.1f}")

    # 4. TASA DE DESLIZAMIENTO (crawl_rate) - Solo activa bajo Crawling Peg
    crawl_val = current_params.get("crawl_rate", 0.02)
    crawl_val = max(0.0, min(0.10, float(crawl_val)))
    
    if regime == "crawling_peg":
        st.sidebar.markdown("**Tasa de Deslizamiento (crawl_rate)** [% por turno]", help="Instrumento de Crawling Peg: Tasa porcentual a la cual se devalúa de forma programada el tipo de cambio nominal en cada período: E_t = E_prev * (1 + crawl_rate).")
        c1, c2 = st.sidebar.columns([3, 1])
        with c1:
            crawl_slider = st.slider("crawl_slider_hidden", 0.0, 0.10, float(crawl_val), step=0.005, format="%.3f", label_visibility="collapsed", key="policy_crawl_slider")
        with c2:
            crawl_num = st.number_input("crawl_num_hidden", 0.0, 0.10, float(crawl_slider), step=0.005, format="%.3f", label_visibility="collapsed", key="policy_crawl_num")
        
        if crawl_num != crawl_val:
            policies["crawl_rate"] = crawl_num

    return policies
