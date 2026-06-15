"""
engine/monetary_rule.py
=======================
Módulo de Política Monetaria Moderna (V3.0 — Reforma 2A).

Implementa el paradigma de Metas de Inflación (Inflation Targeting) donde
el instrumento primario del banco central es la Tasa de Política Monetaria
(TPM / r_ref) y la Oferta Monetaria (M) se convierte en una variable
endógena pasiva.

Bajo monetary_mode = "rate_targeting":
    - El banco central fija r_ref.
    - La curva LM se transforma en una recta horizontal en r = r_ref.
    - M_implicit se calcula ex-post a partir de la ecuación de demanda real.

Bajo monetary_mode = "quantity" (default retrocompat.):
    - El banco central controla M directamente (enfoque monetarista clásico).
    - Comportamiento idéntico a V2.0.

Jerarquía:
    config/parameters_v2.py → engine/monetary_rule.py → engine/core_v2.py
"""

from __future__ import annotations


def apply_taylor_rule(
    r_neutral: float,
    pi_t: float,
    pi_target: float,
    gap: float,
    phi_pi: float = 1.5,
    phi_Y: float = 0.5,
) -> float:
    """
    Regla de Taylor: calcula la Tasa de Política Monetaria óptima.

    r_ref = r_neutral + phi_pi * (pi - pi*) + phi_Y * gap

    La Regla de Taylor (John Taylor, 1993) establece que el banco central
    debería responder de forma sistemática a las desviaciones de la inflación
    respecto a su meta y al output gap para estabilizar la economía.

    Parámetros estándar calibrados (Clarida, Galí & Gertler 1999):
    - phi_pi = 1.5: coeficiente de inflación (debe ser > 1 para satisfacer el
                    Principio de Taylor y garantizar la estabilización).
    - phi_Y  = 0.5: coeficiente del output gap.

    Parameters
    ----------
    r_neutral  : Tasa de interés neutral / natural de largo plazo (r*)
    pi_t       : Inflación observada del período actual
    pi_target  : Meta de inflación del banco central (típicamente 3%)
    gap        : Brecha del producto (Y - Y_pot) / Y_pot
    phi_pi     : Coeficiente de respuesta a la inflación (default: 1.5)
    phi_Y      : Coeficiente de respuesta al output gap (default: 0.5)

    Returns
    -------
    float : Tasa de política monetaria sugerida por la Regla de Taylor (en %)
    """
    inflation_gap = pi_t - pi_target        # Desviación de la meta de inflación
    r_taylor = r_neutral + phi_pi * inflation_gap * 100.0 + phi_Y * gap * 100.0
    return max(0.0, r_taylor)               # Zero lower bound: r_ref ≥ 0


def compute_implied_M(
    r_ref: float,
    Y: float,
    k: float,
    h: float,
    P_local: float,
    velocity_penalty: float = 1.0,
) -> float:
    """
    Calcula la Oferta Monetaria Implícita bajo rate_targeting mode.

    Despejando M de la curva LM (r_ref = (k·Y - M_real) / h):

        M_real = k·Y - h·r_ref
        M_implicit = M_real · P_local · velocity_penalty

    Esta es la cantidad de dinero que el banco central debe proveer
    para que el mercado de dinero se vacíe exactamente en r = r_ref,
    dado el nivel de ingreso Y de equilibrio IS-BP.

    Parameters
    ----------
    r_ref           : Tasa de política monetaria fijada por el banco central
    Y               : PIB de equilibrio del período (de la intersección IS-BP)
    k               : Sensibilidad de la demanda de dinero al ingreso
    h               : Sensibilidad de la demanda de dinero a la tasa de interés
    P_local         : Nivel de precios doméstico
    velocity_penalty: Factor de penalización de velocidad monetaria (default: 1.0)

    Returns
    -------
    float : Oferta monetaria nominal implícita M
    """
    M_real = max(0.0, k * Y - h * r_ref)
    return M_real * P_local * velocity_penalty
