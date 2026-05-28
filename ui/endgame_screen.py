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


def get_custom_narrative(summary: dict, snap_f: TurnSnapshot, snap_0: TurnSnapshot) -> str:
    """
    Retorna un veredicto narrativo personalizado según el desempeño fiscal, monetario y externo.
    """
    verdict = summary["verdict"]
    delta_score = summary["delta_score"]
    colapso_trigger = summary.get("colapso_trigger")
    
    if colapso_trigger:
        reasons_list = colapso_trigger.split(" | ")
        reasons_bulleted = "\n".join([f"• {reason}" for reason in reasons_list])
        return (
            "🚨 CRAC MACROECONÓMICO Y COLAPSO DE GOBIERNO:\n"
            f"{reasons_bulleted}\n\n"
            "La insostenibilidad estructural de sus políticas condujo a un desenlace crítico. "
            "La administración ha sido removida/intervenida políticamente para evitar mayores perjuicios soberanos."
        )
        
    # Calcular ratios
    debt_service_ratio = (snap_f["r"] * snap_f["B"]) / max(snap_f["G"] + snap_f["r"] * snap_f["B"], 1e-6) * 100
    R_ratio = snap_f["R"] / max(snap_0["R"], 1e-6)
    pi_final = snap_f["pi"]
    
    narrative = ""
    if verdict == "reelected":
        if debt_service_ratio >= 30.0:
            narrative = (
                "¡El pueblo reconoció su esfuerzo y lo ha REELEGIDO con honores! Impulsó el empleo "
                "y mantuvo contenta a la ciudadanía, pero la 'Bola de Nieve' de la deuda pública "
                "está activada y le pasará una costosa factura a su propio sucesor."
            )
        elif R_ratio < 0.4:
            narrative = (
                "¡Logró la REELECCIÓN! No obstante, ha vaciado la caja de reservas del Banco Central. "
                "El país es sumamente vulnerable ante cualquier shock cambiario o salida de capitales futura."
            )
        elif pi_final > 0.08:
            narrative = (
                "¡Ha sido REELEGIDO en las urnas! El crecimiento económico amortiguó el descontento, "
                "pero la inflación latente está erosionando el poder adquisitivo de los salarios. "
                "La estabilidad social pende de un hilo."
            )
        else:
            narrative = (
                "¡VICTORIA ROTUNDA! Ha liderado un mandato ejemplar de estabilidad y crecimiento. "
                "Logró conciliar la sostenibilidad fiscal con pleno empleo y estabilidad cambiaria. "
                "Se le considera el mejor Ministro de Economía en la historia moderna del país."
            )
    else:  # removed
        if delta_score < -150:
            narrative = (
                "El electorado lo ha castigado severamente y ha REMOVIDO a su partido del gobierno. "
                "La contracción económica y las medidas erráticas pulverizaron el score general del país."
            )
        elif pi_final > 0.10:
            narrative = (
                "Fue DERROTADO en las urnas. La inflación desbocada destruyó los ingresos reales de la "
                "población, haciendo imposible que renovaran la confianza en su gabinete de ministros."
            )
        else:
            narrative = (
                "El pueblo votó por un cambio de rumbo en el poder. Aunque evitó el colapso crítico del país, "
                "la falta de reformas audaces y el estancamiento económico desgastaron su base política electoral."
            )
            
    return narrative


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


def generate_pdf_report(summary: dict, history: list[TurnSnapshot], scenario_name: str, regime: str, difficulty: str) -> bytes:
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
    
    verdict_label = {
        "reelected": "REELEGIDO CON HONORES",
        "removed": "DESTITUIDO EN ELECCIONES (NO REELEGIDO)",
        "impeached": "GOBIERNO INTERRUMPIDO (GAME OVER - COLAPSO)"
    }.get(summary["verdict"], summary["verdict"].upper())
    
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
    narrative_text = get_custom_narrative(summary, snap_f, snap_0)
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
    
    # Título con globos si es reelegido
    if summary["verdict"] == "reelected":
        st.balloons()
        verdict_badge = "<span style='background-color: #10b981; color: #111827; padding: 6px 12px; border-radius: 6px; font-weight: 800; font-size: 1rem;'>🎉 MANDATO REELEGIDO</span>"
    elif summary["verdict"] == "removed":
        verdict_badge = "<span style='background-color: #f59e0b; color: #111827; padding: 6px 12px; border-radius: 6px; font-weight: 800; font-size: 1rem;'>📉 REEMPLAZADO EN URNAS</span>"
    else:
        verdict_badge = "<span style='background-color: #ef4444; color: #f8fafc; padding: 6px 12px; border-radius: 6px; font-weight: 800; font-size: 1rem;'>🔥 GOBIERNO COLAPSADO</span>"
        
    st.markdown(f"""
    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
      <h2 style='color: #f59e0b; margin: 0; padding: 0;'>🏁 Resumen de Fin de Mandato Presidencial (Endgame)</h2>
      {verdict_badge}
    </div>
    """, unsafe_allow_html=True)
    
    col_left, col_right = st.columns([13, 10])
    
    with col_left:
        # --- VEREDICTO DE GOBIERNO ---
        box_class = "endgame-box" if summary["verdict"] == "reelected" else "game-over-box"
        verdict_text = {
            "reelected": "¡Felicidades Ministro! El pueblo ha renovado masivamente su confianza en el gabinete económico. Su capacidad técnica y política logró sortear las crisis teóricas del trilema cambiario y dejó al país en una senda virtuosa.",
            "removed": "Derrota electoral. La ciudadanía ha decidido votar por un cambio de rumbo debido a los retrocesos o al desequilibrio macroeconómico acumulado durante el semestre final de su gestión.",
            "impeached": "Destitución y juicio político. La acumulación destructiva de deudas sin sostenibilidad fiscal o la pérdida total de reservas del Banco Central forzó su caída prematura."
        }.get(summary["verdict"], "")
        
        st.markdown(f"""
        <div class='{box_class}'>
          <h3 style='margin-top: 0; color: #f8fafc; font-weight: 800;'>📊 VEREDICTO FINAL DE GOBIERNO</h3>
          <p style='color: #cbd5e1; font-size: 0.95rem; line-height: 1.5; margin-bottom: 15px;'>"{get_custom_narrative(summary, snap_f, snap_0)}"</p>
          <div style='font-size: 0.85rem; color: #94a3b8; font-style: italic;'>{verdict_text}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # --- TARJETA DE METADATOS Y EVENTOS ---
        st.markdown(f"""
        <div style='background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 18px; margin-bottom: 15px;'>
          <h4 style='margin-top:0; color: #cbd5e1; font-size: 1rem;'>📋 Estadísticas del Mandato</h4>
          <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;'>
            <div>
              <div style='font-size: 0.75rem; color: #64748b;'>ESCENARIO</div>
              <div style='font-size: 0.9rem; font-weight: 700; color: #f8fafc;'>{scenario_name}</div>
            </div>
            <div>
              <div style='font-size: 0.75rem; color: #64748b;'>DIFICULTAD</div>
              <div style='font-size: 0.9rem; font-weight: 700; color: #f8fafc;'>{difficulty.upper()}</div>
            </div>
            <div>
              <div style='font-size: 0.75rem; color: #64748b;'>RÉGIMEN FINAL</div>
              <div style='font-size: 0.9rem; font-weight: 700; color: #f8fafc;'>{regime.upper()}</div>
            </div>
            <div>
              <div style='font-size: 0.75rem; color: #64748b;'>DURACIÓN</div>
              <div style='font-size: 0.9rem; font-weight: 700; color: #f8fafc;'>{len(history)-1} Semestres</div>
            </div>
          </div>
          <hr style='border-color: #1e293b; margin: 12px 0;'>
          <div style='display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; text-align: center;'>
            <div>
              <div style='font-size: 1.5rem; font-weight: 800; color: #3b82f6;'>{summary["total_score"]}</div>
              <div style='font-size: 0.7rem; color: #94a3b8;'>SCORE ACUMULADO</div>
            </div>
            <div>
              <div style='font-size: 1.5rem; font-weight: 800; color: #10b981;'>{summary["avg_score_per_turn"]}</div>
              <div style='font-size: 0.7rem; color: #94a3b8;'>PROMEDIO GESTIÓN</div>
            </div>
            <div>
              <div style='font-size: 1.5rem; font-weight: 800; color: { "#10b981" if summary["delta_score"] >= 0 else "#ef4444" };'>
                { "+" if summary["delta_score"] >= 0 else "" }{summary["delta_score"]}
              </div>
              <div style='font-size: 0.7rem; color: #94a3b8;'>DELTA SCORE</div>
            </div>
          </div>
          <hr style='border-color: #1e293b; margin: 12px 0;'>
          <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px;'>
            <div>
              <div style='font-size: 0.75rem; color: #64748b;'>HITO MÁS ALTO</div>
              <div style='font-size: 0.85rem; font-weight: 700; color: #10b981;'>Semestre {best_idx} ({int(best_score)} pts)</div>
            </div>
            <div>
              <div style='font-size: 0.75rem; color: #64748b;'>HITO MÁS BAJO</div>
              <div style='font-size: 0.85rem; font-weight: 700; color: #ef4444;'>Semestre {worst_idx} ({int(worst_score)} pts)</div>
            </div>
          </div>
          <hr style='border-color: #1e293b; margin: 12px 0;'>
          <div style='font-size: 0.75rem; color: #64748b;'>EVENTOS DISPARADOS</div>
          <div style='font-size: 0.9rem; font-weight: 700; color: #cbd5e1; margin-top: 2px;'>
            Total: {len(unique_events)} disparados ({endogenous_count} endógenos, {exogenous_count} exógenos)
          </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_right:
        # --- SPIDER CHART ---
        st.markdown("""
        <div style='background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 18px; text-align: center;'>
          <h4 style='margin-top:0; margin-bottom: 5px; color: #cbd5e1; font-size: 1rem;'>🕷️ Spider Chart de Desempeño</h4>
          <span style='font-size: 0.75rem; color: #64748b; display: block; margin-bottom: 10px;'>Mide el área de tu gestión (verde) vs. la base original heredada (rojo)</span>
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
    col_restart, col_download = st.columns([1, 1])
    
    with col_restart:
        if st.button("🔄 Comenzar Nueva Partida (Reset)", type="primary", use_container_width=True):
            mgr.reset()
            st.rerun()
            
    with col_download:
        if FPDF_SUPPORTED:
            # Generar reporte PDF real en memoria
            pdf_data = generate_pdf_report(summary, history, scenario_name, regime, difficulty)
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
"{get_custom_narrative(summary, snap_f, snap_0)}"

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
