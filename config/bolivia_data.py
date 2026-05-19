"""
config/bolivia_data.py
======================
Presets históricos de Bolivia para calibración del modelo Mundell-Fleming.
Fase 4 — Plataforma de Análisis de Políticas.

Fuentes de referencia (aproximadas para calibración académica):
    - INE Bolivia: Indicadores macroeconómicos 2008–2024
    - CEPAL: Anuario estadístico de América Latina y el Caribe
    - BCB: Boletín del Sector Externo

Convención de parámetros (compatibles con engine/core.py):
    c0, c1, I0, NX0, b, m1, x1, k, h, G, T, E, r_star, M
"""

from __future__ import annotations

from typing import Literal

# ── Tipo de régimen cambiario ─────────────────────────────────────────────────
ExchangeRegime = Literal["fixed", "flexible", "managed_float", "de_facto_fixed"]
CapitalMobility = Literal["perfect", "imperfect", "low"]
EconomySize     = Literal["small_open", "large_semi_closed"]


# ── Presets históricos Bolivia ────────────────────────────────────────────────
# Todos los parámetros son compatibles con eq_fixed() y eq_flexible() de core.py
# Los valores son calibraciones académicas basadas en proporciones del PIB.
# El modelo opera en unidades relativas; Y_base≈100 representa el PIB normalizado.

BOLIVIA_PRESETS: dict[str, dict] = {

    # ── 2024: Estanflación y restricción de divisas ───────────────────────────
    "Bolivia_2024_Stagflation": {
        # Metadatos económicos
        "_meta": {
            "label":            "Bolivia 2024 — Estanflación",
            "description":      (
                "Economía bajo presión de reservas internacionales (< 3.2 meses de importaciones), "
                "déficit fiscal persistente (~4.5% PIB), baja inversión privada por incertidumbre "
                "cambiaria, y tipo de cambio de facto fijo ante escasez de divisas."
            ),
            "GDP_nominal_usd":       45e9,
            "GDP_growth_pct":        1.2,
            "unemployment_pct":      3.8,
            "inflation_pct":         3.2,
            "fiscal_balance_pct_gdp": -4.5,
            "reserves_months_imports": 3.2,
            "exchange_regime":       "de_facto_fixed",
            "capital_mobility":      "imperfect",
            "openness_ratio":        0.42,
        },
        # Parámetros del modelo (normalizados, Y_base≈100)
        "c0":    8.0,    # Consumo autónomo bajo (incertidumbre alta)
        "c1":    0.78,   # PMgC relativamente alta (falta de ahorro)
        "I0":   -5.0,    # Inversión autónoma negativa (contracción privada)
        "NX0":  -3.0,    # Déficit estructural de exportaciones netas
        "b":     2.2,    # Sensibilidad inversión a r (moderada)
        "m1":    0.22,   # PMgM alta (dependencia de importaciones)
        "x1":    1.3,    # Elasticidad export–TC reducida (exportaciones primarias inelásticas)
        "k":     0.45,   # Demanda dinero–ingreso (baja dolarización informal)
        "h":     1.8,    # Demanda dinero–tasa (moderada)
        "G":     18.0,   # Gasto público ajustado (presión fiscal)
        "T":     14.0,   # Carga impositiva moderada
        "E":     6.96,   # Tipo de cambio nominal oficial (Bs/USD ≈ 6.96)
        "r_star": 8.0,   # Prima de riesgo país elevada (EMBIG Bolivia)
        "M":     35.0,   # Oferta monetaria reducida (restricción BCB)
    },

    # ── 2019: Precrisis política y desaceleración ─────────────────────────────
    "Bolivia_2019_PreCrisis": {
        "_meta": {
            "label":            "Bolivia 2019 — Precrisis Política",
            "description":      (
                "Año de turbulencia política post-elecciones. Desaceleración del crecimiento "
                "desde niveles del boom, reservas aún aceptables (~7 meses de importaciones), "
                "pero inicio de la caída del precio del gas y presión en la cuenta corriente."
            ),
            "GDP_nominal_usd":       40.9e9,
            "GDP_growth_pct":        2.2,
            "unemployment_pct":      4.0,
            "inflation_pct":         1.8,
            "fiscal_balance_pct_gdp": -7.2,
            "reserves_months_imports": 7.0,
            "exchange_regime":       "de_facto_fixed",
            "capital_mobility":      "imperfect",
            "openness_ratio":        0.45,
        },
        "c0":    10.0,
        "c1":    0.75,
        "I0":     5.0,
        "NX0":    0.5,
        "b":      2.5,
        "m1":     0.20,
        "x1":     1.4,
        "k":      0.48,
        "h":      2.0,
        "G":      22.0,
        "T":      16.0,
        "E":      6.91,
        "r_star":  6.0,
        "M":      42.0,
    },

    # ── 2014: Auge de materias primas ─────────────────────────────────────────
    "Bolivia_2014_Boom": {
        "_meta": {
            "label":            "Bolivia 2014 — Boom de Materias Primas",
            "description":      (
                "Pico del superciclo de materias primas. Superávit fiscal y comercial, "
                "alto precio del gas, reservas internacionales en máximos históricos "
                "(~15 meses de importaciones). Inversión pública masiva y crecimiento > 5%."
            ),
            "GDP_nominal_usd":       33.0e9,
            "GDP_growth_pct":        5.5,
            "unemployment_pct":      3.5,
            "inflation_pct":         5.2,
            "fiscal_balance_pct_gdp": 1.8,
            "reserves_months_imports": 15.0,
            "exchange_regime":       "de_facto_fixed",
            "capital_mobility":      "imperfect",
            "openness_ratio":        0.55,
        },
        "c0":    12.0,
        "c1":    0.72,
        "I0":    12.0,
        "NX0":    8.0,
        "b":      2.8,
        "m1":     0.18,
        "x1":     1.8,
        "k":      0.52,
        "h":      2.2,
        "G":      28.0,
        "T":      20.0,
        "E":      6.87,
        "r_star":  4.0,
        "M":      55.0,
    },

    # ── 2008: Crisis financiera global ────────────────────────────────────────
    "Bolivia_2008_GlobalCrisis": {
        "_meta": {
            "label":            "Bolivia 2008 — Crisis Financiera Global",
            "description":      (
                "Impacto de la crisis financiera global. Caída de exportaciones, "
                "presión sobre el tipo de cambio (Bolivia devalúa levemente), "
                "pero colchón de reservas permite amortiguación. Primer año sin superávit fiscal."
            ),
            "GDP_nominal_usd":       16.7e9,
            "GDP_growth_pct":        6.1,
            "unemployment_pct":      6.7,
            "inflation_pct":        11.8,
            "fiscal_balance_pct_gdp": -0.5,
            "reserves_months_imports": 10.0,
            "exchange_regime":       "managed_float",
            "capital_mobility":      "low",
            "openness_ratio":        0.62,
        },
        "c0":    9.0,
        "c1":    0.70,
        "I0":    8.0,
        "NX0":   5.0,
        "b":     2.0,
        "m1":    0.16,
        "x1":    1.6,
        "k":     0.50,
        "h":     1.5,
        "G":     24.0,
        "T":     18.0,
        "E":     7.07,
        "r_star": 7.5,
        "M":     38.0,
    },

    # ── Hipotético: Ajuste y liberalización ───────────────────────────────────
    "Bolivia_Hypothetical_Reform": {
        "_meta": {
            "label":            "Bolivia Hipotético — Reforma Estructural",
            "description":      (
                "Escenario hipotético de reforma: liberalización parcial del tipo de cambio, "
                "reducción del déficit fiscal, mejora de reservas internacionales y "
                "apertura a inversión extranjera. Sirve como benchmark de política óptima."
            ),
            "GDP_nominal_usd":       50e9,
            "GDP_growth_pct":        4.0,
            "unemployment_pct":      4.5,
            "inflation_pct":         4.0,
            "fiscal_balance_pct_gdp": -2.0,
            "reserves_months_imports": 8.0,
            "exchange_regime":       "managed_float",
            "capital_mobility":      "imperfect",
            "openness_ratio":        0.50,
        },
        "c0":    11.0,
        "c1":    0.73,
        "I0":    10.0,
        "NX0":   2.0,
        "b":     2.5,
        "m1":    0.19,
        "x1":    1.6,
        "k":     0.48,
        "h":     2.0,
        "G":     20.0,
        "T":     17.0,
        "E":     7.50,
        "r_star": 5.5,
        "M":     40.0,
    },
}


# ── Funciones públicas ────────────────────────────────────────────────────────

def get_bolivia_params(key: str) -> dict[str, float]:
    """
    Retorna los parámetros del modelo para un preset boliviano dado.
    Filtra los metadatos (_meta) y retorna solo parámetros numéricos
    compatibles con eq_fixed() y eq_flexible() de engine/core.py.

    Parameters
    ----------
    key : str
        Clave del preset en BOLIVIA_PRESETS.
        Opciones: 'Bolivia_2024_Stagflation', 'Bolivia_2019_PreCrisis',
                  'Bolivia_2014_Boom', 'Bolivia_2008_GlobalCrisis',
                  'Bolivia_Hypothetical_Reform'

    Returns
    -------
    dict[str, float]
        Parámetros listos para pasar a eq_fixed() o eq_flexible().

    Raises
    ------
    KeyError
        Si el key no existe en BOLIVIA_PRESETS.
    """
    if key not in BOLIVIA_PRESETS:
        available = list(BOLIVIA_PRESETS.keys())
        raise KeyError(
            f"Preset '{key}' no encontrado. Disponibles: {available}"
        )
    raw = BOLIVIA_PRESETS[key]
    # Retorna solo claves numéricas (excluye _meta)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def get_bolivia_meta(key: str) -> dict:
    """
    Retorna los metadatos económicos de un preset boliviano.

    Parameters
    ----------
    key : str
        Clave del preset en BOLIVIA_PRESETS.

    Returns
    -------
    dict con GDP_nominal_usd, GDP_growth_pct, unemployment_pct, etc.
    """
    if key not in BOLIVIA_PRESETS:
        return {}
    return BOLIVIA_PRESETS[key].get("_meta", {})


def classify_economy_size(GDP_usd: float, openness_ratio: float) -> EconomySize:
    """
    Clasifica el tamaño relativo de la economía según el PIB nominal
    y el ratio de apertura comercial (exportaciones + importaciones / PIB).

    Criterios (académicos, no oficiales):
        - small_open  : PIB < 100 billion USD Y openness_ratio > 0.35
        - large_semi_closed : PIB >= 100 billion USD O openness_ratio <= 0.35

    Parameters
    ----------
    GDP_usd : float
        PIB nominal en USD.
    openness_ratio : float
        (Exportaciones + Importaciones) / PIB. Rango [0, 1].

    Returns
    -------
    EconomySize : "small_open" | "large_semi_closed"
    """
    if GDP_usd < 100e9 and openness_ratio > 0.35:
        return "small_open"
    return "large_semi_closed"


def list_presets() -> list[dict]:
    """
    Retorna lista de presets con clave, label y descripción para UI.

    Returns
    -------
    list[dict] con keys: 'key', 'label', 'description', 'year_approx'
    """
    result = []
    for key, data in BOLIVIA_PRESETS.items():
        meta = data.get("_meta", {})
        result.append({
            "key":         key,
            "label":       meta.get("label", key),
            "description": meta.get("description", ""),
            "exchange_regime":   meta.get("exchange_regime", "—"),
            "capital_mobility":  meta.get("capital_mobility", "—"),
            "GDP_growth_pct":    meta.get("GDP_growth_pct", float("nan")),
            "inflation_pct":     meta.get("inflation_pct", float("nan")),
        })
    return result
