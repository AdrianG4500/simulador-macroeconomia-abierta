# Explicación de la Implementación Técnica del Simulador

Este documento describe la arquitectura de software, las herramientas de programación y las librerías científicas utilizadas para construir el simulador **"The Economic War Room" (Versión 2.1)**, así como un guión para una presentación técnica de 3 a 4 minutos.

---

## 1. Arquitectura y Stack Tecnológico

El simulador está escrito completamente en **Python 3.12** utilizando una arquitectura desacoplada en tres capas con un flujo de información unidireccional y estricto.

```
[ Capa de Presentación (UI) ] ── (Streamlit 1.35 + Plotly 5.22)
            │
            ▼
[ Orquestador de Estado ] ───── (StateManager / session_state)
            │
            ▼
[ Motor Matemático Puro ] ────── (NumPy 1.26 + SciPy Optimize)
```

### 1.1. Las Tres Capas de Arquitectura

1. **Capa de Presentación (UI / Dashboard):**
   * Desarrollada con **Streamlit 1.35.0**, que permite construir interfaces reactivas de alto rendimiento en Python sin necesidad de JavaScript/HTML complejo.
   * La UI es estrictamente de "solo lectura" (renderiza el estado actual de la partida guardado en el `session_state` de Streamlit) y no interactúa directamente con las ecuaciones.
2. **Orquestador de Estado (`StateManager`):**
   * Encapsula las reglas del juego turno por turno (gestión de los 10 semestres, transiciones de régimen, verificación de condiciones de *Game Over* y cálculo del score de aprobación popular).
3. **Motor Matemático Puro (`core_v2.py` y `dynamics_v2.py`):**
   * Colección de **funciones puras** (sin efectos secundarios) encargadas de resolver las ecuaciones de equilibrio macroeconómico ($IS-LM-BP$), las dinámicas sectoriales (Salter-Swan) y la evolución intertemporal.

---

### 1.2. Herramientas y Librerías Científicas Utilizadas

* **Librería de UI:** `streamlit` (v1.35.0) para estructurar el panel en tres sectores (Sidebar de controles, centro telemétrico y gabinete derecho) e inyectar hojas de estilo CSS dinámicas (*Executive vs. Strategy Mode*).
* **Solvers y Álgebra Lineal:**
  * **SciPy (`scipy.optimize`):** Utiliza solvers no lineales acotados (`least_squares` y `fsolve`) para resolver la circularidad del tipo de cambio flexible ($E \to P_{local} \to M_{real} \to Y \to NX \to E$).
  * **NumPy (v1.26.4):** Emplea álgebra matricial (`np.linalg.solve`) para resolver de forma instantánea el equilibrio de tipo de cambio fijo (sistema lineal 2x2).
* **Visualización Dinámica:** `plotly` (v5.22.0) para renderizar gráficas interactivas y componentes avanzados (odómetros, triángulo del trilema en coordenadas ternarias, diagramas de fase, y radar de reelección).
* **Gestión de Datos y Escenarios:**
  * **Pandas (v2.2.2) y PyArrow (v16.1.0):** Para cargar, estructurar y serializar el historial de turnos y los escenarios preconfigurados (ficheros Parquet).
* **Persistencia y Rendimiento:**
  * **Joblib (v1.4.2):** Sistema de memoria caché para evitar recalcular equilibrios idénticos durante los refrescos de pantalla (*reruns*) de Streamlit.
  * **Python-Dotenv (v1.0.1):** Carga de parámetros económicos por defecto desde un archivo `.env`.
* **Motor de Reportes:** **FPDF2 (v2.7.9)** para generar reportes en PDF de alta fidelidad académica que consolidan los resultados de la gestión del jugador al finalizar los 10 turnos.
* **Análisis Avanzado:** **Scikit-Learn (v1.4.2)** para análisis de sensibilidad de parámetros y simulaciones estocásticas de Monte Carlo.

---

## 2. Guión Explicativo de la Implementación Técnica (Duración: 3-4 minutos)

### [0:00 - 0:45] Introducción y Arquitectura de Tres Capas
* **Visual:** Estructura de archivos de la carpeta del proyecto en pantalla. Animación que destaca el flujo unidireccional: `main.py` -> `ui/dashboard_main.py` -> `engine/state_manager_v2.py` -> `engine/core_v2.py`.
* **Locutor (en off):**
  > *"Detrás de la interfaz del simulador macroeconómico existe una arquitectura de software robusta, diseñada bajo el principio de separación de responsabilidades y flujo unidireccional estricto. El sistema se organiza en tres capas independientes escritas en Python. En primer lugar, la capa de presentación que lee el estado del juego. En segundo lugar, el orquestador o State Manager, que controla las transiciones de turnos y reglas de fin de partida. Y finalmente, el motor matemático puro, compuesto por funciones deterministas encargadas de resolver el equilibrio general de la economía."*

### [0:45 - 1:40] El Stack Tecnológico: UI y Visualización Interactiva
* **Visual:** Grabación de pantalla navegando por el simulador, alternando el interruptor de tema (*Executive Bloomberg* claro a *Strategy* oscuro). Zoom a los gráficos interactivos de Plotly (el radar, el odómetro de déficit fiscal, la curva IS-LM-BP).
* **Locutor (en off):**
  > *"Para la interfaz de usuario elegimos Streamlit 1.35, lo que nos permite construir una aplicación web sumamente responsiva y dinámica en Python nativo. Inyectamos hojas de estilo CSS personalizadas para crear dos interfaces inmersivas: el modo Ejecutivo Bloomberg y el modo de Estrategia Militar. Toda la telemetría gráfica corre bajo Plotly 5.22, generando componentes interactivos avanzados de grado financiero: desde odómetros de riesgo fiscal hasta coordenadas ternarias para ilustrar el Trilema de la economía abierta. El procesamiento y manipulación de datos históricos se estructuran con Pandas en formato de tablas analíticas y de auditoría ex-post."*

### [1:40 - 2:40] Solvers Matemáticos y Computación Científica
* **Visual:** Fragmento de código en pantalla de la función `eq_flexible_v2` mostrando la llamada a `scipy.optimize.least_squares` con sus cotas físicas (`bounds`). Transición a un diagrama que ilustra la resolución instantánea en tipo de cambio fijo usando `numpy.linalg.solve`.
* **Locutor (en off):**
  > *"El verdadero motor de cálculo se apoya en librerías científicas de Python. Bajo tipo de cambio fijo, el sistema macroeconómico es lineal y se resuelve de forma instantánea usando el álgebra matricial de NumPy. Sin embargo, bajo tipo de cambio flexible, la interacción circular entre tipo de cambio, precios y oferta monetaria introduce una fuerte no linealidad. Para resolver esto sin inestabilidades, implementamos los resolvedores no lineales acotados de SciPy, específicamente mínimos cuadrados optimizados. Imponemos cotas físicas para evitar soluciones absurdas, como PIB negativo o tasas bajo cero. Además, para garantizar una experiencia web fluida, utilizamos Joblib para cachear y almacenar en memoria los equilibrios ya resueltos."*

### [2:40 - 3:30] Escenarios, Sensibilidad y Reportes PDF Académicos
* **Visual:** El cursor selecciona el botón "Exportar PDF" al terminar una partida. Se visualiza un archivo PDF académico de 5 páginas con tablas de auditoría y gráficas vectoriales. Se muestra brevemente la consola ejecutando un análisis de Monte Carlo.
* **Locutor (en off):**
  > *"Para la gestión de los escenarios de crisis, tales como 'Credit Crunch' o 'Stagflation', el sistema almacena las calibraciones estructurales serializadas mediante formato Parquet con PyArrow. El análisis de sensibilidad y los shocks probabilísticos de Monte Carlo se ejecutan utilizando algoritmos lineales de Scikit-Learn. Finalmente, al concluir la gestión de diez turnos, la librería FPDF2 compila automáticamente un informe en PDF de rigor académico, conteniendo tablas vectoriales de balance fiscal e inspección de consistencia macroeconómica. En definitiva, es un stack robusto de ciencia de datos aplicado a la simulación y educación económica."*

* **Visual:** Logotipo del proyecto y URL de Streamlit Cloud.
