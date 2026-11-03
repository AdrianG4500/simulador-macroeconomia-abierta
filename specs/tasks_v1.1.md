# Tasks: Plan de Implementación Granular Versión 1.1 (Modo Simple)

Este documento contiene la lista detallada de tareas específicas para la **Versión 1.1** del Simulador Macroeconómico.

---

## Fase 1: Recalibración del Backend Matemático y Regímenes (`engine_simple/`)

- [x] **Tarea 1.1: Recalibrar sensibilidad de política monetaria en `engine_simple/core.py`**
  - Ajustar parámetros base ($b = 0.8$, $f = 1.5$) y reformular la derivada de la TPM en régimen flexible a $\frac{\partial Y}{\partial r_{ref}} = -M_{eff}(b + \varepsilon_x \nu_r) \approx -1.76\%$.
  - Verificar que el impacto por +100 pb se ubique exactamente en el rango didáctico de $[-1.0\%, -2.5\%]$.

- [x] **Tarea 1.2: Consolidar la Matriz de Balanza de Pagos y Reservas por Régimen en `engine_simple/dynamics.py`**
  - En régimen `fixed` y `crawling_peg`: implementar $\Delta R = BP = NX + KA$, con $KA = f \cdot (r - r^* - \Delta E_e - \rho)$.
  - En régimen `flexible`: asegurar $\Delta R = 0$ (flotación limpia donde $E$ absorbe el equilibrio).

- [x] **Tarea 1.3: Rediseñar el cálculo de equilibrio de Salter-Swan en `engine_simple/core.py`**
  - Calcular $(A^*, q^*)$ como el vértice dinámico en función de $Y_{pot}$ del escenario activo.

- [x] **Tarea 1.4: Añadir inercia inflacionaria y curva de Phillips calibrada en `engine_simple/dynamics.py`**
  - Implementar $\pi_t = 0.5 \pi_{t-1} + 0.5 \pi^e + 0.20 gap + \beta_{PT} (\Delta E / E_{prev})$.

---

## Fase 2: Mecanismo de Inercia de Políticas y Guardrails (`engine_simple/state_manager.py`)

- [x] **Tarea 2.1: Implementar inercia gubernamental en Gasto Público ($G$)**
  - Ajustar la ejecución efectiva de gasto: $G_t^{efectivo} = G_{t-1}^{efectivo} + 0.7(G_t^{objetivo} - G_{t-1}^{efectivo})$.
  - Almacenar el gasto objetivo y la pendiente de implementación en el snapshot.

- [x] **Tarea 2.2: Suavizar umbrales de Game Over en `config_simple/scoring.py`**
  - Actualizar $gY_{min} = -0.25$ en 1 turno (o 2 turnos consecutivos $< -0.15$).
  - Mantener $U_{max} = 0.35$, $\pi_{max} = 2.00$, $B/Y_{max} = 1.50$.

- [x] **Tarea 2.3: Crear calculadora de sensidades en tiempo real**
  - Método `compute_live_sensitivities()` en `StateManager` para proyectar el jacobiano activo.

---

## Fase 3: Interfaz de Usuario y UX v1.1 (`ui_simple/`)

- [x] **Tarea 3.1: Implementar Vista Previa de Impacto en Tiempo Real (Live Projection) en `ui_simple/controls_panel.py`**
  - Mostrar la variación proyectada ($\Delta Y, \Delta U, \Delta \pi, \Delta D, \Delta R$) de los sliders antes de ejecutar el turno.
  - Implementar panel de Alertas Tempranas (Fiscal, Inflacionaria, Reservas, Monetaria).

- [x] **Tarea 3.2: Ajustar pasos finos de sliders en `ui_simple/controls_panel.py`**
  - $G$: paso 0.5 MUSD.
  - $t$: paso 0.5%.
  - $r_{ref}$: paso 0.1%.
  - $E$: paso 0.1 unidades.

- [x] **Tarea 3.3: Rediseñar el gráfico de Salter-Swan en `ui_simple/charts_panel.py`**
  - Trazar curvas IB y EB cruzando en $(A^*, q^*)$ con delimitación de las 4 Zonas (I, II, III, IV) en Plotly.

---

## Fase 4: Pruebas y Validación v1.1 (`tests_simple/`)

- [x] **Tarea 4.1: Crear suite de pruebas de sensibilidad v1.1 en `tests_simple/test_v1_1_balance.py`**
  - Validar que $\frac{\partial Y}{\partial r_{ref}} \in [-1.0\%, -2.5\%]$.
  - Validar movimiento dinámico de reservas $\Delta R = BP$ bajo régimen fijo.
  - Validar cumplimiento incondicional de $Y = C + I + G + NX$ con $\text{error} < 10^{-12}$.
