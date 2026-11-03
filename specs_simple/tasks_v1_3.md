# 📋 Checklist de Tareas V1.3 — Realismo Macroeconómico y Experiencia Educativa
> **Especificación:** [`v1_3_enhancements_spec.md`](file:///c:/Ingenieria%20Financiera/Semester%20I-2026/Open%20Macroeconomics/Simulador%20Macroeconomico/specs_simple/v1_3_enhancements_spec.md)  
> **Estado:** Listo para Ejecución  

---

## FASE A: Realismo en Motor Macroeconómico (`engine_simple/`)

- [ ] **A.1: Piso Estructural de Deuda Soberana y Fondo Soberano (FSE):**
  - Modificar `engine_simple/dynamics.py::compute_fiscal_balance`:
    - Evitar que $B$ caiga a $0.0$; fijar piso técnico de bonos soberanos para liquidez de mercado: $B_{\text{min}} = 0.10 \cdot \text{PIB Nominal}$.
    - Asignar el superávit excedente por debajo del piso de deuda al Fondo de Estabilización / Reservas Internacionales.
- [ ] **A.2: Calificación Crediticia Multidimensional (Rating Realista):**
  - Modificar `engine_simple/dynamics.py::compute_sovereign_risk`:
    - Evaluar 3 pilares: Sostenibilidad de Deuda (50%), Estabilidad de Inflación (30%), Empleo y Crecimiento (20%).
    - Asegurar que un país con alta inflación o desempleo no reciba calificación AAA/AA aunque su deuda sea baja.
- [ ] **A.3: Calibración y Cooldown de Eventos Exógenos:**
  - Modificar `engine_simple/events.py`:
    - Acotar la magnitud de los shocks aleatorios (deltas moderados en $r^*, P^*, Y_{\text{pot}}$).
    - Implementar ventana de cooldown (mínimo 2 turnos entre eventos graves).

---

## FASE B: Renovación Didáctica de Gráficos (`ui_simple/charts_panel.py`)

- [ ] **B.1: Rediseño de Tab 1 — Modelo IS-LM-BP:**
  - Reformular la curva LM/MP bajo el enfoque monetario moderno (regla de tasa del Banco Central con leve pendiente o línea horizontal).
  - Graficar con línea punteada el equilibrio del turno anterior vs proyección de los sliders actuales para mostrar el desplazamiento pedagógico.
- [ ] **B.2: Rediseño de Tab 2 — Diagrama Salter-Swan:**
  - Derivar curvas IB y EB con pendientes dinámicas proporcionales y visibles respecto a la absorción ($A$) y tipo de cambio real ($q$).
  - Añadir sombreado de cuadrantes coloreados (Zona I, II, III, IV) y marcador destacado del país con su trayectoria histórica.
- [ ] **B.3: Expansión de Tab 4 — Evolución Temporal:**
  - Agregar panel gráfico de **Balance Fiscal (% del PIB)** con barras de superávit (verde) y déficit (rojo).
  - Agregar panel gráfico de **Balanza de Pagos** desglosando Cuenta Corriente ($NX$) y Flujos de Capital ($KA$).

---

## FASE C: Experiencia de Usuario, Modales y Asesoría (`ui_simple/`)

- [ ] **C.1: Claridad de Controles y Nomenclatura (`controls_panel.py`):**
  - Renombrar `TPM (r_ref %)` a `🏦 Tasa de Interés del Banco Central (TPM %)`.
  - Añadir tooltips y micro-badges a los 8 sliders para guiar al estudiante sobre el sentido de su política.
  - Mejorar visibilidad del botón de avance de turno y diálogo de reforma cambiaria.
- [ ] **C.2: Ventana Emergente Modal para Choques Exógenos (`main_layout.py`):**
  - Implementar modal emergente interactivo (`@st.dialog`) al inicio del turno si se dispara un evento histórico o exógeno.
  - Desplegar titular periodístico, tabla de impactos cuantitativos y recomendaciones preliminares con botón de confirmación.
- [ ] **C.3: Rediseño Visual de Asesores de Gabinete (`explanation_panel.py` y `styles.py`):**
  - Aumentar tamaño de fuente y contraste en toda la columna derecha.
  - Diseñar tarjetas con bordes luminosos y distintivos de cada ministerio (Banco Central en azul, Hacienda en ámbar, Trabajo/Comercio en verde).
  - Destacar con banner de advertencia si algún indicador clave está fuera de equilibrio.

---

## FASE D: Verificación Automatizada y Validación de No-Regresión

- [ ] **D.1: Verificación de Identidad y Tests Existentes:**
  - Ejecutar `python -m pytest tests_simple/ -v`.
  - Garantizar que las 45 pruebas sigan pasando con 100% de éxito.
- [ ] **D.2: Pruebas Específicas de las Nuevas Características:**
  - Crear `tests_simple/test_v1_3_enhancements.py` para validar el piso de deuda, rating multidimensional y cooldown de eventos.
