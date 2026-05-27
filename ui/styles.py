"""
ui/styles.py
============
Definición de estilos CSS inyectados para el simulador macroeconómico.
Soporta dos temas premium:
  1. Executive Mode (Estilo Bloomberg/FMI - Institucional Claro)
  2. Strategy Mode (Estilo Victoria 3/Suzerain - Geopolítico Oscuro)
"""

# Fuentes de Google Fonts a importar
FONTS_IMPORT = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;700&family=Manrope:wght@400;600;700&family=Rajdhani:wght@600;700&family=Space+Grotesk:wght@600;700&display=swap');
"""

# =============================================================================
# 1. EXECUTIVE MODE (Bloomberg / FMI)
# =============================================================================
EXECUTIVE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;700&family=Manrope:wght@400;600;700&family=Rajdhani:wght@600;700&family=Space+Grotesk:wght@600;700&display=swap');

/* Reset de fuentes globales */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #101828 !important;
}

/* Títulos y Encabezados */
h1, h2, h3, h4, h5, h6, [data-testid="stHeader"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    color: #101828 !important;
}

/* Números y KPIs */
.kpi-number {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700;
    font-size: 2.2rem;
    line-height: 1.1;
}

/* Clases de colores para KPIs */
.kpi-pib { color: #1570EF !important; }
.kpi-inflation { color: #F79009 !important; }
.kpi-crisis { color: #D92D20 !important; }
.kpi-default { color: #475467 !important; }

/* Contenedor Principal y Sidebar */
[data-testid="stAppViewContainer"] {
    background-color: #F4F6F8 !important;
}

[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #D0D5DD !important;
}

/* Tarjetas y Contenedores */
.macro-card {
    background-color: #FFFFFF !important;
    border: 1px solid #D0D5DD !important;
    border-radius: 16px !important;
    padding: 16px !important;
    margin-bottom: 16px !important;
    box-shadow: 0px 4px 6px -2px rgba(16, 24, 40, 0.03), 0px 12px 16px -4px rgba(16, 24, 40, 0.08) !important;
    transition: all 0.3s ease;
}

.macro-card:hover {
    transform: translateY(-2px);
    box-shadow: 0px 8px 12px -4px rgba(16, 24, 40, 0.05), 0px 20px 24px -4px rgba(16, 24, 40, 0.1) !important;
}

/* Moody's Rating Badge */
.rating-badge {
    background-color: #FFFFFF !important;
    border: 2px solid #1570EF !important;
    border-radius: 12px !important;
    padding: 14px !important;
    text-align: center !important;
    font-family: 'Space Grotesk', sans-serif !important;
    box-shadow: 0px 4px 8px rgba(21, 112, 239, 0.1) !important;
}

.rating-title {
    font-size: 0.8rem;
    color: #475467;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.rating-value {
    font-size: 2rem;
    font-weight: 700;
    color: #1570EF;
    font-family: 'JetBrains Mono', monospace !important;
}

/* Custom Alert / Periodico */
.alert-card {
    background-color: #F9FAFB !important;
    border: 1px solid #E4E7EC !important;
    border-left: 5px solid #F79009 !important;
    border-radius: 12px !important;
    padding: 12px 14px !important;
    margin-bottom: 10px !important;
}

.alert-card-critical {
    background-color: #FEF3F2 !important;
    border: 1px solid #FEE4E2 !important;
    border-left: 5px solid #D92D20 !important;
    border-radius: 12px !important;
    padding: 12px 14px !important;
    margin-bottom: 10px !important;
}

/* Elementos de Streamlit Overrides */
[data-testid="stExpander"] {
    background-color: #FFFFFF !important;
    border: 1px solid #D0D5DD !important;
    border-radius: 12px !important;
    box-shadow: none !important;
}

.stButton button {
    border-radius: 8px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}

/* Pestañas (Tabs) */
button[data-baseweb="tab"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    color: #475467 !important;
    background-color: #E4E7EC !important;
    border: 1px solid #D0D5DD !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 8px 16px !important;
    margin-right: 4px !important;
}

button[aria-selected="true"] {
    color: #1570EF !important;
    background-color: #FFFFFF !important;
    border-bottom: 2px solid #1570EF !important;
    border-top: 1px solid #D0D5DD !important;
    border-left: 1px solid #D0D5DD !important;
    border-right: 1px solid #D0D5DD !important;
}

/* Estilo para los inputs y Sliders */
.stSlider {
    padding-bottom: 10px !important;
}

div[data-testid="stMarkdownContainer"] p {
    color: #475467;
    font-size: 0.9rem;
}
</style>
"""

# =============================================================================
# 2. STRATEGY MODE (Victoria 3 / Suzerain)
# =============================================================================
STRATEGY_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;700&family=Manrope:wght@400;600;700&family=Rajdhani:wght@600;700&family=Space+Grotesk:wght@600;700&display=swap');

/* Reset de fuentes globales */
html, body, [class*="css"] {
    font-family: 'Manrope', sans-serif;
    color: #F8FAFC !important;
}

/* Títulos y Encabezados */
h1, h2, h3, h4, h5, h6, [data-testid="stHeader"] {
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700 !important;
    color: #F8FAFC !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Números y KPIs */
.kpi-number {
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 700;
    font-size: 2.2rem;
    line-height: 1.1;
}

/* Clases de colores para KPIs */
.kpi-pib { color: #38BDF8 !important; }
.kpi-inflation { color: #FB923C !important; }
.kpi-crisis { color: #DC2626 !important; }
.kpi-default { color: #CBD5E1 !important; }

/* Contenedor Principal y Sidebar */
[data-testid="stAppViewContainer"] {
    background-color: #151821 !important;
}

[data-testid="stSidebar"] {
    background-color: #1D2433 !important;
    border-right: 1px solid #364152 !important;
}

/* Tarjetas y Contenedores */
.macro-card {
    background-color: #1D2433 !important;
    border: 1px solid #364152 !important;
    border-radius: 18px !important;
    padding: 16px !important;
    margin-bottom: 16px !important;
    box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.3) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.macro-card:hover {
    transform: translateY(-3px);
    border-color: #38BDF8 !important;
    box-shadow: 0 0 15px rgba(56, 189, 248, 0.2) !important;
}

/* Efectos Glow */
.glow-red {
    border-color: #DC2626 !important;
    box-shadow: 0 0 20px rgba(220, 38, 38, 0.25) !important;
}

.dim-default {
    opacity: 0.65 !important;
    border-style: dashed !important;
}

/* Moody's Rating Badge */
.rating-badge {
    background-color: #1D2433 !important;
    border: 2px solid #38BDF8 !important;
    border-radius: 14px !important;
    padding: 14px !important;
    text-align: center !important;
    font-family: 'Rajdhani', sans-serif !important;
    box-shadow: 0px 0px 15px rgba(56, 189, 248, 0.15) !important;
}

.rating-title {
    font-size: 0.85rem;
    color: #CBD5E1;
    text-transform: uppercase;
    letter-spacing: 0.15em;
}

.rating-value {
    font-size: 2.2rem;
    font-weight: 700;
    color: #38BDF8;
    font-family: 'IBM Plex Mono', monospace !important;
    text-shadow: 0 0 10px rgba(56, 189, 248, 0.5) !important;
}

/* Custom Alert / Periodico */
.alert-card {
    background-color: #1E293B !important;
    border: 1px solid #334155 !important;
    border-left: 5px solid #FB923C !important;
    border-radius: 10px !important;
    padding: 12px 14px !important;
    margin-bottom: 10px !important;
}

.alert-card-critical {
    background-color: #2D1B22 !important;
    border: 1px solid #4C1D24 !important;
    border-left: 5px solid #DC2626 !important;
    border-radius: 10px !important;
    padding: 12px 14px !important;
    margin-bottom: 10px !important;
    box-shadow: 0px 0px 10px rgba(220, 38, 38, 0.1) !important;
}

/* Elementos de Streamlit Overrides */
[data-testid="stExpander"] {
    background-color: #1D2433 !important;
    border: 1px solid #364152 !important;
    border-radius: 14px !important;
    box-shadow: none !important;
}

.stButton button {
    border-radius: 10px !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    transition: all 0.2s ease !important;
}

/* Pestañas (Tabs) */
button[data-baseweb="tab"] {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    color: #CBD5E1 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.03em !important;
    background-color: #1E293B !important;
    border: 1px solid #334155 !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 8px 16px !important;
    margin-right: 4px !important;
}

button[aria-selected="true"] {
    color: #38BDF8 !important;
    background-color: #1D2433 !important;
    border-bottom: 2px solid #38BDF8 !important;
    border-top: 1px solid #364152 !important;
    border-left: 1px solid #364152 !important;
    border-right: 1px solid #364152 !important;
    text-shadow: 0 0 8px rgba(56, 189, 248, 0.4) !important;
}

/* Estilo para los inputs y Sliders */
.stSlider {
    padding-bottom: 10px !important;
}

div[data-testid="stMarkdownContainer"] p {
    color: #CBD5E1;
    font-size: 0.9rem;
}
</style>
"""
