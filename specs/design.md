# Design: Especificación Técnica y Arquitectura del Simulador Macroeconómico Simplificado

## 1. Contexto y Roles del Sistema

El sistema opera como una aplicación web educativa interactiva desarrollada en **Python + Streamlit**, organizada bajo el patrón arquitectónico de tres capas independientes y desacopladas:

```
[ CAPA DE CONFIGURACIÓN ]  --->  [ CAPA DEL MOTOR ]  --->  [ CAPA DE INTERFAZ (UI) ]
(config_simple/)                 (engine_simple/)           (ui_simple/)
```

### Roles del Sistema
- **Motor Matemático (Backend)**: Funciones puras que resuelven el equilibrio macroeconómico IS-LM-BP y calculan la evolución de variables de estado sin modificar estado global.
- **Orquestador de Estado (State Manager)**: Mantiene el historial de turnos, valida transiciones de política, evalúa eventos y ejecuta el bucle del juego.
- **Interfaz de Usuario (Frontend)**: Renderiza controles, tarjetas de KPIs, gráficos dinámicos Plotly y el informe narrativo de asesores. La UI es de **solo lectura** sobre el `GameState` y solo emite acciones hacia el `StateManager`.

---

## 2. Estructura de Carpetas del Proyecto

Para aislar limpiamente la versión simplificada del simulador legado y permitir commits/saves independientes en Git, se organizará la siguiente estructura modular dentro de la carpeta raíz del proyecto:

```
c:\Ingenieria Financiera\Semester I-2026\Open Macroeconomics\Simulador Macroeconomico\
├── specs/                        # Documentación de especificación del proyecto
│   ├── proposal.md               # Justificación, Alcance e Impacto
│   ├── design.md                 # Arquitectura, Backend, Frontend y Estructura
│   └── tasks.md                  # Hoja de ruta granular por fases y tareas
├── AGENTS.md                     # Guía de operación y reglas para agentes AI
├── engine_simple/                # Módulo Backend Simplificado
│   ├── __init__.py
│   ├── core.py                   # Solvers analíticos analíticamente cerrados (IS-LM-BP)
│   ├── dynamics.py               # Leyes de movimiento (Okun, Phillips, Deuda, Reservas)
│   ├── state_manager.py          # Orquestador del juego (10 turnos)
│   ├── events.py                 # Motor de eventos simplificado (3 exógenos, 2 endógenos)
│   └── advisor.py                # Sistema de recomendaciones y alertas preventivas
├── config_simple/                # Módulo de Configuración Simplificado
│   ├── __init__.py
│   ├── parameters.py             # Tipos TypedDict y defaults (16 params, 10 instrs)
│   ├── scenarios.py              # 4 Escenarios históricos calibrados
│   └── scoring.py                # Evaluación de Percepción Pública (0-100) y Game Over
├── ui_simple/                    # Módulo Frontend Simplificado (Layout Clásico)
│   ├── __init__.py
│   ├── main_layout.py            # Layout de 3 columnas (Izq: Controles, Centro: KPIs/Charts, Der: Explicación)
│   ├── controls_panel.py         # Sliders e inputs con tooltips didácticos
│   ├── kpi_panel.py              # Tarjetas de indicadores macroeconómicos
│   ├── charts_panel.py           # Gráficos IS-LM-BP, Salter-Swan y Timeline (Plotly)
│   ├── explanation_panel.py      # Resumen narrativo y consejos del economista
│   └── styles.py                 # CSS Customdidáctico y limpio
├── tests_simple/                 # Suite de Pruebas Unitarias e Integración
│   ├── test_core_identity.py     # Verificación incondicional de Y = C + I + G + NX
│   ├── test_solvers.py           # Verificación de regímenes Fijo, Flexible y Crawling
│   └── test_game_flow.py         # Prueba completa de partida de 10 turnos
└── main_simple.py                # Punto de entrada principal Streamlit
```

---

## 3. Especificaciones del Backend (Engine & Math)

### 3.1 Garantía de Consistencia Macroeconómica Incondicional
A diferencia del motor legado (donde $Y$ se calculaba por aproximación numérica y se aplicaban parches $75/25$ que rompían la identidad nacional), el motor simplificado garantiza **matemáticamente** que en cada período:

$$Y = C + I + G + NX$$

#### Procedimiento de Cierre Analítico:
1. Se define la demanda privada $C = c_0 + c_1 \cdot (1 - t) \cdot Y$.
2. Se define el sector externo $NX = NX_0 + \varepsilon_x \cdot q - m_1 \cdot Y$.
3. El multiplicador keynesiano estructural es:
   $$k_m = \frac{1}{1 - c_1(1-t) + m_1}$$
4. La inversión privada se determina endógenamente por la tasa de interés de equilibrio:
   $$I = I_0 - b \cdot r$$
5. El PIB de equilibrio $Y$ se resuelve en **forma cerrada** de la intersección del mercado de bienes con el sector externo y monetario:
   $$Y = k_m \cdot (c_0 + I_0 - b \cdot r + G + NX_0 + \varepsilon_x \cdot q)$$
6. Una vez resueltos $Y$ y $r$, las componentes $C, I, NX$ se evalúan exactamente con esos valores. **Resultado**: La suma $C + I + G + NX$ coincide exactamente con $Y$ con tolerancia $< 10^{-12}$.

### 3.2 Soluciones de Equilibrio Cerradas por Régimen Cambiario

#### A. Régimen de Tipo de Cambio Fijo (`fixed`)
- Instrumento cambiario: $E$ es exógeno.
- Instrumento monetario: Tasa de interés de política $r_{ref}$ o tasa de paridad externa $r_{BP}$.
- Condición de paridad de tasas (UIP + Movilidad Imperfecta):
  $$r = r^* + \Delta E_e + \rho - \frac{NX}{f}$$
  Sustituyendo $NX = NX_0 + \varepsilon_x \cdot q - m_1 \cdot Y$ en la condición BP y resolviendo el sistema lineal $2 \times 2$ (IS y BP), obtenemos las soluciones analíticas directas para $(Y, r)$ sin iteración numérica ni solvers aproximados.
- Saldos reales endógenos: $M = (k \cdot Y - h \cdot r) \cdot P_{local}$.

#### B. Régimen de Tipo de Cambio Flexible (`flexible`)
- Instrumento monetario: El Banco Central fija la **Tasa de Política Monetaria ($r_{ref}$)**.
- La tasa doméstica se ancla a la TPM: $r = r_{ref}$.
- El tipo de cambio $E$ se ajusta endógenamente despejando la ecuación de Balanza de Pagos:
  $$E_{endo} = \text{Despeje directo analítico de } r_{ref} = r^* + \Delta E_e + \rho - \frac{NX(E)}{f}$$
- El sistema se resuelve en 1 paso cerrado determinando $(Y, E, P_{local})$.

#### C. Régimen de Deslizamiento Programado (`crawling_peg`)
- $E_t = E_{t-1} \cdot (1 + \text{crawl\_rate})$.
- Se anclan las expectativas a $\Delta E_e = \text{crawl\_rate}$.
- Se resuelve en forma cerrada equivalente al régimen fijo con el nuevo tipo de cambio $E_t$.

---

## 4. Especificaciones del Frontend (UI & UX)

### 4.1 Layout Clásico de 3 Columnas

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  THE ECONOMIC WAR ROOM (Edición Educativa)  │  Escenario: Chile 2005  │ Turno 3 / 10   │
├──────────────────────┬──────────────────────────────────────────┬──────────────────────┤
│ 🎛️ CONTROLES         │ 📊 PANELS DE KPIS & GRÁFICOS             │ 📰 INFORMES Y CONSEJO│
│ (Columna 1: ~25%)    │ (Columna 2: ~50%)                        │ (Columna 3: ~25%)    │
│                      │                                          │                      │
│ 🏛️ Fiscal            │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐     │ 🗣️ Asesor de Gabinete│
│ Gasto (G): [ 20.0 ]  │ │ PIB  │ │Inflac│ │Desemp│ │Rating│     │ "Ministro, la subida │
│ Impuesto (t):[ 0.20] │ │104.2 │ │ 3.5% │ │ 4.8% │ │ AAA  │     │ de G estimuló el PIB │
│                      │ └──────┘ └──────┘ └──────┘ └──────┘     │ en +2.5%, pero las   │
│ 🏦 Monetario         │                                          │ reservas cayeron."   │
│ TPM (r_ref): [ 5.0% ]│ [ Tab 1: Modelo IS-LM-BP ]               │                      │
│                      │   - Gráfico dinámico con flechas         │ 🧠 Recomendación     │
│ 💱 Cambiario         │                                          │   Salter-Swan        │
│ Régimen: [ Fijo ▾ ]  │ [ Tab 2: Diagrama Salter-Swan ]          │ "Zona II: Mueve      │
│ Tipo Cambio (E):[10] │                                          │  el tipo de cambio"  │
│                      │ [ Tab 3: Evolución Temporal ]            │                      │
│ [ 🚀 Siguiente Turno]│                                          │ 📰 Periódico del Día │
└──────────────────────┴──────────────────────────────────────────┴──────────────────────┘
```

### 4.2 Elementos Didácticos Integrados
1. **Tooltips Didácticos**: Cada etiqueta de control incluye un ícono de ayuda `ⓘ` con explicaciones intuitivas en español sencillo.
2. **Explicación Narrativa de Turno**: Generación automática de texto al avanzar de turno detallando la causa y efecto de cada movimiento de política.
3. **Puntuación de Percepción Pública**: Indicador de 0 a 100 con código de colores (Verde/Amarillo/Rojo) reflejando la satisfacción ciudadana.
