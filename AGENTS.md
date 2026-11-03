# AGENTS.md — Directivas de Desarrollo, Control de Tokens y Reglas de Agente AI

Este documento establece las normas operativas, principios arquitectónicos, directivas anti-bucle y uso eficiente de recursos para cualquier agente de IA que trabaje en el **Simulador Macroeconómico (The Economic War Room - Edición Educativa)**.

---

## 1. Principios Fundamentales del Proyecto

1. **Garantía Incondicional de Identidad Macroeconómica**:
   En todo momento, la ecuación de contabilidad nacional debe cumplirse exactamente:
   $$Y = C + I + G + NX \quad (\text{error} < 10^{-12})$$
   Está **estrictamente prohibido** agregar parches de suavizado ad-hoc ($70/30$, $75/25$) o alterar $Y$ independientemente de sus componentes.

2. **Cero Solvers Numéricos Aproximados / Iterativos**:
   Todas las soluciones de equilibrio IS-LM-BP deben calcularse en **forma cerrada analítica (Closed-Form Analytical Solutions)**. No se permite el uso de `fsolve`, `least_squares` ni bucles `while` de optimización no lineal en el motor principal.

3. **Enfoque Monetario Moderno (Tasa de Interés)**:
   La política monetaria se opera mediante la **Tasa de Política Monetaria ($r_{ref}$)** y no mediante la oferta monetaria en especie ($M$). El dinero $M$ es una variable pasiva endógena.

4. **Transparencia Educativa y Didáctica**:
   El objetivo principal es la enseñanza. Todos los controles, métricas y resultados deben estar acompañados de explicaciones intuitivas en español llano y tooltips claros.

---

## 2. Prevención de Bucles, Soluciones Greedy y Detección de Bloqueos

1. **Regla de los 2 Intentos (Límite Estricto de Debugging)**:
   - Si un test, error de sintaxis o fallo de consistencia macroeconómica persiste tras **2 intentos de corrección**, el agente **DEBE DETENERSE INMEDIATAMENTE**.
   - Queda **estrictamente prohibido** entrar en bucles de prueba y error reiterados o probar combinaciones a ciegas.

2. **Prohibición Total de Soluciones Greedy / Parches Superficiales**:
   - **NUNCA** silenciar excepciones con bloques `try/except: pass` o retornos dummy.
   - **NUNCA** introducir constantes mágicas, multiplicadores de ajuste artificiales ($0.95$, $+2.0$) ni forzar variables para "hacer pasar" una prueba.
   - **NUNCA** comentar o debilitar las aserciones de prueba (`assert`) para ocultar un error.
   - Si un test falla, se debe corregir la causa raíz en la lógica matemática o de dominio, no maquillar el test.

3. **Protocolo de Escalamiento al Usuario**:
   Cuando el agente detecte un bucle, fallo recurrente o ambigüedad de diseño, debe detener la ejecución de herramientas y enviar al usuario un reporte limpio con la siguiente estructura:
   ```markdown
   ⚠️ DETECCIÓN DE BLOQUEO / NECESIDAD DE INTERVENCIÓN

   - **Problema / Error Exacto**: [Descripción precisa del traceback o fallo]
   - **Intentos Realizados**:
     1. [Primer intento y por qué no funcionó]
     2. [Segundo intento y resultado]
   - **Causa Raíz / Conflicto Detectado**: [Explicación técnica del obstáculo o inconsistencia]
   - **Opciones Sugeridas / Pregunta**: [Alternativas claras para continuar]
   ```

---

## 3. Eficiencia de Recursos y Gestión de Tokens

1. **Lecturas y Búsquedas Enfocadas**:
   - No inspeccionar carpetas ni archivos completos de forma masiva si se puede usar `grep_search` o ver un rango de líneas específico (`StartLine` / `EndLine`).
   - Evitar re-leer archivos que ya han sido leídos en la misma conversación a menos que hayan sufrido modificaciones.

2. **Ediciones Quirúrgicas de Código**:
   - Al modificar archivos existentes, realizar cambios incrementales y precisos con `replace_file_content` o `multi_replace_file_content`. No reescribir archivos enteros innecesariamente.

3. **Ejecución Directa y Análisis Sin Repetición**:
   - Nunca ejecutar el mismo comando de terminal con los mismos argumentos esperando un resultado diferente si la causa raíz no ha cambiado.
   - Analizar el log o traceback completo antes de proponer cualquier cambio en el código.

4. **Respuestas Concisas y Sin Redundancia**:
   - Proporcionar resúmenes claros, profesionales y directos. Evitar explicaciones teóricas extensas o felicitaciones que consuman tokens innecesarios cuando el usuario requiere código o decisiones operativas.

---

## 4. Organización del Proyecto y Convención de Directorios

- Toda la especificación del proyecto reside en `specs/`:
  - `specs/proposal.md`: El Por Qué, Alcance e Impacto.
  - `specs/design.md`: Arquitectura de 3 capas, Backend, Frontend y Estructura.
  - `specs/tasks.md`: Hojas de ruta por fases y tareas atómicas.
- El código simplificado vive aisladamente en:
  - `config_simple/`: Parámetros, escenarios y scoring.
  - `engine_simple/`: Motor matemático puro y orquestador.
  - `ui_simple/`: Componentes de interfaz Streamlit (Layout de 3 columnas).
  - `tests_simple/`: Pruebas de consistencia e integración.
  - `main_simple.py`: Punto de entrada principal.

---

## 5. Reglas de Codificación y Estilo

- **Estilo de Código**: Python 3.9+ con `from __future__ import annotations` y type annotations estrictas (`TypedDict`, `Optional`, `tuple`).
- **Funciones Puras en Engine**: Las funciones de `engine_simple/core.py` y `dynamics.py` **deben ser puras** (mismo input $\rightarrow$ mismo output, sin mutar objetos ni leer variables globales).
- **Separación de Capas**: `engine_simple` no debe importar nada de `ui_simple` ni de `streamlit`.
- **Commits y Saves**: Antes de marcar una tarea como completada en `specs/tasks.md`, se debe ejecutar la suite de pruebas `tests_simple/` y asegurar que no hay regresiones.

---

## 6. Guía de Ejecución de Pruebas

Para validar los cambios en el motor simplificado:
```bash
python -m pytest tests_simple/ -v
```
Todas las pruebas de identidad macroeconómica deben pasar con 100% de éxito.
