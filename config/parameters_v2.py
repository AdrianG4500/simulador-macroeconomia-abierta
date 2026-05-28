"""
config/parameters_v2.py
=======================
Parámetros estructurales del modelo Mundell-Fleming V2.0 (Economía Abierta).

V2.0 introduce:
  - Impuesto proporcional `t` (reemplaza lump-sum T).
  - Elasticidades Marshall-Lerner (epsilon_x, epsilon_m).
  - Movilidad imperfecta de capitales `f`.
  - Pass-through cambiario (alpha_PT, beta_PT).
  - Crecimiento potencial `g_pot`.
  - 4 escenarios de onboarding con parámetros completos.

Flujo unidireccional: config → engine → state → ui.
Este módulo NO importa de engine/ ni de ui/.
"""

from __future__ import annotations

from typing import Optional, TypedDict


# ── Tipos de datos ────────────────────────────────────────────────────────────

class StructuralParams(TypedDict):
    """
    Parámetros estructurales que definen la economía.
    No cambian turno a turno salvo por eventos endógenos.
    """
    # Bloque consumo e inversión
    c0:        float   # Consumo autónomo
    c1:        float   # Propensión marginal a consumir
    t:         float   # Tasa impositiva proporcional (∈ [0,1]) — retrocompat. con t_c
    I0:        float   # Inversión autónoma
    b:         float   # Sensibilidad inversión–tasa de interés
    rho_k:     float   # Sensibilidad de inversión a impuestos corporativos
    NX0:       float   # Exportaciones netas autónomas

    # Bloque sector externo desagregado
    x0:        float   # Exportaciones autónomas (nivel base)
    x1:        float   # Sensibilidad exportaciones a demanda externa (Y_star)
    Y_star:    float   # PIB del resto del mundo (exógeno)
    m0:        float   # Importaciones autónomas (nivel base)

    # Bloque comercio exterior y tipo de cambio
    epsilon_x: float   # Elasticidad-precio de exportaciones (condición M-L)
    epsilon_m: float   # Elasticidad-precio de importaciones (condición M-L)
    m1:        float   # Propensión marginal a importar

    # Bloque monetario
    k:         float   # Sensibilidad demanda de dinero al ingreso
    h:         float   # Sensibilidad demanda de dinero a la tasa de interés

    # Bloque movilidad de capitales
    f:         float   # Parámetro de movilidad de capitales (∞ = perfecta)

    # Bloque pass-through cambiario
    alpha_PT:  float   # Peso bienes transables en índice de precios [0,1]
    beta_PT:   float   # Coeficiente pass-through en curva de Phillips [0,0.5]
    P_star:    float   # Nivel de precios externo (base = 1.0)

    # Bloque producto potencial
    Y_pot_0:   float   # PIB potencial inicial
    g_pot:     float   # Tasa de crecimiento del PIB potencial

    # Bloque mercado laboral y precios
    U_n:        float  # NAIRU (tasa natural de desempleo)
    gamma_okun: float  # Coeficiente de la Ley de Okun
    alpha_inf:  float  # Pendiente de la curva de Phillips
    pi_0:       float  # Inflación base adicional (estanflación)
    G_needed:   float  # Gasto de reconstrucción requerido (desastre natural)


class PolicyInstruments(TypedDict):
    """
    Variables controladas por el jugador cada turno.
    El régimen cambiario determina cuál instrumento es exógeno.
    """
    # Gasto fiscal desagregado (G_total = G_c + I_g)
    G_c:         float  # Gasto corriente del gobierno
    I_g:         float  # Inversión pública
    Tr:          float  # Transferencias a hogares (afecta demanda vía consumo)

    # Tributación dual
    t_c:         float  # Tasa impositiva al consumo / ingreso (reemplaza 't')
    t_k:         float  # Tasa impositiva corporativa (afecta I_inv vía rho_k)

    # Instrumentos comerciales
    tau:         float  # Arancel a importaciones ∈ [0, 1)
    s_x:         float  # Subsidio a exportaciones ∈ [0, 1)

    # Controles de flujo de capitales y encaje
    k_c:         float  # Controles de capital ∈ [0, 1); 0 = libre movilidad
    theta:       float  # Encaje legal (reserva fraccionaria) ∈ [0, 1)

    # Cambiario y monetario
    E:           float  # Tipo de cambio nominal (exógeno bajo TC fijo / crawling)
    M:           float  # Oferta monetaria (exógena bajo TC flexible)
    r_star:      float  # Tasa de interés internacional (exógena)
    regime:      str    # "fixed" | "flexible" | "crawling_peg" | "dirty_float"
    crawl_rate:  float  # Tasa de deslizamiento mensual (solo crawling_peg)
    E_band_upper: Optional[float]  # Banda superior para flotación sucia

    # Retrocompatibilidad: G = G_c + I_g calculado internamente
    G:           float  # Gasto público total (derivado; mantenido para snapshot)


class EquilibriumV2(TypedDict):
    """
    Output del motor por turno.
    Contiene todas las variables de equilibrio IS-LM-BP del período.
    """
    Y:          float  # PIB/Ingreso de equilibrio
    r:          float  # Tasa de interés de equilibrio
    E_endo:     float  # Tipo de cambio endógeno (NaN bajo TC fijo)
    M_endo:     float  # Oferta monetaria endógena (NaN bajo TC flexible)
    NX:         float  # Exportaciones netas de equilibrio (X - M_imp)
    X:          float  # Exportaciones brutas de equilibrio
    M_imp:      float  # Importaciones brutas de equilibrio
    G_total:    float  # Gasto público total (G_c + I_g)
    C:          float  # Consumo privado
    I_inv:      float  # Inversión privada
    mult:       float  # Multiplicador keynesiano
    P_local:    float  # Nivel de precios doméstico
    q_real:     float  # Tipo de cambio real
    M_real:     float  # Saldos reales (M / P_local)
    gap:        float  # Brecha del producto (Y - Y_pot) / Y_pot
    A_domestic: float  # Absorción doméstica (C + I_inv + G_total)
    P_T:        float  # Precio de bienes transables
    q_int:      float  # Tipo de cambio real interno (P_T / P_NT)
    Y_T:        float  # PIB del sector transable
    Y_NT:       float  # PIB del sector no-transable


class SalterSwanResult(TypedDict):
    """
    Resultado del análisis Salter-Swan dinámico.
    Pendientes derivadas de los parámetros del modelo.
    """
    zone:          str    # "I", "II", "III", "IV"
    diagnosis:     str    # Descripción del desequilibrio
    policy:        str    # Recomendación de política
    q_actual:      float  # TCR actual del equilibrio
    A_actual:      float  # Absorción doméstica actual
    q_IB_at_A:    float  # Umbral IB en el nivel de A actual
    q_EB_at_A:    float  # Umbral EB en el nivel de A actual
    slope_IB:      float  # Pendiente curva Balance Interno (derivada del modelo)
    slope_EB:      float  # Pendiente curva Balance Externo (derivada del modelo)
    ml_satisfied:  bool   # ¿Se satisface la condición Marshall-Lerner?


# ── Parámetros base V2.0 ─────────────────────────────────────────────────────

DEFAULT_STRUCTURAL_PARAMS: StructuralParams = {
    # Consumo e inversión
    "c0":        10.0,   # Consumo autónomo
    "c1":        0.75,   # PMgC
    "t":         0.20,   # Tasa impositiva retrocompat. (= t_c por defecto)
    "I0":        15.0,   # Inversión autónoma
    "b":         2.0,    # Sensibilidad I a r
    "rho_k":     5.0,    # Sensibilidad de I a tasa corporativa t_k
    "NX0":       5.0,    # NX autónomo (= x0 - m0 cuando Y_star=0)

    # Sector externo desagregado (opt-in)
    # Cuando x0=m0=0 el motor usa NX0 directamente (modo retrocompat. V2.0).
    # Los escenarios concretos pueden activar el modo desagregado seteando x0 y m0.
    "x0":        0.0,    # Exportaciones autónomas (0 = modo legacy NX0)
    "x1":        0.0,    # Sensibilidad X a Y_star (0 = ignorado)
    "Y_star":    0.0,    # PIB mundial (0 = ignorado en modo legacy)
    "m0":        0.0,    # Importaciones autónomas (0 = modo legacy)

    # Comercio exterior — condición Marshall-Lerner
    "epsilon_x": 1.16,   # Elasticidad exportaciones (suma M-L: 1.16+1.015=2.175 > 1 ✓)
    "epsilon_m": 1.015,  # Elasticidad importaciones
    "m1":        0.15,   # Propensión marginal a importar

    # Monetario
    "k":         0.50,   # Sensibilidad Ld a Y
    "h":         2.00,   # Sensibilidad Ld a r

    # Movilidad de capitales
    "f":         5.0,    # Moderadamente imperfecta

    # Pass-through cambiario
    "alpha_PT":  0.40,   # 40% bienes transables en canasta de precios
    "beta_PT":   0.20,   # 20% del shock cambiario pasa a inflación
    "P_star":    1.0,    # Precio externo normalizado

    # Producto potencial
    "Y_pot_0":   100.0,  # PIB potencial inicial
    "g_pot":     0.02,   # Crecimiento potencial anual 2%

    # Mercado laboral y precios
    "U_n":        0.05,  # NAIRU 5%
    "gamma_okun": 0.50,  # Coeficiente Okun
    "alpha_inf":  0.50,  # Pendiente Phillips
    "pi_0":       0.0,   # Inflación base adicional
    "G_needed":   0.0,   # Gasto público de reconstrucción adicional
}

DEFAULT_POLICY_INSTRUMENTS: PolicyInstruments = {
    # Gasto fiscal desagregado
    "G_c":        15.0,  # Gasto corriente
    "I_g":         5.0,  # Inversión pública
    "Tr":          0.0,  # Transferencias
    # Tributación dual
    "t_c":         0.20, # Tasa impositiva al consumo/ingreso
    "t_k":         0.20, # Tasa corporativa
    # Instrumentos comerciales
    "tau":         0.0,  # Arancel (0 = libre comercio)
    "s_x":         0.0,  # Subsidio exportaciones (0 = ninguno)
    # Controles de flujo
    "k_c":         0.0,  # Controles de capital (0 = libre movilidad)
    "theta":       0.10,  # Encaje legal (reserva fraccionaria base 10%)
    # Cambiario y monetario
    "E":          10.0,
    "M":          40.0,
    "r_star":      5.0,
    "regime":     "fixed",
    "crawl_rate":  0.02,
    "E_band_upper": None,
    # Retrocompatibilidad: G = G_c + I_g
    "G":          20.0,
}


# ── Escenarios de onboarding ──────────────────────────────────────────────────

SCENARIO_PRESETS: dict[str, dict] = {

    "Bolivia_2024_Stagflation": {
        "description": "Bolivia 2024 — Estanflación con restricción de divisas",
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "NX0":       -3.0,
            "I0":        -5.0,
            "c1":         0.65,
            "epsilon_x":  0.435,   # Aumentado en 45% (original: 0.30)
            "epsilon_m":  0.5075,  # Aumentado en 45% (original: 0.35)
            "f":           1.0,   # Baja movilidad de capitales
            "alpha_PT":    0.55,  # Alta exposición a bienes transables
            "beta_PT":     0.35,  # Alto pass-through
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "G_c":    12.0,
            "I_g":     3.0,
            "G":      15.0,
            "E":      10.0,
            "r_star":  8.0,
            "regime": "fixed",
        },
        "initial_state": {
            "Y_pot": 100.0,
            "P_NT":    1.0,
            "pi_e":   0.08,
            "R":      20.0,
            "B":     150.0,
        },
    },

    "Boom_Exportador": {
        "description": "Shock de demanda externa positivo — Bonanza",
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "NX0":       15.0,
            "x0":        20.0,   # Exportaciones autónomas elevadas
            "epsilon_x":  1.20,
            "epsilon_m":  0.80,
            "f":          10.0,   # Alta movilidad de capitales
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "G_c":    17.0,
            "I_g":     5.0,
            "G":      22.0,
            "E":      10.0,
            "r_star":  3.0,
            "regime": "fixed",
        },
        "initial_state": {
            "Y_pot": 100.0,
            "P_NT":    1.0,
            "pi_e":   0.03,
            "R":      80.0,
            "B":      50.0,
        },
    },

    "Credit_Crunch": {
        "description": "Crisis de liquidez — Sequía de crédito",
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "I0":       -10.0,
            "c1":         0.60,
            "h":          0.80,
            "f":           2.0,
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "G_c":    20.0,
            "I_g":     5.0,
            "G":      25.0,
            "M":       50.0,
            "r_star":  10.0,
            "regime":  "flexible",
        },
        "initial_state": {
            "Y_pot": 100.0,
            "P_NT":    1.0,
            "pi_e":   0.04,
            "R":      30.0,
            "B":     100.0,
        },
    },

    "Economia_Saludable": {
        "description": "Economía de referencia — Condiciones base",
        "structural": DEFAULT_STRUCTURAL_PARAMS,
        "policy":     DEFAULT_POLICY_INSTRUMENTS,
        "initial_state": {
            "Y_pot": 100.0,
            "P_NT":    1.0,
            "pi_e":   0.03,
            "R":      50.0,
            "B":      60.0,
        },
    },
}


# ── Función de carga ──────────────────────────────────────────────────────────

def get_base_params_v2() -> tuple[StructuralParams, PolicyInstruments]:
    """
    Retorna los parámetros base V2.0.

    Prioridad:
        1. Variables de entorno (pendiente implementación por fases)
        2. DEFAULT_STRUCTURAL_PARAMS / DEFAULT_POLICY_INSTRUMENTS hardcoded

    Returns
    -------
    tuple[StructuralParams, PolicyInstruments]
        (sp, pi) — parámetros estructurales e instrumentos de política base.
    """
    sp: StructuralParams = dict(DEFAULT_STRUCTURAL_PARAMS)   # type: ignore[assignment]
    pi: PolicyInstruments = dict(DEFAULT_POLICY_INSTRUMENTS) # type: ignore[assignment]
    return sp, pi


def get_scenario_params(key: str) -> tuple[StructuralParams, PolicyInstruments, dict]:
    """
    Retorna los parámetros de un escenario predefinido.

    Parameters
    ----------
    key : str
        Clave del escenario en SCENARIO_PRESETS.

    Returns
    -------
    tuple[StructuralParams, PolicyInstruments, dict]
        (sp, pi, initial_state)

    Raises
    ------
    KeyError
        Si el escenario no existe.
    """
    # Importación local para evitar dependencias circulares con config/scenarios_v2.py
    try:
        from config.scenarios_v2 import SCENARIO_PRESETS_V3
    except ImportError:
        SCENARIO_PRESETS_V3 = {}

    if key in SCENARIO_PRESETS_V3:
        preset = SCENARIO_PRESETS_V3[key]
        sp: StructuralParams = dict(preset["structural"])       # type: ignore[assignment]
        pi: PolicyInstruments = dict(preset["policy"])          # type: ignore[assignment]
        init: dict = dict(preset["initial_state"])
        return sp, pi, init

    if key not in SCENARIO_PRESETS:
        available = list(SCENARIO_PRESETS.keys()) + list(SCENARIO_PRESETS_V3.keys())
        raise KeyError(
            f"Escenario '{key}' no encontrado. Disponibles: {available}"
        )
    preset = SCENARIO_PRESETS[key]
    sp: StructuralParams = dict(preset["structural"])       # type: ignore[assignment]
    pi: PolicyInstruments = dict(preset["policy"])          # type: ignore[assignment]
    init: dict = dict(preset["initial_state"])
    return sp, pi, init

try:
    import streamlit as st
    get_base_params_v2 = st.cache_data(get_base_params_v2)
    get_scenario_params = st.cache_data(get_scenario_params)
except ImportError:
    pass

