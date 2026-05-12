"""
report/generator.py - Generador de informe académico PDF con fpdf2.

Estructura del informe (máx. 8 páginas):
  Sección 1: Verificación del modelo (cálculos algebraicos paso a paso)
  Sección 2: Registro de prompts (tabla pre-formateada)
  Sección 3: Errores y correcciones (3 bloques)
  Sección 4: Análisis de política Bolivia 2024 (pre-llenado)
  Sección 5: Reflexión final (espacio en blanco para el estudiante)

Dependencia: fpdf2 (pip install fpdf2)
"""
from __future__ import annotations

import io
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF, XPos, YPos

# ── Configuración de fuentes y colores ────────────────────────────────────────
_DARK_BG   = (3,  9, 18)      # #030712
_AMBER     = (252, 211, 77)   # #fcd34d
_LIGHT_TXT = (248, 250, 252)  # #f8fafc
_GRAY_TXT  = (148, 163, 184)  # #94a3b8
_RED_LIGHT = (252, 165, 165)
_GREEN_LT  = (134, 239, 172)
_SECTION_BG = (17, 24, 39)    # #111827

_REPORT_DIR = Path(__file__).parent.parent / "reports"
_REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ── Clase PDF ─────────────────────────────────────────────────────────────────

class _MacroPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 18, 18)
        self._section_num = 0

    # ── Header ──────────────────────────────────────────────────────────────
    def header(self):
        self.set_fill_color(*_DARK_BG)
        self.rect(0, 0, 210, 12, "F")
        self.set_text_color(*_AMBER)
        self.set_font("Helvetica", "B", 9)
        self.set_y(3)
        self.cell(0, 6, "Simulador Macroeconómico Abierto - Mundell-Fleming + Salter-Swan",
                  align="C")
        self.set_y(14)

    # ── Footer ──────────────────────────────────────────────────────────────
    def footer(self):
        self.set_y(-12)
        self.set_fill_color(*_DARK_BG)
        self.rect(0, self.get_y() - 2, 210, 14, "F")
        self.set_text_color(*_GRAY_TXT)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 8,
                  f"Pág. {self.page_no()} | Ingeniería Financiera - Open Macroeconomics - {datetime.now().year}",
                  align="C")

    # ── Helpers ─────────────────────────────────────────────────────────────
    def section_title(self, num: int, title: str) -> None:
        self.set_fill_color(*_SECTION_BG)
        self.set_text_color(*_AMBER)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 9, f"Sección {num}: {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                  fill=True, border=False)
        self.ln(2)

    def subsection(self, text: str) -> None:
        self.set_text_color(*_AMBER)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*_LIGHT_TXT)
        self.set_font("Helvetica", "", 10)

    def body_text(self, text: str) -> None:
        self.set_text_color(*_LIGHT_TXT)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def key_value_row(self, label: str, value: str, highlight: bool = False) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_AMBER if highlight else _GRAY_TXT)
        self.cell(70, 6, label, border="B")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_LIGHT_TXT)
        self.cell(0, 6, str(value), border="B", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def draw_table(self, headers: list[str], rows: list[list[str]],
                   col_widths: list[float] | None = None) -> None:
        usable = 210 - 36  # A4 - márgenes
        if col_widths is None:
            col_widths = [usable / len(headers)] * len(headers)

        # Header
        self.set_fill_color(*_AMBER)
        self.set_text_color(*_DARK_BG)
        self.set_font("Helvetica", "B", 9)
        for h, w in zip(headers, col_widths):
            self.cell(w, 7, h, border=1, fill=True, align="C")
        self.ln()

        # Rows
        self.set_font("Helvetica", "", 8)
        for i, row in enumerate(rows):
            bg = _SECTION_BG if i % 2 == 0 else _DARK_BG
            self.set_fill_color(*bg)
            self.set_text_color(*_LIGHT_TXT)
            max_lines = 1
            for cell, w in zip(row, col_widths):
                lines = math.ceil(len(str(cell)) / max(1, int(w / 2.2)))
                max_lines = max(max_lines, lines)
            row_h = max(6, max_lines * 5)
            for cell, w in zip(row, col_widths):
                x0, y0 = self.get_x(), self.get_y()
                self.multi_cell(w, 5, str(cell), border=1, fill=True)
                self.set_xy(x0 + w, y0)
            self.ln(row_h)
        self.ln(2)

    def placeholder_box(self, height_mm: float, label: str = "[ Espacio para respuesta del estudiante ]") -> None:
        self.set_fill_color(*_SECTION_BG)
        self.set_draw_color(*_AMBER)
        self.set_line_width(0.3)
        x, y = self.get_x(), self.get_y()
        self.rect(x, y, 174, height_mm, "D")
        self.set_text_color(*_GRAY_TXT)
        self.set_font("Helvetica", "I", 9)
        cy = y + height_mm / 2 - 3
        self.set_xy(x, cy)
        self.cell(174, 6, label, align="C")
        self.set_xy(x, y + height_mm + 2)
        self.ln(2)

    def error_block(self, num: int) -> None:
        self.set_fill_color(*_SECTION_BG)
        self.set_text_color(*_AMBER)
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 6, f"Error #{num}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        for field in ["Error detectado:", "Causa raíz:", "Solución aplicada:"]:
            self.set_text_color(*_GRAY_TXT)
            self.set_font("Helvetica", "B", 8)
            self.cell(0, 5, field, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.placeholder_box(12, "[ Complete aquí ]")
        self.ln(2)


# ── Funciones auxiliares ──────────────────────────────────────────────────────

def export_graph_for_report(fig: Any, filename: str) -> Path | None:
    """
    Exporta una figura Plotly como PNG de alta resolución para incrustar en PDF.

    Parameters
    ----------
    fig      : go.Figure de Plotly.
    filename : Nombre base del archivo (sin extensión).

    Returns
    -------
    Path al PNG generado, o None si falla.
    """
    try:
        out_path = _REPORT_DIR / f"{filename}.png"
        fig.write_image(str(out_path), width=900, height=500, scale=2)
        return out_path
    except Exception as e:
        print(f"[export_graph_for_report] Error: {e}")
        return None


def _fmt(val: float, decimals: int = 4) -> str:
    if val != val:
        return "N/A"
    return f"{val:.{decimals}f}"


# ── Generador principal ───────────────────────────────────────────────────────

def generate_academic_pdf(
    base_params:       dict[str, float],
    current_params:    dict[str, float],
    equilibrium_base:  dict[str, float],
    equilibrium_current: dict[str, float],
    salter_zone:       dict | None = None,
    prompts_used:      list[dict]  | None = None,
    bolivia_analysis:  dict | None = None,
    fig_islm:          Any | None = None,
    fig_salter:        Any | None = None,
) -> bytes:
    """
    Genera un informe académico PDF completo con 5 secciones.

    Parameters
    ----------
    base_params          : Parámetros base del modelo.
    current_params       : Parámetros actuales del simulador.
    equilibrium_base     : Equilibrio base (eq_fixed o eq_flexible).
    equilibrium_current  : Equilibrio con parámetros actuales.
    salter_zone          : Resultado de get_zone() para el análisis Salter-Swan.
    prompts_used         : Lista de dicts con claves: paso, prompt, respuesta, modificacion.
    bolivia_analysis     : Dict con resultados del preset Bolivia_2024_Stagflation.
    fig_islm             : go.Figure IS-LM para exportar (opcional).
    fig_salter           : go.Figure Salter-Swan para exportar (opcional).

    Returns
    -------
    bytes : Contenido del PDF listo para st.download_button.
    """
    pdf = _MacroPDF()
    pdf.set_fill_color(*_DARK_BG)

    # ── Portada ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_DARK_BG)
    pdf.rect(0, 0, 210, 297, "F")

    pdf.set_y(50)
    pdf.set_text_color(*_AMBER)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 12, "INFORME DE EVALUACIÓN", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 12, "Simulador Macroeconómico Abierto", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(6)
    pdf.set_text_color(*_LIGHT_TXT)
    pdf.set_font("Helvetica", "", 13)
    pdf.cell(0, 8, "Mundell-Fleming (IS-LM-BP) + Salter-Swan", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, "Economía Abierta con Movilidad Perfecta de Capitales", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(20)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*_GRAY_TXT)
    pdf.cell(0, 7, "Ingeniería Financiera - Open Macroeconomics", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── SECCIÓN 1: Verificación del Modelo ───────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_DARK_BG)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.section_title(1, "Verificación del Modelo - Cálculos Algebraicos")

    pdf.body_text(
        "Esta sección verifica que el motor matemático reproduce exactamente los equilibrios "
        "analíticos de la Sección 3.1 del documento de referencia. Todos los cálculos se muestran "
        "paso a paso para facilitar la revisión manual."
    )

    # Parámetros base
    pdf.subsection("1.1 Parámetros Base")
    bp = base_params
    param_rows = [
        ["c0 (consumo autónomo)", _fmt(bp.get("c0", 10), 2),
         "c1 (prop. marginal a consumir)", _fmt(bp.get("c1", 0.75), 2)],
        ["I0 (inversión autónoma)", _fmt(bp.get("I0", 15), 2),
         "NX0 (exp. netas autónomas)", _fmt(bp.get("NX0", 5), 2)],
        ["G (gasto gobierno)", _fmt(bp.get("G", 20), 2),
         "T (impuestos)", _fmt(bp.get("T", 20), 2)],
        ["b (IS - sensib. inv.)", _fmt(bp.get("b", 2), 2),
         "x1 (IS - sensib. exp.)", _fmt(bp.get("x1", 1.5), 2)],
        ["k (LM - sensib. ingreso)", _fmt(bp.get("k", 0.5), 2),
         "h (LM - sensib. tasa)", _fmt(bp.get("h", 2), 2)],
        ["m1 (prop. marginal importar)", _fmt(bp.get("m1", 0.15), 2),
         "r* (tasa internacional)", _fmt(bp.get("r_star", 5), 2)],
        ["E (tipo de cambio fijo)", _fmt(bp.get("E", 10), 2),
         "M (oferta monetaria)", _fmt(bp.get("M", 40), 2)],
    ]
    pdf.draw_table(
        ["Parámetro", "Valor", "Parámetro", "Valor"],
        param_rows,
        [65, 22, 65, 22],
    )

    # Cálculo paso a paso
    pdf.subsection("1.2 Cálculo Paso a Paso")

    c0 = bp.get("c0", 10)
    c1 = bp.get("c1", 0.75)
    T  = bp.get("T", 20)
    I0 = bp.get("I0", 15)
    G  = bp.get("G", 20)
    NX0= bp.get("NX0", 5)
    b  = bp.get("b", 2.0)
    x1 = bp.get("x1", 1.5)
    k  = bp.get("k", 0.5)
    h  = bp.get("h", 2.0)
    m1 = bp.get("m1", 0.15)
    E  = bp.get("E", 10.0)
    r_star = bp.get("r_star", 5.0)
    M  = bp.get("M", 40.0)

    A    = c0 - c1*T + I0 + G + NX0
    mult = 1.0 / (1 - c1 + m1)
    Y_fixed   = mult * (A + x1*E - b*r_star)
    M_endo    = k*Y_fixed - h*r_star
    Y_flex    = (M + h*r_star) / k
    E_endo    = ((1 - c1 + m1)*Y_flex + b*r_star - A) / x1

    calc_rows = [
        ["A = c0 - c1-T + I0 + G + NX0",
         f"= {c0} - {c1}-{T} + {I0} + {G} + {NX0}",
         f"= {A:.4f}",
         "OK" if abs(A - 35) < 0.01 else "?"],
        ["mult = 1/(1 - c1 + m1)",
         f"= 1/(1 - {c1} + {m1})",
         f"= {mult:.4f}",
         "OK" if abs(mult - 2.5) < 0.01 else "?"],
        ["Y (fijo) = mult-(A + x1-E - b-r*)",
         f"= {mult:.2f}-({A:.1f} + {x1}-{E} - {b}-{r_star})",
         f"= {Y_fixed:.4f}",
         "OK" if abs(Y_fixed - 100) < 0.1 else "?"],
        ["M_endo = k-Y - h-r*",
         f"= {k}-{Y_fixed:.1f} - {h}-{r_star}",
         f"= {M_endo:.4f}",
         "OK" if abs(M_endo - 40) < 0.1 else "?"],
        ["Y (flexible) = (M + h-r*)/k",
         f"= ({M} + {h}-{r_star})/{k}",
         f"= {Y_flex:.4f}",
         "OK" if abs(Y_flex - 100) < 0.1 else "?"],
        ["E_endo = ((1-c1+m1)-Y + b-r* - A)/x1",
         f"= ({1-c1+m1:.2f}-{Y_flex:.1f} + {b}-{r_star} - {A:.1f})/{x1}",
         f"= {E_endo:.4f}",
         "OK" if abs(E_endo - 10) < 0.1 else "?"],
    ]
    pdf.draw_table(
        ["Ecuación", "Sustitución", "Resultado", "OK"],
        calc_rows,
        [62, 55, 35, 22],
    )

    # Comparación engine vs analítico
    pdf.subsection("1.3 Verificación Engine vs Analítico (tolerancia 0.01)")
    verify_rows = [
        ["Multiplicador (mult)", "2.5000", _fmt(equilibrium_base.get("mult", 0)),
         "OK" if abs(equilibrium_base.get("mult", 0) - 2.5) < 0.01 else "FAIL"],
        ["Y (TC Fijo)", "100.0000", _fmt(equilibrium_base.get("Y", 0)),
         "OK" if abs(equilibrium_base.get("Y", 0) - 100) < 0.01 else "FAIL"],
        ["M endógena", "40.0000", _fmt(equilibrium_base.get("M_endo", 0)),
         "OK" if abs(equilibrium_base.get("M_endo", 0) - 40) < 0.01 else "FAIL"],
    ]
    pdf.draw_table(["Variable", "Esperado", "Engine", "Estado"], verify_rows, [55, 35, 35, 22])

    # ── SECCIÓN 2: Registro de Prompts ────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_DARK_BG)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.section_title(2, "Registro de Prompts Utilizados con IA")

    pdf.body_text(
        "Complete la siguiente tabla con cada interacción significativa con la IA durante el "
        "desarrollo del simulador. Documente el prompt exacto, la respuesta recibida y cualquier "
        "modificación que haya tenido que hacer manualmente."
    )

    prompt_headers = ["#", "Prompt Utilizado", "Respuesta IA (resumen)", "Modificación manual"]
    prompt_widths  = [8, 58, 58, 50]

    # Si hay prompts pre-cargados, los muestra; si no, crea filas vacías
    if prompts_used:
        prompt_rows = [
            [str(i+1), p.get("prompt", ""), p.get("respuesta", ""), p.get("modificacion", "")]
            for i, p in enumerate(prompts_used)
        ]
    else:
        prompt_rows = [[str(i+1), "", "", ""] for i in range(8)]

    pdf.draw_table(prompt_headers, prompt_rows, prompt_widths)

    pdf.body_text(
        "Nota: Documente también los casos donde la IA generó código incorrecto y tuvo que "
        "verificarse manualmente contra la solución analítica (ver Sección 1)."
    )

    # ── SECCIÓN 3: Errores y Correcciones ────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_DARK_BG)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.section_title(3, "Errores Encontrados y Correcciones Aplicadas")

    pdf.body_text(
        "Documente al menos 3 errores significativos encontrados durante el desarrollo. "
        "Incluya el error exacto, su causa raíz y la solución implementada. "
        "Esto demuestra comprensión del modelo y capacidad de debugging."
    )

    for i in range(1, 4):
        pdf.error_block(i)

    # ── SECCIÓN 4: Análisis de Política Bolivia 2024 ──────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_DARK_BG)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.section_title(4, "Análisis de Política Económica - Bolivia 2024")

    pdf.body_text(
        "El preset 'Bolivia_2024_Stagflation' representa el escenario de estanflación que enfrenta "
        "Bolivia en 2024: caída de reservas internacionales, restricción de divisas, contracción "
        "de la inversión privada y presión sobre el tipo de cambio. Se analizan ambos regímenes "
        "cambiarios para evaluar las alternativas de política disponibles."
    )

    # Parámetros del shock Bolivia
    from config.parameters import CRISIS_PRESETS
    bolivia_shock = CRISIS_PRESETS.get("Bolivia_2024_Stagflation", {})
    pdf.subsection("4.1 Shocks Aplicados al Preset Bolivia 2024")
    shock_rows = [[k, _fmt(float(v), 2)] for k, v in bolivia_shock.items()]
    pdf.draw_table(["Parámetro chocado", "Valor"], shock_rows, [80, 40])

    # Resultados Bolivia
    if bolivia_analysis:
        pdf.subsection("4.2 Equilibrios Resultantes")
        bolivia_rows = []
        for regime_label, eq in bolivia_analysis.items():
            if isinstance(eq, dict):
                bolivia_rows.append([
                    regime_label,
                    _fmt(eq.get("Y", float("nan"))),
                    _fmt(eq.get("r", float("nan"))),
                    _fmt(eq.get("M_endo", eq.get("E_endo", float("nan")))),
                    _fmt(eq.get("NX", float("nan"))),
                ])
        if bolivia_rows:
            pdf.draw_table(
                ["Régimen", "Y (PIB)", "r (tasa)", "M_endo / E_endo", "NX"],
                bolivia_rows,
                [45, 28, 28, 42, 28],
            )

    # Interpretación automática (estructurada, el estudiante completa)
    pdf.subsection("4.3 Análisis de Política - Bolivia en la Clasificación Salter-Swan")
    if salter_zone:
        zone = salter_zone.get("zone", "?")
        pdf.body_text(
            f"Zona identificada: {zone} | "
            f"q_IB = {salter_zone.get('q_IB', 0):.4f} | "
            f"q_EB = {salter_zone.get('q_EB', 0):.4f}"
        )
    pdf.body_text(
        "Bajo tipo de cambio FIJO: La política fiscal expansiva es efectiva (IS se desplaza "
        "hacia la derecha), pero Bolivia pierde reservas para mantener el tipo de cambio. "
        "La política monetaria es inefectiva (M es endógena).\n\n"
        "Bajo tipo de cambio FLEXIBLE: La política monetaria sería efectiva "
        "(LM se desplaza -> depreciación ->  up NX ->  up Y), pero el costo es la depreciación "
        "cambiaria con potencial inflación importada."
    )

    pdf.subsection("4.4 Recomendación de Política (complete el estudiante)")
    pdf.placeholder_box(45, "[ Escriba su recomendación de política aquí (máx. 150 palabras) ]")

    # Gráfico IS-LM Bolivia (si se proporciona)
    if fig_islm:
        png_path = export_graph_for_report(fig_islm, "islm_bolivia")
        if png_path and png_path.exists():
            pdf.image(str(png_path), x=18, w=174)
            pdf.ln(3)

    # ── SECCIÓN 5: Reflexión Final ────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_DARK_BG)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.section_title(5, "Reflexión Final")

    pdf.body_text(
        "En máximo media página, reflexione sobre:\n"
        "  a) ¿Qué supuestos del modelo Mundell-Fleming le parecen más irreales para una "
        "economía como Bolivia?\n"
        "  b) ¿Cómo cambiarían los resultados si se relajara el supuesto de movilidad "
        "perfecta de capitales?\n"
        "  c) ¿Qué limitaciones encontró en el uso de IA para construir el simulador y "
        "cómo las superó?\n\n"
        "Importante: Esta sección debe ser escrita completamente por el estudiante. "
        "El uso de texto generado por IA sin análisis propio no se evaluará como reflexión."
    )

    pdf.placeholder_box(100, "[ Reflexión del estudiante - máx. media página ]")

    pdf.ln(4)
    pdf.set_text_color(*_GRAY_TXT)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6,
             "Nota: Este informe fue generado automáticamente como plantilla. "
             "El contenido en [ corchetes ] debe ser completado por el estudiante.",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Exportar ──────────────────────────────────────────────────────────────
    date_str  = datetime.now().strftime("%Y%m%d_%H%M")
    filename  = f"Informe_MacroAbierta_{date_str}.pdf"
    out_path  = _REPORT_DIR / filename

    pdf_bytes = pdf.output()
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)

    return bytes(pdf_bytes)
