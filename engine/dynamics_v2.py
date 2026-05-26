"""
engine/dynamics_v2.py
=====================
Leyes de movimiento de las variables de estado entre turnos (V2.0).

Principios V2.0:
  - Funciones PURAS: sin efectos laterales, sin estado global.
  - Okun usa `gap` (brecha del producto), no `gY` (tasa de crecimiento). [C-2]
  - Phillips usa `gap` y añade pass-through cambiario `beta_PT`. [C-3]
  - Reservas solo cambian bajo TC Fijo. [C-7]
  - Deuda soberana acumula déficit + intereses (crowding-out intertemporal).
  - Efecto J-curve detectado mediante variación significativa de E.

Estas funciones son llamadas por el StateManager (Fase 2) una vez por turno,
después de que el motor core_v2.py calcula el equilibrio IS-LM-BP.

Jerarquía:
    engine/core_v2.py → engine/dynamics_v2.py → (StateManager Fase 2)

Este módulo NO importa de ui/, streamlit, ni directamente de config/.
"""

from __future__ import annotations


# ─────────────────────────────────────────────────────────────────────────────
# BRECHA DEL PRODUCTO Y POTENCIAL
# ─────────────────────────────────────────────────────────────────────────────

def compute_output_gap(Y: float, Y_pot: float) -> float:
    """
    Brecha del producto (output gap).

    gap = (Y - Y_pot) / Y_pot

    - gap > 0: economía por encima del potencial (presiones inflacionarias).
    - gap < 0: economía por debajo del potencial (capacidad ociosa).
    - gap = 0: pleno empleo / equilibrio de largo plazo.

    Parameters
    ----------
    Y     : PIB de equilibrio del período actual
    Y_pot : PIB potencial del período actual

    Returns
    -------
    float : Brecha del producto

    Raises
    ------
    ValueError
        Si Y_pot <= 0.
    """
    if Y_pot <= 0.0:
        raise ValueError(f"Y_pot debe ser positivo, recibido: {Y_pot}")
    return (Y - Y_pot) / Y_pot


def update_potential_output(
    Y_pot: float,
    g_pot: float,
    endogenous_shock: float = 0.0,
) -> float:
    """
    Actualizacion del PIB potencial entre turnos.

    Y_pot_new = Y_pot * (1 + g_pot + endogenous_shock)

    El `endogenous_shock` permite que eventos de juego (e.g., "Malestar Social",
    destruccion de capital) reduzcan el potencial permanentemente.

    Parameters
    ----------
    Y_pot            : PIB potencial del periodo anterior
    g_pot            : Tasa de crecimiento potencial estructural
    endogenous_shock : Shock endogeno sobre el potencial (negativo = contraccion)

    Returns
    -------
    float : Nuevo PIB potencial

    Raises
    ------
    ValueError
        Si Y_pot <= 0.
    """
    if Y_pot <= 0.0:
        raise ValueError(f"Y_pot debe ser positivo, recibido: {Y_pot}")
    growth_rate = g_pot + endogenous_shock
    return Y_pot * (1.0 + growth_rate)


# ─────────────────────────────────────────────────────────────────────────────
# MERCADO LABORAL — LEY DE OKUN V2 (CORRECCION ERROR C-2)
# ─────────────────────────────────────────────────────────────────────────────

def compute_unemployment(
    U_n: float,
    gamma_okun: float,
    gap: float,
) -> float:
    """
    Tasa de desempleo segun la Ley de Okun V2.

    U = max(0.01, U_n - gamma_okun * gap)

    CORRECCION V2 [Error C-2 de auditoria]:
        V1.0 usaba: U = U_n - gamma * gY  (tasa de crecimiento del PIB)
        V2.0 usa:   U = U_n - gamma * gap (brecha del producto)

    La Ley de Okun relaciona el desempleo con la BRECHA del producto,
    no con la tasa de crecimiento. Usando gY se ignora el nivel del potencial
    y se obtienen valores incorrectos cuando el crecimiento es positivo pero
    la economia esta aun por debajo del potencial.

    Parameters
    ----------
    U_n        : Tasa natural de desempleo (NAIRU)
    gamma_okun : Coeficiente de Okun (tipicamente 0.3-0.5)
    gap        : Brecha del producto = (Y - Y_pot) / Y_pot

    Returns
    -------
    float : Tasa de desempleo (acotada en minimo 1%)
    """
    U = U_n - gamma_okun * gap
    return max(0.01, U)


# ─────────────────────────────────────────────────────────────────────────────
# INFLACION — CURVA DE PHILLIPS V2 (CORRECCION ERROR C-3)
# ─────────────────────────────────────────────────────────────────────────────

def compute_inflation(
    pi_e: float,
    alpha_inf: float,
    gap: float,
    beta_PT: float,
    delta_E: float,
    E_prev: float,
    pi_0: float = 0.0,
) -> float:
    """
    Inflacion segun la Curva de Phillips Aumentada con Pass-through V2.

    pi = pi_e + alpha * gap + beta_PT * (delta_E / E_prev) + pi_0

    CORRECCION V2 [Error C-3 de auditoria]:
        V1.0 usaba: pi = pi_0 + alpha * gY  (sin expectativas, sin pass-through)
        V2.0 usa:   pi = pi_e + alpha * gap + beta_PT * (delta_E / E)

    Componentes:
    - pi_e             : Expectativas de inflacion (adaptativas del turno anterior)
    - alpha * gap      : Presion de demanda (gap > 0 -> inflacion sube)
    - beta_PT*(dE/E)   : Pass-through cambiario (devaluacion -> inflacion sube)
    - pi_0             : Inflación base adicional (Trampa de Estanflación, Fase 3)

    Parameters
    ----------
    pi_e     : Expectativa de inflacion del periodo (= inflacion periodo anterior)
    alpha_inf: Pendiente de la curva de Phillips
    gap      : Brecha del producto
    beta_PT  : Coeficiente de pass-through cambiario
    delta_E  : Variacion nominal del tipo de cambio (E_t - E_{t-1})
    E_prev   : Tipo de cambio del periodo anterior
    pi_0     : Inflación base adicional (default: 0.0)

    Returns
    -------
    float : Tasa de inflacion del periodo

    Raises
    ------
    ValueError
        Si E_prev <= 0.
    """
    if E_prev <= 0.0:
        raise ValueError(f"E_prev debe ser positivo, recibido: {E_prev}")

    devaluation_rate = delta_E / E_prev
    pi = pi_e + alpha_inf * gap + beta_PT * devaluation_rate + pi_0
    return pi


def update_adaptive_expectations(pi_t: float) -> float:
    """
    Actualizacion de expectativas de inflacion adaptativas.

    pi_e_{t+1} = pi_t

    El agente utiliza la inflacion observada en el periodo actual como
    mejor prediccion para el siguiente periodo (expectativas adaptativas puras).

    Parameters
    ----------
    pi_t : Tasa de inflacion del periodo actual

    Returns
    -------
    float : Expectativa de inflacion para el proximo periodo
    """
    return pi_t


def update_non_tradable_price(P_NT: float, pi_core: float) -> float:
    """
    Actualizacion del precio de bienes no-transables.

    P_NT_new = P_NT * (1 + pi_core)

    pi_core es la inflacion nucleo (sin componente cambiario).

    Parameters
    ----------
    P_NT    : Precio de no-transables del periodo anterior
    pi_core : Inflacion nucleo (componente domestico de precios)

    Returns
    -------
    float : Nuevo precio de bienes no-transables
    """
    return P_NT * (1.0 + pi_core)


# ─────────────────────────────────────────────────────────────────────────────
# FINANZAS PUBLICAS Y DEUDA — CROWDING-OUT INTERTEMPORAL
# ─────────────────────────────────────────────────────────────────────────────

def compute_fiscal_balance(
    G: float,
    t: float,
    Y: float,
    r: float,
    B_prev: float,
    r_scale: float = 100.0,
) -> tuple[float, float, float, float]:
    """
    Balance fiscal y evolucion de la deuda soberana.

    recaudacion = t * Y
    intereses   = (r / r_scale) * B_prev
    deficit     = G - recaudacion + intereses
    B_new       = B_prev + deficit

    NOTA SOBRE ESCALA DE r:
    El motor IS-LM-BP trabaja con r en unidades de puntos porcentuales
    (e.g., r = 5.0 significa 5%). Para calcular intereses sobre la deuda
    nominal B_prev, se necesita la tasa en decimal: r / 100.
    El parametro r_scale controla esta conversion (default = 100).

    El crowding-out opera inter-periodo: mayor B_prev eleva la carga de
    intereses, expandiendo el deficit, lo que presionara r al alza en
    periodos futuros a traves de la condicion de solvencia soberana.
    No hay circularidad dentro del mismo periodo.

    Parameters
    ----------
    G       : Gasto publico
    t       : Tasa impositiva proporcional
    Y       : PIB de equilibrio del periodo
    r       : Tasa de interes de equilibrio del periodo (en puntos porcentuales)
    B_prev  : Deuda soberana al inicio del periodo
    r_scale : Factor de escala de r (default 100: r en puntos porcentuales)

    Returns
    -------
    tuple[float, float, float, float]
        (recaudacion, intereses, deficit, B_new)
    """
    recaudacion = t * Y
    intereses   = (r / r_scale) * B_prev
    deficit     = G - recaudacion + intereses
    B_new       = B_prev + deficit

    return (
        round(recaudacion, 6),
        round(intereses, 6),
        round(deficit, 6),
        round(B_new, 6),
    )


# ─────────────────────────────────────────────────────────────────────────────
# RESERVAS INTERNACIONALES (CORRECCION ERROR C-7)
# ─────────────────────────────────────────────────────────────────────────────

def update_reserves(
    R_prev: float,
    NX: float,
    regime: str,
    capital_flows: float = 0.0,
) -> float:
    """
    Actualizacion de reservas internacionales.

    CORRECCION V2 [Error C-7 de auditoria]:
        V1.0: Las reservas siempre acumulan NX independientemente del regimen.
        V2.0: Las reservas solo cambian bajo TC Fijo.

    Bajo TC Fijo:
        R_new = R_prev + NX + capital_flows
        (El banco central interviene comprando/vendiendo divisas para defender E)

    Bajo TC Flexible / Crawling Peg:
        R_new = R_prev
        (El tipo de cambio se ajusta libremente; el BC no interviene)

    Parameters
    ----------
    R_prev        : Reservas del periodo anterior
    NX            : Exportaciones netas del periodo
    regime        : Regimen cambiario: "fixed" | "flexible" | "crawling_peg"
    capital_flows : Flujos de capital netos (entradas - salidas)

    Returns
    -------
    float : Nuevas reservas internacionales
    """
    if regime == "fixed":
        R_new = R_prev + NX + capital_flows
    else:
        # TC Flexible o Crawling Peg: el BC no interviene en el mercado cambiario
        R_new = R_prev

    return round(R_new, 6)


# ─────────────────────────────────────────────────────────────────────────────
# DETECCION DE EFECTO J-CURVE
# ─────────────────────────────────────────────────────────────────────────────

def compute_j_curve_flag(
    E_t: float,
    E_prev: float,
    threshold: float = 0.02,
) -> bool:
    """
    Detecta si hubo una devaluacion significativa que activa el efecto J-curve.

    Si la variacion porcentual del tipo de cambio supera el umbral, se activa
    el efecto J en el turno actual: las exportaciones responden lentamente
    (usando epsilon_x_short ~ 0.1) y NX cae antes de mejorar.

    |delta_E / E_prev| > threshold  ->  j_curve_active = True

    Parameters
    ----------
    E_t       : Tipo de cambio del periodo actual
    E_prev    : Tipo de cambio del periodo anterior
    threshold : Variacion porcentual minima para activar el efecto J (default: 2%)

    Returns
    -------
    bool : True si se activa el efecto J-curve este turno

    Raises
    ------
    ValueError
        Si E_prev <= 0.
    """
    if E_prev <= 0.0:
        raise ValueError(f"E_prev debe ser positivo, recibido: {E_prev}")

    variation = abs(E_t - E_prev) / E_prev
    return variation > threshold


# ─────────────────────────────────────────────────────────────────────────────
# CIRCUIT BREAKER: COLAPSO DE RESERVAS
# ─────────────────────────────────────────────────────────────────────────────

def check_reserve_circuit_breaker(
    R: float,
    regime: str,
    E_current: float,
    devaluation_factor: float = 1.20,
) -> tuple[bool, str, float]:
    """
    Verifica si las reservas han caido a un nivel critico bajo TC Fijo.

    Si R <= 0 bajo TC Fijo -> crisis cambiaria:
    - El regimen se fuerza a "flexible".
    - El tipo de cambio se devalua automaticamente (devaluation_factor).
    - Se genera un evento de crisis.

    Parameters
    ----------
    R                 : Reservas actuales
    regime            : Regimen actual
    E_current         : Tipo de cambio actual
    devaluation_factor: Factor de devaluacion de emergencia (default: 20%)

    Returns
    -------
    tuple[bool, str, float]
        (crisis_triggered, new_regime, new_E)
        - crisis_triggered: True si se activo el circuit breaker
        - new_regime      : Regimen resultante
        - new_E           : Nuevo tipo de cambio tras la crisis
    """
    if regime == "fixed" and R <= 0.0:
        new_regime = "flexible"
        new_E      = E_current * devaluation_factor
        return True, new_regime, round(new_E, 6)

    return False, regime, E_current
