# Explicación Macroeconómica y Paradigmas del Simulador

Este documento detalla las bases teóricas, ecuaciones clave y paradigmas económicos detrás del motor del simulador **"The Economic War Room" (Versión 2.1)**. También incluye un guión explicativo para un video de 3 a 4 minutos enfocado en el modelo macroeconómico.

---

## 1. Fundamentos y Paradigmas Macroeconómicos

El simulador combina pilares de la teoría macroeconómica clásica, keynesiana y estructuralista en un modelo dinámico consistente de **Consistencia Stock-Flujo (SFC)**.

```mermaid
graph TD
    subgraph Corto Plazo (Demanda)
        IS[Curva IS: Mercado de Bienes]
        LM[Curva LM: Mercado Monetario]
        BP[Curva BP: Paridad UIP y Balanza de Pagos]
        MF[Mundell-Fleming Ampliado] --> IS & LM & BP
    end
    subgraph Mediano Plazo (Oferta y Estructura)
        SS[Salter-Swan: Transables vs No Transables]
        OK[Okun No Lineal: Empleo]
        PH[Phillips Aceleradora: Inflación]
    end
    subgraph Dinámica de Stocks (Intertemporal)
        Debt[Bola de Nieve Fiscal: Deuda B]
        Res[Reservas Netas: R]
        Kg[Capital Público: K_g]
    end
    MF --> SS
    SS --> PH & OK
    PH & OK --> Debt & Res & Kg
    Debt & Res & Kg -->|Retroalimentación| MF
```

### 1.1. Corto Plazo: Modelo Mundell-Fleming Ampliado ($IS-LM-BP$)

El equilibrio de corto plazo determina simultáneamente el ingreso real ($Y$), la tasa de interés doméstica ($r$) y el tipo de cambio nominal ($E$, si es flexible) o la masa monetaria ($M$, si es fijo).

#### A. Curva IS (Demanda Agregada Desagregada)
La demanda agregada se determina por:
$$Y = k_m \cdot (A + \epsilon_{eff}(s_x) \cdot q - b \cdot (r - \pi^e))$$
Donde:
* **Multiplicador Keynesiano ($k_m$):** Incorpora impuestos proporcionales al ingreso ($t_c$) y aranceles a las importaciones ($\tau$):
  $$k_m = \frac{1}{1 - c_1(1-t_c) + m_1(1-\tau)}$$
* **Demanda Autónoma Neto-Sensible ($A$):**
  $$A = c_0(\lambda_h) + c_1 Tr + I_0 + \delta I_0 - \rho_k t_k + G_{total} + NX_0^{eff}$$
  * *Inercia de Consumo ($\lambda_h$):* El consumo autónomo depende del consumo del período anterior para reflejar hábitos persistentes.
  * *Efecto Desplazamiento ($\delta I_0$):* Modela la interacción de **Crowding-In** (inversión privada estimulada por el stock de capital público $K_g$) y **Crowding-Out** (inversión desplazada por la deuda soberana $B$):
    $$\delta I_0 = \psi_{ci} \ln\left(1 + \frac{K_g}{Y_{pot}}\right) - \psi_{co} \left(\frac{B}{Y_{pot}}\right)$$
  * *Impuesto Corporativo ($t_k$):* Desincentiva la inversión privada autónoma según el coeficiente $\rho_k$.

#### B. Curva LM (Paradigma Monetario Dual)
El mercado monetario sigue dos modos operativos según el diseño institucional:
1. **Control de Agregados Monetarios ($M$ exógeno):** La tasa de interés se equilibra endógenamente según:
   $$r = \frac{k \cdot Y - (M/P_{local})}{h}$$
2. **Metas de Tasa de Interés ($r_{ref}$ exógeno - Flexible):** El Banco Central fija la Tasa de Política Monetaria ($r_{ref}$) y acomoda de forma pasiva la oferta nominal de dinero ($M$) demandada por el mercado.
   * *Acomodación y Esterilización:* Bajo tipo de cambio fijo, $M$ es 100% pasivo para defender la paridad. Sin embargo, el jugador puede aplicar **Esterilización Monetaria ($\psi_s$)** mediante la emisión de bonos de estabilización para absorber el excedente de dinero y evitar que deprima las tasas.

#### C. Curva BP (Paridad de Tasas de Interés y Fuga de Capitales)
La tasa de interés de equilibrio externo incorpora la movilidad imperfecta de capitales y la prima de riesgo soberano ($\rho$):
$$r_{BP} = r^* + \Delta E^e + \rho - \frac{NX}{f_{eff}}$$
* **Cepo / Controles de Capital ($k_c$):** Afectan la movilidad de capitales efectiva. Si hay salidas de capital ($r < r_{UIP}$), los controles limitan la velocidad del flujo de divisas reduciendo el coeficiente $f$:
  $$f_{eff} = f \cdot (1 - k_c)$$
* **Elasticidades de Comercio (Condición Marshall-Lerner & J-Curve):** Una devaluación solo mejora el balance externo neto ($NX$) si se cumple la condición de Marshall-Lerner ($\epsilon_x + \epsilon_m > 1$). El motor implementa el efecto **J-Curve**: ante devaluaciones severas, en el primer turno las elasticidades caen drásticamente ($\epsilon_x \to 0.1, \epsilon_m \to 0.05$) deteriorando el saldo comercial antes de que las exportaciones reaccionen.

---

### 1.2. Mercado Laboral y Oferta: Leyes de Okun y Phillips No Lineales

Para evitar distorsiones matemáticas comunes en simuladores básicos (como desempleo negativo o inflaciones infinitas lineales), el motor adopta formulaciones no lineales.

#### A. Desempleo Asintótico (Okun No Lineal)
En fases recesivas (brecha de producto $gap < 0$), el desempleo responde de forma lineal. En fases de recalentamiento de demanda ($gap > 0$), el desempleo se comprime exponencialmente, aproximándose asintóticamente a un **piso friccional estructural ($U_{floor}$)**:
$$U = \begin{cases} 
  U_n - \gamma_{okun} \cdot gap & \text{si } gap \le 0 \\
  U_n \cdot \exp\left(-\frac{\gamma_{okun} \cdot gap}{U_n}\right) & \text{si } gap > 0 
\end{cases}$$

#### B. Curva de Phillips con Aceleración NAIRU
La tasa de inflación general ($\pi$) responde a las expectativas adaptativas de inflación ($\pi^e$), la brecha de producto, el impacto del traspaso cambiario (*pass-through* cambiario directo $\beta_{PT}$) y las tensiones del mercado laboral:
$$\pi = \pi^e + \alpha_{inf} \cdot gap + \beta_{PT} \frac{\Delta E}{E_{t-1}} + \alpha_{nonlinear} \left(\frac{U_n - U}{U}\right)^{1.5}$$
* *Aceleración NAIRU:* Si el desempleo ($U$) cae por debajo de su tasa natural ($U_n$), la escasez de mano de obra genera presiones salariales exponenciales que aceleran la inflación.
* *Anclaje de Expectativas:* Las expectativas de inflación se actualizan ponderando la inflación pasada con la meta del 3% fijada por el Banco Central:
  $$\pi^e_{t+1} = \theta \cdot 0.03 + (1 - \theta) \cdot \pi_t$$

---

### 1.3. Dinámica Cambiaria Sectorial: Salter-Swan y Enfermedad Holandesa

El motor divide el producto total ($Y$) en dos sectores según la relación de precios relativos $q_{int} = P_T / P_{NT}$:
* **Sector Transable ($Y_T$):** Compuesto por bienes exportables e importables. Su precio está anclado por el tipo de cambio efectivo y el arancel: $P_T = E_{eff} P^* (1 + \tau)$.
* **Sector No Transable ($Y_{NT}$):** Bienes locales (servicios, construcción). Su precio ($P_{NT}$) crece según la inflación interna del período anterior.

#### Enfermedad Holandesa (Dutch Disease)
Cuando ingresan divisas de forma masiva (ej. shocks de exportación o flujos financieros), se aprecia el tipo de cambio real ($q \downarrow$ o $q_{int} \downarrow$). Esto reduce la participación del sector transable doméstico ($Y_T \downarrow$) en favor del sector no transable ($Y_{NT} \uparrow$), destruyendo la base industrial exportadora a largo plazo.

---

### 1.4. Consistencia Stock-Flujo (SFC) y Finanzas Públicas

La acumulación de deudas y activos obedece a reglas de consistencia física:
* **Recaudación Impositiva Desagregada:**
  $$T_t = (t_c + t_k) Y_t + \tau \cdot M_{imp, t}$$
* **Sostenibilidad Fiscal y Prima de Riesgo:** La prima de riesgo país ($\rho$) se recalcula mediante un modelo de disparadores multidimensionales:
  1. *Deuda sobre PIB potencial ($B_{t-1} / Y_{pot}$):* Escalera de calificación crediticia de AAA a Default.
  2. *Carga del servicio de la deuda (Intereses / Recaudación):* Si supera el 30%, se añade una penalización a $\rho$.
  3. *Velocidad del deterioro fiscal:* Penalización adicional si el endeudamiento aumenta más de 10% del PIB en un solo turno.
* **Señoreaje de Emergencia y Default:** Si la deuda cruza el límite insostenible del 300% del PIB ($B_{max}$), el motor simula un colapso monetario (default y monetización): el 60% del déficit excedente se financia emitiendo dinero inorgánico (provocando hiperinflación) y el 40% entra en moratoria del gasto primario (*arrears*).

---

## 2. Guión Explicativo de la Teoría Macroeconómica (Duración: 3-4 minutos)

### [0:00 - 0:40] Introducción al Motor y Paradigmas Teóricos
* **Visual:** Diagrama del flujo general de información del simulador (el gráfico de flujo circular de la sección 1). Animación que destaca los tres niveles: Corto Plazo, Mediano Plazo, y Dinámicas de Stocks.
* **Locutor (en off):**
  > *"El motor detrás de 'The Economic War Room' no es una simple colección de ecuaciones lineales; es una síntesis matemática consistente de los paradigmas macroeconómicos fundamentales. El simulador unifica el corto plazo keynesiano del modelo Mundell-Fleming ampliado, el análisis sectorial de Salter-Swan de la escuela estructuralista, y las dinámicas de acumulación intertemporal de los modelos de Consistencia Stock-Flujo. Esta arquitectura permite modelar una economía abierta donde las decisiones de política en el mercado monetario y fiscal alteran permanentemente la estructura productiva y la solvencia intertemporal del país."*

### [0:40 - 1:30] La Demanda Agregada: Multiplicador Keynesiano y Efecto Desplazamiento
* **Visual:** Ecuación de la curva IS en pantalla con elementos resaltados de forma dinámica. Flechas mostrando cómo un aumento en la Inversión Pública ($I_g$) expande la demanda, pero un aumento en la deuda soberana ($B$) genera crowding-out financiero al desplazar la inversión privada.
* **Locutor (en off):**
  > *"Comencemos en el mercado de bienes. La curva IS determina la demanda agregada. El motor incorpora un multiplicador keynesiano ampliado por la propensión a importar y las distorsiones arancelarias. Pero la verdadera innovación intertemporal es el canal de inversión privada. Este responde a las tasas de interés reales y al efecto neto de desplazamiento. La inversión pública genera un efecto 'Crowding-In', expandiendo la productividad marginal a largo plazo. Sin embargo, si el gobierno se endeuda en exceso para financiar gasto corriente, se activa el 'Crowding-Out' o desplazamiento financiero, contrayendo la inversión del sector privado al encarecer el costo del crédito doméstico."*

### [1:30 - 2:25] La Estructura de Oferta y Trabajo: Okun y Phillips No Lineales
* **Visual:** Gráfico que muestra la curva de Phillips aceleradora y el comportamiento exponencial del desempleo de Okun ante brechas positivas de producto. Se destaca el umbral de la NAIRU y la zona del desempleo friccional estructural.
* **Locutor (en off):**
  > *"El mercado laboral y la oferta agregada están gobernados por leyes de comportamiento no lineales. La tasa de desempleo se modela bajo una formulación asintótica de la Ley de Okun, impidiendo tasas negativas y simulando la compresión exponencial del empleo cuando la economía opera sobre su potencial. Por su parte, la inflación responde a una curva de Phillips aumentada con expectativas adaptativas y pass-through cambiario directo. La escasez extrema de mano de obra cuando el desempleo cae por debajo de su tasa natural o NAIRU, genera presiones exponenciales sobre los salarios que aceleran rápidamente el nivel general de precios, reproduciendo con alta fidelidad las espirales de estanflación de las economías emergentes."*

### [2:25 - 3:15] Análisis Sectorial de Salter-Swan y Enfermedad Holandesa
* **Visual:** Diagrama sectorial de la división del PIB ($Y_T$ y $Y_{NT}$) y el gráfico de Salter-Swan. El punto de la economía se desplaza hacia la zona de apreciación cambiaria real, contrayendo el bloque del sector transable.
* **Locutor (en off):**
  > *"Para analizar la competitividad cambiaria y la estructura industrial, el motor implementa el modelo sectorial de Salter-Swan. Dividimos la economía en un sector transable, expuesto a la competencia internacional, y un sector no transable, guiado por la demanda interna. A través de esta mecánica, el simulador recrea la 'Enfermedad Holandesa'. Si un boom exportador de recursos naturales o una entrada masiva de capitales aprecian el tipo de cambio real, los precios locales suben por encima de la paridad, encareciendo los bienes transables domésticos. Esto destruye la competitividad externa, reduciendo la producción industrial exportadora y forzando una peligrosa dependencia de los servicios internos."*

### [3:15 - 3:45] Sostenibilidad SBF y Consistencia Stock-Flujo
* **Visual:** Fórmulas de la deuda soberana y la prima de riesgo país. Simulación del circuit breaker de señoreaje y moratoria al cruzar el límite del 300% del PIB.
* **Locutor (en off):**
  > *"Finalmente, el motor garantiza la consistencia física de la deuda y las reservas internacionales. La prima de riesgo país no responde solo a la ratio Deuda-PIB, sino también a la velocidad de endeudamiento y al peso del servicio de la deuda sobre los ingresos tributarios. Si el país alcanza el techo insostenible del trescientos por ciento del PIB, el motor simula el colapso financiero: un shock de señoreaje inorgánico que monetiza a la fuerza el déficit, provocando hiperinflación, y forzando una moratoria de pagos primarios. De esta forma, el simulador enseña que los límites fiscales son rigurosos y que toda deuda tiene un costo real sobre el crecimiento futuro."*

* **Visual:** Logotipo institucional de Ingeniería Financiera y créditos del simulador.
