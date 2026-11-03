# 🏛️ ESPECIFICACIÓN TÉCNICA V1.3: MEJORAS DE REALISMO MACROECONÓMICO Y EXPERIENCIA EDUCATIVA
> **Proyecto:** The Economic War Room — Edición Educativa (V1.3 SIMPLE)  
> **Fecha:** Noviembre 2026  
> **Estado:** Propuesta de Diseño Aprobada para Implementación  

---

## 1. Motivación y Diagnóstico Post-Prueba Manual

Tras las pruebas de jugabilidad manual de la Versión 1.2, se confirmó la **total solidez algebraica** (error contable $< 10^{-12}$, cero solvers iterativos, superación garantizada de los 4 escenarios en 10 turnos). Sin embargo, se identificaron seis áreas clave de mejora didáctica y realismo económico:

1. **Claridad de Controles y Nombres:** El término `Tasa de Política Monetaria (TPM r_ref %)` resulta poco intuitivo para estudiantes iniciales; debe renombrarse a `Tasa de Interés del Banco Central (TPM %)`. Los botones de acción requieren mejor jerarquía visual y tooltips explicativos.
2. **Gráficos Teóricos (IS-LM-BP y Salter-Swan):** Requieren mayor fidelidad conceptual y dinamismo pedagógico:
   - **IS-LM-BP:** Debe reflejar la regla de política monetaria moderna (tasa horizontal/Taylor) y mostrar visualmente los desplazamientos provocados por los sliders.
   - **Salter-Swan:** Las curvas IB y EB deben derivarse con pendientes visibles respecto a la absorción real y el PIB potencial dinámico, con zonas didácticas sombreadas y el punto del país claramente trazado.
3. **Visibilidad y Jerarquía de Asesores de Gabinete:** La columna derecha requiere tipografía de alto contraste y tarjetas ministeriales con llamada de atención destacada (*Bancos Centrales, Hacienda, Comercio*) con semáforos de advertencia inmediata.
4. **Choques Exógenos con Ventanas Emergentes (Pop-ups):** Los eventos programados y aleatorios deben desplegarse como un diálogo emergente modal (`st.dialog`) con crónica periodística, impacto cuantitativo acotado y ventana de cooldown (sin shocks consecutivos destructivos).
5. **Realismo en Dinámica de Deuda, Reservas y Calificación Soberana:**
   - **Piso Estructural de Deuda / Fondo Soberano:** La deuda no puede caer a $0$. En la realidad, los gobiernos mantienen bonos soberanos para dar liquidez al sistema financiero (piso del $10\%-12\%$ del PIB); los superávits adicionales se acumulan en un **Fondo Soberano de Estabilización** o Reservas.
   - **Calificación Crediticia Multidimensional:** El rating no puede depender solo de la deuda. Un país con inflación $> 20\%$ o desempleo $> 15\%$ no puede tener grado de inversión (`AAA` o `AA`), reflejando la metodología de S&P, Moody's y Fitch.
6. **Evolución Temporal Enriquecida:** Incorporar gráficos explícitos de **Déficit/Superávit Fiscal (% del PIB)** y **Balanza de Pagos ($NX$ y $KA$)** para que el estudiante entienda la causa raíz de la evolución de la deuda y las reservas.

---

## 2. Catálogo de Mejoras por Módulo

### 2.1. Nomenclatura y Ergonomía de Controles (`ui_simple/controls_panel.py`)
- Renombrar la palanca monetaria a:  
  **`🏦 Tasa de Interés del Banco Central (TPM %)`** (con tooltip: *"Tasa de referencia para préstamos interbancarios. Subirla encarece el crédito y frena la inflación; bajarla estimula el consumo y la inversión"*).
- Incorporar badges con micro-explicaciones bajo cada slider (ej. *"Expansivo"*, *"Neutral"*, *"Contractivo"*).
- Botón principal de avance de turno con diseño visual más prominente y mensaje del turno entrante (`"Avanzar al Turno t+1 ⏩"`).

### 2.2. Ventanas Emergentes para Eventos Macroeconómicos (`ui_simple/` y `engine_simple/`)
- Implementar diálogo modal Streamlit (`@st.dialog("🚨 EVENTO MACROECONÓMICO: COMUNICADO OFICIAL")`):
  - Título con emoji institucional y crónica periodística.
  - Tabla de impacto cuantitativo del shock (ej. *"Tasa externa $r^*$: $+1.5\%$ | Demanda externa $X_0$: $-3.0$"*).
  - Dictamen preventivo de los asesores antes de que el alumno tome decisiones.
- **Calibración de Shocks Aleatorios:**
  - *Boom de commodities:* $+5\%$ temporal en $P^*$.
  - *Alza de tasas de la Fed:* $+150$ bps en $r^*$ (acotado, no destructivo).
  - *Sequía / Shock climático:* $-2\%$ en PIB potencial temporal.
  - *Cooldown garantizado:* Mínimo 2 turnos de pausa entre shocks exógenos graves.

### 2.3. Renovación Didáctica de Gráficos (`ui_simple/charts_panel.py`)

#### A. Modelo IS-LM-BP
- **Enfoque Monetario Moderno:** Curva MP/LM como tasa fijada por el Banco Central (línea horizontal/leve pendiente positiva) en lugar de una LM clásica fija de dinero en especie.
- Curva IS calculada con el multiplicador ampliado $k_m$ y componentes de gasto.
- Curva BP con pendiente positiva moderada por movilidad de capitales $f$.
- **Visualización de Desplazamiento:** Dibuja en línea tenue punteada la posición del turno anterior vs la posición proyectada por los sliders actuales, permitiendo al alumno ver hacia dónde empuja la curva IS su política fiscal.

#### B. Diagrama Salter-Swan
- **Eje X:** Absorción Doméstica $A = C + I_{\text{priv}} + G$.
- **Eje Y:** Tipo de Cambio Real $q = (E \cdot P^*) / P_{\text{local}}$.
- **Curva IB (Balance Interno):** $A + NX(q, Y_{\text{pot}}) = Y_{\text{pot}} \implies$ pendiente negativa calculada dinámicamente según la capacidad productiva del turno.
- **Curva EB (Balance Externo):** $NX(q, A) = 0 \implies$ pendiente positiva calculada según la propensión a importar y elasticidad de exportaciones.
- **Zonas Sombreadas:** Cuatro cuadrantes didácticos coloreados con transparencia (Zona I: Verde ámbar, Zona II: Azul, Zona III: Rojo alerta, Zona IV: Púrpura).

#### C. Tab 4 — Evolución Temporal con Finanzas Públicas y Balanza de Pagos
- Incorporar 2 nuevos paneles temporales:
  1. **Balance Fiscal:** Barras bicolores de Déficit/Superávit Total (% del PIB) turno a turno.
  2. **Balanza de Pagos y Reservas:** Evolución de Exportaciones Netas ($NX$), Flujos de Capital ($KA$) y variación de Reservas ($R$).

### 2.4. Realismo en Deuda Soberana y Calificación Crediticia (`engine_simple/dynamics.py`)

#### A. Piso Estructural de Deuda y Fondo Soberano
- En economías con superávits fiscales continuos (ej. Corea del Sur o Chile en superciclo), la deuda pública bruta no cae a $0.0$, sino que se estabiliza en un piso de liquidez de mercado:
  $$B_t = \max(B_{\text{min}}, \; B_{t-1} + \text{Déficit}_t) \quad \text{con } B_{\text{min}} = 0.10 \cdot \text{PIB Nominal}_t$$
- Todo superávit fiscal que exceda la amortización de deuda por debajo de $B_{\text{min}}$ se acumula automáticamente en el **Fondo Soberano de Estabilización (FSE)** o en Reservas del Banco Central:
  $$\text{Si } \text{Déficit}_t < 0 \text{ y } B_t \le B_{\text{min}} \implies \Delta R_t = |\text{Déficit}_t|$$

#### B. Calificación Soberana Multidimensional (Metodología S&P / Moody's)
El Rating Soberano se calcula mediante una matriz de 3 factores ponderados:
1. **Ratio Deuda / PIB Nominal ($50\%$ peso):**
   - $< 30\% \to$ Puntaje 10; $< 60\% \to$ Puntaje 7; $< 90\% \to$ Puntaje 4; $> 130\% \to$ Puntaje 1.
2. **Estabilidad de Precios / Inflación ($30\%$ peso):**
   - $|\pi - 3\%| \le 2\% \to$ Puntaje 10; $\le 5\% \to$ Puntaje 7; $\le 15\% \to$ Puntaje 4; $> 20\% \to$ Puntaje 1.
3. **Salud del Mercado Laboral y Crecimiento ($20\%$ peso):**
   - $U \le U_n + 1\% \to$ Puntaje 10; $U \le U_n + 4\% \to$ Puntaje 6; $U > 15\% \to$ Puntaje 2.
- **Escalera Final Integrada:**
  - $[9.0, 10.0] \to \text{AAA}$ | $[8.0, 8.9] \to \text{AA}$ | $[6.5, 7.9] \to \text{A}$ | $[5.0, 6.4] \to \text{BBB}$ | $[3.5, 4.9] \to \text{BB}$ | $[2.0, 3.4] \to \text{B}$ | $[1.0, 1.9] \to \text{CCC/D}$.

### 2.5. Rediseño Visual de Asesores de Gabinete (`ui_simple/explanation_panel.py`)
- Incrementar tamaño y contraste de tipografía en toda la columna derecha.
- Tarjetas con bordes luminosos y banners de rol ministerial:
  - 🏛️ **Banco Central:** Enfoque en tasa real, anclaje de expectativas y trilema.
  - 💼 **Ministerio de Hacienda:** Enfoque en balance estructural, deuda y sostenibilidad.
  - 📈 **Ministerio de Comercio y Trabajo:** Enfoque en empleo, competitividad cambiaria y exportaciones.
- Sección `"⚠️ ADVERTENCIA CRÍTICA DEL TURNO"` resaltada en amarillo/rojo si algún KPI se desvía en más de 2 sigmas.

---

## 3. Garantías de Consistencia y No Regresión

1. **Invarianza de Identidad Nacional:** En todas las modificaciones, $|Y - (C+I+G+NX)| < 10^{-12}$ se mantiene inquebrantable.
2. **Cero Solvers Iterativos:** Todas las curvas y ecuaciones continúan calculándose en forma cerrada analítica directa.
3. **Retrocompatibilidad Total:** La suite de pruebas de Fase 5 (`pytest tests_simple/ -v`) continuará pasando con 100% de éxito.
