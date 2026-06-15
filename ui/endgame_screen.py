"""
ui/endgame_screen.py
====================
Pantalla de fin de partida (Endgame) y Game Over para el Simulador Macroeconómico V2.0 (Fase 4).

Rinde:
  1. El Spider Chart (Radar) interactivo que compara t=0 (rojo) vs t=10 (verde) en 5 ejes normalizados.
  2. Panel de Veredicto con KPIs de desempeño (Score total, Delta, mejor/peor semestre, eventos).
  3. Comentario narrativo personalizado según la salud fiscal, cambiaria e inflacionaria.
  4. Generador de reportes en PDF (con fpdf2) o descarga en Markdown para respaldos.
"""

from __future__ import annotations

import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from engine.state_manager_v2 import SimStateManagerV2
from engine.game_state import TurnSnapshot

# Intentar importar FPDF para soportar descargas en PDF
try:
    from fpdf import FPDF
    FPDF_SUPPORTED = True
except ImportError:
    FPDF_SUPPORTED = False


def calculate_normalized_metrics(snap: TurnSnapshot, snap_0: TurnSnapshot, history: list[TurnSnapshot] = None, is_final: bool = False) -> list[float]:
    """
    Calcula los 5 ejes normalizados [0, 1] para el gráfico de radar:
    1. Crecimiento (Y)
    2. Empleo (U)
    3. Estabilidad de Precios (pi)
    4. Fiscal (deficit)
    5. Externo (R)
    """
    R_0 = max(1e-3, snap_0["R"])
    Y_0 = max(1e-3, snap_0["Y"])

    if is_final and history and len(history) > 1:
        # Para el estado final, evaluamos los valores promedio del mandato (turnos 1 a 10)
        played_snaps = history[1:]
        
        # 1. Crecimiento: mean(gY_t) / 4.0%
        mean_gY = np.mean([s.get("gY", 0.0) for s in played_snaps])
        growth = max(0.0, min(1.0, mean_gY / 0.04))
        
        # 2. Empleo: 1 - mean(U_t)
        mean_U = np.mean([s.get("U", 0.0) for s in played_snaps])
        employment = max(0.0, min(1.0, 1.0 - mean_U))
        
        # 3. Estabilidad: max(0, 1 - abs(mean(pi_t) - 3.0%) / 7.0%)
        mean_pi = np.mean([s.get("pi", 0.0) for s in played_snaps])
        stability = max(0.0, min(1.0, 1.0 - abs(mean_pi - 0.03) / 0.07))
        
        # 4. Fiscal: max(0, 1 - mean(deficit_t/Y_t) / 10.0%)
        def_ratios = [s.get("deficit", 0.0) / max(s.get("Y", 1.0), 1e-3) for s in played_snaps]
        mean_def_pct = np.mean(def_ratios)
        fiscal = max(0.0, min(1.0, 1.0 - mean_def_pct / 0.10))
        
        # 5. Externo: R_final / R_0
        external = max(0.0, min(1.0, snap["R"] / R_0))
    else:
        # Para el estado inicial (t=0), evaluamos los valores puntuales de snap
        growth = max(0.0, min(1.0, snap.get("gY", 0.0) / 0.04))
        employment = max(0.0, min(1.0, 1.0 - snap.get("U", 0.05)))
        stability = max(0.0, min(1.0, 1.0 - abs(snap.get("pi", 0.03) - 0.03) / 0.07))
        fiscal = max(0.0, min(1.0, 1.0 - (snap.get("deficit", 0.0) / Y_0) / 0.10))
        external = max(0.0, min(1.0, snap.get("R", R_0) / R_0))

    return [growth, employment, stability, fiscal, external]


def plot_endgame_spider(snap_0: TurnSnapshot, snap_f: TurnSnapshot, history: list[TurnSnapshot]) -> go.Figure:
    """
    Rinde el gráfico de radar comparando t=0 (rojo) y t=10 (verde).
    """
    categories = [
        "Crecimiento (PIB)",
        "Empleo (1-U)",
        "Estabilidad Precios (π)",
        "Equilibrio Fiscal",
        "Sector Externo (Reservas)"
    ]
    
    # Calcular métricas normalizadas
    metrics_0 = calculate_normalized_metrics(snap_0, snap_0, is_final=False)
    metrics_f = calculate_normalized_metrics(snap_f, snap_0, history=history, is_final=True)
    
    # Cerrar los polígonos repitiendo el primer elemento
    metrics_0_closed = metrics_0 + [metrics_0[0]]
    metrics_f_closed = metrics_f + [metrics_f[0]]
    categories_closed = categories + [categories[0]]
    
    fig = go.Figure()
    
    # Polígono Inicial (t=0) - Rojo
    fig.add_trace(go.Scatterpolar(
        r=metrics_0_closed,
        theta=categories_closed,
        fill="toself",
        fillcolor="rgba(239, 68, 68, 0.15)",
        line=dict(color="#ef4444", width=2, dash="dash"),
        name="Línea Base Inicial (t=0)",
        hovertemplate="Línea Base: %{r:.2f}<extra></extra>"
    ))
    
    # Polígono Final (t=10) - Verde
    fig.add_trace(go.Scatterpolar(
        r=metrics_f_closed,
        theta=categories_closed,
        fill="toself",
        fillcolor="rgba(16, 185, 129, 0.25)",
        line=dict(color="#10b981", width=3.5),
        name="Gestión Promedio (t=10)",
        hovertemplate="Tu Gestión: %{r:.2f}<extra></extra>"
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                gridcolor="#334155",
                linecolor="#334155",
                tickfont=dict(size=8, color="#94a3b8"),
            ),
            angularaxis=dict(
                gridcolor="#334155",
                tickfont=dict(size=10, color="#cbd5e1", weight="bold")
            ),
            bgcolor="rgba(0,0,0,0)"
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            y=-0.15,
            x=0.5,
            xanchor="center",
            font=dict(size=11, color="#f8fafc")
        ),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=25, b=40),
        height=320
    )
    
    return fig


def get_custom_narrative(summary: dict, snap_f: TurnSnapshot, snap_0: TurnSnapshot, scenario_id: str = "") -> str:
    """
    Retorna un veredicto narrativo personalizado según el desempeño fiscal, monetario y externo.
    """
    colapso_trigger = summary.get("colapso_trigger")
    
    if colapso_trigger:
        reasons_list = colapso_trigger.split(" | ")
        reasons_bulleted = "\n".join([f"• {reason}" for reason in reasons_list])
        return (
            "🚨 COLAPSO DE GOBERNABILIDAD Y CRAC MACROECONÓMICO:\n"
            f"{reasons_bulleted}\n\n"
            "La insostenibilidad estructural de sus políticas condujo a un desenlace crítico. "
            "La administración ha sido removida/intervenida políticamente para evitar mayores perjuicios soberanos."
        )
        
    final_score = snap_f["score"]
    
    if scenario_id == "death_spiral":
        return (
            "🗳️ Reelección Ajustada (Héroe de la Estanflación):\n"
            "¡Logro histórico! Su gestión logró lo que parecía imposible: sobrevivir a la espiral hiperinflacionaria boliviana. "
            "A pesar del desgaste electoral inherente a una terapia de choque tan profunda (concluyendo con un score de "
            f"{final_score:.1f} pts), el electorado le ha concedido un voto de confianza y la reelección para consolidar "
            "el retorno definitivo a la estabilidad institucional y el crecimiento."
        )
        
    if scenario_id == "latam_crisis":
        return (
            "🗳️ Reelección de Emergencia:\n"
            "¡Mandato revalidado! En medio de la asfixia por deuda externa y fuga de capitales de la crisis de 1982, "
            "su gestión logró reequilibrar la balanza de pagos y detener el pánico cambiario usando cepos y aranceles oportunos. "
            "Aunque el costo social fue severo (concluyendo con un score de "
            f"{final_score:.1f} pts), el país evitó el default catastrófico y la ciudadanía premia su solidez con la reelección."
        )
    
    if final_score >= 70.0:
        base_msg = (
            "🗳️ Landslide Electoral (Reelección aplastante): "
            "¡Histórico! El electorado ha premiado su brillante conducción de la economía con un apoyo abrumador en las urnas. "
            "Su enfoque centrado en el bienestar ciudadano (bajo desempleo, inflación controlada y crecimiento sólido) "
            "le otorga un mandato incuestionable para profundizar las reformas."
        )
    elif final_score >= 50.0:
        base_msg = (
            "🗳️ Reelección Ajustada: "
            "¡Victoria trabajada! Logró asegurar la reelección, aunque con un margen estrecho. "
            "La ciudadanía reconoce la estabilidad en el empleo y el control inflacionario, "
            "pero advierte tensiones latentes en el crecimiento. Su nuevo mandato requerirá tejer amplios consensos."
        )
    elif final_score >= 30.0:
        base_msg = (
            "🗳️ Desgaste Político (No reelegido): "
            "Derrota en las urnas. El severo desgaste político acumulado debido a la desaceleración y la pérdida "
            "de dinamismo en los 'problemas de la mesa de la cocina' convencieron al electorado de votar por un cambio de rumbo. "
            "Debe entregar el mando a la oposición."
        )
    else:
        base_msg = (
            "🗳️ Colapso de Gobernabilidad: "
            "Crisis política total. La desaprobación ciudadana ha alcanzado niveles críticos debido al deterioro severo "
            "del empleo y el poder adquisitivo. Protestas sociales masivas obligan a una reestructuración inmediata "
            "de la administración."
        )

    # Añadir advertencias fiscales o cambiarias personalizadas
    warnings = []
    if snap_f.get("B", 0.0) > 120.0:
        warnings.append("⚠️ Sostenibilidad Fiscal: La deuda pública elevada devela un efecto bola de nieve que amenaza la sostenibilidad fiscal de largo plazo.")
    if snap_f.get("R", 50.0) < 15.0:
        warnings.append("⚠️ Sector Externo: El bajo nivel de reservas internacionales expone al país a una alta vulnerabilidad cambiaria y riesgo de balanza de pagos.")
        
    if warnings:
        base_msg += "\n\n" + "\n".join(warnings)
        
    return base_msg


def sanitize_for_pdf(text: str) -> str:
    # Reemplazar viñeta redonda • por -
    text = text.replace("•", "-")
    # Reemplazar emojis comunes por equivalentes de texto o simplemente eliminarlos
    replacements = {
        "🚨": "[CRISIS]",
        "💥": "[PROTESTAS]",
        "🔥": "[COLAPSO]",
        "💸": "[DEFAULT]",
        "📈": "[INFLACION]",
        "💀": "[CRITICO]",
        "🏛️": "[GOBIERNO]",
        "🐯": "[TIGRE]",
        "📉": "[RECESION]",
        "🌟": "[EXITO]",
        "🏦": "[BANCO]",
        "💻": "[TECH]"
    }
    for emoji, rep in replacements.items():
        text = text.replace(emoji, rep)
    
    # Filtrar cualquier otro carácter no soportado en latin-1
    safe_chars = []
    for char in text:
        if ord(char) <= 255:
            safe_chars.append(char)
        else:
            if char in ("\u201c", "\u201d", "\u2018", "\u2019"):
                safe_chars.append('"')
            elif char == "\u2014":
                safe_chars.append("-")
            elif char == "\u2022":
                safe_chars.append("-")
            else:
                pass
    return "".join(safe_chars)


def generate_pdf_report(summary: dict, history: list[TurnSnapshot], scenario_name: str, regime: str, difficulty: str, scenario_id: str = "") -> bytes:
    """
    Genera un reporte PDF formal de la administración usando FPDF.
    """
    if not FPDF_SUPPORTED:
        return b""
        
    scenario_name_safe = sanitize_for_pdf(scenario_name)
        
    pdf = FPDF()
    pdf.add_page()
    
    # Título principal
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(11, 17, 32)
    pdf.cell(0, 10, "REPORTE FORMAL DE GESTIÓN ECONÓMICA", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "Simulador Macroeconómico Abierto V2.0", ln=True, align="C")
    pdf.ln(10)
    
    # Sección 1: Ficha del Mandato
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "1. Datos Generales de la Administración", ln=True)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(90, 6, f"Escenario de Inicio: {scenario_name_safe}", ln=False)
    pdf.cell(90, 6, f"Dificultad de Juego: {difficulty.upper()}", ln=True)
    pdf.cell(90, 6, f"Régimen Cambiario Final: {regime.upper()}", ln=False)
    pdf.cell(90, 6, f"Períodos Simulados: {len(history)-1} Semestres", ln=True)
    pdf.ln(6)
    
    # Sección 2: Desempeño
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "2. Resultados de Gestión y Veredicto", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    
    snap_f_temp = summary["t10_snapshot"]
    final_score_temp = snap_f_temp["score"]
    if summary["verdict"] == "impeached":
        verdict_label = "COLAPSO DE GOBERNABILIDAD (GAME OVER)"
    elif final_score_temp >= 70.0:
        verdict_label = "LANDSLIDE ELECTORAL (REELECCIÓN APLASTANTE)"
    elif final_score_temp >= 50.0:
        verdict_label = "REELECCIÓN AJUSTADA"
    elif final_score_temp >= 30.0:
        verdict_label = "DESGASTE POLÍTICO (NO REELEGIDO)"
    else:
        verdict_label = "COLAPSO DE GOBERNABILIDAD"
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, f"Veredicto del Mandato: {verdict_label}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(90, 6, f"Score de Desempeño Promedio: {summary['avg_score_per_turn']} / 100", ln=False)
    pdf.cell(90, 6, f"Variación de Score (Delta): {'+' if summary['delta_score'] >= 0 else ''}{summary['delta_score']} puntos", ln=True)
    pdf.ln(6)
    
    # Sección 3: Métricas de Comparación
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "3. Tabla Comparativa Macro: Línea Base vs Cierre", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    
    # Cabecera de la tabla
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(50, 8, " Variable", border=1, fill=True)
    pdf.cell(45, 8, " Estado Inicial (t=0)", border=1, fill=True, align="C")
    pdf.cell(45, 8, " Cierre Mandato (t=10)", border=1, fill=True, align="C")
    pdf.cell(50, 8, " Variación Neta", border=1, fill=True, align="C")
    pdf.ln()
    
    snap_0 = summary["t0_snapshot"]
    snap_f = summary["t10_snapshot"]
    deltas = summary["dimension_deltas"]
    
    pdf.set_font("Helvetica", "", 9)
    # Fila 1: Y
    pdf.cell(50, 7, " Producción / PIB (Y)")
    pdf.cell(45, 7, f"{snap_0['Y']:.2f} MM", align="C")
    pdf.cell(45, 7, f"{snap_f['Y']:.2f} MM", align="C")
    pdf.cell(50, 7, f"{'+' if deltas['Y'] >= 0 else ''}{deltas['Y']:.2f} MM", align="C")
    pdf.ln()
    
    # Fila 2: U
    pdf.cell(50, 7, " Desempleo (U)")
    pdf.cell(45, 7, f"{snap_0['U']*100:.2f}%", align="C")
    pdf.cell(45, 7, f"{snap_f['U']*100:.2f}%", align="C")
    pdf.cell(50, 7, f"{-deltas['U']*100:.2f}%", align="C")
    pdf.ln()
    
    # Fila 3: Inflation
    pdf.cell(50, 7, " Inflación (pi)")
    pdf.cell(45, 7, f"{snap_0['pi']*100:.2f}%", align="C")
    pdf.cell(45, 7, f"{snap_f['pi']*100:.2f}%", align="C")
    pdf.cell(50, 7, f"{-deltas['pi']*100:.2f}%", align="C")
    pdf.ln()
    
    # Fila 4: Reservas
    pdf.cell(50, 7, " Reservas Cambiarias (R)")
    pdf.cell(45, 7, f"{snap_0['R']:.2f} MM", align="C")
    pdf.cell(45, 7, f"{snap_f['R']:.2f} MM", align="C")
    pdf.cell(50, 7, f"{'+' if deltas['R'] >= 0 else ''}{deltas['R']:.2f} MM", align="C")
    pdf.ln()
    
    # Fila 5: Deficit
    def_0 = (snap_0['deficit']/max(snap_0['Y'],1e-6))*100
    def_f = (snap_f['deficit']/max(snap_f['Y'],1e-6))*100
    pdf.cell(50, 7, " Déficit Fiscal / PIB")
    pdf.cell(45, 7, f"{def_0:.2f}%", align="C")
    pdf.cell(45, 7, f"{def_f:.2f}%", align="C")
    pdf.cell(50, 7, f"{-deltas['deficit_pct']*100:.2f}%", align="C")
    pdf.ln(10)
    
    # Comentario del Gabinete Asesor
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "4. Veredicto Histórico y Análisis del Pueblo", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(80, 80, 80)
    narrative_text = get_custom_narrative(summary, snap_f, snap_0, scenario_id)
    pdf.multi_cell(0, 5, sanitize_for_pdf(narrative_text))
    
    # Firma y cierre
    pdf.ln(25)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(11, 17, 32)
    pdf.cell(0, 5, "_______________________________", ln=True, align="C")
    pdf.cell(0, 5, "Consejo Nacional de Planificación Macroeconómica", ln=True, align="C")
    
    # Output en bytes
    pdf_bytes = pdf.output(dest="S")
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode('latin1')
    return pdf_bytes


def render_endgame_screen(mgr: SimStateManagerV2) -> None:
    """
    Renderiza la pantalla completa de endgame.
    """
    state = mgr.state
    history = state["history"]
    snap_0 = history[0]
    snap_f = history[-1]
    
    # Obtener el resumen final del orquestador
    summary = mgr.get_endgame_summary()
    
    # Calcular mejor y peor turnos
    scores_played = state["scores"][1:] if len(state["scores"]) > 1 else state["scores"]
    best_idx = int(np.argmax(scores_played)) + 1
    best_score = float(np.max(scores_played))
    worst_idx = int(np.argmin(scores_played)) + 1
    worst_score = float(np.min(scores_played))
    
    # Clasificar y contar eventos
    all_events = []
    for snap in history:
        for ev in snap.get("events_triggered", []):
            all_events.append(ev)
    unique_events = list(set(all_events))
    
    endogenous_count = sum(1 for e in unique_events if e in ("social_unrest", "bank_panic", "stagflation_trap", "virtuous_circle"))
    exogenous_count = len(unique_events) - endogenous_count
    
    # Extraer metadatos
    scenario_id = state.get("scenario_id", "Economia_Saludable")
    scenario_name = scenario_id.replace("_", " ").title()
    difficulty = state.get("difficulty", "easy")
    regime = state.get("regime", "fixed")
    
    # --- RENDERIZACIÓN DE LA UI STREAMLIT ---
    from ui.styles import EXECUTIVE_CSS, STRATEGY_CSS
    theme = st.session_state.get("theme", "executive")
    if theme == "strategy":
        st.markdown(STRATEGY_CSS, unsafe_allow_html=True)
        bg_card = "#111827"
        border_card = "#1e293b"
        text_title = "#cbd5e1"
        text_label = "#64748b"
        text_value = "#f8fafc"
        hr_color = "#1e293b"
    else:
        st.markdown(EXECUTIVE_CSS, unsafe_allow_html=True)
        bg_card = "#ffffff"
        border_card = "#cbd5e1"
        text_title = "#0f172a"
        text_label = "#475569"
        text_value = "#0f172a"
        hr_color = "#e2e8f0"
        
    # Título con globos según aprobación
    final_score = snap_f["score"]
    is_impeached = (summary["verdict"] == "impeached")
    
    if is_impeached or final_score < 30.0:
        verdict_badge = "<span style='background-color: #ef4444; color: #f8fafc; padding: 6px 12px; border-radius: 6px; font-weight: 800; font-size: 1rem;'>🔥 COLAPSO DE GOBERNABILIDAD</span>"
    elif final_score >= 70.0:
        st.balloons()
        verdict_badge = "<span style='background-color: #10b981; color: #111827; padding: 6px 12px; border-radius: 6px; font-weight: 800; font-size: 1rem;'>🎉 LANDSLIDE ELECTORAL</span>"
    elif final_score >= 50.0:
        st.balloons()
        verdict_badge = "<span style='background-color: #10b981; color: #111827; padding: 6px 12px; border-radius: 6px; font-weight: 800; font-size: 1rem;'>🎉 REELECCIÓN AJUSTADA</span>"
    else:
        verdict_badge = "<span style='background-color: #f59e0b; color: #111827; padding: 6px 12px; border-radius: 6px; font-weight: 800; font-size: 1rem;'>📉 DESGASTE POLÍTICO</span>"
        
    st.markdown(f"""
    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
      <h2 style='color: #f59e0b; margin: 0; padding: 0;'>🏁 Resumen de Fin de Mandato Presidencial (Endgame)</h2>
      {verdict_badge}
    </div>
    """, unsafe_allow_html=True)
    
    col_left, col_right = st.columns([13, 10])
    
    with col_left:
        # --- VEREDICTO DE GOBIERNO ---
        if is_impeached or final_score < 30.0:
            box_class = "game-over-box"
            verdict_text = "Crisis y colapso de gobernabilidad. La pérdida del apoyo popular o la violación de los límites macroeconómicos duros provocó la caída de la administración."
        elif final_score >= 50.0:
            box_class = "endgame-box"
            verdict_text = "¡Felicidades Ministro! Ha logrado conservar el poder y consolidar una mayoría política estable basada en la aprobación ciudadana."
        else:
            box_class = "game-over-box"
            verdict_text = "Transición de poder. La ciudadanía castigó el desempeño en las urnas, forzando una entrega de mando ordenada del gobierno a la oposición."
        
        st.markdown(f"""
        <div class='{box_class}'>
          <h3 style='margin-top: 0; color: #f8fafc; font-weight: 800;'>📊 VEREDICTO FINAL DE GOBIERNO</h3>
          <p style='color: #cbd5e1; font-size: 0.95rem; line-height: 1.5; margin-bottom: 15px;'>"{get_custom_narrative(summary, snap_f, snap_0, scenario_id)}"</p>
          <div style='font-size: 0.85rem; color: #94a3b8; font-style: italic;'>{verdict_text}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # --- TARJETA DE METADATOS Y EVENTOS ---
        st.markdown(f"""
        <div style='background-color: {bg_card}; border: 1px solid {border_card}; border-radius: 8px; padding: 18px; margin-bottom: 15px;'>
          <h4 style='margin-top:0; color: {text_title}; font-size: 1rem;'>📋 Estadísticas del Mandato</h4>
          <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;'>
            <div>
              <div style='font-size: 0.75rem; color: {text_label};'>ESCENARIO</div>
              <div style='font-size: 0.9rem; font-weight: 700; color: {text_value};'>{scenario_name}</div>
            </div>
            <div>
              <div style='font-size: 0.75rem; color: {text_label};'>DIFICULTAD</div>
              <div style='font-size: 0.9rem; font-weight: 700; color: {text_value};'>{difficulty.upper()}</div>
            </div>
            <div>
              <div style='font-size: 0.75rem; color: {text_label};'>RÉGIMEN FINAL</div>
              <div style='font-size: 0.9rem; font-weight: 700; color: {text_value};'>{regime.upper()}</div>
            </div>
            <div>
              <div style='font-size: 0.75rem; color: {text_label};'>DURACIÓN</div>
              <div style='font-size: 0.9rem; font-weight: 700; color: {text_value};'>{len(history)-1} Semestres</div>
            </div>
          </div>
          <hr style='border-color: {hr_color}; margin: 12px 0;'>
          <div style='display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; text-align: center;'>
            <div>
              <div style='font-size: 1.5rem; font-weight: 800; color: #3b82f6;'>{summary["total_score"]}</div>
              <div style='font-size: 0.7rem; color: {text_label};'>SCORE ACUMULADO</div>
            </div>
            <div>
              <div style='font-size: 1.5rem; font-weight: 800; color: #10b981;'>{summary["avg_score_per_turn"]}</div>
              <div style='font-size: 0.7rem; color: {text_label};'>PROMEDIO GESTIÓN</div>
            </div>
            <div>
              <div style='font-size: 1.5rem; font-weight: 800; color: { "#10b981" if summary["delta_score"] >= 0 else "#ef4444" };'>
                { "+" if summary["delta_score"] >= 0 else "" }{summary["delta_score"]}
              </div>
              <div style='font-size: 0.7rem; color: {text_label};'>DELTA SCORE</div>
            </div>
          </div>
          <hr style='border-color: {hr_color}; margin: 12px 0;'>
          <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px;'>
            <div>
              <div style='font-size: 0.75rem; color: {text_label};'>HITO MÁS ALTO</div>
              <div style='font-size: 0.85rem; font-weight: 700; color: #10b981;'>Semestre {best_idx} ({int(best_score)} pts)</div>
            </div>
            <div>
              <div style='font-size: 0.75rem; color: {text_label};'>HITO MÁS BAJO</div>
              <div style='font-size: 0.85rem; font-weight: 700; color: #ef4444;'>Semestre {worst_idx} ({int(worst_score)} pts)</div>
            </div>
          </div>
          <hr style='border-color: {hr_color}; margin: 12px 0;'>
          <div style='font-size: 0.75rem; color: {text_label};'>EVENTOS DISPARADOS</div>
          <div style='font-size: 0.9rem; font-weight: 700; color: {text_value}; margin-top: 2px;'>
            Total: {len(unique_events)} disparados ({endogenous_count} endógenos, {exogenous_count} exógenos)
          </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_right:
        # --- SPIDER CHART ---
        st.markdown(f"""
        <div style='background-color: {bg_card}; border: 1px solid {border_card}; border-radius: 8px; padding: 18px; text-align: center;'>
          <h4 style='margin-top:0; margin-bottom: 5px; color: {text_title}; font-size: 1rem;'>🕷️ Spider Chart de Desempeño</h4>
          <span style='font-size: 0.75rem; color: {text_label}; display: block; margin-bottom: 10px;'>Mide el área de tu gestión (verde) vs. la base original heredada (rojo)</span>
        """, unsafe_allow_html=True)
        
        spider_fig = plot_endgame_spider(snap_0, snap_f, history)
        st.plotly_chart(spider_fig, use_container_width=True, config={"displayModeBar": False})
        
        st.markdown("</div>", unsafe_allow_html=True)
        
    # --- TABLA COMPARATIVA DETALLADA ---
    st.subheader("📊 Tabla Comparativa de Variables Macro (t=0 vs t=10)")
    
    deltas = summary["dimension_deltas"]
    
    # Calcular déficit fiscal porcentual
    def_pct_0 = (snap_0["deficit"] / max(snap_0["Y"], 1e-3)) * 100
    def_pct_f = (snap_f["deficit"] / max(snap_f["Y"], 1e-3)) * 100
    delta_def_pct = def_pct_f - def_pct_0
    
    compare_df = pd.DataFrame({
        "Dimensión Macroeconómica": [
            "Producción Real (Y) - MM USD",
            "Tasa de Desempleo (U) - %",
            "Tasa de Inflación (π) - %",
            "Reservas Internacionales (R) - MM USD",
            "Déficit Fiscal / PIB - %"
        ],
        "Línea Base (t=0)": [
            f"{snap_0['Y']:.2f} MM",
            f"{snap_0['U']*100:.2f}%",
            f"{snap_0['pi']*100:.2f}%",
            f"{snap_0['R']:.2f} MM",
            f"{def_pct_0:.2f}%"
        ],
        "Fin de Mandato (t=10)": [
            f"{snap_f['Y']:.2f} MM",
            f"{snap_f['U']*100:.2f}%",
            f"{snap_f['pi']*100:.2f}%",
            f"{snap_f['R']:.2f} MM",
            f"{def_pct_f:.2f}%"
        ],
        "Variación Neta (Desempeño)": [
            f"{'+' if deltas['Y'] >= 0 else ''}{deltas['Y']:.2f} MM",
            f"{-deltas['U']*100:+.2f}% (Baja U)" if deltas['U'] > 0 else f"{-deltas['U']*100:+.2f}% (Sube U)",
            f"{-deltas['pi']*100:+.2f}% (Baja π)" if deltas['pi'] > 0 else f"{-deltas['pi']*100:+.2f}% (Sube π)",
            f"{'+' if deltas['R'] >= 0 else ''}{deltas['R']:.2f} MM",
            f"{-delta_def_pct:+.2f}% (Baja déficit)" if delta_def_pct < 0 else f"{-delta_def_pct:+.2f}% (Sube déficit)"
        ]
    })
    
    st.table(compare_df)
    
    # --- CONTROLES DE REPORTE Y NUEVA PARTIDA ---
    st.divider()
    col_download, _ = st.columns([1, 1])
    with col_download:
        if FPDF_SUPPORTED:
            # Generar reporte PDF real en memoria
            pdf_data = generate_pdf_report(summary, history, scenario_name, regime, difficulty, scenario_id)
            st.download_button(
                label="📄 Descargar Reporte Formal (PDF)",
                data=bytes(pdf_data),
                file_name=f"Reporte_Gestion_{scenario_id}_{regime}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            # Fallback a reporte Markdown elegante
            md_report = f"""# REPORTE DE MANDATO MACROECONÓMICO
            
## Datos de la Gestión
- **Escenario:** {scenario_name}
- **Dificultad:** {difficulty.upper()}
- **Régimen Cambiario:** {regime.upper()}
- **Score Total:** {summary['total_score']} / 1000
- **Promedio Gestión:** {summary['avg_score_per_turn']} / 100
- **Delta Gestión:** {'+' if summary['delta_score'] >= 0 else ''}{summary['delta_score']}
 
## Veredicto de la Gestión
"{get_custom_narrative(summary, snap_f, snap_0, scenario_id)}"

## Resultados Comparativos
- PIB Final: {snap_f['Y']:.2f} MM (Línea base: {snap_0['Y']:.2f} MM)
- Desempleo Final: {snap_f['U']*100:.2f}% (Línea base: {snap_0['U']*100:.2f}%)
- Inflación Final: {snap_f['pi']*100:.2f}% (Línea base: {snap_0['pi']*100:.2f}%)
- Reservas Finales: {snap_f['R']:.2f} MM (Línea base: {snap_0['R']:.2f} MM)
- Déficit Fiscal Final: {def_pct_f:.2f}% (Línea base: {def_pct_0:.2f}%)
"""
            st.download_button(
                label="📄 Descargar Reporte de Mandato (Markdown)",
                data=md_report,
                file_name=f"Reporte_Gestion_{scenario_id}.md",
                mime="text/markdown",
                use_container_width=True
            )

    # ── AJUSTE V3.10: FORZAR TABLA DEBUG EN PANTALLA DE FIN DE JUEGO (F-29) ──────
    if state.get("status") == "game_over" or mgr.status == "game_over":
        st.divider()
        with st.expander("🔍 Ver Matriz Técnica de Auditoría Ex-Post", expanded=False):
            st.markdown("### 🔍 Inspección Técnica y Consistencia de Datos (Debug)")
            st.markdown("<p style='font-size: 0.85rem; color: #64748b; margin-top:-10px;'>Auditoría intertemporal completa del equilibrio macroeconómico.</p>", unsafe_allow_html=True)
            
            debug_rows = []
            sp = state.get("structural", {})
            
            for i, snap in enumerate(history):
                t = snap.get("t", 0)
                pol = snap.get("policy_applied", {})
                
                # 1. Políticas Exógenas (Sliders)
                G_c = pol.get("G_c", snap.get("G_c", 15.0))
                I_g = pol.get("I_g", snap.get("I_g", 5.0))
                t_c = pol.get("t_c", snap.get("t_c", 0.20))
                t_k = pol.get("t_k", snap.get("t_k", 0.20))
                M = snap.get("M", pol.get("M", 40.0))
                E = snap.get("E", pol.get("E", 10.0))
                theta = pol.get("theta", 0.10)
                tau = pol.get("tau", 0.0)
                k_c = pol.get("k_c", 0.0)
                Tr = pol.get("Tr", 0.0)
                regime = pol.get("regime", snap.get("regime", "fixed"))
                
                # 2. Parámetros del Motor
                k_m = snap.get("mult", 1.5)
                rho = snap.get("rho", 0.0)
                velocity_penalty = snap.get("velocity_penalty", 1.0)
                f_eff = max(sp.get("f", 10.0) * (1.0 - k_c), 1e-4)
                
                x0 = sp.get("x0", 0.0)
                x1 = sp.get("x1", 0.0)
                Y_star = sp.get("Y_star", 0.0)
                m0 = sp.get("m0", 0.0)
                use_disaggregated = (x0 != 0.0 or m0 != 0.0 or x1 != 0.0 or Y_star != 0.0)
                ml_ok = (sp.get("epsilon_x", 0.5) + sp.get("epsilon_m", 0.5)) > 1.0
                j_curve_active = snap.get("j_curve_active", False)
                if use_disaggregated:
                    if j_curve_active:
                        eps_x_eff = 0.10
                        eps_m_eff = 0.10
                    elif ml_ok:
                        eps_x_eff = sp.get("epsilon_x", 0.5)
                        eps_m_eff = sp.get("epsilon_m", 0.5)
                    else:
                        eps_x_eff = -(sp.get("epsilon_m", 0.5) - sp.get("epsilon_x", 0.5))
                        eps_m_eff = sp.get("epsilon_m", 0.5)
                else:
                    if j_curve_active:
                        eps_eff = 0.10
                    elif ml_ok:
                        eps_eff = sp.get("epsilon_x", 0.5)
                    else:
                        eps_eff = -(sp.get("epsilon_m", 0.5) - sp.get("epsilon_x", 0.5))
                    eps_x_eff = eps_eff
                    eps_m_eff = sp.get("epsilon_m", 0.5)
                    
                G_total = G_c + I_g
                if use_disaggregated:
                    NX0_eff = x0 + x1 * Y_star - m0
                else:
                    NX0_eff = sp.get("NX0", 0.0)
                rho_k = sp.get("rho_k", 0.0)
                A_auto = sp.get("c0", 50.0) + sp.get("c1", 0.6) * Tr + sp.get("I0", 15.0) - rho_k * t_k + G_total + NX0_eff
                
                # 3. Resultados
                Y = snap.get("Y", 100.0)
                gap = snap.get("gap", 0.0)
                Y_pot = Y / (1.0 + gap) if abs(gap + 1.0) > 1e-5 else 100.0
                U = snap.get("U", 0.05)
                pi = snap.get("pi", 0.03)
                
                if i == 0:
                    pi_core = pi
                else:
                    prev_snap = history[i - 1]
                    E_prev = prev_snap.get("E", 10.0)
                    E_curr = snap.get("E", 10.0)
                    devaluation_rate = (E_curr - E_prev) / max(E_prev, 1e-9)
                    beta_PT = sp.get("beta_PT", 0.4)
                    pi_core = max(-0.015, pi - beta_PT * devaluation_rate)
                    
                R = snap.get("R", 50.0)
                B = snap.get("B", 0.0)
                NX = snap.get("NX", 0.0)
                
                CF = snap.get("capital_flows_eq", 0.0)
                
                s_x = pol.get("s_x", snap.get("s_x", 0.0))
                gY = snap.get("gY", 0.0)
                r_rate = snap.get("r", 5.0)
                P_local = snap.get("P_local", 4.60)
                score = snap.get("score", 90.0)
                events = snap.get("events_triggered", [])
                events_str = ", ".join(events) if events else "--"
                
                # Ratios
                B_Y = B / Y if Y > 0 else 0.0
                nom_GDP = Y * P_local
                R_nomGDP = R / nom_GDP if nom_GDP > 0 else 0.0

                debug_rows.append({
                    "t": f"T{t}",
                    "Regimen": regime.upper(),
                    "G_c": round(G_c, 2),
                    "I_g": round(I_g, 2),
                    "t_c": f"{t_c*100:.1f}%",
                    "t_k": f"{t_k*100:.1f}%",
                    "Tr": round(Tr, 2),
                    "M": round(M, 2) if regime == "flexible" else f"{round(M, 2)} (Endógena)",
                    "E": round(E, 2),
                    "theta": f"{theta*100:.1f}%",
                    "tau": f"{tau*100:.1f}%",
                    "s_x": f"{s_x*100:.1f}%",
                    "k_c": f"{k_c*100:.1f}%",
                    "Y": round(Y, 2),
                    "Y_pot": round(Y_pot, 2),
                    "Gap(%)": f"{gap*100:.2f}%",
                    "U(%)": f"{U*100:.2f}%",
                    "pi(%)": f"{pi*100:.2f}%",
                    "gY(%)": f"{gY*100:.2f}%",
                    "r": round(r_rate, 2),
                    "B": round(B, 2),
                    "R": round(R, 2),
                    "NX": round(NX, 2),
                    "P_local": round(P_local, 4),
                    "B/Y": round(B_Y, 3),
                    "R/nomGDP": round(R_nomGDP, 4),
                    "Score": round(score, 2),
                    "Eventos": events_str
                })
                
            df_debug = pd.DataFrame(debug_rows)
            st.dataframe(df_debug, use_container_width=True, hide_index=True)

