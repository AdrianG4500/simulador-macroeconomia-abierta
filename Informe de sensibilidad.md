# Informe de Sensibilidad Macroeconómica
## Diagnóstico de Anomalías Estructurales, Errores Numéricos y Soluciones del Motor V3.2

Este informe analiza en detalle los resultados de las simulaciones estocásticas de Monte Carlo y el barrido de rejilla (*Grid Search*) realizados sobre los 4 escenarios de política económica en el **Simulador Macroeconómico V3.2**. El objetivo es aislar los errores numéricos del solucionador y las inconsistencias de teoría macroeconómica que impiden la supervivencia a largo plazo (Turno 10) de los programas de estabilización.

---

## 1. Resumen Ejecutivo de Supervivencia y Causas de Colapso

El arnés de estrés sometió al motor a 40 iteraciones estocásticas con perturbaciones en la demanda agregada ($\pm 3\%$ en $c_0, I_0$) y variables internacionales ($\pm 2\%$ en $r^*, P^*$), evaluando la efectividad de las palancas bajo rangos de control viables: Gasto Corriente $G_c \in [8.0, 24.0]$, Inversión Pública $I_g \in [8.0, 24.0]$, Tasa Impositiva $t_c \in [0.08, 0.25]$, Encaje Legal $\theta \in [0.05, 0.35]$ y Arancel $\tau \in [0.00, 0.15]$.

### Tabla Comparativa de Estrés por Escenario
| Escenario Histórico | Supervivencia T2 (%) | Supervivencia T10 (%) | Turno Promedio de Caída | Principal Causa de Game Over |
| :--- | :---: | :---: | :---: | :--- |
| **Estabilidad Chilena** (`Economia_Saludable`) | 77.50% | 0.00% | 3.27 | Colapso de Aprobación ($85\%$) / Depresión ($15\%$) |
| **Milagro Coreano** (`tiger_asia`) | 72.50% | 22.50% | 3.61 | Colapso de Aprobación ($60\%$) / Depresión ($17.5\%$) |
| **Crisis de Deuda** (`latam_crisis`) | 0.00% | 0.00% | 1.88 | Colapso de Aprobación ($77.5\%$) / Depresión ($12.5\%$) |
| **Stagflation Boliviana** (`death_spiral`) | 0.00% | 0.00% | 1.00 | Hiperinflación ($97.5\%$) |

### Conclusiones Principales:
1. **La supervivencia de largo plazo es prácticamente nula (0%) en tres de los cuatro escenarios.** Incluso en la economía estructuralmente sana (`Economia_Saludable`), el juego colapsa a la mitad del camino.
2. **Existe un sesgo contractivo severo en el sistema.** Las combinaciones de políticas de ajuste fiscal/monetario necesarias para equilibrar el sector externo destruyen la aprobación presidencial debido a la alta sensibilidad del score al desempleo y a la desviación de la inflación.

---

## 2. Diagnóstico Detallado de Errores y Anomalías Macroeconómicas

### A. La Fricción Monetaria de Fisher Desbocada (Espiral Deflacionaria)
El error conceptual más grave en la transmisión monetaria se manifiesta cuando la economía entra en deflación bajo un esquema de **tipo de cambio fijo o crawling peg**.

#### Mecanismo del Fallo:
De acuerdo con la ecuación de Fisher:
$$r_{real} = r_{nominal} - \pi$$

En el motor V3.2, la tasa doméstica nominal de equilibrio $r$ está anclada por la paridad descubierta de intereses (UIP) ajustada por prima de riesgo soberano ($\rho$) y movilidad imperfecta de capitales ($f$):
$$r_{BP} = r^* + \Delta E^e + \rho - \frac{NX}{f}$$

Cuando la economía sufre un shock contractivo, la tasa de inflación $\pi$ se vuelve negativa (deflación). Dado que el tipo de cambio está fijo, $r_{nominal}$ no puede caer libremente porque debe defender la paridad (mantener las reservas $R$). Como consecuencia:
1. Al volverse $\pi$ negativa (ej. $-10.52\%$ en `latam_crisis`), el término $-\pi$ se convierte en positivo ($+10.52\%$).
2. Esto dispara la tasa de interés real de Fisher ($r_{real}$) a niveles absurdos de dos dígitos: **72.70%** promedio en `latam_crisis` (Turno 2) y **25.77%** en `tiger_asia` (Turno 1).
3. Una tasa de interés real del $72.70\%$ encarece brutalmente el crédito y contrae de forma masiva la inversión privada ($I_{inv}$ cae y arrastra a $Y$ de $102.50$ a $68.59$ en `latam_crisis`, una contracción del **33.1%**).
4. La fuerte contracción del PIB reduce la demanda, lo que intensifica la deflación del siguiente período, alimentando una espiral recesiva e imparable (asfixia monetaria endógena).

---

### B. Descalce de Consistencia Stock-Flujo Fiscal (Stock-Flow Consistency - SFC)
La identidad macroeconómica contable fundamental exige que la acumulación de deuda ($B_t - B_{t-1}$) sea exactamente igual al déficit financiero del gobierno central.

#### Mecanismo del Fallo:
En `engine/dynamics_v2.py`, la deuda soberana se actualiza mediante:
```python
B_new = max(B_min, min(B_max, B_prev + deficit))
```
Donde el límite superior de endeudamiento está acotado por:
```python
B_max = 3.0 * max(Y, 100.0)
```
En situaciones de colapso de actividad (como el escenario `death_spiral` donde el PIB real $Y$ cae al piso de soporte de $10.0$ debido al descalabro hiperinflacionario), el déficit fiscal explota a niveles de **302.77 unidades** en algunas iteraciones por el desplome de recaudación y el alza en los intereses soberanos.
1. `B_prev + deficit` resulta en $65.0 + 302.77 = 367.77$ unidades de deuda esperada.
2. Sin embargo, la función trunca la deuda soberana a `B_max = 300.0` para evitar una explosión infinita de deuda.
3. El motor actualiza el estado de la deuda soberana con `state["B"] = 300.0`, pero **mantiene el registro del déficit original de 302.77**.
4. Esto introduce un descalce contable severo: **se pierden 67.78 unidades de flujo financiero** que no se tradujeron en deuda ni fueron financiadas por emisión (emisión de dinero o señoreaje). Esto destruye la consistencia stock-flujo (SFC) de la economía de forma ficticia.

---

### C. Rigidez Matemático-Conductual y Sesgo Contractivo del Score Presidencial
La función de utilidad del votante (`calc_period_score_v2`) penaliza simétricamente las desviaciones de la inflación y del desempleo respecto a sus metas históricas.

#### Elasticidades del Votante:
- **Desempleo:** Resta exactamente **5.00 puntos** en la aprobación por cada **1%** que la tasa de desempleo cíclica supere el 4% (NAIRU de referencia).
- **Inflación/Deflación:** Resta exactamente **3.33 puntos** por cada **1%** de desviación de la inflación con respecto a la meta de estabilidad del 3%.

#### Mecanismo del Fallo:
Cuando el jugador intenta corregir un desequilibrio de balanza de pagos (ej. fuga de reservas $R$ en `latam_crisis`), la teoría de Mundell-Fleming exige una contracción de la demanda agregada mediante alza de impuestos ($t_c$) o recorte de gasto corriente ($G_c$). Esto genera de forma endógena:
1. Una caída temporal del PIB y un aumento del desempleo cíclico (Okun).
2. Deflación temporal por la reducción de la brecha de producto (Phillips).
3. **El colapso del Score:** Si el desempleo sube del 5% al 10% y la inflación cae al $-2\%$ (deflación), la aprobación presidencial sufre una penalización acumulada de:
   $$\text{Penalización U} = (10\% - 4\%) \times 5.0 = 30.0\text{ puntos}$$
   $$\text{Penalización }\pi = | -2\% - 3\% | \times 3.33 = 16.65\text{ puntos}$$
   Junto con el impacto recesivo directo sobre el PIB, el score cae por debajo del umbral de gobernabilidad ($Score < 10$) en apenas 2 turnos. El votante penaliza simultáneamente los tres canales del ajuste, haciendo imposible la supervivencia política a largo plazo de cualquier programa económico serio.

---

### D. Hiperinflación Crónica e Inercia Aguda en `death_spiral`
En la *Stagflation Boliviana*, la tasa de supervivencia es del **0.00% en el Turno 1**, con inflaciones promedio que se disparan al **424.60%** anual.

#### Mecanismo del Fallo:
1. El escenario se inicializa con una expectativa inercial extremadamente alta ($\pi^e_0 = 14.0\%$).
2. Para representar los hábitos del consumidor, el motor calcula el consumo autónomo dinámico efectivo mediante inercia de consumo rezagado con un coeficiente $\lambda_h = 0.7435$:
   $$c0_{eff} = \lambda_h \cdot C_{prev} + (1 - \lambda_h) \cdot c_0$$
   Dado que el consumo en el Turno 0 ($C_{prev}$) es muy elevado debido a la distorsión inflacionaria inicial, $c0_{eff}$ se arrastra hacia valores gigantescos en el Turno 1 ($129.81$ unidades frente al valor base de $6.00$).
3. Este exceso de consumo nominal inercial infla artificialmente la absorción interna en el solver, impidiendo que el PIB real retorne a su nivel potencial.
4. El solver responde forzando una inflación geométrica de tres dígitos para cerrar el mercado de bienes, lo que activa el límite de Game Over por hiperinflación de forma inmediata en el Turno 1.

---

## 3. Propuestas de Solución Técnica e Ingeniería de Software

Para subsanar las deficiencias del motor macroeconómico V3.2 y permitir un entorno de juego retador pero físicamente coherente y ganable, se proponen las siguientes refactorizaciones de código:

### Solución 1: Suavizado de la Tasa Real ante Deflaciones (Fricción de Fisher)
Para evitar que una deflación transitoria genere tasas de interés reales destructivas de más del 70%, se debe modificar el cálculo de la tasa real que afecta a las decisiones de inversión privada en `engine/core_v2.py`.

#### Implementación propuesta:
En lugar de utilizar la inflación contemporánea $\pi_t$, la inversión privada debe reaccionar a la **inflación esperada de mediano plazo** ($\pi^e_{t+1}$), la cual es mucho más estable y está anclada por la credibilidad de la política económica:
```python
# En engine/core_v2.py (dentro de eq_fixed_v2 y eq_flexible_v2)
# Reemplazar la tasa real implícita instantánea por una tasa real esperada suavizada:
pi_expectativa_anclada = 0.6 * pi_e + 0.4 * max(-0.02, pi_t) # Acotar la deflación esperada al -2%
r_real_suavizada = r - pi_expectativa_anclada * 100.0
I_inv = sp["I0"] + delta_I0 - sp["b"] * r_real_suavizada - rho_k * t_k
```

---

### Solución 2: Consistencia Contable Stock-Flujo con Señoeraje y Arrears (SFC)
Para corregir la discrepancia fiscal cuando la deuda alcanza su techo máximo `B_max`, se propone forzar la consistencia del flujo en `engine/dynamics_v2.py`. El exceso de déficit que no puede ser financiado con emisión de deuda nueva debe traducirse en **financiamiento monetario (señoreaje)** o en **atrasos de pago (default técnico)**, afectando las variables nominales correspondientes.

#### Implementación propuesta:
```python
# En engine/dynamics_v2.py (dentro de compute_fiscal_balance)
B_new_raw = B_prev + deficit
B_new = max(B_min, min(B_max, B_new_raw))

# Si la deuda supera el techo legal B_max, el excedente es monetizado o entra en mora:
financiamiento_monetario_extra = 0.0
gasto_impago_arrears = 0.0

if B_new_raw > B_max:
    brecha_financiamiento = B_new_raw - B_max
    # El 60% se financia con señoreaje (emisión monetaria inorgánica, eleva pi_0)
    financiamiento_monetario_extra = 0.60 * brecha_financiamiento
    # El 40% entra en mora (ajuste recesivo forzoso del gasto público efectivo)
    gasto_impago_arrears = 0.40 * brecha_financiamiento

# El déficit efectivo acumulado en deuda se recalcula para mantener SFC estricto:
deficit_financiado = B_new - B_prev
# Retornar las nuevas variables en el diccionario para su impacto inflacionario posterior:
return FiscalBalanceResult({
    "recaudacion": round(recaudacion, 6),
    "gasto": round(gasto - gasto_impago_arrears, 6), # El gasto real cae por default
    "intereses": round(intereses, 6),
    "deficit": round(deficit_financiado, 6), # Coherencia SFC perfecta
    "B_new": round(B_new, 6),
    "seigniorage_shock": round(financiamiento_monetario_extra, 6)
})
```
*Nota: El `seigniorage_shock` debe ser consumido en `state_manager_v2.py` para sumar una penalización transitoria a `pi_0` en la curva de Phillips, encareciendo la inflación endógenamente si el gobierno abusa del señoreaje.*

---

### Solución 3: Flexibilización y No-Linealidad en el Score Presidencial
Para evitar que un ajuste ordenado sea penalizado de forma destructiva y simétrica, se debe reformar la función `calc_period_score_v2` en `config/scoring_v2.py`.

#### Implementación propuesta:
1. **Piso de Tolerancia (Deadband):** Desviaciones de inflación de hasta $\pm 2\%$ de la meta no deben penalizarse de forma lineal.
2. **Asimetría Inflación/Deflación:** La deflación moderada (ej. hasta $-2\%$) debe penalizarse con una elasticidad menor (1.00 punto por 1%) que la inflación (3.33 puntos por 1%), ya que representa el costo necesario de una consolidación externa.
3. **Ponderación por Turnos:** La penalización por desempleo debe atenuarse en los turnos 1 a 3 si el gobierno está ganando reservas internacionales (demostrando éxito en el ajuste externo).

```python
# En config/scoring_v2.py (dentro de calc_period_score_v2)
# Asimetría y no-linealidad en la penalización de inflación
desviacion_pi = pi - 0.03
if abs(desviacion_pi) < 0.02:
    penalty_pi = 0.0 # Margen de tolerancia de 2 puntos porcentuales
else:
    if desviacion_pi < 0:
        penalty_pi = abs(desviacion_pi) * 150.0 # Menor peso a la deflación
    else:
        penalty_pi = desviacion_pi * 333.0 # Alta penalidad a la inflación
```

---

### Solución 4: Anclaje de Expectativas en `death_spiral` vía Consolidación Creíble
En el escenario de hiperinflación, las expectativas no deben ser puramente adaptativas inerciales. Si el jugador implementa una política fiscal restrictiva agresiva (reducción drástica de $G_c$ y aumento de $t_c$), la credibilidad debe reducir la expectativa de inflación de forma no-lineal, desarmando la inercia del consumo por hábitos.

#### Implementación propuesta:
```python
# En engine/state_manager_v2.py (dentro de step_forward)
# Si el balance primario es superavitario o hay un fuerte ajuste fiscal:
balance_primario = snap["recaudacion"] - snap["G"]
if balance_primario > 0.0:
    # La inercia del consumo se debilita porque los agentes confían en el ajuste:
    sp["lambda_h"] = max(0.10, sp["lambda_h"] * 0.50)
    # Las expectativas inflacionarias se anclan rápidamente:
    pi_e_new = 0.3 * pi_e_new + 0.7 * sp.get("pi_target", 0.03)
```

Este conjunto de modificaciones estabilizará los solvers matemáticos, eliminará los descalces contables de stock-flujo y ofrecerá una curva de aprendizaje justa y consistente con la macroeconomía cuantitativa moderna.
