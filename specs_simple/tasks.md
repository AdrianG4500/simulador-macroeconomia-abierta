# 📋 Plan de Tareas Detallado: The Economic War Room (V1.2 SIMPLE)
> **Referencia Normativa:** [`master_spec.md`](file:///c:/Ingenieria%20Financiera/Semester%20I-2026/Open%20Macroeconomics/Simulador%20Macroeconomico/specs_simple/master_spec.md)  
> **Objetivo:** Implementación y calibración matemática integral del motor analítico cerrado, interfaz de 3 columnas, blindaje anti-bucle y garantía de jugabilidad hasta el Turno 10 sin colapsos injustos para los 4 escenarios históricos.

---

## FASE 1: Estructura de Datos, Catálogo de Palancas y Escenarios (`config_simple/`)

### 1.1. Catálogo de Parámetros y las 8 Palancas de Política (`config_simple/parameters.py`)
- [x] **1.1.1. Tipos de Datos TypedDict Estrictos:**
  - Actualizar `StructuralParams` para incluir parámetros del modelo extendido:
    - $\alpha_{PT} = 0.40$ (peso de transables)
    - $\beta_{PT} = 0.20$ (pass-through cambiario)
    - Sensibilidad de inversión privada: $b$ (tasa), $\rho_k$ (impuesto corporativo), $\psi_{ci}$ (crowding-in de inversión pública), $\psi_{co}$ (crowding-out de deuda $> 60\%$).
    - Comercio exterior: $\epsilon_x, \epsilon_m$ (sensibilidad TCR), $\eta_x$ (sensibilidad a subsidios exportadores).
    - Crecimiento potencial: $g_{\text{pot}}$ (tasa autónoma), $I_{g,\text{dep}}$ (inversión pública de reposición/depreciación).
  - Actualizar `PolicyInstruments` para reflejar exactamente el catálogo de las **8 palancas**:
    1. $G_c$: Gasto Público Corriente ($[5.0, 35.0]$, paso $0.5$)
    2. $I_g$: Inversión Pública en Infraestructura ($[0.0, 25.0]$, paso $0.5$)
    3. $t_c$: Impuesto a la Renta / Consumo ($[0.05, 0.40]$, paso $0.005$)
    4. $t_k$: Impuesto Corporativo a Empresas ($[0.00, 0.35]$, paso $0.005$)
    5. $r_{\text{ref}}$: Tasa de Política Monetaria TPM ($[0.01, 0.30]$, paso $0.0025$)
    6. $\tau$: Arancel a las Importaciones ($[0.00, 0.30]$, paso $0.005$)
    7. $s_x$: Subsidio a las Exportaciones ($[0.00, 0.20]$, paso $0.005$)
    8. $E$ / $\text{crawl}$: Tipo de Cambio Nominal / Tasa de Deslizamiento ($E \in [5.0, 25.0]$, paso $0.1$; $\text{crawl} \in [0.0, 0.25]$)
    - Campos contextuales y de régimen: `regime` (`"fixed"`, `"flexible"`, `"crawling_peg"`), `r_star`, `P_star`, `pi_target`.
- [x] **1.1.2. Actualizar `Equilibrium` y `TurnSnapshot`:**
  - Incorporar variables clave de la especificación:
    - `PIB_nominal`: $Y_t \cdot P_{\text{local}, t}$
    - `debt_to_gdp_nominal`: $B_t / (Y_t \cdot P_{\text{local}, t})$
    - Desglose de demanda agregada: $C_t, I_{\text{priv}, t}, G_c, I_g, X_t, M_{\text{imp}, t}, NX_t$.
    - Desglose fiscal: Recaudación $t_c + t_k + \text{aranceles}$, subsidios $s_x \cdot X$, intereses $((r^* + \rho)/100)B_{t-1}$, déficit total.
    - Credibilidad endógena: $\theta_t \in [0.40, 0.80]$.
    - Estado de alerta roja crítica: `red_alert_active: bool`, `red_alert_reason: str`, `consecutive_alert_turns: int`.

### 1.2. Calibración Histórica de los 4 Escenarios (`config_simple/scenarios.py`)
- [x] **1.2.1. Escenario 1: 🇰🇷 Corea del Sur (1985) — Fácil:**
  - Calibración exacta $T=0$: $Y_0 = 100.0, Y_{\text{pot},0} = 100.0, \pi_0 = 3.0\%, U_0 = 4.0\%, R_0 = 80.0, B_0 = 20.0$.
  - Palancas iniciales: Régimen `FIXED` ($E=10.0$), $G_c = 12.0, I_g = 8.0, t_c = 0.15, t_k = 0.10, r_{\text{ref}} = 6.0\%, \tau = 0.05, s_x = 0.02$.
  - Programación de evento en T3: Alza de tasas internacionales ($r^*$ sube $+1.5\%$).
- [x] **1.2.2. Escenario 2: 🇨🇱 Chile (2000–2005) — Normal:**
  - Calibración exacta $T=0$: $Y_0 = 100.0, Y_{\text{pot},0} = 100.0, \pi_0 = 3.0\%, U_0 = 5.0\%, R_0 = 60.0, B_0 = 15.0$.
  - Palancas iniciales: Régimen `FLEXIBLE` ($E=10.0$), $G_c = 14.0, I_g = 6.0, t_c = 0.16, t_k = 0.10, r_{\text{ref}} = 5.0\%, \tau = 0.06, s_x = 0.00$.
  - Programación de eventos: T3 desaceleración global ($X_0$ cae $-4.0$), T6 superciclo del cobre ($X_0$ sube $+8.0$).
- [x] **1.2.3. Escenario 3: 🇲🇽 México (1994–1995) — Difícil:**
  - Calibración exacta $T=0$: $Y_0 = 98.0, Y_{\text{pot},0} = 100.0, \pi_0 = 7.5\%, U_0 = 6.5\%, R_0 = 22.0, B_0 = 52.0$.
  - Palancas iniciales: Régimen `FIXED` ($E=10.0$), $G_c = 16.0, I_g = 4.0, t_c = 0.14, t_k = 0.10, r_{\text{ref}} = 8.0\%, \tau = 0.05, s_x = 0.00$.
  - Programación de evento en T1: Fuga de capitales y salto en tasas de EE. UU. ($r^*$ sube $+2.5\%$ y riesgo $\rho$ se dispara).
- [x] **1.2.4. Escenario 4: 🇧🇴 Bolivia (1982–1985) — Muy Difícil:**
  - Calibración exacta $T=0$: $Y_0 = 92.0, Y_{\text{pot},0} = 100.0, \pi_0 = 24.0\%, U_0 = 11.0\%, R_0 = 15.0, B_0 = 70.0$.
  - Palancas iniciales: Régimen `CRAWLING_PEG` ($\text{crawl} = 8.0\%$), $G_c = 22.0, I_g = 2.0, t_c = 0.08, t_k = 0.05, r_{\text{ref}} = 10.0\%, \tau = 0.10, s_x = 0.00$.
  - Calibración de parámetros de rezago tributario y señoreaje para representar la espiral previa al D.S. 21060.

### 1.3. Blindaje Anti-Bucle, Umbrales de Game Over y Score (`config_simple/scoring.py`)
- [x] **1.3.1. Implementar Regla 1 (Período de Gracia + Persistencia de 2 Turnos):**
  - Período de gracia: Garantizar que en los Turnos 1 y 2 sea **imposible** el Game Over.
  - A partir del Turno 3: El Game Over requiere que la condición crítica se mantenga por **2 turnos consecutivos**.
  - Sistema de Alerta Roja Crítica en el 1er turno de infracción con mensaje didáctico de advertencia:
    - Default Soberano: Alerta si $B / (Y \cdot P_{\text{local}}) > 135\%$; Game Over si $> 150\%$ por 2 turnos.
    - Crisis de Balanza de Pagos: Alerta si $R_t < 8.0\text{ MUSD}$; Game Over si $R_t \le 2.0\text{ MUSD}$ por 2 turnos.
    - Hiperinflación: Alerta si $\pi_t > 35.0\%$; Game Over si $\pi_t > 50.0\%$ por 2 turnos.
    - Estallido Social / Depresión: Alerta si $U_t > 22.0\%$ o $g_Y < -15\%$; Game Over si $U_t > 25.0\%$ por 2 turnos.
- [x] **1.3.2. Implementar Regla 2 (Score de Aprobación Ciudadana Ponderado):**
  - Fórmula exacta:
    $$\text{Score}_t = 100 - \left(1.2 \cdot |\text{Gap}_t \cdot 100| + 2.0 \cdot \max(0, (U_t - U_n)\cdot 100) + 1.5 \cdot |\pi_t - 0.03|\cdot 100 + 0.5 \cdot \max(0, \text{RatioDeuda}_t\cdot 100 - 60)\right)$$
  - Inercia ciudadana: $\text{Score}_t = 0.70 \cdot \text{Score}_{\text{calc}} + 0.30 \cdot \text{Score}_{t-1}$, acotado estrictamente en $[0, 100]$.

---

## FASE 2: Motor Matemático Analítico Cerrado (`engine_simple/`)

### 2.1. Núcleo Algebraico Puro (`engine_simple/core.py`)
- [x] **2.1.1. Normalización de Precios y TCR (Base $E_0 = 10.0$):**
  - Precios transables con arancel: $P_T = (E_t / 10.0) \cdot P^* \cdot (1 + 0.50 \cdot \tau)$.
  - Nivel de precios doméstico: $P_{\text{local}} = 0.40 \cdot P_T + 0.60 \cdot P_{NT, t}$.
  - Tipo de cambio real normalizado: $q_t = \frac{(E_t / 10.0) \cdot P^*}{P_{\text{local}}}$.
  - Validación: en $T=0$, con $E_0=10.0, P^*=1.0, P_{NT}=1.0, \tau=0.0 \implies P_{\text{local}}=1.00$ y $q=1.00$.
- [x] **2.1.2. Multiplicador Keynesiano Ampliado:**
  - $k_m = \frac{1}{1 - c_1(1 - t_c) + m_1(1 - \tau)}$.
- [x] **2.1.3. Tasa de Interés Doméstica Efectiva ($r_t$):**
  - Flexible: $r_t = r_{\text{ref}} + 0.5 \cdot \rho_t$.
  - Fijo / Crawling (Trilema): $r_t = 0.60 \cdot r_{\text{ref}} + 0.40 \cdot (r^* + \text{crawl\_rate} \cdot 100 + \rho_t)$.
- [x] **2.1.4. Formación Bruta de Capital Privado ($I_{\text{priv}, t}$):**
  - $I_{\text{priv}, t} = \max\left(2.0, \; I_0 - b \cdot (r_t - r_0) - \rho_k \cdot (t_k - t_{k,0}) + \psi_{ci} \cdot (I_g - I_{g,0}) - \psi_{co} \cdot \max(0, \text{RatioDeuda}_{t-1} - 0.60)\right)$.
- [x] **2.1.5. Sector Externo Desagregado:**
  - Exportaciones: $X_t = x_0 + \epsilon_x \cdot (q_t - 1.0) + \eta_x \cdot s_x$.
  - Importaciones: $M_{\text{imp}, t} = \max(2.0, \; m_0 + m_1(1 - \tau)Y_t - \epsilon_m(q_t - 1.0))$.
  - Balanza comercial: $NX_t = X_t - M_{\text{imp}, t}$.
- [x] **2.1.6. Solución Analítica Cerrada del PIB Real ($Y_t$):**
  - Nivel de equilibrio puro: $Y_{\text{eq}} = k_m \cdot [c_0 + I_{\text{priv}, t} + G_c + I_g + X_t - m_0 + \epsilon_m(q_t - 1.0)]$.
  - Amortiguador de inercia macroeconómica (65/35): $Y_t = 0.65 \cdot Y_{\text{eq}} + 0.35 \cdot Y_{t-1}$.
  - **Garantía Incondicional de Identidad Macroeconómica:**
    - Evaluar $C_t = c_0 + c_1(1 - t_c)Y_t$.
    - Evaluar $M_{\text{imp}, t}$ con $Y_t$.
    - Asignar la absorción de inventarios post-inercia a $I_{\text{priv}, t} = Y_t - C_t - (G_c + I_g) - NX_t$.
    - Comprobar que $|Y_t - (C_t + I_{\text{priv},t} + G_t + NX_t)| < 10^{-12}$.
- [x] **2.1.7. Salter-Swan y Curvas IS-LM-BP:**
  - Determinar coordenadas dinámicas del punto $(A, q)$ con $A = C + I_{\text{priv}} + G$.
  - Computar las curvas de balance interno (IB) y externo (EB) para clasificar la zona (I, II, III o IV).

### 2.2. Leyes de Movimiento y Dinámicas Interturnos (`engine_simple/dynamics.py`)
- [x] **2.2.1. Oferta Agregada y PIB Potencial:**
  - $Y_{\text{pot}, t} = Y_{\text{pot}, t-1} \cdot (1 + g_{\text{pot}}) + 0.18 \cdot (I_g - I_{g,\text{dep}})$.
  - Brecha: $\text{Gap}_t = (Y_t - Y_{\text{pot}, t}) / Y_{\text{pot}, t}$.
- [x] **2.2.2. Mercado Laboral (Okun):**
  - $U_t = \max(0.02, \; U_n - \gamma_{\text{okun}} \cdot \text{Gap}_t)$.
- [x] **2.2.3. Inflación Multicausal (Phillips Ponderada de 4 Fuerzas):**
  - $\pi_t = \pi^e_t + \alpha_{\text{inf}} \cdot \text{Gap}_t + \beta_{PT} \cdot \left(\frac{E_t - E_{t-1}}{E_{t-1}}\right) + 0.15 \cdot (\tau_t - \tau_{t-1}) + \text{Shock}_{\text{señoreaje}}$.
- [x] **2.2.4. Credibilidad Endógena ($\theta_t$) y Expectativas Adaptativas ($\pi^e_{t+1}$):**
  - $\theta_{\text{base}} = 0.40$.
  - Bono Taylor: $+0.20$ si $r_{\text{ref}} \ge \pi_t \cdot 100$.
  - Bono de disciplina fiscal: $+0.20$ si $\text{Déficit Primario} \le 0.015 \cdot Y_t$.
  - Rango: $\theta_t \in [0.40, 0.80]$.
  - $\pi^e_{t+1} = \theta_t \cdot \pi_{\text{meta}} + (1 - \theta_t) \cdot \pi_t$ con $\pi_{\text{meta}} = 0.03$.
- [x] **2.2.5. Finanzas Públicas y Deuda sobre PIB Nominal:**
  - $\text{Recaudación}_t = (t_c + t_k) \cdot Y_t + \tau \cdot M_{\text{imp}, t}$.
  - $\text{CostoSubsidios}_t = s_x \cdot X_t$.
  - $\text{InteresesDeuda}_t = \left(\frac{r^* + \rho_t}{100}\right) \cdot B_{t-1}$.
  - $\text{Déficit}_t = G_c + I_g + \text{CostoSubsidios}_t + \text{InteresesDeuda}_t - \text{Recaudación}_t$.
  - $B_t = \max(0.0, \; B_{t-1} + \text{Déficit}_t)$.
  - $\text{PIB Nominal}_t = Y_t \cdot P_{\text{local}, t}$.
  - $\text{RatioDeuda}_t = B_t / \text{PIB Nominal}_t$.
  - Calificación crediticia soberana (`AAA` a `D`) y prima de riesgo $\rho_t$ según $\text{RatioDeuda}_t$ y nivel de reservas $R_t$.
- [x] **2.2.6. Flujo de Capitales y Reservas Internacionales:**
  - $KA_t = f \cdot \left(\frac{r_t - r^* - \rho_t - \Delta E^e}{100}\right)$.
  - En régimen Fijo / Crawling: $R_t = R_{t-1} + NX_t + KA_t$.
  - En régimen Flexible: $R_t = R_{t-1} + 0.15 \cdot (NX_t + KA_t)$, y el tipo de cambio absorbe el desbalance:
    $E_t = E_{t-1} \cdot [1 - 0.015 \cdot (NX_t + KA_t)]$.

### 2.3. Eventos y Shocks Históricos (`engine_simple/events.py`)
- [x] **2.3.1. Catálogo de Eventos Históricos Vinculados a los Escenarios:**
  - Evento Corea T3: "Shock de tasas externas de la Reserva Federal y fricción comercial".
  - Eventos Chile: T3 "Desaceleración comercial global", T6 "Superciclo del cobre / Boom de commodities".
  - Eventos México: T1 "Efecto Tequila: Fuga masiva de capitales y ataque especulativo contra el peso".
  - Eventos Bolivia: T0-T2 "Rezago de Olivera-Tanzi y crisis de señoreaje".
- [x] **2.3.2. Aplicación Pura y Transparente:**
  - Los eventos aplican deltas multiplicativos o aditivos explícitos sobre parámetros exógenos sin mutar variables protegidas.

### 2.4. Asesores Socráticos de Gabinete (`engine_simple/advisor.py`)
- [x] **2.4.1. Los 3 Asesores Didácticos:**
  - 🏦 **Banco Central:** Monitorea la meta de inflación ($\pi$), la tasa real ($r_{\text{ref}} - \pi$), el pass-through cambiario y el nivel crítico de reservas $R_t$.
  - 🏛️ **Ministerio de Hacienda:** Supervisa la sostenibilidad del Ratio Deuda/PIB Nominal, la regla fiscal y el balance entre $G_c$ e $I_g$.
  - 🏭 **Ministerio de Trabajo y Comercio:** Evalúa el desempleo ($U$), la competitividad cambiaria ($q$), el impacto de los aranceles $\tau$ en costos y la efectividad de los subsidios $s_x$.
- [x] **2.4.2. Función `run_dry_run`:**
  - Simula instantáneamente el impacto en el turno actual con las 8 palancas modificadas por los sliders sin avanzar el turno, mostrando proyecciones de $Y$, $\pi$, $U$, $NX$, $R$, y Deuda/PIB.

---

## FASE 3: Orquestación de Estado y Persistencia (`engine_simple/state_manager.py`)

- [x] **3.1. Flujo de Transición de Turno (`step_forward`):**
  - Implementar la secuencia estricta de 8 pasos:
    1. Aplicación de las 8 palancas seleccionadas y eventos programados/activos.
    2. Resolución cerrada analítica del equilibrio macroeconómico $Y_t$ e identidades.
    3. Cálculo de dinámicas de precios, inflación de 4 componentes, desempleo Okun y PIB potencial.
    4. Balance fiscal, deuda soberana sobre PIB nominal y prima de riesgo.
    5. Balanza de pagos (KA, NX, acumulación de reservas o flotación cambiaria).
    6. Verificación de Alerta Roja Crítica y evaluación de persistencia de Game Over (Regla 1).
    7. Cálculo del Score de Percepción Ciudadana (Regla 2).
    8. Creación y congelamiento del `TurnSnapshot` inmutable en el historial.
- [x] **3.2. Mecanismo de Alerta Roja y Ventana de Tolerancia:**
  - Contador de turnos en condición crítica (`consecutive_danger_turns`).
  - Flag de `red_alert` para activar el banner preventivo en UI y orientar al estudiante.
- [x] **3.3. Reforma Cambiaria de Emergencia (`switch_regime`):**
  - Método en `StateManager` para cambiar el régimen cambiario durante la partida (ej. de Fijo a Flexible en México T1-T2 para detener la sangría de reservas, o unificar el cambio en Bolivia).
- [x] **3.4. Gancho de Serialización JSON (Preparación Fase B):**
  - Implementar `to_dict() -> Dict[str, Any]` para empaquetar todo el estado del juego (parámetros, palancas, historial, eventos, turno, score).
  - Implementar `from_dict(payload: Dict[str, Any]) -> StateManager` para reconstruir la simulación con fidelidad 100%.

---

## FASE 4: Interfaz de Usuario de 3 Columnas (`ui_simple/`)

### 4.1. Columna Izquierda: Panel de Controles y Sliders (`ui_simple/controls_panel.py`)
- [x] **4.1.1. Selector de Escenario:**
  - Dropdown con los 4 escenarios, badges de dificultad (`Fácil`, `Normal`, `Difícil`, `Muy Difícil`), metadatos históricos y botón de reinicio/carga.
- [x] **4.1.2. Las 8 Palancas Agrupadas por Bloques Ministeriales:**
  - **Bloque Fiscal:**
    - Slider 1: $G_c$ (Gasto Corriente) $[5.0, 35.0]$
    - Slider 2: $I_g$ (Inversión en Infraestructura) $[0.0, 25.0]$
    - Slider 3: $t_c$ (Impuesto a la Renta/Consumo) $[5.0\%, 40.0\%]$
    - Slider 4: $t_k$ (Impuesto Corporativo) $[0.0\%, 35.0\%]$
  - **Bloque Monetario:**
    - Slider 5: $r_{\text{ref}}$ (Tasa de Política Monetaria) $[1.0\%, 30.0\%]$
  - **Bloque Comercial:**
    - Slider 6: $\tau$ (Arancel de Importación) $[0.0\%, 30.0\%]$
    - Slider 7: $s_x$ (Subsidio Exportador) $[0.0\%, 20.0\%]$
  - **Bloque Cambiario:**
    - Slider 8: Tipo de cambio $E \in [5.0, 25.0]$ (en régimen Fijo) o $\text{crawl} \in [0.0\%, 25.0\%]$ (en régimen Crawling); deshabilitado con mensaje educativo en régimen Flexible.
- [x] **4.1.3. Acciones de Juego:**
  - Botón de **"Reforma Cambiaria de Emergencia"** con diálogo y selector de nuevo régimen institucional.
  - Botón principal: **"Avanzar al Turno t+1 ⏩"**.
- [x] **4.1.4. Vista Previa de Impacto Enriquecida (Proyección t+1 en Tiempo Real para Beta-Testing):**
  - Muestra deltas en vivo al mover cualquier slider: $\Delta Y$, $\Delta \pi$, $\Delta U$, $\Delta \text{Deuda/PIB Nom}$, $\Delta R$, $\Delta \text{Score}$.
  - Sistema de alertas tempranas preventivas si la combinación conduce a zona crítica.

### 4.2. Columna Central: KPIs y Pestañas Gráficas (`ui_simple/kpi_panel.py` y `charts_panel.py`)
- [x] **4.2.1. Panel de 8 Tarjetas KPI:**
  - Fila 1: PIB Real ($Y$), Brecha del Producto ($\text{Gap}$), Inflación ($\pi$), Desempleo ($U$), Aprobación Ciudadana (Score con badge).
  - Fila 2: Tasa de Interés ($r$), Tipo de Cambio Real ($q$), Deuda / PIB Nominal ($B/(Y \cdot P_{\text{local}})$), Reservas ($R$), Rating Soberano.
  - Banner dinámico de **Alerta Roja Crítica** parpadeante si se entra en zona de riesgo.
- [x] **4.2.2. Tab 1 — Modelo IS-LM-BP (`📈 Modelo IS-LM-BP`):**
  - Renderizado Plotly de las curvas IS (azul), LM (verde) y BP (roja segmentada).
  - Comparación visual del punto de equilibrio previo vs punto proyectado por los sliders.
- [x] **4.2.3. Tab 2 — Diagrama Salter-Swan (`⚖️ Diagrama Salter-Swan`):**
  - Gráfico Plotly con Eje X = Absorción Doméstica ($A$) y Eje Y = Tipo de Cambio Real ($q$).
  - Las 4 zonas didácticas coloreadas (I: Inflación+Superávit, II: Desempleo+Superávit, III: Desempleo+Déficit, IV: Inflación+Déficit).
  - Marcador de posición actual y trazado de la trayectoria histórica turno a turno.
- [x] **4.2.4. Tab 3 — Trilema de Mundell-Fleming (`🔺 Trilema Cambiario`):**
  - Diagrama visual interactivo del triángulo de Mundell-Fleming iluminando los 2 vértices activos y desvaneciendo el vértice sacrificado con explicación didáctica.
- [x] **4.2.5. Tab 4 — Evolución Temporal (`🕒 Evolución Temporal`):**
  - Series temporales a 10 turnos de: PIB Real vs Potencial, Inflación vs Meta, Desempleo vs NAIRU, Ratio Deuda / PIB Nominal y Reservas Internacionales.

### 4.3. Columna Derecha: Prensa y Asesores de Gabinete (`ui_simple/explanation_panel.py`)
- [x] **4.3.1. Periódico "El Observador Macroeconómico":**
  - Titular principal dinámico generado según el indicador más crítico del turno y crónica de eventos históricos.
- [x] **4.3.2. Tarjetas de los 3 Asesores de Gabinete:**
  - Dictámenes socráticos en lenguaje claro: Banco Central, Ministerio de Hacienda, Ministerio de Trabajo y Comercio.

### 4.4. Estructura General y Modal de Fin de Partida (`ui_simple/main_layout.py`)
- [x] **4.4.1. Sidebar con Utilidades:**
  - Botón de "💾 Guardar Partida JSON" (descarga el payload de `state_mgr.to_dict()`).
  - Uploader de "📂 Cargar Partida JSON" (restaura el estado con `state_mgr.from_dict()`).
  - Botón de reinicio rápido.
- [x] **4.4.2. Pantallas Especiales de Cierre:**
  - Vista de **Game Over** (con autopsia económica didáctica de los 2 turnos consecutivos).
  - Vista de **Victoria (Turno 10 Completado)** con boleta de calificaciones macroeconómicas y Score final.
- [x] **4.4.3. Consola de Auditoría Macroeconómica y Diagnóstico de Bugs (Inspector Beta-Testing):**
  - Widget en Sidebar que audita en vivo:
    - Error contable exacto $|Y - (C + I + G + NX)| < 10^{-12}$.
    - Desglose analítico de demanda agregada ($C, I_{\text{priv}}, G_c, I_g, X, M_{\text{imp}}, NX$).
    - Desglose fiscal (Recaudación, subsidios, intereses, déficit primario, déficit total, deuda acumulada).
    - Contadores de persistencia de Game Over (`consecutive_danger_turns`).
    - Nivel de credibilidad endógena $\theta_t \in [0.40, 0.80]$ y bonos Taylor / fiscal activos.
    - Condición Marshall-Lerner ($\epsilon_x + \epsilon_m > 1$).

---

## FASE 5: Suite de Pruebas Automatizadas y Calibración de Jugabilidad a 10 Turnos (`tests_simple/`)

### 5.1. Pruebas de Identidad Macroeconómica y Núcleo (`tests_simple/test_core_identity.py`)
- [x] **5.1.1. Identidad Contable Absoluta:**
  - Ejecutar 1,000 combinaciones aleatorias de las 8 palancas y verificar:
    $$|Y_t - (C_t + I_{\text{priv},t} + G_t + NX_t)| < 10^{-12}$$
- [x] **5.1.2. Normalización de Precios en $T=0$:**
  - Verificar que en el estado base $E=10.0, P^*=1.0 \implies P_{\text{local}}=1.00$ y $q=1.00$.
- [x] **5.1.3. Signos de Transmisión Económica:**
  - Probar que $G_c \uparrow \implies Y \uparrow, \text{Déficit} \uparrow$.
  - Probar que $I_g \uparrow \implies Y \uparrow, Y_{\text{pot, futuro}} \uparrow, I_{\text{priv}} \uparrow$.
  - Probar que $r_{\text{ref}} \uparrow \implies I_{\text{priv}} \downarrow, KA \uparrow, \pi \downarrow$.
  - Probar que $\tau \uparrow \implies M_{\text{imp}} \downarrow, P_{\text{local}} \uparrow, \pi \uparrow$.
  - Probar que $s_x \uparrow \implies X \uparrow, \text{Déficit} \uparrow$.

### 5.2. Pruebas del Blindaje Anti-Bucle y Game Over (`tests_simple/test_game_over_shields.py`)
- [x] **5.2.1. Test de Inmunidad en Período de Gracia:**
  - Forzar políticas destructivas extremas en Turnos 1 y 2 (ej. $r_{\text{ref}} = 30\%, G_c = 35$) y comprobar que **nunca** se declara Game Over en T1 o T2.
- [x] **5.2.2. Test de la Regla de 2 Turnos Consecutivos:**
  - Forzar superación de umbral crítico en T3: comprobar que se emite Alerta Roja pero **no** Game Over.
  - Si en T4 se corrige: comprobar que se desactiva la alerta y el juego continúa.
  - Si en T4 se repite: comprobar que se declara Game Over con la causa exacta.

### 5.3. Pruebas de Jugabilidad a 10 Turnos de los 4 Escenarios (`tests_simple/test_scenarios_playability_10_turns.py`)
- [x] **5.3.1. Jugabilidad Completa Corea del Sur (1985):**
  - Simular los 10 turnos aplicando la receta histórica recomendada ($I_g \in [9, 12], s_x \in [4\%, 6\%], r_{\text{ref}} \approx 7\%$).
  - Verificar que alcanza el Turno 10 con éxito, reservas crecientes y Score $> 75$.
- [x] **5.3.2. Jugabilidad Completa Chile (2000–2005):**
  - Simular los 10 turnos aplicando política contracíclica (estímulo en T3-T4 ante desaceleración, ahorro y rebaja arancelaria en T6-T9 durante superciclo).
  - Verificar que alcanza el Turno 10 con éxito, inflación anclada en $3\%$ y Score $> 80$.
- [x] **5.3.3. Jugabilidad Completa México (1994–1995):**
  - Simular los 10 turnos aplicando la estabilización de emergencia (transición a régimen flexible / devaluación y subida de TPM en T1-T2, recorte de $G_c$, posterior impulso exportador con $s_x$).
  - **Comprobar explícitamente que NO colapsa por crisis de reservas en T3** y que culmina los 10 turnos con Score aprobatorio.
- [x] **5.3.4. Jugabilidad Completa Bolivia (1982–1985):**
  - Simular los 10 turnos aplicando la terapia del D.S. 21060 (recorte de $G_c$ de 22 a 14, reforma tributaria subiendo $t_c$ al 16% y $t_k$ al 10%, tasa real positiva y desinflación).
  - **Comprobar explícitamente que la credibilidad sube a $0.80$, la inflación se desploma de 24% a $<7\%$ en 3 turnos** y el juego llega al Turno 10 con plena reactivación económica.

### 5.4. Pruebas de Serialización y Frontend (`tests_simple/test_serialization.py`)
- [x] **5.4.1. Test de Guardado y Carga JSON:**
  - Jugar 4 turnos aleatorios, exportar a diccionario JSON, inicializar un nuevo `StateManager.from_dict()`, y verificar que todos los atributos, listas y snapshots son idénticos bit a bit.
- [x] **5.4.2. Test de Integración de Componentes UI:**
  - Verificar que todas las funciones de renderizado de UI aceptan el nuevo formato de 8 palancas y 4 tabs sin excepciones ni advertencias de Streamlit.
