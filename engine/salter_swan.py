"""
engine/salter_swan.py
=====================
Implementación del modelo Salter-Swan para economía abierta pequeña.

El modelo Salter-Swan analiza el equilibrio simultáneo de:
    - Balance Interno (IB): pleno empleo / estabilidad de precios
    - Balance Externo (EB): equilibrio de cuenta corriente

Instrumentos:
    - Absorción doméstica (A): política fiscal/monetaria
    - Tipo de cambio real (q): política cambiaria

Zonas de desequilibrio (I a IV):
    Zona I   : q > IB  y  q > EB  → Superávit externo + Sobreempleo
    Zona II  : q < IB  y  q > EB  → Superávit externo + Desempleo
    Zona III : q < IB  y  q < EB  → Déficit externo + Desempleo
    Zona IV  : q > IB  y  q < EB  → Déficit externo + Sobreempleo

Nota: q es el tipo de cambio real (↑q = depreciación real = mejora competitividad)
"""

from __future__ import annotations

from typing import TypedDict


# ── Tipos de retorno ─────────────────────────────────────────────────────────

class SalterSwanZone(TypedDict):
    """Resultado del análisis de zona Salter-Swan."""
    zone:      str    # "I", "II", "III" o "IV"
    diagnosis: str    # Descripción del desequilibrio
    policy:    str    # Recomendación de política económica
    q_IB:      float  # Umbral de la curva de Balance Interno
    q_EB:      float  # Umbral de la curva de Balance Externo
    q:         float  # Tipo de cambio real actual
    A:         float  # Absorción doméstica actual


# ── Curvas de equilibrio ─────────────────────────────────────────────────────

def q_IB(A: float) -> float:
    """
    Curva de Balance Interno (IB) en el espacio (A, q).

    Pendiente negativa: mayor absorción requiere menor tipo de cambio real
    (apreciación) para mantener el pleno empleo.

    q_IB(A) = 1.0 - 0.005 * (A - 100)

    Parameters
    ----------
    A : float
        Absorción doméstica (gasto total de la economía)

    Returns
    -------
    float : Tipo de cambio real de Balance Interno
    """
    return 1.0 - 0.005 * (A - 100.0)


def q_EB(A: float) -> float:
    """
    Curva de Balance Externo (EB) en el espacio (A, q).

    Pendiente positiva: mayor absorción requiere mayor tipo de cambio real
    (depreciación) para mantener el equilibrio externo.

    q_EB(A) = 1.0 + 0.005 * (A - 100)

    Parameters
    ----------
    A : float
        Absorción doméstica (gasto total de la economía)

    Returns
    -------
    float : Tipo de cambio real de Balance Externo
    """
    return 1.0 + 0.005 * (A - 100.0)


# ── Diagnóstico y política ───────────────────────────────────────────────────

# Mapa de zona → (diagnóstico económico, recomendación de política)
_ZONE_MAP: dict[str, tuple[str, str]] = {
    "I": (
        "Superávit de cuenta corriente + Sobreempleo (presiones inflacionarias). "
        "La economía está por encima del pleno empleo con saldo externo positivo.",
        "Apreciar el tipo de cambio real (revaluar E) Y/O contraer la absorción "
        "(política fiscal contractiva). Objetivo: enfriar demanda sin comprometer externo.",
    ),
    "II": (
        "Superávit de cuenta corriente + Desempleo (capacidad ociosa). "
        "La economía tiene exceso de oferta con saldo externo favorable.",
        "Expandir la absorción doméstica (política fiscal expansiva) Y mantener "
        "o apreciar moderadamente el tipo de cambio. Objetivo: estimular demanda interna.",
    ),
    "III": (
        "Déficit de cuenta corriente + Desempleo (el peor escenario). "
        "Presión simultánea sobre reservas y empleo — dilema de política.",
        "Depreciar el tipo de cambio real (devaluar E) PARA mejorar competitividad, "
        "con contención fiscal moderada. PRECAUCIÓN: riesgo de espiral inflacionaria.",
    ),
    "IV": (
        "Déficit de cuenta corriente + Sobreempleo (economía recalentada). "
        "Alta demanda presiona precios e importaciones simultáneamente.",
        "Contraer absorción (política fiscal restrictiva) Y depreciar el tipo de "
        "cambio real para reequilibrar la cuenta corriente. Política dual necesaria.",
    ),
}


def get_zone(A: float, q: float) -> SalterSwanZone:
    """
    Determina la zona de desequilibrio Salter-Swan y la política recomendada.

    Clasificación según posición relativa a las curvas IB y EB:
        Zona I   : q > q_IB(A)  y  q > q_EB(A)
        Zona II  : q < q_IB(A)  y  q > q_EB(A)
        Zona III : q < q_IB(A)  y  q < q_EB(A)
        Zona IV  : q > q_IB(A)  y  q < q_EB(A)

    Parameters
    ----------
    A : float
        Absorción doméstica (nivel de gasto agregado de la economía)
    q : float
        Tipo de cambio real actual

    Returns
    -------
    SalterSwanZone : Diccionario tipado con zona, diagnóstico y política

    Raises
    ------
    ValueError
        Si q ≤ 0 (tipo de cambio real debe ser positivo).
    """
    if q <= 0.0:
        raise ValueError(
            f"El tipo de cambio real q debe ser positivo, recibido q={q:.4f}."
        )

    # Umbrales de las curvas en el nivel de absorción A
    threshold_IB = q_IB(A)
    threshold_EB = q_EB(A)

    # Clasificación por zona
    above_IB = q > threshold_IB
    above_EB = q > threshold_EB

    if above_IB and above_EB:
        zone = "I"
    elif (not above_IB) and above_EB:
        zone = "II"
    elif (not above_IB) and (not above_EB):
        zone = "III"
    else:  # above_IB and not above_EB
        zone = "IV"

    diagnosis, policy = _ZONE_MAP[zone]

    return SalterSwanZone(
        zone=zone,
        diagnosis=diagnosis,
        policy=policy,
        q_IB=round(threshold_IB, 6),
        q_EB=round(threshold_EB, 6),
        q=round(q, 6),
        A=round(A, 6),
    )
