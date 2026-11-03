# Proposal: Simulador Macroeconómico Simplificado (The Economic War Room - Edición Educativa)

## 1. Por Qué (Justificación y Antecedentes)

### 1.1 El Problema del Simulador Actual
El simulador macroeconómico en su versión avanzada (V3.0+) se convirtió en un sistema altamente complejo, orientado a la investigación académica avanzada y a la modelación empírica compleja. Cuenta con:
- **33 parámetros estructurales y 22 instrumentos de política.**
- **14 reformas matemáticas acumuladas y acopladas** (pass-through de 3 períodos, crowding-in/out logarítmico, NAIRU no-lineal, inercia de hábitos de consumo PIH, bandas PPP+UIP, etc.).
- **Parches de estabilidad numérica ad-hoc** (suavizados $70/30$ de tasa de interés, $75/25$ de PIB, damping en bucles de optimización no lineal).

Esta complejidad genera dos problemas fundamentales:
1. **Barrera de Aprendizaje**: Para estudiantes o personas con conocimientos superficiales de Macroeconomía Abierta, la cantidad de variables causa sobrecarga cognitiva. No logran aislar los conceptos clave (IS-LM-BP, Trilema de Mundell, Regímenes Cambiarios).
2. **Fragilidad Macroeconómica**: El apilamiento de parches dificulta garantizar identidades contables puras ($Y = C + I + G + NX$) y causa comportamientos inesperados ante combinaciones extremas de políticas.

### 1.2 La Solución Propuesta
Crear una **versión simplificada y rigurosa** del simulador, diseñada específicamente para fines didácticos. Esta versión:
- Sustituye la oferta monetaria en especie ($M$) por la **Tasa de Política Monetaria ($r_{ref}$)** como instrumento primario de política monetaria (enfoque moderno de Metas de Inflación).
- Se resuelve mediante **soluciones analíticas cerradas (Closed-Form)**, eliminando bucles numéricos inestables y parches ad-hoc.
- Ofrece una interfaz intuitiva con distribución clásica (Controles a la izquierda, KPIs al centro, Gráficos e Explicación/Gabinete a la derecha).

---

## 2. Alcance del Proyecto (Scope)

### 2.1 Incluido (In-Scope)
- **Motor Matemático Estructural Puro**:
  - Modelo Mundell-Fleming IS-LM-BP en forma analítica cerrada.
  - 3 Regímenes cambiarios: **Fijo**, **Flexible** y **Crawling Peg**.
  - Política monetaria por **Tasa de Interés ($r_{ref}$)** en lugar de agregados monetarios ($M$).
  - Cumplimiento estricto e incondicional de la identidad macroeconómica $Y = C + I + G + NX$.
  - Curva de Phillips lineal y Ley de Okun lineal.
  - Condición de Marshall-Lerner y efecto J-curve de 1 turno (simple).
  - Diagrama de Salter-Swan dinámico (4 zonas).
- **Frontend y UX**:
  - Layout clásico: Controles (Izquierda), KPIs + Gráficos (Centro), Explicación/Asesores (Derecha).
  - Explicación narrativa automática en cada turno ("¿Qué pasó y por qué?").
  - Tooltips educativos en cada slider y KPI.
  - Visualización del gráfico IS-LM-BP con flechas de desplazamiento.
- **Sistema de Juego**:
  - 4 Escenarios históricos calibrados (Milagro Coreano 1985, Chile 2005, México 1982, Bolivia 1982).
  - 5 Eventos macronarrativos (3 exógenos, 2 endógenos).
  - Sistema de Percepción Pública (Score 0-100) y Game Over.

### 2.2 Excluido (Out-of-Scope)
- Modos de esterilización monetaria compleja ($\psi_s$).
- Pass-through dinámico distribuido en 3 períodos (usar pass-through directo $\alpha_{PT}$).
- Modelación de capital público dinámico ($K_g$) y crowding-in/out logarítmico.
- Solvers numéricos no-lineales inestables (`fsolve` / `least_squares`).
- Impuestos corporativos separados ($t_k$); se consolida en una tasa impositiva única $t$.

---

## 3. Impacto Esperado

1. **Educativo**: Los estudiantes aprenderán la intuición detrás de la Macroeconomía Abierta sin frustrarse por la complejidad del software.
2. **Robustez Técnica**: Cero fallos por parches o divergencias de solvers; soluciones analíticas exactas y rápidas.
3. **Mantenibilidad**: Código limpio, modular y documentado, fácil de auditar por el docente supervisor.
