# Tasks: Plan de Implementación Granular por Fases

Este documento contiene la lista detallada de tareas específicas para construir el **Simulador Macroeconómico Simplificado**. Cada tarea es atómica y verificable.

---

## Fase 1: Configuración y Definición de Tipos (`config_simple/`)

- [x] **Tarea 1.1: Crear la estructura de directorios**
  - Crear carpetas: `config_simple/`, `engine_simple/`, `ui_simple/`, `tests_simple/`.
  - Crear los archivos `__init__.py` en cada carpeta.

- [x] **Tarea 1.2: Definir estructuras de datos en `config_simple/parameters.py`**
  - Crear `TypedDict` para `StructuralParams` (16 variables: `c0`, `c1`, `t`, `I0`, `b`, `NX0`, `epsilon_x`, `epsilon_m`, `m1`, `k`, `h`, `f`, `alpha_PT`, `beta_PT`, `P_star`, `U_n`).
  - Crear `TypedDict` para `PolicyInstruments` (10 variables: `G`, `t`, `E`, `r_ref`, `regime`, `crawl_rate`, `r_star`, `P_star`, `pi_target`, `G_needed`).
  - Crear `TypedDict` para `Equilibrium` y `TurnSnapshot`.
  - Definir diccionario de valores por defecto `DEFAULT_STRUCTURAL_PARAMS` y `DEFAULT_POLICY_INSTRUMENTS`.

- [x] **Tarea 1.3: Configurar escenarios en `config_simple/scenarios.py`**
  - Definir los 4 escenarios históricos: `tiger_asia` (Corea 1985), `Economia_Saludable` (Chile 2005), `latam_crisis` (México 1982), `death_spiral` (Bolivia 1982).
  - Incluir metadatos narrativos (descripción, bullets) y parámetros iniciales calibrados.

- [x] **Tarea 1.4: Implementar sistema de scoring en `config_simple/scoring.py`**
  - Crear función `calc_period_score(gap, U, pi, gY)` que retorne el Score de Percepción Pública (0-100).
  - Ponderación: Desempleo (40%), Inflación (40%), Crecimiento del PIB (20%).
  - Crear función `check_game_over(gY, U, pi, B_Y_ratio)` para verificar los 4 umbrales de colapso.

---

## Fase 2: Motor Matemático Analítico Cerrado (`engine_simple/`)

- [x] **Tarea 2.1: Implementar funciones puras básicas en `engine_simple/core.py`**
  - `compute_multiplier(c1, t, m1)`: Multiplicador keynesiano $k_m = 1 / (1 - c_1(1-t) + m_1)$.
  - `compute_price_level(E, P_star, P_NT, alpha_PT)`: Precios locales $P = \alpha_{PT}(E \cdot P^*) + (1 - \alpha_{PT})P_{NT}$.
  - `compute_real_exchange_rate(E, P_star, P_local)`: TCR $q = (E \cdot P^*) / P_{local}$.
  - `compute_NX(NX0, epsilon_x, epsilon_m, q, m1, Y, j_curve_active)`: Exportaciones netas con verificación de Marshall-Lerner y J-curve.

- [x] **Tarea 2.2: Implementar solver analítico de TC Fijo (`eq_fixed`)**
  - Resolver analíticamente el sistema $2 \times 2$ (IS y BP).
  - Despejar $Y$ y $r$ exactos sin iteraciones numéricas.
  - Calcular $M_{endo} = (k \cdot Y - h \cdot r) \cdot P_{local}$.
  - Derivar $C = c_0 + c_1(1-t)Y$, $I = I_0 - b \cdot r$, $NX = X - M_{imp}$.
  - **Verificación obligatoria**: Validar $|Y - (C + I + G + NX)| < 10^{-12}$.

- [x] **Tarea 2.3: Implementar solver analítico de TC Flexible (`eq_flexible`)**
  - Fijar la tasa doméstica a la TPM: $r = r_{ref}$.
  - Despejar analíticamente $E_{endo}$ de la condición BP: $r_{ref} = r^* + \Delta E_e + \rho - NX(E)/f$.
  - Calcular $Y$ directamente de la curva IS con el $E_{endo}$ resuelto.
  - Derivar $C, I, NX$.
  - **Verificación obligatoria**: Validar $|Y - (C + I + G + NX)| < 10^{-12}$.

- [x] **Tarea 2.4: Implementar solver analítico de Crawling Peg (`eq_crawling_peg`)**
  - Actualizar $E_t = E_{t-1} \cdot (1 + crawl\_rate)$ y $\Delta E_e = crawl\_rate$.
  - Ejecutar el solver de TC Fijo con el nuevo $E_t$.

- [x] **Tarea 2.5: Implementar dinámicas interturnos en `engine_simple/dynamics.py`**
  - `compute_output_gap(Y, Y_pot)` y `update_potential_output(Y_pot, g_pot)`.
  - `compute_unemployment(U_n, gap)`: Ley de Okun lineal $U = U_n - 0.5 \cdot gap$.
  - `compute_inflation(pi_e, gap, delta_E, E_prev)`: Phillips lineal $\pi = \pi_e + 0.5 \cdot gap + \beta_{PT}(\Delta E / E_{prev})$.
  - `update_adaptive_expectations(pi_t, pi_target)`: Expectativas $\pi_e = 0.5 \cdot \pi_{prev} + 0.5 \cdot \pi_{target}$.
  - `compute_fiscal_balance(G, t, Y, r, B_prev, r_star, rho)`: Recaudación, Déficit y acumulación de deuda $B_{new}$.
  - `update_reserves(R_prev, NX, regime)`: Actualización de reservas (solo en TC Fijo).
  - `compute_sovereign_risk(B, Y_pot, R)`: Tabla simplificada de prima de riesgo $\rho$ y rating crediticio.

- [x] **Tarea 2.6: Implementar diagnóstico Salter-Swan en `engine_simple/core.py`**
  - Calcular pendientes estructurales $dq/dA|_{IB}$ y $dq/dA|_{EB}$.
  - Clasificar posición $(A, q)$ en Zonas I, II, III o IV.
  - Generar texto de diagnóstico y recomendación de política.

---

## Fase 3: Orquestación, Eventos y Asesores (`engine_simple/`)

- [x] **Tarea 3.1: Crear motor de eventos en `engine_simple/events.py`**
  - Definir 3 eventos exógenos (`commodity_boom`, `fed_rate_shock`, `global_recession`).
  - Definir 2 eventos endógenos (`social_unrest` si $U > 15\%$, `virtuous_circle` si 3 turnos con $gY > 4\%$).
  - Aplicar y revertir deltas paramétricos limpiamente.

- [x] **Tarea 3.2: Crear sistema de asesores en `engine_simple/advisor.py`**
  - Implementar "dry-run" del turno $t+1$ para generar alertas preventivas.
  - Emitir recomendaciones de Gabinete (Banco Central, Hacienda, Trabajo).

- [x] **Tarea 3.3: Implementar StateManager en `engine_simple/state_manager.py`**
  - Métodos `calibrate()`, `start_simulation()`, `step_forward()`, `get_endgame_summary()`.
  - Ejecución limpia del flujo de turno de 8 pasos sin parches ad-hoc.


---

## Fase 4: Interfaz de Usuario y Layout Clásico (`ui_simple/`)

- [x] **Tarea 4.1: Construir layout de 3 columnas en `ui_simple/main_layout.py`**
  - Columna 1 (Izquierda ~25%): Panel de Controles (Sliders de $G, t, r_{ref}, E$, Régimen).
  - Columna 2 (Centro ~50%): Fila Superior de KPIs + Sistema de Tabs para Gráficos.
  - Columna 3 (Derecha ~25%): Explicación del Turno + Consejo Salter-Swan + Periódico del Día.

- [x] **Tarea 4.2: Implementar controles con tooltips en `ui_simple/controls_panel.py`**
  - Agregar tooltips didácticos explicativos en cada slider.
  - Sincronizar estado de controles habilitados/deshabilitados según el régimen cambiario activo (Trilema).

- [x] **Tarea 4.3: Implementar tarjetas de KPIs en `ui_simple/kpi_panel.py`**
  - Mostrar PIB ($Y$), Inflación ($\pi$), Desempleo ($U$), Tasa ($r$), Reservas ($R$), Deuda/PIB ($B/Y$), Rating y Score.

- [x] **Tarea 4.4: Construir gráficos dinámicos en `ui_simple/charts_panel.py`**
  - Plotly IS-LM-BP con marcas de equilibrio y flechas de dirección.
  - Diagrama Plotly de Salter-Swan (4 cuadrantes).
  - Línea de tiempo multi-variable de 10 turnos.

- [x] **Tarea 4.5: Implementar panel narrativo en `ui_simple/explanation_panel.py`**
  - Generación de texto automático de causa-efecto post-turno.
  - Sección "¿Qué recomienda un economista?" basada en Salter-Swan.

---

## Fase 5: Pruebas y Validación (`tests_simple/`)

- [x] **Tarea 5.1: Crear prueba de identidad contable `tests_simple/test_core_identity.py`**
  - Probar 1,000 combinaciones aleatorias de parámetros e instrumentos.
  - Verificar que $|Y - (C + I + G + NX)| < 10^{-12}$ en el 100% de los casos.

- [x] **Tarea 5.2: Crear prueba de solvers por régimen `tests_simple/test_solvers.py`**
  - Probar estabilidad y convergencia analítica en Fijo, Flexible y Crawling.

- [x] **Tarea 5.3: Crear prueba de partida completa `tests_simple/test_game_flow.py`**
  - Simular partidas completas de 10 turnos en los 4 escenarios sin excepciones ni NaN.

---

## Fase 6: Punto de Entrada e Integración

- [x] **Tarea 6.1: Crear punto de entrada `main_simple.py`**
  - Inicializar Streamlit, cargar estilos CSS didácticos y conectar con `ui_simple/main_layout.py`.

- [x] **Tarea 6.2: Crear `AGENTS.md` en la raíz del workspace**
  - Documentar las reglas de desarrollo, parámetros del proyecto y flujo de trabajo para agentes AI.

