"""
config/parameters.py
====================
Carga de parámetros base del modelo Mundell-Fleming + Salter-Swan.
Fuente: Sección 3.1 del documento de referencia académico.

Responsabilidades:
    - Cargar .env con python-dotenv (fallback a valores hardcoded).
    - Exportar get_base_params() → dict tipado.
    - Definir CRISIS_PRESETS con escenarios de crisis económica.
    - Exportar apply_shocks() → fusiona parámetros base con preset.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# ── Carga del archivo .env (si existe) ──────────────────────────────────────
_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)

# ── Fallback: valores hardcoded de la Sección 3.1 ───────────────────────────
_FALLBACK: dict[str, float] = {
    "c0":     10.0,    # Consumo autónomo
    "c1":     0.75,    # Propensión marginal a consumir
    "I0":     15.0,    # Inversión autónoma
    "NX0":    5.0,     # Exportaciones netas autónomas
    "b":      2.0,     # Sensibilidad inversión–tasa de interés
    "m1":     0.15,    # Sensibilidad demanda dinero–ingreso (también 'k')
    "x1":     1.5,     # Sensibilidad exportaciones–tipo de cambio
    "k":      0.5,     # Parámetro k de la curva LM
    "h":      2.0,     # Sensibilidad demanda dinero–tasa de interés
    "G":      20.0,    # Gasto de gobierno
    "T":      20.0,    # Impuestos lump-sum
    "E":      10.0,    # Tipo de cambio nominal (régimen fijo)
    "r_star": 5.0,     # Tasa de interés internacional
    "M":      40.0,    # Oferta de dinero (régimen flexible)
}

# Mapa de variables de entorno → clave interna del modelo
_ENV_MAP: dict[str, str] = {
    "BASE_C0":   "c0",
    "BASE_C1":   "c1",
    "BASE_I0":   "I0",
    "BASE_NX0":  "NX0",
    "BASE_B":    "b",
    "BASE_M1":   "m1",
    "BASE_X1":   "x1",
    "BASE_K_LM": "k",
    "BASE_H":    "h",
    "BASE_G":    "G",
    "BASE_T":    "T",
    "BASE_E":    "E",
    "BASE_RS":   "r_star",
    "BASE_M":    "M",
}

# ── Presets de crisis económica ──────────────────────────────────────────────
CRISIS_PRESETS: dict[str, dict[str, float]] = {
    # Bolivia 2024 — Estanflación con restricción de divisas y caída de reservas
    "Bolivia_2024_Stagflation": {
        "NX0":    -3.0,   # Déficit de exportaciones netas
        "I0":     -5.0,   # Contracción de inversión privada
        "G":      15.0,   # Ajuste fiscal (reducción del gasto)
        "c1":     0.65,   # Caída en propensión marginal (incertidumbre)
        "r_star":  8.0,   # Prima de riesgo país elevada
        "m1":     0.25,   # Mayor demanda de liquidez preventiva
        "x1":      1.0,   # Menor elasticidad de exportaciones al tipo de cambio
        "h":       1.2,   # Menor sensibilidad de demanda dinero a tasa de interés
    },
    # Shock de demanda externa positivo (escenario de bonanza)
    "Boom_Exportador": {
        "NX0":    15.0,
        "x1":      2.0,
        "r_star":  3.0,
        "G":      22.0,
    },
    # Crisis de liquidez / credit crunch
    "Credit_Crunch": {
        "I0":    -10.0,
        "c1":     0.60,
        "h":      0.8,
        "r_star": 10.0,
        "G":      25.0,
    },
}


def get_base_params() -> dict[str, float]:
    """
    Retorna el diccionario de parámetros base del modelo.

    Prioridad:
        1. Variables de entorno definidas en .env
        2. Valores fallback hardcoded de la Sección 3.1

    Returns
    -------
    dict[str, float]
        Parámetros tipados del modelo macroeconómico.
    """
    params: dict[str, float] = dict(_FALLBACK)  # copia defensiva

    for env_key, param_key in _ENV_MAP.items():
        raw = os.environ.get(env_key)
        if raw is not None:
            try:
                params[param_key] = float(raw)
            except ValueError:
                # Mantiene el fallback si el valor en .env no es numérico
                pass

    return params


def apply_shocks(
    base_params: dict[str, float],
    preset_key: str,
) -> dict[str, float]:
    """
    Fusiona los parámetros base con un preset de crisis.

    Parameters
    ----------
    base_params : dict[str, float]
        Parámetros base obtenidos de get_base_params().
    preset_key : str
        Clave del preset en CRISIS_PRESETS.

    Returns
    -------
    dict[str, float]
        Parámetros fusionados (base + shocks del preset).

    Raises
    ------
    KeyError
        Si el preset_key no existe en CRISIS_PRESETS.
    """
    if preset_key not in CRISIS_PRESETS:
        available = list(CRISIS_PRESETS.keys())
        raise KeyError(
            f"Preset '{preset_key}' no encontrado. "
            f"Opciones disponibles: {available}"
        )

    shocked: dict[str, float] = dict(base_params)
    shocked.update(CRISIS_PRESETS[preset_key])
    return shocked
