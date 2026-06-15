"""
ui/styles.py
============
Definición de estilos CSS inyectados para el simulador macroeconómico.
Rediseñado en su totalidad bajo el estándar financiero Bloomberg Terminal (Modo Claro de Alta Densidad).
Soporta dos variantes de alto contraste:
  1. Executive Mode (Estilo Bloomberg clásico - Azul #0068ff)
  2. Strategy Mode (Estilo Bloomberg alternativo - Azul Oscuro/Gris Neutro)
"""

# Fuentes de Google Fonts — inyectar UNA sola vez en el layout
FONTS_LINK_TAG = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;700&family=Manrope:wght@400;600;700&family=Rajdhani:wght@600;700&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet">
"""

# =============================================================================
# 1. EXECUTIVE MODE (Bloomberg / FMI Claro)
# =============================================================================
EXECUTIVE_CSS = """
<style>
/* Incremento controlado de fuentes para evitar desbordamientos */
p, li, label, .stMarkdown p, .stSlider label {
    font-size: 1.12rem !important; /* Incremento suave de ~2px equivalente */
    line-height: 1.5 !important;
    color: #000000 !important;
}

/* Fijar títulos limpios */
h1 { font-size: 2.3rem !important; color: #000000 !important; }
h2 { font-size: 1.8rem !important; color: #000000 !important; }
h3 { font-size: 1.4rem !important; color: #000000 !important; }

/* Evitar cortes de texto en tarjetas KPI */
[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
}
[data-testid="stMetricLabel"] p {
    font-size: 1.0rem !important;
    white-space: normal !important;
}

/* Reset de fuentes globales y colores Bloomberg */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #000000 !important;
}

/* Títulos y Encabezados */
h1, h2, h3, h4, h5, h6, [data-testid="stHeader"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    color: #000000 !important;
}

/* Números y KPIs */
.kpi-number {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700;
    font-size: 2.2rem;
    line-height: 1.1;
    color: #000000 !important;
}

/* Clases de colores para KPIs */
.kpi-pib { color: #0068ff !important; }
.kpi-inflation { color: #fb8b1e !important; }
.kpi-crisis { color: #ff433d !important; }
.kpi-default { color: #000000 !important; }

/* Contenedor Principal y Sidebar */
[data-testid="stAppViewContainer"] {
    background-color: #F8FAFC !important;
}

[data-testid="stSidebar"] {
    background-color: #E2E8F0 !important;
    border-right: 1px solid #CBD5E1 !important;
}

/* Tarjetas y Contenedores */
.macro-card {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
    padding: 16px !important;
    margin-bottom: 16px !important;
    box-shadow: 0px 1px 3px rgba(0, 0, 0, 0.05) !important;
    transition: all 0.2s ease;
}

.macro-card:hover {
    border-color: #0068ff !important;
    box-shadow: 0px 4px 12px rgba(0, 104, 255, 0.08) !important;
}

/* Moody's Rating Badge */
.rating-badge {
    background-color: #FFFFFF !important;
    border: 2px solid #0068ff !important;
    border-radius: 8px !important;
    padding: 14px !important;
    text-align: center !important;
    font-family: 'Space Grotesk', sans-serif !important;
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
    color: #0068ff;
    font-family: 'JetBrains Mono', monospace !important;
}

/* Custom Alert / Periodico */
.alert-card {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-left: 5px solid #fb8b1e !important;
    border-radius: 6px !important;
    padding: 12px 14px !important;
    margin-bottom: 10px !important;
    color: #000000 !important;
}

.alert-card div, .alert-card p {
    color: #000000 !important;
}

.alert-card-critical {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-left: 5px solid #ff433d !important;
    border-radius: 6px !important;
    padding: 12px 14px !important;
    margin-bottom: 10px !important;
    color: #000000 !important;
}

.alert-card-critical div, .alert-card-critical p {
    color: #000000 !important;
}

/* Elementos de Streamlit Overrides - Erradicación de cuadro negro */
[data-testid="stExpander"] {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}

[data-testid="stExpander"] details, [data-testid="stExpander"] summary {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}

[data-testid="stExpander"] details[open] > summary {
    background-color: #F8FAFC !important;
    color: #000000 !important;
}

.stButton button {
    background-color: #0068ff !important;
    color: #FFFFFF !important;
    border-radius: 6px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    border: none !important;
    transition: all 0.2s ease !important;
}

.stButton button:hover {
    background-color: #0052cc !important;
    box-shadow: 0px 4px 8px rgba(0, 104, 255, 0.25) !important;
}

/* Evitar cuadros negros al hacer foco o clic */
.stButton button:focus, .stButton button:active {
    background-color: #0052cc !important;
    color: #FFFFFF !important;
    outline: none !important;
    box-shadow: none !important;
}

/* Pestañas (Tabs) sin cuadros oscuros */
button[data-baseweb="tab"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    color: #475467 !important;
    background-color: #E2E8F0 !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 8px 16px !important;
    margin-right: 4px !important;
}

button[aria-selected="true"] {
    color: #0068ff !important;
    background-color: #FFFFFF !important;
    border-bottom: 2px solid #0068ff !important;
    border-top: 1px solid #CBD5E1 !important;
    border-left: 1px solid #CBD5E1 !important;
    border-right: 1px solid #CBD5E1 !important;
}

button[data-baseweb="tab"]:focus, button[data-baseweb="tab"]:active {
    background-color: #FFFFFF !important;
    color: #0068ff !important;
    outline: none !important;
}

/* Inputs, Selectors y Sliders interactivos con fondo claro */
input, select, textarea {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}

div[data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}

/* Estilo para los inputs y Sliders */
.stSlider {
    padding-bottom: 10px !important;
}

div[data-testid="stMarkdownContainer"] p {
    color: #000000 !important;
    font-size: 0.9rem;
}
</style>
"""

# =============================================================================
# 2. STRATEGY MODE (Bloomberg Alternativo Claro)
# =============================================================================
STRATEGY_CSS = """
<style>
/* Incremento controlado de fuentes para evitar desbordamientos */
p, li, label, .stMarkdown p, .stSlider label {
    font-size: 1.12rem !important; /* Incremento suave de ~2px equivalente */
    line-height: 1.5 !important;
    color: #000000 !important;
}

/* Fijar títulos limpios */
h1 { font-size: 2.3rem !important; color: #000000 !important; }
h2 { font-size: 1.8rem !important; color: #000000 !important; }
h3 { font-size: 1.4rem !important; color: #000000 !important; }

/* Evitar cortes de texto en tarjetas KPI */
[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
}
[data-testid="stMetricLabel"] p {
    font-size: 1.0rem !important;
    white-space: normal !important;
}

/* Reset de fuentes globales y colores Bloomberg */
html, body, [class*="css"] {
    font-family: 'Manrope', sans-serif;
    color: #000000 !important;
}

/* Títulos y Encabezados */
h1, h2, h3, h4, h5, h6, [data-testid="stHeader"] {
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700 !important;
    color: #000000 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Números y KPIs */
.kpi-number {
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 700;
    font-size: 2.2rem;
    line-height: 1.1;
    color: #000000 !important;
}

/* Clases de colores para KPIs */
.kpi-pib { color: #0068ff !important; }
.kpi-inflation { color: #fb8b1e !important; }
.kpi-crisis { color: #ff433d !important; }
.kpi-default { color: #000000 !important; }

/* Contenedor Principal y Sidebar */
[data-testid="stAppViewContainer"] {
    background-color: #F8FAFC !important;
}

[data-testid="stSidebar"] {
    background-color: #E2E8F0 !important;
    border-right: 1px solid #CBD5E1 !important;
}

/* Tarjetas y Contenedores */
.macro-card {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
    padding: 16px !important;
    margin-bottom: 16px !important;
    box-shadow: 0px 1px 3px rgba(0, 0, 0, 0.05) !important;
    transition: all 0.2s ease;
}

.macro-card:hover {
    border-color: #0068ff !important;
    box-shadow: 0px 4px 12px rgba(0, 104, 255, 0.08) !important;
}

/* Moody's Rating Badge */
.rating-badge {
    background-color: #FFFFFF !important;
    border: 2px solid #0068ff !important;
    border-radius: 8px !important;
    padding: 14px !important;
    text-align: center !important;
    font-family: 'Rajdhani', sans-serif !important;
}

.rating-title {
    font-size: 0.85rem;
    color: #475467;
    text-transform: uppercase;
    letter-spacing: 0.15em;
}

.rating-value {
    font-size: 2.2rem;
    font-weight: 700;
    color: #0068ff;
    font-family: 'IBM Plex Mono', monospace !important;
}

/* Custom Alert / Periodico */
.alert-card {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-left: 5px solid #fb8b1e !important;
    border-radius: 6px !important;
    padding: 12px 14px !important;
    margin-bottom: 10px !important;
    color: #000000 !important;
}

.alert-card div, .alert-card p {
    color: #000000 !important;
}

.alert-card-critical {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-left: 5px solid #ff433d !important;
    border-radius: 6px !important;
    padding: 12px 14px !important;
    margin-bottom: 10px !important;
    color: #000000 !important;
}

.alert-card-critical div, .alert-card-critical p {
    color: #000000 !important;
}

/* Elementos de Streamlit Overrides - Erradicación de cuadro negro */
[data-testid="stExpander"] {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}

[data-testid="stExpander"] details, [data-testid="stExpander"] summary {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}

[data-testid="stExpander"] details[open] > summary {
    background-color: #F8FAFC !important;
    color: #000000 !important;
}

.stButton button {
    background-color: #0068ff !important;
    color: #FFFFFF !important;
    border-radius: 6px !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    border: none !important;
    transition: all 0.2s ease !important;
}

.stButton button:hover {
    background-color: #0052cc !important;
    box-shadow: 0px 4px 8px rgba(0, 104, 255, 0.25) !important;
}

/* Evitar cuadros negros al hacer foco o clic */
.stButton button:focus, .stButton button:active {
    background-color: #0052cc !important;
    color: #FFFFFF !important;
    outline: none !important;
    box-shadow: none !important;
}

/* Pestañas (Tabs) sin cuadros oscuros */
button[data-baseweb="tab"] {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    color: #475467 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.03em !important;
    background-color: #E2E8F0 !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 8px 16px !important;
    margin-right: 4px !important;
}

button[aria-selected="true"] {
    color: #0068ff !important;
    background-color: #FFFFFF !important;
    border-bottom: 2px solid #0068ff !important;
    border-top: 1px solid #CBD5E1 !important;
    border-left: 1px solid #CBD5E1 !important;
    border-right: 1px solid #CBD5E1 !important;
}

button[data-baseweb="tab"]:focus, button[data-baseweb="tab"]:active {
    background-color: #FFFFFF !important;
    color: #0068ff !important;
    outline: none !important;
}

/* Inputs, Selectors y Sliders interactivos con fondo claro */
input, select, textarea {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}

div[data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}

/* Estilo para los inputs y Sliders */
.stSlider {
    padding-bottom: 10px !important;
}

div[data-testid="stMarkdownContainer"] p {
    color: #000000 !important;
    font-size: 0.9rem;
}
</style>
"""
