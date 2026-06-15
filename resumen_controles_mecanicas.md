# Guía de Controles, Mecánicas y Guión del Simulador Macroeconómico

Este documento contiene un resumen detallado de los controles y las mecánicas del simulador **"The Economic War Room" (Versión 2.1)**, así como un guión explicativo diseñado para una presentación o video de 3 a 4 minutos.

---

## 1. Resumen de Controles y Mecánicas del Simulador

El **Economic War Room** es un simulador macroeconómico dinámico e intertemporal para una economía abierta. El usuario asume el rol de Ministro de Economía o Presidente del Banco Central a lo largo de un horizonte de **10 semestres (turnos)**, con el objetivo de mantener la estabilidad económica, la sostenibilidad fiscal y la aprobación popular.

### 1.1. Regímenes Cambiarios e Instrumentos de Política (Controles)

El simulador implementa el principio del **Trilema de la Economía Abierta**: el jugador no puede tener simultáneamente libre movilidad de capitales, política monetaria autónoma y tipo de cambio fijo. Por ello, la disponibilidad de los controles cambia dinámicamente según el régimen cambiario activo:

| Política / Instrumento | Símbolo | Tipo de Control | Comportamiento según Régimen Cambiario |
| :--- | :---: | :---: | :--- |
| **Gasto Corriente** | $G_c$ | Fiscal | **Siempre activo** ($0.0 - 40.0$). Financia el consumo público corriente. Estimula el PIB de corto plazo pero genera déficit. |
| **Inversión Pública** | $I_g$ | Fiscal | **Siempre activo** ($0.0 - 30.0$). Gasto de capital en infraestructura. Aumenta la demanda agregada hoy y expande el PIB Potencial ($Y_{pot}$) a futuro. |
| **Impuesto al Consumo** | $t_c$ | Fiscal | **Siempre activo** ($0\% - 50\%$). Reduce el ingreso disponible (y el multiplicador), frenando el PIB y la inflación, pero aumenta la recaudación fiscal. |
| **Impuesto Corporativo** | $t_k$ | Fiscal | **Siempre activo** ($0\% - 50\%$). Grava utilidades de empresas. Genera recaudación, pero desincentiva la inversión privada ($I$). |
| **Transferencias Directas** | $Tr$ | Fiscal | **Siempre activo** ($0.0 - 20.0$). Subsidios a hogares. Estimula el consumo privado autónomo de forma indirecta según la PMgC ($c_1$). |
| **Tipo de Cambio Nominal** | $E$ | Cambiario | **Fijo/Deslizante:** Activo ($1.0 - 30.0$). Devaluar ($\uparrow E$) mejora la competitividad cambiaria real ($q$) y la balanza comercial ($NX$), pero genera inflación por *pass-through*.<br>**Flexible:** Bloqueado (se determina endógenamente). |
| **Tasa de Deslizamiento** | $crawl$ | Cambiario | **Solo en Crawling Peg:** Activo ($0\% - 10\%$). Tasa a la cual la moneda se devalúa de forma programada y previsible en cada turno. |
| **Tasa de Política Monetaria** | $r_{ref}$ | Monetario | **Flexible:** Activo ($0\% - 25\%$). La TPM contrae la inversión (si aumenta) y atrae capitales financieros.<br>**Fijo/Deslizante:** Bloqueado y determinado por la paridad internacional ($r = r^* + \rho$). |
| **Encaje Legal Bancario** | $\theta$ | Monetario | **Siempre activo** ($0\% - 90\%$). Coeficiente de reservas obligatorio para bancos. Limita el multiplicador monetario secundario. |
| **Arancel a la Importación** | $\tau$ | Comercial | **Siempre activo** ($0\% - 50\%$). Gravamen aduanero. Reduce la propensión a importar y recauda fondos, pero eleva los precios domésticos. |
| **Subsidio a la Exportación**| $s_x$ | Comercial | **Siempre activo** ($0\% - 30\%$). Estímulo fiscal a exportadores. Mejora la balanza comercial ($NX$), financiado por el tesoro. |
| **Controles de Capital** | $k_c$ | Financiero | **Siempre activo** ($0\% - 90\%$). Restringe la libre movilidad de flujos financieros. Disminuye la fuga de divisas y amortigua la tasa de interés doméstica de shocks externos, pero penaliza la inversión extranjera directa. |

> [!NOTE]
> **Modo Fácil vs. Modo Difícil:** En el Modo Fácil, el jugador también tiene acceso a sliders estructurales (PMgC, PMgM, movilidad de capitales base, etc.) en la barra lateral para "calibrar" la economía en tiempo real con fines didácticos, además de herramientas de depuración técnica. En el Modo Difícil, estos parámetros están fijos y ocultos.

---

### 1.2. Mecánicas Macroeconómicas Clave (El Motor del Juego)

1. **Equilibrio IS-LM-BP Dinámico:**
   * En cada turno, el motor resuelve un sistema de ecuaciones simultáneas. Bajo tipo de cambio flexible, la circularidad de las variables (donde el tipo de cambio influye en los precios, la demanda de dinero y viceversa) se resuelve mediante un solucionador no lineal acotado en Python (`scipy.optimize.least_squares`).
2. **Dinámica Intertemporal de la Deuda:**
   * El déficit total se acumula como deuda pública soberana ($B$). La prima de riesgo país ($\rho$) se ajusta dinámicamente según la relación Deuda/PIB (con tramos desde Rating A hasta DEFAULT). Una mayor prima encarece el servicio de la deuda, acelerando una "bola de nieve" fiscal.
3. **Estructura Sectorial de Salter-Swan:**
   * El producto se divide entre el **Sector Transable** (sensible al comercio mundial) y el **Sector No Transable** (sensible a presiones domésticas de demanda). Si la economía se aprecia de forma real ($q_{int} \downarrow$), pierde competitividad y experimenta **Enfermedad Holandesa** (contracción del sector transable en favor del no transable).
4. **Flotación Sucia e Intervención Cambiaria:**
   * Si el jugador define bandas cambiarias bajo flotación sucia, el Banco Central intervendrá automáticamente quemando o acumulando Reservas Netas ($R$) para evitar desvíos extremos en el tipo de cambio.
5. **Inflación y Expectativas:**
   * La inflación general es impulsada por la brecha de producto (demanda), la devaluación nominal (*pass-through*) y las expectativas de inflación, las cuales son adaptativas (la inflación del período anterior influye en la actual).

---

### 1.3. Condiciones de Fin del Juego (Game Over)

El juego puede terminar abruptamente antes del semestre 10 si se cruzan los límites de tolerancia:
* **💀 Insolvencia Soberana:** Ratio de Deuda/PIB superior al **150%**.
* **💀 Hiperinflación Descontrolada:** Tasa de inflación superior al **30%**.
* **💀 Depresión Económica:** Brecha de PIB recesiva menor al **-15%** durante dos turnos consecutivos.
* **💀 Crisis de Balanza de Pagos:** Agotamiento total de Reservas Netas ($R \le 0$) bajo tipo de cambio fijo. Esto dispara un *circuit breaker* que fuerza el tipo de cambio flexible, deprecia la moneda un 20% de emergencia y desata una crisis inflacionaria.

---

## 2. Guión Explicativo del Simulador (Duración: 3-4 minutos)

*Este guión está redactado en español con indicaciones visuales y narrativas detalladas. Tiene una longitud aproximada de 500 palabras, ideal para una locución pausada de 3.5 minutos.*

### Ficha Técnica del Video
* **Tono:** Profesional, académico, estructurado y dinámico.
* **Música de fondo:** Tecnológica, tenue, de ritmo constante y corporativo.
* **Objetivo:** Explicar qué es el simulador, cómo se juega, qué variables controla el usuario y cómo interpretar las alertas.

---

### [0:00 - 0:30] Introducción y Contexto del Simulador
* **Visual:** Toma de pantalla completa mostrando la pantalla de Onboarding del simulador, el título principal *"The Economic War Room"* y la selección de escenarios (ej. *Bolivia 2024 Stagflation*, *Tiger Asia*). Se ve un cursor haciendo clic en "Comenzar Gestión".
* **Locutor (voz en off):**
  > *"Bienvenidos a 'The Economic War Room', un avanzado simulador macroeconómico intertemporal diseñado para experimentar, en tiempo real, los complejos desafíos de formular políticas en una economía abierta. Como ministros de economía o presidentes del banco central, su misión es gestionar la estabilidad de una nación a lo largo de un horizonte crítico de diez semestres. En este entorno, cada decisión fiscal, monetaria o cambiaria que tomen tendrá repercusiones inmediatas y acumulativas sobre el bienestar social, la inflación y la solvencia del país."*

### [0:30 - 1:20] El Panel de Control y el Trilema Cambiario
* **Visual:** Zoom al sector izquierdo del tablero (la barra lateral). El cursor se desplaza por los acordeones de "Política Fiscal", "Política Monetaria" y "Comercio Exterior". Se muestra cómo cambian los sliders activos al alternar el régimen cambiario de "Fijo" a "Flexible".
* **Locutor (voz en off):**
  > *"La interfaz se divide en tres áreas clave. En el panel izquierdo controlamos los instrumentos de política. Aquí radica el núcleo dinámico del juego: el Trilema de la Economía Abierta. Si eligen un régimen de tipo de cambio fijo, el tipo de cambio nominal se convierte en su instrumento de control y la oferta monetaria se ajusta de forma pasiva; la tasa de interés queda atada a la paridad internacional. En cambio, si liberan el tipo de cambio al régimen flexible, recuperan la autonomía de su política monetaria, permitiéndoles fijar activamente la Tasa de Interés de Referencia para contener la inflación o estimular la inversión privada."*

### [1:20 - 2:15] Visualización Analítica y Mecánicas Internas
* **Visual:** El video pasa a la sección central. Se muestran las tres pestañas telemétricas. Primero, en la pestaña de **Economía Real**, se hace un barrido del gráfico de **Salter-Swan** destacando las cuatro zonas (desempleo/inflación, superávit/déficit) y el punto dinámico del país. Luego, se pasa a la pestaña **Monetaria** mostrando la gráfica dinámica de las curvas **IS-LM-BP**.
* **Locutor (voz en off):**
  > *"En la sección central, el 'Tablero de Mando Soberano' ofrece una telemetría en tiempo real a través de seis indicadores clave con sus gráficos de evolución histórica. En la pestaña de Economía Real, el diagrama de Salter-Swan nos muestra si la economía sufre de Enfermedad Holandesa o desempleo estructural, analizando la balanza interna y externa según el tipo de cambio real. En la pestaña de Sector Monetario, las curvas IS-LM-BP se recalculan instantáneamente mediante solvers numéricos de Python, permitiéndonos ver gráficamente cómo un incremento del gasto público desplaza la curva IS, provocando presiones sobre las tasas de interés y la balanza de pagos."*

### [2:15 - 3:00] Sostenibilidad Fiscal, Shocks y Reglas de Game Over
* **Visual:** Se hace clic en la pestaña de **Sostenibilidad Fiscal**. Se muestran los dos odómetros de Reservas Netas y Déficit Fiscal, y el gráfico de la bola de nieve de la deuda. Aparece en pantalla un mensaje emergente de un evento aleatorio (ej. *"Shock de Precios de Commodities"* o *"Aumento de la Tasa de Interés de la Fed"*).
* **Locutor (voz en off):**
  > *"La tercera pestaña vigila la acumulación de stocks. El déficit fiscal acumulado alimenta la deuda soberana. Si esta deuda supera ciertos límites, la prima de riesgo país sube, encareciendo el financiamiento y arriesgando un default técnico. Pero cuidado: la economía está expuesta a shocks externos imprevisibles, como caídas en los precios de exportación o crisis de confianza. Si sus reservas netas caen a cero bajo tipo de cambio fijo, se disparará una crisis cambiaria obligando a una devaluación forzosa. Exceder una inflación del 30%, caer en una recesión severa prolongada o superar el 150% de deuda sobre PIB significará un Game Over inmediato."*

### [3:00 - 3:30] Cierre y Recomendación de Estrategia
* **Visual:** El presentador regresa a la vista general. Muestra la pantalla final de evaluación (Onboarding o Scorecard de fin de gestión) con la puntuación de bienestar y la Percepción Pública final. Se destaca el botón de reinicio y exportación de reportes PDF.
* **Locutor (voz en off):**
  > *"Para ganar la partida, el secreto está en la consistencia técnica y la previsibilidad. Utilicen la inversión pública para expandir la capacidad productiva del país, controlen el déficit primario mediante tasas impositivas equilibradas y adapten el régimen cambiario al tipo de shock que enfrente la nación. En resumen, 'The Economic War Room' es el laboratorio definitivo para comprender que, en macroeconomía, no existen soluciones mágicas, sino equilibrios intertemporales. ¿Están listos para asumir el mando y gobernar la economía? ¡Comiencen su gestión hoy mismo!"*

* **Visual:** Fundido a negro con el logo del proyecto o la dirección local del servidor (`http://localhost:8501`).
