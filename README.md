# Simulador Macroeconómico Abierto

**Mundell-Fleming (IS-LM-BP) + Salter-Swan** — Ingeniería Financiera · Open Macroeconomics

Motor académico verificado contra soluciones analíticas de la Sección 3.1.
Interfaz Streamlit con análisis de sensibilidad, modo comparativo e informe PDF.

---

## Instalación y Ejecución Local

```bash
# 1. Clonar el repositorio
git clone https://github.com/<tu-usuario>/simulador-macro-abierta.git
cd simulador-macro-abierta

# 2. Crear entorno virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Copiar parámetros base
cp .env.example .env        # Opcional: edita .env para personalizar parámetros

# 5. Ejecutar la app
streamlit run main.py
```

La app abre en: `http://localhost:8501`

---

## Estructura del Proyecto

```
Simulador_Macroeconomico/
├── .env.example              # Plantilla de parámetros base
├── .streamlit/
│   └── config.toml           # Tema oscuro + configuración servidor
├── requirements.txt          # Dependencias Python
├── main.py                   # Entry point Streamlit (3 pestañas + sidebar)
│
├── config/                   # Carga de parámetros y escenarios (NO modificar)
│   ├── parameters.py         # dotenv + fallback + CRISIS_PRESETS
│   └── scenarios.py          # Serialización Parquet de escenarios
│
├── engine/                   # Motor matemático puro (NO modificar)
│   ├── core.py               # IS, LM, BP, eq_fixed(), eq_flexible()
│   ├── salter_swan.py        # q_IB(), q_EB(), get_zone()
│   └── cache.py              # Caché joblib
│
├── ui/                       # Interfaz Streamlit
│   ├── controls.py           # Sliders, presets, session_state
│   ├── charts.py             # Gráficos Plotly IS-LM y Salter-Swan
│   ├── narrative.py          # Narrativa económica automática
│   └── comparison.py         # Modo comparativo base vs actual
│
├── analysis/
│   └── sensitivity.py        # Barrido ±20%, tornado chart, Monte Carlo
│
├── report/
│   └── generator.py          # Generador PDF académico (fpdf2)
│
└── validation/
    └── test_equilibrium.py   # Verificación automática del motor
```

---

## Guía de Verificación Numérica

### Verificaciones Base (parámetros Sección 3.1)

| Verificación | Valor esperado | Comando |
|---|---|---|
| Multiplicador (mult) | 2.500 | `python -c "from engine.core import *; p=get_base_params(); print(eq_fixed(p)['mult'])"` |
| Y bajo TC fijo | 100.000 | `eq_fixed(base_params)['Y']` |
| M endógena | 40.000 | `eq_fixed(base_params)['M_endo']` |
| Y bajo TC flexible | 100.000 | `eq_flexible(base_params)['Y']` |
| E endógeno | 10.000 | `eq_flexible(base_params)['E_endo']` |

### Verificaciones de Política

```
G = 30, TC Fijo → Y = 125.00, M_endo = 52.50
  Cálculo: mult × (A + x1×E − b×r*) = 2.5 × (35 + 15×10 − 2×5)... 
  A(G=30) = 10 − 0.75×20 + 15 + 30 + 5 = 45
  Y = 2.5 × (45 + 1.5×10 − 2×5) = 2.5 × 50 = 125 ✓
  M_endo = 0.5×125 − 2×5 = 62.5 − 10 = 52.5 ✓

M = 55, TC Flexible → Y = 130.00, E_endo = 18.00
  Y = (55 + 2×5)/0.5 = 65/0.5 = 130 ✓
  E_endo = (0.40×130 + 2×5 − 35)/1.5 = (52+10−35)/1.5 = 27/1.5 = 18 ✓

Salter-Swan:
  A = 75, q = 0.75 → Zona III (déficit + desempleo) ✓
  A = 115, q = 1.30 → Zona I (superávit + sobreempleo) ✓
```

> **Nota académica:** Este simulador fue diseñado para verificar manualmente los equilibrios  
> *antes* de confiar en la IA. Ver Sección 3.2 del documento original.

---

## Despliegue en Streamlit Community Cloud (3 pasos)

### Requisitos previos
1. Cuenta en [Streamlit Community Cloud](https://streamlit.io/cloud)
2. Repositorio público en GitHub con todos los archivos del proyecto

### Pasos

**Paso 1:** Sube el proyecto a GitHub
```bash
git init
git add .
git commit -m "feat: Simulador Macro Abierta Fase 3"
git remote add origin https://github.com/<tu-usuario>/<repo>.git
git push -u origin main
```

**Paso 2:** En Streamlit Cloud
- Ve a https://share.streamlit.io
- Haz clic en **"New app"**
- Selecciona el repositorio, rama `main` y archivo `main.py`
- Haz clic en **"Deploy!"**

**Paso 3:** Verifica
- La app cargará en `https://<tu-usuario>-<repo>.streamlit.app`
- Verifica que Y=100 en estado base en las 3 pestañas

> `scikit-learn` puede fallar en Python 3.14+ (sin wheel). Si ocurre,  
> Streamlit Cloud usa Python 3.12 por defecto (compatible). Alternativamente,  
> agrega `.python-version` con contenido `3.12` a la raíz del repo.

---

## Funcionalidades por Fase

| Fase | Componentes | Estado |
|------|-------------|--------|
| **Fase 1** | Motor IS-LM-BP, Salter-Swan, validación analítica, caché joblib | ✅ Completo |
| **Fase 2** | Interfaz Streamlit, gráficos Plotly, narrativa, exportación CSV | ✅ Completo |
| **Fase 3** | Modo comparativo, sensibilidad, Monte Carlo, informe PDF | ✅ Completo |

---

## Notas Académicas

- **Motor validado:** Todas las ecuaciones coinciden con la Sección 3.1 (tolerancia < 0.01).
- **Funciones puras:** `engine/core.py` y `engine/salter_swan.py` no tienen efectos laterales.
- **Caché:** `joblib.Memory` + `@st.cache_data` evitan recálculos en reruns de Streamlit.
- **Exportación:** Resultados en CSV y Parquet; informe en PDF académico con 5 secciones.
- **Sensibilidad:** Barrido ±20% con 20 puntos por parámetro; tornado chart de impacto relativo.
