# 🔬 AUDITORÍA TÉCNICA Y MACROESTRUCTURAL PROFUNDA — V3.2

**Fecha:** 2026-05-31  
**Consorcio:** Principal Software Architect + Ph.D. Macroeconomía de Economía Abierta  
**Alcance:** Base de código completa del Simulador Macroeconómico Abierto V2.1  
**Estatus:** ⛔ DIAGNÓSTICO PURO — NO SE APLICARON CAMBIOS AL CÓDIGO

---

## 1. Diagnóstico del Sistema de Ecuaciones y Estabilidad Estática (`engine/core_v2.py`)

### 1.1 Consistencia IS-LM-BP — Análisis del Equilibrio Simultáneo

#### 🔴 FALLA CRÍTICA F-01: Elasticidad efectiva asimétrica entre `eq_fixed_v2` y `eq_flexible_v2` en modo legacy

En **modo legacy** (cuando `x0 = m0 = 0`), la elasticidad efectiva de las exportaciones netas se calcula de forma **diferente** en las dos funciones de equilibrio:

```python
# eq_fixed_v2, línea 549 (modo legacy):
eps_eff_sx = eps_eff * (1.0 + s_x)
# Esto solo incluye epsilon_x (o su transformación J-curve/M-L),
# NO incluye epsilon_m.

# eq_flexible_v2, línea 738 (modo legacy):
eps_eff_sx = eps_eff * (1.0 + s_x)
# IDÉNTICO — pero en modo desagregado la diferencia es:
eps_eff_sx = eps_x_eff * (1.0 + s_x) + eps_m_eff  # línea 539/728
```

**Problema teórico:** En modo legacy, `eps_eff_sx` solo captura la respuesta de las **exportaciones** al TCR, pero no la respuesta de las **importaciones**. La curva IS integrada al sistema 2×2 depende de `eps_eff_sx * q`, lo que implica que:

```
Y_IS = k_m * (A_auto + eps_eff_sx * q - b * r)
```

Para que el efecto del TCR sobre la demanda agregada sea correcto (condición Marshall-Lerner completa), `eps_eff_sx` debería ser `eps_x + eps_m` cuando M-L se cumple, pero en modo legacy solo toma `eps_x` (o `-(eps_m - eps_x)` si M-L no se cumple). La elasticidad de importaciones se pierde del lado de la IS. **La pendiente de la IS respecto a q está subestimada en modo legacy.**

Esto contrasta con el modo desagregado donde `eps_eff_sx = eps_x_eff * (1.0 + s_x) + eps_m_eff` sí captura ambos lados.

**Impacto:** La efectividad de la política cambiaria (devaluaciones) está artificialmente debilitada bajo los escenarios que usan el motor legacy. El jugador en `Economia_Saludable` obtiene una respuesta anémica de NX ante cambios en E.

#### 🔴 FALLA CRÍTICA F-02: La curva BP en el sistema 2×2 de `eq_fixed_v2` mezcla escalas de NX

En `eq_fixed_v2`, la fila BP del sistema 2×2 es:

```python
# Línea 556-559
rhs_bp = (
    r_star + delta_E_expected + rho
    - NX0_eff / f_eff
    - eps_eff_sx * q / f_eff
)

# Fila BP de la matriz: [-m1_eff / f_eff, 1.0]
# Con rhs = rhs_bp
```

Esto codifica la ecuación:
```
r = r* + ΔEe + ρ - (NX0_eff + eps_eff_sx * q - m1_eff * Y) / f_eff
```

Sin embargo, `compute_NX` calcula las exportaciones netas como:
```
NX = (NX0 + eps_x_eff * q * (1 + s_x)) - m1 * (1 - tau) * Y
```

El sistema 2×2 usa `eps_eff_sx * q` como el componente cambiario de NX. En modo legacy, `eps_eff_sx = eps_eff * (1 + s_x)`, donde `eps_eff = epsilon_x` (si M-L cumplida). Pero `compute_NX` usa `eps_x_eff * q * (1 + s_x)` para las exportaciones brutas y **resta** `eps_m_eff * q` de las importaciones. En el sistema 2×2 de `eq_fixed_v2` **la corrección `eps_m_eff * q` sobre las importaciones no aparece** en modo legacy. Hay una inconsistencia algebraica entre cómo se resuelve (Y, r) y cómo se recalcula NX post-equilibrio.

**Consecuencia:** La verificación de identidad `Y = C + I + G + NX` (líneas 604-611) arrojará violaciones no triviales cuando `eps_m > 0`, y de hecho el warning está presente para capturar exactamente esto. La raíz del problema es esta discrepancia.

#### 🟡 ADVERTENCIA F-03: `compute_autonomous_demand` incluye `-b*r` pero nunca se llama

La función `compute_autonomous_demand` (línea 88-136) incluye el término `-b*r` en su retorno:

```python
return c0 + c1 * Tr + I0 - rho_k * t_k - b * r + G_total + NX0
```

Pero ninguna parte de `eq_fixed_v2` ni `eq_flexible_v2` la invoca. En su lugar, `A_auto` se calcula inline (línea 552 y 741):

```python
A_auto = sp["c0"] + sp["c1"] * Tr + sp["I0"] - rho_k * t_k + G_total + NX0_eff
```

Note que aquí **no** se incluye `-b*r` porque `r` es endógena y se resuelve en el sistema lineal. La función `compute_autonomous_demand` es **código muerto** con una semántica incorrecta (mezcla componentes autónomos con el componente sensible a `r`). Se debe eliminar o refactorizar.

#### 🟡 ADVERTENCIA F-04: La curva IS standalone `is_curve_v2` es inconsistente con el solver

La función `is_curve_v2` (línea 380-416) calcula:

```python
r_IS = (A + epsilon_x * q - Y * slope_term) / b
```

Donde `slope_term = 1 - c1*(1-t) + m1`. Pero:
1. No incluye el arancel `tau` que modifica `m1` efectivo (debería ser `m1*(1-tau)`).
2. No incluye el subsidio a exportaciones `s_x` (debería ser `epsilon_x * (1+s_x)`).
3. El parámetro `A` recibido debería excluir NX0 (ya que `eps_x * q` lo captura parcialmente), pero la documentación es ambigua.

Esta función no se llama desde los solvers (se usa solo para visualización), pero si se usa para graficar la curva IS en `ui/charts_v2.py`, **la IS graficada no coincide con la IS resuelta por el motor**.

#### 🔴 FALLA CRÍTICA F-05: Escalado incompatible de `rho` entre `compute_sovereign_risk` y `solve_equilibrium_v2`

El flujo de `rho` es:

```
compute_sovereign_risk → devuelve rho ∈ [0.01, 0.30+]  (fracción decimal)
↓
state_manager_v2.step_forward, línea 619:
    rho=rho * 100.0   ← convierte a PORCENTAJE (1.0 → 100.0)
↓
solve_equilibrium_v2, línea 1132:
    rho = rho + risk_penalty * 100.0  ← SUMA risk_penalty * 100 a rho que ya está en %
↓
eq_fixed_v2, línea 454:
    rho: float = 0.0   ← recibe rho en PORCENTAJE
↓
compute_bp_curve, línea 377:
    r_BP = r_star + delta_E_expected + rho - NX/f
    ← rho aquí está en PORCENTAJE. r_star está en puntos % (e.g. 5.0)
    ← rho = 3.0 (= 300 bps) se suma a r_star = 5.0 → r_BP = 8.0 + ΔEe - NX/f
```

**Hay una doble multiplicación por 100:**
- `calibrate`, línea 198: `rho=rho_0 * 100.0` → correcto si `rho_0` es fracción y `r_star` es porcentaje.
- `solve_equilibrium_v2`, línea 1132: `rho = rho + risk_penalty * 100.0` → **`risk_penalty` son valores como 0.02, multiplicados por 100 = 2.0 puntos**. Pero `risk_penalty` ya fue calculada con exponenciales de `(G-30)`, `(M-120)`, etc. Veamos: si `G = 35`, `risk_penalty += 0.02 * (exp(0.4*5) - 1) = 0.02 * (e^2 - 1) ≈ 0.02 * 6.39 ≈ 0.128`. Luego `0.128 * 100 = 12.8` puntos porcentuales sumados a `rho`. Esto es **devastador** para la economía.

**Además**, la misma lógica de penalización exponencial se calcula **DOS VECES**: una en `compute_sovereign_risk` (líneas 503-516 de `dynamics_v2.py`) y otra en `solve_equilibrium_v2` (líneas 1111-1131 de `core_v2.py`). La primera afecta al `rho` base del rating; la segunda se suma **adicionalmente** como `risk_penalty * 100.0`. El jugador sufre una **doble penalización** por las mismas desviaciones de G y M.

**Impacto de juego:** Un gasto público de 35.0 (solo 5 unidades por encima del umbral de 30) genera una prima de riesgo de ~12.8% **adicional** sobre la tasa de interés, lo que colapsa la inversión privada y dispara el desempleo. Esto explica los colapsos prematuros reportados.

#### 🟡 ADVERTENCIA F-06: `velocity_penalty` divide M_real pero su efecto es asimétrico

En `eq_fixed_v2` (línea 582):
```python
M_real_eq = (sp["k"] * Y - sp["h"] * r) / velocity_penalty
```

En `eq_flexible_v2` (línea 749):
```python
M_real = (M / P_local) / velocity_penalty
```

En el solver fsolve del flexible (línea 782):
```python
eq_LM = r_s - (sp["k"] * Y_s - M_real_s / velocity_penalty) / sp["h"]
```

Nótese que en la línea 749 `M_real` ya fue dividido por `velocity_penalty`, pero en la línea 782 el `M_real_s` se calcula como `M / P_loc_s` (sin `velocity_penalty`), y luego se divide por `velocity_penalty` **dentro de la ecuación LM**. La doble aplicación no ocurre aquí solo porque la línea 766 calcula `M_real_s = M / P_loc_s` sin penalizar, y la penalización se aplica inline en la línea 782. **Esto es correcto pero confuso y frágil.** Si alguien refactoriza para usar `M_real` precalculado (como en la línea 749), se aplicaría la penalización dos veces.

En `eq_fixed_v2`, `velocity_penalty` reduce `M_real_eq` (la oferta monetaria endógena), lo que mecánicamente reduce la oferta de dinero que el banco central debe proveer. Esto **no tiene fundamento teórico** — bajo TC fijo, M es endógena y se acomoda para mantener `r = r_BP`. Castigar M_real bajo TC fijo es como decir que el banco central tiene menos capacidad de acomodar, pero el modelo asume acomodación perfecta.

---

### 1.2 Análisis de Signos Teóricos y Pendientes

#### ✅ CORRECTO: Pendiente IS

`slope_IS = -(1 - c1*(1-t) + m1) / b < 0` (IS decreciente en plano Y-r). Con parámetros default: `-(1 - 0.75*0.8 + 0.15) / 2.0 = -(1 - 0.6 + 0.15) / 2.0 = -0.55/2.0 = -0.275`. Signo correcto.

#### ✅ CORRECTO: Pendiente LM

`slope_LM = k / h > 0` (LM creciente). Con defaults: `0.5 / 2.0 = 0.25`. Correcto.

#### ✅ CORRECTO: Pendiente BP

`slope_BP = m1 / f > 0` (BP creciente con pendiente inversamente proporcional a f). Con defaults: `0.15 / 5.0 = 0.03`. Correcto — movilidad imperfecta implica BP con pendiente positiva.

#### ✅ CORRECTO: Condición Marshall-Lerner

`eps_x + eps_m = 1.16 + 1.015 = 2.175 > 1`. Cumplida en escenario base. En Bolivia_2024: `0.435 + 0.5075 = 0.9425 < 1`. No cumplida — correcto para un país exportador de commodities con baja elasticidad.

#### ✅ CORRECTO: Signo del multiplicador keynesiano

`k_m = 1 / (1 - 0.75*0.8 + 0.15) = 1/0.55 ≈ 1.818`. Positivo y > 1. Correcto.

### 1.3 Anomalías Numéricas y Riesgo de Singularidad

#### 🔴 FALLA F-07: Matriz 2×2 de `eq_fixed_v2` puede ser quasi-singular

La matriz del sistema 2×2 (línea 562-565):
```python
A_mat = np.array([
    [1.0,              sp["b"] * k_m],
    [-m1_eff / f_eff,  1.0          ],
])
```

El determinante es: `det = 1.0 + sp["b"] * k_m * m1_eff / f_eff`.

Con defaults: `det = 1 + 2.0 * 1.818 * 0.15*(1-0) / 5.0 = 1 + 0.109 = 1.109`. OK.

**Pero con controles de capital extremos** (`k_c = 0.99`): `f_eff = max(5.0 * 0.01, 1e-4) = 0.05`. Entonces: `det = 1 + 2.0 * 1.818 * 0.15 / 0.05 = 1 + 10.908 = 11.908`. Esto es estable.

El riesgo de singularidad se minimiza porque el `1.0` en la diagonal garantiza `det ≥ 1.0`. El fallback `except np.linalg.LinAlgError` (línea 574-577) es adecuado.

#### 🟡 ADVERTENCIA F-08: `fsolve` en `eq_flexible_v2` sin comprobación de convergencia

En el fallback de `eq_flexible_v2` (línea 800-803), `fsolve` se invoca sin verificar `info["fvec"]` (residuos). Si `fsolve` no converge, devuelve la última iteración como si fuera la solución. Los `max/min` bounds (línea 801-803) acotan los valores pero no detectan divergencia.

```python
sol_f = fsolve(system, [Y0, r0, E0])
Y_new = max(10.0, min(300.0, float(sol_f[0])))
r_new = max(0.1, min(100.0, float(sol_f[1])))
E_new = max(1e-4, min(100.0, float(sol_f[2])))
```

**El bound superior de Y = 300.0 es arbitrario** y podría truncar resultados legítimos bajo expansión fiscal extrema. Además, `r_new = max(0.1, ...)` impone un piso de 10 bps en la tasa de interés, lo que distorsiona escenarios de trampa de liquidez.

#### 🟡 ADVERTENCIA F-09: `least_squares` con bounds estáticos no adaptados al escenario

En `eq_flexible_v2` (líneas 788-796):
```python
lower_bounds = [10.0, 0.1, 0.1]
upper_bounds = [300.0, 100.0, 100.0]
```

El upper bound de `E = 100.0` es razonable, pero el upper bound de `r = 100.0` podría ser insuficiente si `rho` alcanza valores extremos por la doble penalización descrita en F-05 (rho de 30+ pp no es imposible). `Y = 300.0` es 3x el PIB potencial base, lo cual podría ser estrecho bajo booms exportadores con multiplicadores altos.

---

## 2. Parámetros Límite y Barreras de Falla (*Game Over Triggers*)

### 2.1 Calibración de Fronteras

#### 🔴 FALLA CRÍTICA F-10: Umbral de Reservas `R < 5.0` es demasiado estricto y se evalúa en régimen flexible

En `state_manager_v2.py`, línea 868:
```python
if R_new < 5.0:
    causes.append("Agotamiento crítico de Reservas...")
```

Este check se aplica **independientemente del régimen cambiario**. Bajo TC flexible, R solo cambia por flujos de capital endógenos (`capital_flows_eq`), no por intervención del banco central. Sin embargo, si NX es negativo y los flujos de capital son adversos, R puede caer por debajo de 5.0 incluso bajo flexible.

**Problema teórico:** Bajo TC flexible, las reservas no son relevantes para la sostenibilidad cambiaria (el tipo de cambio se ajusta). El game over por R < 5.0 no debería dispararse bajo flexible.

**Problema de gameplay:** El escenario Bolivia_2024 comienza con `R = 20.0` y déficit comercial (`NX0 = -3.0`). Bajo TC fijo, las reservas caen ~3-5 por turno por la intervención cambiaria. Con capital outflows adicionales, el jugador tiene **apenas 3-4 turnos** antes de que R < 5.0 dispare game over, sin darle suficiente tiempo para que una devaluación surta efecto (efecto J-curve).

#### 🔴 FALLA CRÍTICA F-11: `update_reserves` bajo flexible retorna `R_prev` sin cambios, pero `step_forward` aplica flujos de capital

En `dynamics_v2.py`, líneas 362-368:
```python
def update_reserves(...):
    if regime == "fixed":
        R_new = R_prev + NX + capital_flows
    else:
        R_new = R_prev  # ← R nunca cambia bajo flexible
```

Sin embargo, en `state_manager_v2.py`, línea 720:
```python
R_new = update_reserves(state["R"], eq["NX"], regime, capital_flows=capital_flows_eq)
```

Bajo flexible, `R_new = R_prev` siempre. **Las reservas no reflejan flujos de capital bajo flexible**, lo cual es incorrecto. En la realidad, bajo floating administrado o incluso floating puro, el banco central puede acumular reservas por flujos de capital sin intervenir en el mercado cambiario (e.g., recepción de préstamos del FMI, etc.). La simplificación es aceptable, pero genera una **inconsistencia con el game-over trigger F-10** que penaliza bajas reservas bajo flexible.

#### 🟡 ADVERTENCIA F-12: Umbral de inflación para game over (150%) es paradójicamente alto

El umbral `pi > 1.50` (150%) para hiperinflación game over es excesivamente generoso para un modelo semestral. 150% semestral equivale a ~525% anualizado compuesto. El umbral práctico debería estar más cerca de 50% semestral (~125% anual) para reflejar un escenario de hiperinflación clásica.

### 2.2 Zonas de Frustración vs. Realismo — Penalizaciones No Lineales

#### 🔴 FALLA CRÍTICA F-13: Las penalizaciones exponenciales están sobrecalibradas y se duplican

Como se documentó en F-05, la penalización por G > 30 se calcula **dos veces**:

1. **En `compute_sovereign_risk`** (`dynamics_v2.py`, líneas 504-507):
   ```python
   if G > 30.0:
       new_risk_penalty += 0.02 * (math.exp(0.4 * (G - 30.0)) - 1.0)
   ```

2. **En `solve_equilibrium_v2`** (`core_v2.py`, líneas 1115-1118):
   ```python
   if G_total > 30.0:
       new_risk_penalty += 0.02 * (math.exp(0.4 * (G_total - 30.0)) - 1.0)
   ```

Ambas usan la **misma fórmula idéntica**. La primera afecta al `rho` devuelto por `compute_sovereign_risk`, que se pasa como `rho * 100.0` al solver. La segunda calcula un `risk_penalty` adicional que luego se multiplica por 100 y se suma al mismo `rho`.

**Tabla de impacto combinado para G = 35:**
| Componente | Cálculo | Resultado |
|---|---|---|
| `compute_sovereign_risk` | `0.02 * (e^2 - 1) ≈ 0.128`, luego `rho += 0.128` | rho base = 0.03 + 0.128 = 0.158 |
| `state_manager` pasa | `rho * 100 = 15.8` | 15.8% sumado a r_BP |
| `solve_equilibrium_v2` | `0.02 * (e^2 - 1) ≈ 0.128`, luego `risk_penalty * 100 = 12.8` | **+12.8% adicional** |
| **Total prima sobre r_BP** | | **28.6 puntos porcentuales** |

Con `r_star = 5.0`, la tasa de equilibrio de la BP sería `r_BP ≈ 33.6%`. Esto **destruye** la inversión privada (`I_inv = I0 - b*r = 15 - 2*33.6 = -52.2`) y colapsa la economía instantáneamente.

**Veredicto:** Un gasto público de 35 (75% por encima de la media de 20, no es ni remotamente extremo) genera un colapso económico inevitable en 1-2 turnos. El espacio de soluciones del jugador está **asfixiado** por la doble penalización exponencial. Esto es la causa raíz de los game-over prematuros.

#### 🟡 ADVERTENCIA F-14: Inercia intertemporal 0.6/0.4 impide recuperación

La inercia `risk_penalty = 0.6 * prev_risk_penalty + 0.4 * new_risk_penalty` (línea 1129 de `core_v2.py` y línea 515 de `dynamics_v2.py`) hace que las penalizaciones se acumulen exponencialmente. Si el jugador corrige G de 35 a 20, la penalización tarda ~5 turnos en disiparse al 10% del pico, lo que en un juego de 10 turnos significa que un error en t=2 persigue al jugador hasta t=7.

#### 🟡 ADVERTENCIA F-15: El umbral de G < 5.0 penaliza gasto público bajo con una función convexa más agresiva

```python
elif G < 5.0:
    new_risk_penalty += 0.03 * (math.exp(0.5 * (5.0 - G)) - 1.0)
```

Con `G = 3.0`: `penalty = 0.03 * (e^1 - 1) ≈ 0.03 * 1.718 = 0.052`. Más tolerable que el caso G alto, pero el coeficiente 0.5 (vs. 0.4 para G alto) y el multiplicador 0.03 (vs. 0.02) significan que la penalización por austeridad es **más severa** que la penalización por gasto excesivo, lo cual es económicamente discutible.

---

## 3. Orquestación Temporal y Estado (`engine/state_manager_v2.py`)

### 3.1 Inercia y Leyes de Movimiento — Inspección de `step_forward`

#### 🔴 FALLA CRÍTICA F-16: Los eventos se evalúan con variables del turno ANTERIOR pero se aplican ANTES del equilibrio

En `step_forward`, Paso 1.5 (líneas 414-431):

```python
provisional_event_snap = {
    "t": t_new,
    "U": prev.get("U", 0.05),      # ← Variables del turno anterior
    "R": prev.get("R", 50.0),
    "Y": prev.get("Y", 100.0),
    ...
}
state["history"].append(provisional_event_snap)
events = evaluate_events(state, seed_int)
state["history"].pop()  # Remueve el snap provisional
```

Luego, los eventos se aplican **antes** del Paso 4 (equilibrio):

```python
for ev in events:
    apply_event_deltas(state, ev)
```

**Problema de timing:** Los eventos endógenos (e.g., `social_unrest` con trigger `U > 0.12`) se evalúan contra el desempleo del turno **anterior**. Si el jugador ya tomó medidas correctivas este turno (reduciendo G, etc.), esas medidas no se reflejan. El evento se dispara con información obsoleta.

**Más grave:** `apply_event_deltas` modifica `state["structural"]` (e.g., `c1 -= 0.05` por `social_unrest`) **antes** de que se construya la copia `sp = dict(state["structural"])` en la línea 457. Esto significa que el shock del evento SÍ afecta el equilibrio del turno actual, creando un acoplamiento correcto shock→equilibrio, pero la decisión de disparar el evento usa datos stale.

#### 🟡 ADVERTENCIA F-17: `Y_pot` se actualiza antes de aplicar shocks de eventos

En Paso 3 (línea 527-533):
```python
endogenous_shock = 0.0  # Siempre hardcodeado a 0
Y_pot = update_potential_output(
    state["Y_pot"], sp["g_pot"], endogenous_shock, I_g=pi.get("I_g", 0.0),
)
```

Sin embargo, eventos como `social_unrest` y `natural_disaster` modifican `Y_pot` via:
```python
state["Y_pot"] *= 0.95  # o *= 0.90
```

Estos se aplican en Paso 1.5 (antes del Paso 3). Luego Paso 3 calcula:
```python
Y_pot = state["Y_pot"] * (1 + g_pot + 0.0) + gamma * I_g
```

Esto significa que el shock de `natural_disaster` (multiplicativo 0.90) se aplica al `Y_pot` del estado, y luego se **vuelve a crecer** con `g_pot`. El orden es: `Y_pot_new = (Y_pot_old * 0.90) * (1.02) + 0.15 * I_g`. Es aceptable teóricamente (el shock reduce el nivel, el crecimiento opera sobre el nuevo nivel), pero `endogenous_shock` nunca se usa — es código muerto.

#### 🔴 FALLA CRÍTICA F-18: `G_needed` del desastre natural nunca se aplica al gasto

El evento `natural_disaster` setea `sp["G_needed"] = 5.0`, pero **ningún lugar del código** fuerza `G_c` a incrementarse en `G_needed`. La variable se almacena en `structural` pero nunca se consume. El "gasto forzoso de reconstrucción" que promete el evento no se materializa.

### 3.2 Trazabilidad de Contadores — Flujo de Scores y Métricas de Endgame

#### 🔴 FALLA F-19: Los scores de turnos no jugados pueden estar en cero

En `endgame_screen.py` (líneas 415-419):
```python
scores_played = state["scores"][1:] if len(state["scores"]) > 1 else state["scores"]
best_idx = int(np.argmax(scores_played)) + 1
best_score = float(np.max(scores_played))
worst_idx = int(np.argmin(scores_played)) + 1
worst_score = float(np.min(scores_played))
```

Si ocurre game_over en turno 2, `state["scores"]` tiene 3 elementos: `[score_0, score_1, score_2]`. `scores_played = [score_1, score_2]`. `best_idx` y `worst_idx` usan `+1` offset, lo que da turno 1-based correcto.

**Pero:** En `get_endgame_summary` (línea 1219):
```python
turn_scores = state["scores"][1:]
total_score = sum(turn_scores)
avg_score = total_score / max(len(turn_scores), 1)
```

`total_score` es la suma de **todos** los scores de turnos jugados (no promediados contra 10). Si el jugador juega 3 turnos con score 80, `total_score = 240`, `avg_score = 80`. Esto es correcto. Pero la UI muestra `total_score` como "SCORE ACUMULADO" (línea 499 de endgame_screen), y el jugador que sobrevive 10 turnos puede acumular ~800, mientras que el que colapsa en 3 acumula ~240. **No hay normalización por duración**, lo que hace que el score total sea inútil para comparaciones entre partidas de diferente longitud.

#### 🟡 ADVERTENCIA F-20: `delta_score` se calcula como diferencia puntual, no promedio

```python
def calc_endgame_delta_score(history):
    return float(snap_f["score"] - snap_0["score"])
```

`delta_score = score_final - score_inicial`. Si el jugador comienza con score_0 = 100 (escenario saludable, todo en rango óptimo) y termina con score_10 = 75 (sigue siendo "Bueno"), `delta_score = -25` y el veredicto es `"removed"`. Esto es **extremadamente punitivo** porque el score de referencia t=0 de un escenario saludable es artificialmente alto (es la economía perfecta antes de que el jugador toque algo).

#### 🟡 ADVERTENCIA F-21: El `provisional_snap` se construye duplicado

El snapshot provisional (líneas 760-796) y el snapshot final (líneas 810-846) son **idénticos** excepto por `score` (0 en el provisional, calculado en el final). El provisional se construye pero **nunca se usa** porque la evaluación de eventos fue trasladada al Paso 1.5. Este es código muerto de ~40 líneas que debería eliminarse.

---

## 4. Cuellos de Botella de Rendimiento y Arquitectura Streamlit

### 4.1 Fugas de Renderizado ("Connecting...")

#### 🔴 FALLA CRÍTICA F-22: 12 gráficos Plotly renderizados sin caché en cada rerun

En `dashboard_main.py`, cada interacción con **cualquier** widget (toggle de tema, expansión de acordeón, hover de tooltip) provoca un **rerun completo** de Streamlit. En cada rerun se recalculan y renderizan:

1. 6 KPIs con 6 mini-gráficos de barras (líneas 316-346) → 6 `go.Figure`
2. Tab 1: `plot_gdp_decomposition` + `plot_sectoral_composition` + `plot_fiscal_odometer` → 3 `go.Figure`
3. Tab 2: `plot_butterfly_trade` + `plot_exchange_intervention` + `plot_salter_swan` → 3 `go.Figure`
4. Tab 3: `plot_islm_bp_dynamic` + `plot_trilemma_ternary` + `plot_debt_snowball` → 3 `go.Figure`
5. Tab 4: `plot_business_cycle_clock` + `plot_reelection_radar` → 2 `go.Figure`
6. Tabla de decisiones con `pd.DataFrame` → 1 dataframe render

**Total: 18 objetos Plotly + 1 DataFrame en cada rerun.** Ninguna de estas funciones está decorada con `@st.cache_data`. El archivo `charts_v2.py` tiene 49,470 bytes de código de gráficos — cada `go.Figure` involucra decenas de operaciones `add_trace`, `update_layout`, etc.

**Solución requerida:**
```python
@st.cache_data(hash_funcs={list: lambda x: hash(str(x))})
def plot_gdp_decomposition(history: list) -> go.Figure:
    ...
```

O alternativamente, encapsular **toda la lógica de generación de charts** en `st.fragment` (Streamlit 1.33+) para evitar rerenderizar pestañas no visibles.

#### 🔴 FALLA CRÍTICA F-23: Las Google Fonts se importan 3 veces por rerun

El `@import url(...)` de Google Fonts aparece en:
1. `main.py` CSS inline (no — solo styles nativos)
2. `EXECUTIVE_CSS` (línea 20 de `styles.py`)
3. `STRATEGY_CSS` (línea 173 de `styles.py`)

Cada `st.markdown(STRATEGY_CSS, unsafe_allow_html=True)` (línea 151 de `dashboard_main.py`) inyecta un bloque `<style>` con `@import url(...)`. En un rerun, esto genera una petición HTTP a `fonts.googleapis.com` que **bloquea el renderizado CSS** del navegador hasta que las fuentes se descarguen. En Streamlit Cloud con latencia ~200ms por petición, esto añade ~600ms de bloqueo perceptible.

**Solución:** Mover los `@import` a un `<link>` en el `<head>` usando `st.html` o `st.components.v1.html` una sola vez, o cachear las fuentes con `@st.cache_resource`.

#### 🟡 ADVERTENCIA F-24: `import pandas as pd` dentro de la función de renderizado

En `dashboard_main.py`, línea 417:
```python
import pandas as pd
df_decisions = pd.DataFrame(decisions_list)
```

El `import pandas` está dentro del cuerpo de `render_game_dashboard`, no al nivel superior. Aunque Python cachea imports, el overhead de resolución del módulo se paga en cada rerun. El import debería estar al nivel de archivo (como ya existe en la línea 12 de `main.py` — pero `dashboard_main.py` no lo importa a nivel de módulo).

#### 🔴 FALLA F-25: `advisor_system.py` ejecuta un `solve_equilibrium_v2` completo en cada turno

En `generate_advisor_warnings` (línea 84-103):
```python
eq = solve_equilibrium_v2(
    sp=sp, pi=pi, Y_pot=Y_pot_next, P_NT=P_NT_next,
    E_prev=E_prev, Y_prev=Y_prev, r_prev=r_prev,
    j_curve_active=state["j_curve_active"],
    delta_E_expected=state["delta_E_expected"],
)
```

Esto ejecuta el solver completo (incluyendo `fsolve`/`least_squares` para flexible) como un **dry-run especulativo** para cada turno. Bajo régimen flexible, esto involucra ~200 iteraciones del loop externo, cada una con un call a `least_squares`. El costo es O(200 * costo_fsolve) **adicional** al solver real que ya se ejecutó en `step_forward`.

**Nota crítica:** Este call no pasa `rho` ni `prev_risk_penalty` ni `prev_velocity_penalty`, por lo que la proyección es **inexacta** (usa los defaults de 0.0 y 1.0 respectivamente). Las alertas del asesor se generan con una economía artificial sin prima de riesgo, mientras que el equilibrio real sí la tiene. Las alertas pueden ser falsamente optimistas.

#### 🟡 ADVERTENCIA F-26: `engine/cache.py` importa `engine.core` (V1 legacy, no V2)

```python
# cache.py, línea 49:
from engine.core import eq_fixed  # Import local para evitar circularidad
```

Este módulo importa de `engine.core` (sin `_v2`), que ya no es el motor activo. **El sistema de caché es completamente inoperante** para la V2. Debería importar `engine.core_v2` o ser actualizado.

### 4.2 Estrategia de Optimización — Puntos Exactos de Cacheo

| Archivo | Línea | Función | Decorador Recomendado |
|---|---|---|---|
| `ui/charts_v2.py` | todas las `plot_*` | Todas las funciones de gráficos | `@st.cache_data` con hash de `history` |
| `ui/dashboard_main.py` | 33 | `_render_kpi_card_with_history` | `@st.cache_data` |
| `engine/advisor_system.py` | 34 | `generate_advisor_warnings` | Mover a `@st.cache_data` o eliminar dry-run |
| `ui/endgame_screen.py` | 77 | `plot_endgame_spider` | `@st.cache_data` |
| `ui/dashboard_main.py` | 236-256 | Bloque "APLICAR POLÍTICAS" | Envolver en `st.form("policy_form")` |

**El envoltorio en `st.form` es CRÍTICO:** Actualmente, cada slider genera un rerun individual cuando el usuario lo mueve. Con 10 sliders, el usuario genera 10 reruns antes de presionar "Avanzar". Cada rerun recalcula 18 gráficos. Total: **180 renders de gráficos** para un solo turno de ajuste de políticas.

Solución con `st.form`:
```python
with st.sidebar.form("policy_form"):
    gc = st.slider("Gasto Corriente", ...)
    ig = st.slider("Inversión Pública", ...)
    # ... todos los sliders
    submitted = st.form_submit_button("⏭️ APLICAR POLÍTICAS Y AVANZAR")
    if submitted:
        mgr.step_forward(policy_changes)
        st.rerun()
```

Esto reduce los reruns a **1 por turno**.

---

## 5. Consistencia de la Interfaz Visual (UX/UI)

### 5.1 Aislamiento de Componentes

#### 🔴 FALLA F-27: CSS inyectado puede colisionar con widgets nativos de Streamlit

En `STRATEGY_CSS` (línea 306-328 de `styles.py`):
```css
button[data-baseweb="tab"] {
    background-color: #1E293B !important;
    ...
}
button[aria-selected="true"] {
    color: #38BDF8 !important;
    ...
}
```

Estos selectores son **globales** — afectan a TODOS los elementos `<button>` con atributo `data-baseweb="tab"` en la página. Si Streamlit introduce otros componentes basados en BaseWeb que usen tabs (e.g., `st.tabs` internos de widgets), estos estilos los afectarán. Además:

- `div[data-testid="stMarkdownContainer"] p` (línea 335) aplica `color: #CBD5E1` a **todos** los párrafos dentro de containers markdown, incluyendo los de la sidebar, tooltips, y popups.
- La clase `.stSlider` (línea 331) afecta a TODOS los sliders globalmente.

#### 🟡 ADVERTENCIA F-28: El toggle de tema dispara un rerun completo sin necesidad

En `dashboard_main.py`, línea 140-147:
```python
theme_selection = st.sidebar.toggle(
    "Activar Strategy Mode", ...
)
st.session_state["theme"] = "strategy" if theme_selection else "executive"
```

Cambiar el toggle de tema provoca un rerun que recalcula **todo el dashboard** incluyendo 18 gráficos. Un cambio puramente visual (CSS) no debería requerir recalcular los datos.

#### 🔴 FALLA F-29: `t_val` usado en la columna derecha puede no estar definido cuando `status ∉ {running}`

En `dashboard_main.py`, la variable `t_val` se define en la línea 162 dentro del bloque condicional:
```python
if mgr.state.get("status") not in ["game_over", "completed"] and mgr.t < 10:
    t_val = mgr.t
    ...
```

Pero en la columna derecha (línea 437):
```python
if t_val == 0:
    st.markdown("...")
```

Si el status es `game_over` o `completed`, `t_val` **nunca se asigna** y se produce un `NameError`. Esto crashea la UI si se llega al bloque de la columna derecha cuando el juego terminó pero el status aún no es `endgame`.

**Excepción activa en producción:** Este bug se oculta porque `main.py` redirige a `render_endgame_screen` antes de llegar a `render_game_dashboard`. Pero si un desarrollador llama a `render_game_dashboard` directamente con status `game_over`, la aplicación crashea.

#### 🟡 ADVERTENCIA F-30: Inflación no-transable es un "mock" hardcodeado

En `dashboard_main.py`, línea 277:
```python
pi_nt_val = last_snap.get("pi_e", 0.03) * 100.0 - 0.2  # Mock NT inflation
```

El KPI "Inflación No-Transable (π_NT)" muestra `pi_e * 100 - 0.2`, que es la expectativa de inflación menos un offset arbitrario de 0.2 puntos. **No es la inflación real de no-transables** (que sería `pi_core` calculada en `step_forward`). Este dato mockup engaña al jugador sobre la dinámica de precios sectoriales.

#### 🟡 ADVERTENCIA F-31: El bloque de noticias mock se muestra incluso cuando hay advisor_warnings reales

En `dashboard_main.py`, líneas 506-530:
```python
elif not has_events:
    # Sala de Crisis con alertas mock Premium de transmisión si no hay eventos reales
    ...
    st.markdown(f"""
    {riesgo_cambiario_html}
    <!-- Alerta 2: Crowding Out -->
    ...
    <!-- Alerta 3: Asesor de Hacienda -->
    ...
    """)
```

Si `advisor_warnings` está vacío Y no hay eventos, se muestran alertas **mock** genéricas ("Crowding Out", "Asesor de Hacienda") con datos inventados ("4.2% del PIB"). Estas alertas estáticas no reflejan el estado real de la economía y pueden confundir al jugador avanzado.

---

## 6. Hallazgos Adicionales

### 6.1 Coherencia del Score y Penalización Doble del Escenario Bolivia

#### 🔴 FALLA F-32: Bolivia_2024 comienza con `B = 150.0` y `Y_pot = 100.0`, lo que implica deuda/PIB = 150%

En `parameters_v2.py`, línea 258:
```python
"initial_state": {
    "Y_pot": 100.0,
    ...
    "B": 150.0,
}
```

`B/Y_pot = 1.50 = 150%`, lo que **ya cruza el umbral de game over** `B_Y_ratio_max = 1.50` desde t=0. El game over no se dispara en t=0 porque la verificación solo opera cuando `state["t"] > 1` (línea 874), pero en t=2 el jugador hereda una deuda que ya está en default soberano. Combinado con `I0 = -5.0` (contracción de inversión), `NX0 = -3.0` (déficit comercial), y `R = 20.0` (reservas bajas), este escenario es **matemáticamente imposible de ganar** bajo las penalizaciones actuales.

#### 🟡 ADVERTENCIA F-33: `hashlib` se importa dos veces en `state_manager_v2.py`

Línea 67: `import hashlib` (nivel de módulo)  
Línea 410: `import hashlib` (dentro de `step_forward`)

La segunda importación es redundante.

#### 🟡 ADVERTENCIA F-34: `sys` se importa inline repetidamente

En `step_forward`, `import sys` aparece en líneas 426, 875, y 892. Debería moverse al nivel de módulo.

---

## Resumen Ejecutivo de Prioridad

| # | Severidad | Archivo | Descripción |
|---|---|---|---|
| F-05 | 🔴 CRÍTICA | `core_v2.py` + `dynamics_v2.py` | Doble penalización exponencial de `rho` (escalado ×100 duplicado) |
| F-13 | 🔴 CRÍTICA | `core_v2.py` + `dynamics_v2.py` | Misma lógica de penalización duplicada en dos módulos |
| F-10 | 🔴 CRÍTICA | `state_manager_v2.py` | Game over por R < 5.0 se aplica en régimen flexible |
| F-22 | 🔴 CRÍTICA | `ui/dashboard_main.py` | 18 Plotly charts sin `@st.cache_data` → "Connecting..." |
| F-01 | 🔴 CRÍTICA | `core_v2.py` | `eps_eff_sx` omite `epsilon_m` en modo legacy |
| F-18 | 🔴 CRÍTICA | `events_engine.py` + `state_manager_v2.py` | `G_needed` del desastre natural nunca se consume |
| F-32 | 🔴 CRÍTICA | `parameters_v2.py` | Bolivia_2024 inicia con B/Y = 150% (en default) |
| F-16 | 🔴 CRÍTICA | `state_manager_v2.py` | Eventos evaluados con variables stale del turno anterior |
| F-02 | 🔴 CRÍTICA | `core_v2.py` | Inconsistencia algebraica NX en sistema 2×2 vs. recálculo post |
| F-25 | 🔴 CRÍTICA | `advisor_system.py` | Dry-run completo del solver sin pasar rho/penalizaciones |
| F-29 | 🔴 CRÍTICA | `ui/dashboard_main.py` | `t_val` undefined en rama game_over |
| F-04 | 🟡 MEDIA | `core_v2.py` | `is_curve_v2` inconsistente con solver (falta tau, s_x) |
| F-06 | 🟡 MEDIA | `core_v2.py` | `velocity_penalty` sin fundamento bajo TC fijo |
| F-08 | 🟡 MEDIA | `core_v2.py` | `fsolve` sin verificación de convergencia |
| F-14 | 🟡 MEDIA | `core_v2.py` | Inercia 0.6/0.4 impide recuperación en 10 turnos |
| F-20 | 🟡 MEDIA | `scoring_v2.py` | `delta_score` punitivo contra escenarios saludables |
| F-23 | 🔴 MEDIA-ALTA | `ui/styles.py` | Google Fonts se importan 3 veces bloqueando render |
| F-26 | 🟡 MEDIA | `engine/cache.py` | Cache importa `engine.core` V1, inoperante para V2 |
| F-30 | 🟡 MENOR | `ui/dashboard_main.py` | π_NT es mock hardcodeado, no dato real |
| F-31 | 🟡 MENOR | `ui/dashboard_main.py` | Alertas mock genéricas con datos inventados |

---

**Fin del Informe de Auditoría V3.2**  
*Consorcio de Arquitectura de Software y Macroeconomía Aplicada*
