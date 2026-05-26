"""
engine/core.py
==============
Motor matemático puro del modelo Mundell-Fleming (economía abierta).
Sección 3.1 del documento de referencia académico.

FUNCIONES PURAS — SIN EFECTOS LATERALES NI ESTADO GLOBAL.

Ecuaciones del modelo:
    IS:  r = (A + x1*E - Y*(1 - c1 + m1)) / b
    LM:  r = (k*Y - M) / h
    BP:  r = r*  (movilidad perfecta de capitales)
    A  = c0 - c1*T + I0 + G + NX0
    mult = 1 / (1 - c1 + m1)

Régimen de tipo de cambio FIJO (E exógeno, M endógena):
    Y      = mult * (A + x1*E - b*r*)
    M_endo = k*Y - h*r*

Régimen de tipo de cambio FLEXIBLE (M exógena, E endógena):
    Y      = (M + h*r*) / k
    E_endo = ((1 - c1 + m1)*Y + b*r* - A) / x1
"""

from __future__ import annotations

from typing import TypedDict


# ── Tipos de retorno ─────────────────────────────────────────────────────────

class EquilibriumFixed(TypedDict):
    """Resultado del equilibrio bajo tipo de cambio fijo."""
    Y:      float   # Ingreso/PIB de equilibrio
    r:      float   # Tasa de interés de equilibrio (= r*)
    E:      float   # Tipo de cambio (exógeno, fijo)
    M_endo: float   # Oferta monetaria endógena
    NX:     float   # Exportaciones netas de equilibrio
    C:      float   # Consumo privado de equilibrio
    I_inv:  float   # Inversión de equilibrio
    mult:   float   # Multiplicador keynesiano


class EquilibriumFlexible(TypedDict):
    """Resultado del equilibrio bajo tipo de cambio flexible."""
    Y:      float   # Ingreso/PIB de equilibrio
    r:      float   # Tasa de interés de equilibrio (= r*)
    E_endo: float   # Tipo de cambio endógeno
    M:      float   # Oferta monetaria (exógena)
    NX:     float   # Exportaciones netas de equilibrio
    C:      float   # Consumo privado de equilibrio
    I_inv:  float   # Inversión de equilibrio
    mult:   float   # Multiplicador keynesiano


# ── Componentes del modelo ───────────────────────────────────────────────────

def autonomous_demand(
    c0: float,
    c1: float,
    T: float,
    I0: float,
    G: float,
    NX0: float,
) -> float:
    """
    Calcula la demanda autónoma agregada (A).

    A = c0 - c1*T + I0 + G + NX0

    Parameters
    ----------
    c0  : Consumo autónomo
    c1  : Propensión marginal a consumir
    T   : Impuestos lump-sum
    I0  : Inversión autónoma
    G   : Gasto de gobierno
    NX0 : Exportaciones netas autónomas

    Returns
    -------
    float : Demanda autónoma agregada
    """
    return c0 - c1 * T + I0 + G + NX0


def multiplier(c1: float, m1: float) -> float:
    """
    Calcula el multiplicador keynesiano de economía abierta.

    mult = 1 / (1 - c1 + m1)

    Parameters
    ----------
    c1 : Propensión marginal a consumir
    m1 : Propensión marginal a importar

    Returns
    -------
    float : Multiplicador keynesiano

    Raises
    ------
    ValueError
        Si el denominador es cero o negativo (modelo inestable).
    """
    denominator = 1.0 - c1 + m1
    if denominator <= 0.0:
        raise ValueError(
            f"Multiplicador indefinido: (1 - c1 + m1) = {denominator:.4f}. "
            "El modelo requiere (1 - c1 + m1) > 0."
        )
    return 1.0 / denominator


def is_curve(
    Y: float,
    c1: float,
    m1: float,
    b: float,
    A: float,
    x1: float,
    E: float,
) -> float:
    """
    Curva IS: tasa de interés como función del ingreso.

    r_IS = (A + x1*E - Y*(1 - c1 + m1)) / b

    Parameters
    ----------
    Y   : Nivel de ingreso
    c1  : Propensión marginal a consumir
    m1  : Propensión marginal a importar
    b   : Sensibilidad inversión–tasa de interés
    A   : Demanda autónoma
    x1  : Sensibilidad exportaciones–tipo de cambio
    E   : Tipo de cambio nominal

    Returns
    -------
    float : Tasa de interés sobre la curva IS
    """
    if b <= 0.0:
        raise ValueError(f"Parámetro b debe ser positivo, recibido b={b}")
    return (A + x1 * E - Y * (1.0 - c1 + m1)) / b


def lm_curve(Y: float, k: float, M: float, h: float) -> float:
    """
    Curva LM: tasa de interés como función del ingreso.

    r_LM = (k*Y - M) / h

    Parameters
    ----------
    Y : Nivel de ingreso
    k : Sensibilidad demanda de dinero al ingreso
    M : Oferta monetaria
    h : Sensibilidad demanda de dinero a la tasa de interés

    Returns
    -------
    float : Tasa de interés sobre la curva LM
    """
    if h <= 0.0:
        raise ValueError(f"Parámetro h debe ser positivo, recibido h={h}")
    return (k * Y - M) / h


def bp_curve(r_star: float) -> float:
    """
    Curva BP: condición de movilidad perfecta de capitales.

    r_BP = r*  (la tasa doméstica iguala la tasa internacional)

    Parameters
    ----------
    r_star : Tasa de interés internacional

    Returns
    -------
    float : Tasa de interés de equilibrio externo
    """
    return r_star


# ── Equilibrios del modelo ───────────────────────────────────────────────────

def eq_fixed(p: dict[str, float]) -> EquilibriumFixed:
    """
    Calcula el equilibrio IS-LM-BP bajo tipo de cambio FIJO.

    Bajo TC fijo, el banco central acomoda la oferta monetaria (M endógena)
    para mantener r = r*. El tipo de cambio E es exógeno.

    Ecuaciones de solución:
        Y      = mult * (A + x1*E - b*r*)
        M_endo = k*Y - h*r*

    Parameters
    ----------
    p : dict con claves requeridas:
        c0, c1, T, I0, G, NX0, b, x1, k, h, E, r_star, m1

    Returns
    -------
    EquilibriumFixed : Dict tipado con Y, r, E, M_endo, NX, C, I_inv, mult

    Raises
    ------
    ValueError
        Si los valores de equilibrio están fuera del dominio económico válido.
    """
    # Extraer parámetros
    c0     = p["c0"]
    c1     = p["c1"]
    T      = p["T"]
    I0     = p["I0"]
    G      = p["G"]
    NX0    = p["NX0"]
    b      = p["b"]
    x1     = p["x1"]
    k      = p["k"]
    h      = p["h"]
    E      = p["E"]
    r_star = p["r_star"]
    m1     = p["m1"]

    # Cálculos intermedios
    A    = autonomous_demand(c0, c1, T, I0, G, NX0)
    mult = multiplier(c1, m1)

    # Solución de equilibrio — TC fijo
    r      = bp_curve(r_star)
    Y      = mult * (A + x1 * E - b * r)
    M_endo = k * Y - h * r

    # Variables derivadas
    C     = c0 + c1 * (Y - T)
    I_inv = I0 - b * r          # Inversión neta de la tasa de interés
    NX    = NX0 + x1 * E        # Exportaciones netas en equilibrio

    # Validación de dominio económico (no-estricto: warnings para shocks extremos)
    _validate_equilibrium(Y=Y, r=r, label="TC Fijo", strict=False)

    return EquilibriumFixed(
        Y=round(Y, 6),
        r=round(r, 6),
        E=round(E, 6),
        M_endo=round(M_endo, 6),
        NX=round(NX, 6),
        C=round(C, 6),
        I_inv=round(I_inv, 6),
        mult=round(mult, 6),
    )


def eq_flexible(p: dict[str, float]) -> EquilibriumFlexible:
    """
    Calcula el equilibrio IS-LM-BP bajo tipo de cambio FLEXIBLE.

    Bajo TC flexible, la oferta monetaria M es exógena y el tipo de cambio
    E se ajusta endógenamente para limpiar el mercado externo.

    Ecuaciones de solución:
        Y      = (M + h*r*) / k
        E_endo = ((1 - c1 + m1)*Y + b*r* - A) / x1

    Parameters
    ----------
    p : dict con claves requeridas:
        c0, c1, T, I0, G, NX0, b, x1, k, h, M, r_star, m1

    Returns
    -------
    EquilibriumFlexible : Dict tipado con Y, r, E_endo, M, NX, C, I_inv, mult

    Raises
    ------
    ValueError
        Si los valores de equilibrio están fuera del dominio económico válido.
    """
    # Extraer parámetros
    c0     = p["c0"]
    c1     = p["c1"]
    T      = p["T"]
    I0     = p["I0"]
    G      = p["G"]
    NX0    = p["NX0"]
    b      = p["b"]
    x1     = p["x1"]
    k      = p["k"]
    h      = p["h"]
    M      = p["M"]
    r_star = p["r_star"]
    m1     = p["m1"]

    # Cálculos intermedios
    A    = autonomous_demand(c0, c1, T, I0, G, NX0)
    mult = multiplier(c1, m1)

    # Solución de equilibrio — TC flexible
    r      = bp_curve(r_star)
    Y      = (M + h * r) / k
    E_endo = ((1.0 - c1 + m1) * Y + b * r - A) / x1

    # Variables derivadas
    C     = c0 + c1 * (Y - T)
    I_inv = I0 - b * r
    NX    = NX0 + x1 * E_endo

    # Validación de dominio económico (no-estricto: warnings para shocks extremos)
    _validate_equilibrium(Y=Y, r=r, label="TC Flexible", strict=False)

    return EquilibriumFlexible(
        Y=round(Y, 6),
        r=round(r, 6),
        E_endo=round(E_endo, 6),
        M=round(M, 6),
        NX=round(NX, 6),
        C=round(C, 6),
        I_inv=round(I_inv, 6),
        mult=round(mult, 6),
    )


# ── Validación de dominio ────────────────────────────────────────────────────

def _validate_equilibrium(Y: float, r: float, label: str = "", strict: bool = True) -> None:
    """
    Verifica que los valores de equilibrio sean económicamente válidos.

    Parameters
    ----------
    Y      : Ingreso de equilibrio (debe ser positivo)
    r      : Tasa de interés (debe ser no negativa)
    label  : Etiqueta para mensajes de error
    strict : Si True, lanza ValueError. Si False, imprime advertencia.

    Raises
    ------
    ValueError
        Si Y <= 0 o r < 0 y strict=True.
    """
    prefix = f"[{label}] " if label else ""
    issues = []
    if Y <= 0.0:
        issues.append(
            f"{prefix}Y = {Y:.4f} (ingreso negativo — posible colapso de demanda agregada)"
        )
    if r < 0.0:
        issues.append(
            f"{prefix}r = {r:.4f} (tasa de interes negativa)"
        )
    if issues:
        msg = "Equilibrio fuera de dominio economico valido:\n  " + "\n  ".join(issues)
        if strict:
            raise ValueError(msg)
        else:
            print(f"[ADVERTENCIA] {msg}")
