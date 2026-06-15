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

import math
from typing import Optional


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
    I_g: float = 0.0,
    gamma: float = 0.15,
    Y_pot_base: float = None,
    g_pot_max: float = None,
) -> float:
    """
    Actualizacion del PIB potencial entre turnos (V2.1).

    Y_pot_new = Y_pot * (1 + g_pot + endogenous_shock) + gamma * I_g

    El `endogenous_shock` permite que eventos de juego (e.g., "Malestar Social",
    destruccion de capital) reduzcan el potencial permanentemente.
    gamma * I_g modela el impacto de la inversión pública en la capacidad productiva de largo plazo.

    Parameters
    ----------
    Y_pot            : PIB potencial del periodo anterior
    g_pot            : Tasa de crecimiento potencial estructural
    endogenous_shock : Shock endogeno sobre el potencial (negativo = contraccion)
    I_g              : Inversión pública del turno actual (default 0.0)
    gamma            : Eficiencia marginal de la inversión pública en Y_pot (default 0.15)
    Y_pot_base       : PIB potencial base estructural para convergencia (V3.5)

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
    if g_pot_max is not None:
        g_pot = min(g_pot, g_pot_max)
    # Sincronizar oferta con demanda: si la brecha es muy negativa, el potencial no expande capacidad
    current_gap = (Y_pot - Y_pot_base) / Y_pot_base if Y_pot_base else 0.0
    effective_g_pot = 0.0 if current_gap < -0.05 else g_pot
    growth_rate = effective_g_pot + endogenous_shock
    Y_pot_new = Y_pot * (1.0 + growth_rate) + (gamma * I_g)
    
    # V3.6: Cap de histéresis destructiva (pérdida máxima de PIB potencial limitada a un 5% por período)
    Y_pot_new = max(Y_pot * 0.95, Y_pot_new)
    
    # R6: Convergencia de Y_pot (recuperación del 3%/turno hacia Y_pot_base)
    if Y_pot_base is not None and Y_pot_new < Y_pot_base:
        Y_pot_new += 0.03 * (Y_pot_base - Y_pot_new)
        
    return Y_pot_new


# ─────────────────────────────────────────────────────────────────────────────
# MERCADO LABORAL — LEY DE OKUN V2 (CORRECCION ERROR C-2)
# ─────────────────────────────────────────────────────────────────────────────

def compute_unemployment(
    U_n: float,
    gamma_okun: float,
    gap: float,
    U_floor: float = 0.04,
) -> float:
    """
    Tasa de desempleo segun la Ley de Okun V3.0 (No-Lineal).

    V3.0 [Reforma 3A]:
    - Piso friccional estructural: U_floor = 3.5% (economias emergentes).
    - Sobreempleo (gap > 0): compresión exponencial del desempleo.
      U = U_n · exp(-gamma * gap / U_n)
      Modela las presiones geometricas de contratación cuando la economia
      opera muy por encima del potencial.
    - Recesión (gap < 0): respuesta lineal estándar de Okun.
      U = U_n - gamma * gap

    La formulación exponencial para gap > 0 garantiza que cuando la brecha
    es grande y positiva, el desempleo no puede caer por debajo de
    U_floor de forma lineal ilimitada, sino que se acerca asíntoticamente.

    Parameters
    ----------
    U_n        : Tasa natural de desempleo (NAIRU)
    gamma_okun : Coeficiente de Okun (tipicamente 0.3-0.5)
    gap        : Brecha del producto = (Y - Y_pot) / Y_pot
    U_floor    : Piso de desempleo friccional/estructural (default: 3.5%)

    Returns
    -------
    float : Tasa de desempleo (acotada por U_floor)
    """
    if gap > 0:
        # Sobreempleo: compresión exponencial
        import math as _math
        U = U_n * _math.exp(-gamma_okun * gap / max(U_n, 1e-6))
    else:
        # Recesión: respuesta lineal estandar de Okun
        U = U_n - gamma_okun * gap

    return U


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
    # V3.0 — Reforma 3A: No-linealidad NAIRU
    U: float = 0.05,
    U_n: float = 0.05,
    alpha_nonlinear: float = 0.0,
    pi_prev: Optional[float] = None,
) -> float:
    """
    Inflacion segun la Curva de Phillips Aumentada con Pass-through V3.0.

    pi = pi_e + alpha*gap + beta_PT*(delta_E/E_prev) + pi_0 + NAIRU_pressure

    V3.0 [Reforma 3A] agrega término de ACELERACIÓN NO-LINEAL ante sobreempleo:

        NAIRU_pressure = alpha_nonlinear * ((U_n - U) / U)^2
        (solo cuando U < U_n, es decir, el mercado laboral está recalentado)

    Este término modela la asimetría de la curva de Phillips: una economía
    que opera por debajo de la NAIRU genera presiones salariales exponenciales,
    no lineales. Si alpha_nonlinear = 0 (default), reproduce V2.0 exactamente.

    Componentes:
    - pi_e              : Expectativas de inflacion (adaptativas del turno anterior)
    - alpha * gap       : Presion de demanda (gap > 0 -> inflacion sube)
    - beta_PT*(dE/E)    : Pass-through cambiario (devaluacion -> inflacion sube)
    - pi_0              : Inflación base adicional (Trampa de Estanflación, Fase 3)
    - NAIRU_pressure    : Aceleración no-lineal ante sobreempleo extremo (V3.0)

    Parameters
    ----------
    pi_e           : Expectativa de inflacion del periodo
    alpha_inf      : Pendiente de la curva de Phillips
    gap            : Brecha del producto
    beta_PT        : Coeficiente de pass-through cambiario
    delta_E        : Variacion nominal del tipo de cambio (E_t - E_{t-1})
    E_prev         : Tipo de cambio del periodo anterior
    pi_0           : Inflación base adicional (default: 0.0)
    U              : Desempleo del periodo (V3.0; default: U_n)
    U_n            : NAIRU (V3.0; default: 0.05)
    alpha_nonlinear: Pendiente de la aceleración NAIRU (V3.0; 0 = sin efecto)

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

    # V3.0 Reforma 3A: aceleración NAIRU no-lineal
    if alpha_nonlinear > 0.0 and U < U_n and U > 1e-6:
        nairu_pressure = alpha_nonlinear * ((U_n - U) / U) ** 1.5
        # R1: Cap la NAIRU pressure a máximo 0.05 (5%) por turno
        nairu_pressure = min(nairu_pressure, 0.05)
        pi += nairu_pressure

    if pi_prev is not None:
        max_delta = 0.08  # máximo 8 puntos porcentuales de cambio por turno
        pi = max(pi_prev - max_delta, min(pi_prev + max_delta, pi))

    return pi


def update_adaptive_expectations(pi_t: float, t: Optional[int] = None, pi_previo: Optional[float] = None, theta: Optional[float] = None) -> float:
    """
    Actualizacion de expectativas de inflacion adaptativas con anclaje dinamico (V4.7).
    """
    pi_target = 0.03
    base_anchor = 0.60 if (t is not None and t >= 3) else 0.40
    if theta is not None:
        weight_target = max(base_anchor, min(0.90, theta))
    else:
        weight_target = base_anchor
    ref_val = pi_previo if pi_previo is not None else pi_t
    return max(-0.02, weight_target * pi_target + (1.0 - weight_target) * ref_val)


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
    pi_core_bounded = max(-0.015, pi_core)
    return P_NT * (1.0 + pi_core_bounded)


# ─────────────────────────────────────────────────────────────────────────────
# CAPITAL PUBLICO Y EFECTOS DE DESPLAZAMIENTO (V3.0 — REFORMA 4A)
# ─────────────────────────────────────────────────────────────────────────────

def update_public_capital(
    K_g: float,
    I_g: float,
    delta_kg: float = 0.05,
) -> float:
    """
    Acumulación del stock de capital público entre turnos.

    K_g_new = K_g * (1 - delta_kg) + I_g

    El capital público (infraestructura, energía, telecomunicaciones) se deprecia
    a la tasa delta_kg y se acumula con la inversión pública I_g del turno.

    Parameters
    ----------
    K_g      : Stock de capital público del período anterior
    I_g      : Inversión pública del turno actual
    delta_kg : Tasa de depreciación del capital público (default: 5%)

    Returns
    -------
    float : Nuevo stock de capital público
    """
    return K_g * (1.0 - delta_kg) + I_g


def compute_crowding_effect(
    K_g: float,
    Y_pot: float,
    B: float,
    psi_ci: float = 0.0,
    psi_co: float = 0.0,
) -> float:
    """
    Calcula el efecto neto de Crowding-In y Crowding-Out sobre la inversión privada.

    delta_I0 = psi_ci * ln(1 + K_g / Y_pot) - psi_co * (B / Y_pot)

    - Crowding-In (psi_ci > 0): El stock de capital público acumulado mejora
      la rentabilidad esperada del sector privado, elevando I0 de forma
      logarítmica (retornos decrecientes del capital público).

    - Crowding-Out (psi_co > 0): El endeudamiento soberano eleva el costo
      del crédito y desplaza la inversión privada del mercado de capitales.

    Si psi_ci = psi_co = 0 (default), retorna 0.0 sin costo computacional
    (retrocompatibilidad total con V2.0).

    Parameters
    ----------
    K_g    : Stock de capital público acumulado
    Y_pot  : PIB potencial (para normalizar)
    B      : Deuda soberana acumulada
    psi_ci : Elasticidad crowding-in (default: 0 = sin efecto)
    psi_co : Elasticidad crowding-out (default: 0 = sin efecto)

    Returns
    -------
    float : Ajuste neto sobre I0 (δI0); positivo = crowding-in neto
    """
    if psi_ci == 0.0 and psi_co == 0.0:
        return 0.0  # Atajo rápido: sin efecto (retrocompat. V2.0)

    K_g_ratio = K_g / max(Y_pot, 1.0)
    B_ratio   = max(0.0, B) / max(Y_pot, 1.0)  # Solo deuda positiva desplaza

    ci_effect = psi_ci * math.log(1.0 + K_g_ratio) if psi_ci > 0 else 0.0
    co_effect = psi_co * B_ratio if psi_co > 0 else 0.0

    return ci_effect - co_effect


# ─────────────────────────────────────────────────────────────────────────────
# FINANZAS PUBLICAS Y DEUDA — CROWDING-OUT INTERTEMPORAL
# ─────────────────────────────────────────────────────────────────────────────

class FiscalBalanceResult(dict):
    """
    Clase que hereda de dict para permitir acceso por llaves,
    pero define __iter__ para soportar desempaquetado de tuplas (retrocompatibilidad).
    """
    def __iter__(self):
        yield self["recaudacion"]
        yield self["intereses"]
        yield self["deficit"]
        yield self["B_new"]

def compute_fiscal_balance(
    G: float,
    t: float,
    Y: float,
    r: float,
    B_prev: float,
    r_scale: float = 100.0,
    # Nuevos argumentos opcionales V2.1
    G_c: Optional[float] = None,
    I_g: Optional[float] = None,
    Tr: float = 0.0,
    t_c: Optional[float] = None,
    t_k: float = 0.0,
    tau: float = 0.0,
    M_imp: float = 0.0,
    r_star: Optional[float] = None,
    rho: float = 0.0,
    Y_pot: Optional[float] = None,
) -> FiscalBalanceResult:
    """
    Balance fiscal y evolucion de la deuda soberana desagregado (V2.1).

    Recaudacion = (t_c * Y) + (t_k * Y) + (tau * M_imp)
    Gasto = G_c + I_g + Tr
    Intereses = sovereign_rate * B_prev
    Deficit = Gasto + Intereses - Recaudacion
    B_new = B_prev + Deficit

    Retrocompatibilidad:
    Si no se pasan los argumentos desagregados, se cae en el cálculo agregado
    V2.0 original. Adicionalmente, el retorno hereda de dict pero puede
    desempaquetarse como tupla: (recaudacion, intereses, deficit, B_new).
    """
    # Fallbacks retrocompatibles
    if t_c is None:
        t_c = t
        # Si se usa la tasa proporcional sp["t"] y no hay t_k, recaudacion = t * Y
    
    if G_c is None:
        # Si no hay G_c ni I_g, asumimos que G es el gasto total y es corriente
        if I_g is None:
            G_c = G
            I_g = 0.0
        else:
            # Si hay I_g, G_c = G - I_g
            G_c = G - I_g
    elif I_g is None:
        I_g = G - G_c

    # ── Blanco 2: Recaudación Real y Ley de Acumulación Real de Deuda ─────────
    # Fuerza a que el cómputo de la recaudación por impuesto al consumo e ingreso
    # doméstico se indexe de forma matemática y estricta al PIB real (Y) y a las
    # importaciones físicas de equilibrio (M_imp), previniendo que la inflación nominal
    # infle falsamente los ingresos o licúe de forma espuria el stock de deuda real.
    recaudacion = (t_c + t_k) * Y + tau * M_imp
    gasto = G_c + I_g + Tr

    if r_star is None:
        # Fallback retrocompatible: usar la tasa doméstica de equilibrio r
        if B_prev < 0.0:
            sovereign_rate = (r / r_scale) * 0.5
        else:
            sovereign_rate = r / r_scale
    else:
        # Tasa internacional + prima de riesgo país
        if B_prev < 0.0:
            # Si tiene activos, gana tasa más baja sin prima de riesgo soberano (rho)
            sovereign_rate = (r_star / 100.0) * 0.5
        else:
            # Si tiene deuda, paga tasa internacional + prima de riesgo soberano
            sovereign_rate = r_star / 100.0 + rho

    intereses = sovereign_rate * B_prev
    deficit = gasto + intereses - recaudacion
    
    # ── CORRECCIÓN BUG 3: Límite macroeconómicamente significativo ─────────────
    # El gobierno no puede tener activos netos > 50% del PIB potencial.
    # Se pasa Y_pot como argumento opcional, si es None, se usa Y.
    Y_pot_val = Y_pot if Y_pot is not None else Y
    B_min = -0.5 * max(Y_pot_val, 100.0)
    B_max = 3.0 * max(Y, 100.0)  # Deuda máxima: 300% del PIB
    
    B_new_raw = B_prev + deficit
    B_new = max(B_min, min(B_max, B_new_raw))
    
    # V3.5: Consistencia Stock-Flujo (SFC) cuando el techo de deuda B_max es alcanzado
    seigniorage_shock = 0.0
    gasto_impago_arrears = 0.0
    
    if B_new_raw > B_max:
        brecha = B_new_raw - B_max
        # 60% se monetiza (shock de señoreaje inorgánico)
        seigniorage_shock = 0.60 * brecha
        # 40% entra en mora (recorte real involuntario de gasto público efectivo)
        gasto_impago_arrears = 0.40 * brecha
        deficit_efectivo = B_new - B_prev
    elif B_new_raw < B_min:
        deficit_efectivo = B_new - B_prev
    else:
        deficit_efectivo = deficit

    return FiscalBalanceResult({
        "recaudacion": round(recaudacion, 6),
        "gasto": round(gasto - gasto_impago_arrears, 6),
        "intereses": round(intereses, 6),
        "deficit": round(deficit_efectivo, 6),
        "B_new": round(B_new, 6),
        "seigniorage_shock": round(seigniorage_shock, 6),
        "Recaudacion": round(recaudacion, 6),
        "Gasto": round(gasto - gasto_impago_arrears, 6),
        "Intereses": round(intereses, 6),
        "Deficit": round(deficit_efectivo, 6),
    })


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
    # Circuit breaker triggers when reserves fall below the critical level of 5.0
    if regime == "fixed" and R < 5.0:
        new_regime = "flexible"
        new_E      = E_current * devaluation_factor
        return True, new_regime, round(new_E, 6)

    return False, regime, E_current


def compute_sovereign_risk(
    B: float,
    Y_pot: float,
    R: float,
    G: float = 20.0,
    M: float = 40.0,
    prev_risk_penalty: float = 0.0,
    # V3.0 — Reforma 5A: disparadores multi-dimensionales
    recaudacion: float = 0.0,
    intereses: float = 0.0,
    B_prev: float = 0.0,
    # V3.1 — Parametrización
    debt_velocity_threshold: float = 0.10,
) -> tuple[float, str, float]:
    """
    Calcula la prima de riesgo soberano (rho) y la calificación crediticia.
    Fuente única de verdad para la prima de riesgo país.

    V3.0 [Reforma 5A] agrega dos disparadores adicionales:

    Disparador 1 — Ratio Intereses/Recaudación (phi_service):
        Si el servicio de deuda supera el 30% de la recaudación fiscal,
        se produce un salto gradual de rho. Es el umbral crítico donde
        las agencias Moody's/Fitch inician rebajas automáticas de rating.

    Disparador 2 — Velocidad de Acumulación de Deuda (phi_velocity):
        Si el ratio B/Y_pot subió más de 10 puntos porcentuales en un
        turno, se agrega una prima por momentum de deterioro fiscal.

    Ajuste por Reservas internacionales críticas:
    - Si R < 0.0, suma 0.05 a rho y añade '(Reserva Crítica)' al rating.

    Parameters
    ----------
    B               : Deuda acumulada
    Y_pot           : PIB potencial
    R               : Reservas internacionales actuales
    G               : Gasto público total
    M               : Oferta monetaria
    prev_risk_penalty: Penalización de riesgo del turno previo
    recaudacion     : Recaudación fiscal del turno actual (V3.0)
    intereses       : Pago de intereses de la deuda del turno actual (V3.0)
    B_prev          : Deuda del período anterior (para calcular velocidad) (V3.0)

    Returns
    -------
    tuple[float, str, float]
        (rho, rating, risk_penalty)
    """
    debt_ratio = B / max(Y_pot, 1.0)

    # Escalera gradual de rho base indexada al ratio de sostenibilidad fiscal
    if debt_ratio < 0.15:
        rho = 0.005
    elif debt_ratio < 0.30:
        rho = 0.015
    elif debt_ratio < 0.45:
        rho = 0.03
    elif debt_ratio < 0.60:
        rho = 0.045
    elif debt_ratio < 0.80:
        rho = 0.065
    elif debt_ratio < 1.00:
        rho = 0.09
    elif debt_ratio < 1.20:
        rho = 0.13
    else:
        rho = 0.25

    base_rho_with_R = rho
    if R < 0.0:
        base_rho_with_R += 0.05

    # V3.0 Reforma 5A — Disparador 1: Ratio Intereses/Recaudación
    interest_burden_premium = 0.0
    if recaudacion > 0.0 and intereses > 0.0:
        interest_burden = intereses / recaudacion
        if interest_burden > 0.30:
            # Escala gradual por cada 10pp extra sobre el umbral del 30%
            interest_burden_premium = 0.04 * (interest_burden - 0.30) / 0.10
            interest_burden_premium = min(interest_burden_premium, 0.12)  # Cap: +12pp

    # V3.0 Reforma 5A — Disparador 2: Velocidad de acumulación de deuda (V3.1 paramétrica)
    debt_velocity_premium = 0.0
    if Y_pot > 0.0 and B_prev > 0.0:
        prev_debt_ratio = B_prev / Y_pot
        delta_BY = debt_ratio - prev_debt_ratio
        if delta_BY > debt_velocity_threshold:
            debt_velocity_premium = 0.02 * (delta_BY - debt_velocity_threshold) / 0.05
            debt_velocity_premium = min(debt_velocity_premium, 0.02)  # Cap: +2pp

    # Penalización extrema no-lineal (G y M fuera de rango)
    new_risk_penalty = 0.0
    if G > 30.0:
        new_risk_penalty += 0.008 * (G - 30.0)
    elif G < 5.0:
        new_risk_penalty += 0.015 * (5.0 - G)

    if M > 120.0:
        new_risk_penalty += 0.002 * (M - 120.0)
    elif M < 15.0:
        new_risk_penalty += 0.012 * (15.0 - M)

    # Inercia intertemporal: 0.6 * previo + 0.4 * nuevo
    risk_penalty = 0.6 * prev_risk_penalty + 0.4 * new_risk_penalty
    final_rho = base_rho_with_R + risk_penalty + interest_burden_premium + debt_velocity_premium

    # Mapeo gradual indexado a rho final y debt_ratio
    if debt_ratio >= 1.20 or final_rho >= 0.22:
        rating = "Default"
    elif final_rho >= 0.12 or debt_ratio >= 1.00:
        rating = "CCC"
    elif final_rho >= 0.08 or debt_ratio >= 0.80:
        rating = "B"
    elif final_rho >= 0.055 or debt_ratio >= 0.60:
        rating = "BB"
    elif final_rho >= 0.035 or debt_ratio >= 0.45:
        rating = "BBB"
    elif final_rho >= 0.02 or debt_ratio >= 0.30:
        rating = "A"
    elif final_rho >= 0.01 or debt_ratio >= 0.15:
        rating = "AA"
    else:
        rating = "AAA"

    # Marcar reserva crítica si corresponde
    if R < 0.0:
        rating = f"{rating} (Reserva Crítica)"

    return final_rho, rating, risk_penalty
