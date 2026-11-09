# 📋 Checklist de Tareas V1.3 — Realismo Macroeconómico y Experiencia Educativa
> **Especificación:** [`v1_3_enhancements_spec.md`](file:///c:/Ingenieria%20Financiera/Semester%20I-2026/Open%20Macroeconomics/Simulador%20Macroeconomico/specs_simple/v1_3_enhancements_spec.md)  
> **Estado:** Listo para Ejecución  

---

## FASE A: Realismo en Motor Macroeconómico (`engine_simple/`)

- [x] **A.1: Piso Estructural de Deuda Soberana y Fondo Soberano (FSE):**
  - Modificar `engine_simple/dynamics.py::compute_fiscal_balance`:
    - Evitar que la deuda pública caiga a $0.0$; fijar piso técnico de bonos soberanos para liquidez del mercado financiero: $B_{\text{min}} = 0.10 \cdot \text{PIB Nominal}$.
    - Asignar todo superávit fiscal excedente por debajo del piso de deuda a acumulación de activos en Reservas / Fondo Soberano.
- [x] **A.2: Calificación Crediticia Multidimensional (Rating Realista S&P/Moody's):**
  - Modificar `engine_simple/dynamics.py::compute_sovereign_risk`:
    - Evaluar 3 pilares ponderados: Sostenibilidad de Deuda (50%), Estabilidad de Precios/Inflación (30%), Empleo y Crecimiento (20%).
    - Asegurar que un país con alta inflación o desempleo no reciba calificación AAA/AA aunque su deuda sea baja.
- [x] **A.3: Calibración y Cooldown de Eventos Exógenos:**
  - Modificar `engine_simple/events.py`:
    - Acotar la magnitud de los shocks aleatorios (deltas moderados en $r^*, P^*, Y_{\text{pot}}$).
    - Implementar ventana de cooldown (mínimo 2 turnos entre eventos graves).
    - Asegurar que los eventos aleatorios se procesen en el ciclo interno y NO dependan de botones manuales en la barra lateral.
- [x] **A.4: Clasificación Analítica Rigurosa de Cuadrantes Salter-Swan:**
  - Modificar `engine_simple/core.py::compute_salter_swan`:
    - Corregir el mapeo exacto de las 4 zonas:
      - Zona I: Inflación + Superávit ($q > q_{IB}$ y $q > q_{EB}$).
      - Zona II: Desempleo + Superávit ($q < q_{IB}$ y $q > q_{EB}$).
      - Zona III: Desempleo + Déficit ($q < q_{IB}$ y $q < q_{EB}$).
      - Zona IV: Inflación + Déficit ($q > q_{IB}$ y $q < q_{EB}$).

---

## FASE B: Renovación Didáctica de Gráficos (`ui_simple/charts_panel.py`)

- [x] **B.1: Rediseño Canónico de Tab 2 — Diagrama Salter-Swan:**
  - Graficar curvas IB (pendiente negativa) y EB (pendiente positiva) con escalas visuales proporcionales y derivación macroeconómica.
  - Sombreado coloreado de los 4 cuadrantes con transparencia y etiquetas textuales claras.
  - Marcador de posición actual y trazado de la trayectoria histórica del país turno a turno.
  - Botón de ayuda `help` explícito explicando cómo leer el diagrama.
- [x] **B.2: Rediseño de Tab 1 — Modelo IS-LM-BP:**
  - Reformular la curva LM/MP bajo el enfoque monetario moderno (tasa de interés fijada por el Banco Central).
  - Graficar con línea punteada el equilibrio del turno anterior vs proyección de los sliders actuales para mostrar pedagógicamente los desplazamientos.
  - Botón de ayuda `help` detallando el significado de cada curva.
- [x] **B.3: Expansión de Tab 4 — Evolución Temporal:**
  - Agregar panel gráfico de **Balance Fiscal (% del PIB)** con barras de superávit (verde) y déficit (rojo).
  - Agregar panel gráfico de **Balanza de Pagos** desglosando Cuenta Corriente ($NX$) y Flujos de Capital ($KA$).

---

## FASE C: Experiencia de Usuario, Modales Emergentes y Asesoría (`ui_simple/`)

- [x] **C.1: Ergonomía de Controles, Nomenclatura y Botones Help (`controls_panel.py`):**
  - Renombrar `TPM (r_ref %)` a `🏦 Tasa de Interés del Banco Central (TPM %)`.
  - Agregar textos de ayuda `help="..."` explícitos, claros y didácticos a las 8 palancas explicando su canal de transmisión económico.
  - Añadir micro-badges informativos bajo los sliders.
  - Eliminar cualquier botón manual de choque del panel izquierdo.
- [x] **C.2: Ventana Emergente Modal para Choques Exógenos (`main_layout.py`):**
  - Implementar modal emergente interactivo (`@st.dialog`) al activarse un evento histórico o aleatorio.
  - Desplegar titular periodístico, tabla de impactos cuantitativos, recomendación del gabinete y el botón único: `"Continuar gobernando 🏛️"`.
- [x] **C.3: Rediseño Visual y Tipografía de Asesores de Gabinete (`explanation_panel.py` y `styles.py`):**
  - Aumentar tamaño de fuente y contraste en toda la columna derecha para máxima legibilidad.
  - Tarjetas ministeriales con bordes distintivos llamativos (Banco Central en azul, Hacienda en dorado/ámbar, Trabajo/Comercio en verde).
  - Incorporar banner superior parpadeante `"⚠️ ADVERTENCIA CRÍTICA PARA EL MINISTRO"` si algún KPI entra en tensión.

---

## FASE D: Verificación Automatizada y Validación de No-Regresión

- [x] **D.1: Verificación de Identidad y Suite Existente:**
  - Ejecutar `python -m pytest tests_simple/ -v`.
  - Garantizar que todas las pruebas pasen con 100% de éxito (57 de 57 pruebas superadas).
- [x] **D.2: Pruebas Específicas de las Nuevas Características:**
  - Crear `tests_simple/test_v1_3_enhancements.py` para validar:
    - Piso de deuda ($B \ge 0.10 \cdot \text{PIB Nominal}$).
    - Acumulación de excedentes en reservas/fondo soberano.
    - Calificación multidimensional (pérdida de grado de inversión por inflación o desempleo).
    - Asignación canónica de cuadrantes de Salter-Swan.
    - Período de gracia, cooldown de 2 turnos y estructura del modal interactivo.
