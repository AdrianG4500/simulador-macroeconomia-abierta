"""
config_simple/scenarios.py
==========================
Presets de escenarios históricos calibrados para The Economic War Room (V1.2 SIMPLE).
Datos basados en estadísticas históricas del Banco Mundial (WDI), FMI y Bancos Centrales.

Catálogo de los 4 Escenarios:
1. tiger_asia: 🇰🇷 Corea del Sur (1985) — "El Milagro del Río Han" (Fácil)
2. chile_rule (alias Economia_Saludable): 🇨🇱 Chile (2000–2005) — "Regla Fiscal y Estabilidad" (Normal)
3. mexico_tequila (alias latam_crisis): 🇲🇽 México (1994–1995) — "El Efecto Tequila" (Difícil)
4. bolivia_hyper (alias death_spiral): 🇧🇴 Bolivia (1982–1985) — "Hiperinflación y D.S. 21060" (Muy Difícil)
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Tuple

from config_simple.parameters import (
    DEFAULT_POLICY_INSTRUMENTS,
    DEFAULT_STRUCTURAL_PARAMS,
    PolicyInstruments,
    StructuralParams,
)

SCENARIOS: Dict[str, Dict[str, Any]] = {
    # ─────────────────────────────────────────────────────────────────────────
    # ESCENARIO 1: COREA DEL SUR (1985) — FÁCIL
    # ─────────────────────────────────────────────────────────────────────────
    "tiger_asia": {
        "id": "tiger_asia",
        "name": "🇰🇷 Corea del Sur (1985) — El Milagro del Río Han",
        "country": "Corea del Sur",
        "year": "1985",
        "difficulty": "Fácil",
        "description": (
            "Es 1985. Corea del Sur consolida su transformación industrial exportadora hacia la alta tecnología. "
            "Cuentas macroeconómicas saneadas, alta propensión a la inversión y fuerte competitividad externa. "
            "Tu misión es guiar el crecimiento protegiendo la estabilidad de precios y ampliando la infraestructura."
        ),
        "historical_context": (
            "Datos Históricos Reales (WDI 1985): Crecimiento del PIB ≈ 7.8%, Inflación 2.5%, Desempleo 4.0%, "
            "Deuda Pública ≈ 19% del PIB y reservas en rápida acumulación."
        ),
        "bullets": [
            "🚀 Alto potencial exportador y mano de obra calificada (U_n = 4.0%).",
            "🏦 Sólido colchón externo: Reservas iniciales de 80.0 MUSD con deuda baja (B = 20.0).",
            "⚡ Alerta en T3: Fricción comercial internacional y alza de tasas externas (r* sube +1.5%)."
        ],
        "winning_recipe": (
            "Mantener alta la inversión en infraestructura (Ig ∈ [9, 12]), apoyar con subsidios exportadores "
            "(sx ∈ [4%, 6%]), mantener impuestos corporativos competitivos (tk ≤ 10%) y anclar expectativas con r_ref ≈ 7%."
        ),
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "c0": 8.0,
            "c1": 0.65,
            "I0": 16.0,
            "b": 0.80,
            "rho_k": 8.0,
            "psi_ci": 0.30,
            "psi_co": 12.0,
            "r0": 5.60,
            "tk0": 0.10,
            "Ig0": 8.0,
            "x0": 15.0,
            "m0": 1.425248,
            "m1": 0.14,
            "epsilon_x": 1.40,
            "epsilon_m": 1.10,
            "eta_x": 25.0,
            "f": 2.20,
            "alpha_PT": 0.40,
            "beta_PT": 0.15,
            "alpha_inf": 0.20,
            "P_star": 1.0,
            "U_n": 0.04,
            "gamma_okun": 0.45,
            "g_pot": 0.015,
            "Ig_dep": 6.0,
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "Gc": 12.0,
            "Ig": 8.0,
            "tc": 0.15,
            "tk": 0.10,
            "r_ref": 6.0,
            "tau": 0.05,
            "sx": 0.02,
            "E": 10.0,
            "regime": "fixed",
            "crawl_rate": 0.00,
            "r_star": 4.5,
            "P_star": 1.0,
            "pi_target": 0.03,
            "G_needed": 0.0,
            "G": 20.0,
            "t": 0.15,
        },
        "initial_state": {
            "Y": 100.0,
            "Y_pot": 100.0,
            "pi": 0.030,
            "pi_e": 0.030,
            "U": 0.040,
            "B": 20.0,
            "R": 80.0,
            "P_NT": 1.0,
            "rho": 0.50,
            "rating": "AA",
        },
        "scheduled_events": [
            {
                "turn": 3,
                "id": "fed_hike_kor",
                "title": "Shock de Tasas Internacionales y Fricción Comercial",
                "description": "La Reserva Federal eleva tasas de interés (+1.5%), encareciendo el crédito externo.",
                "deltas": {"r_star": 1.5, "rho": 0.3},
            }
        ]
    },

    # ─────────────────────────────────────────────────────────────────────────
    # ESCENARIO 2: CHILE (2000–2005) — NORMAL
    # ─────────────────────────────────────────────────────────────────────────
    "chile_rule": {
        "id": "chile_rule",
        "name": "🇨🇱 Chile (2000–2005) — Regla Fiscal y Estabilidad",
        "country": "Chile",
        "year": "2000-2005",
        "difficulty": "Normal",
        "description": (
            "Inicio del nuevo milenio. Chile implementa su pionera Regla de Balance Estructural Fiscal y consolida "
            "la flotación cambiaria con metas de inflación en el 3.0%. Deuda soberana mínima y grado de inversión de primera línea."
        ),
        "historical_context": (
            "Datos Históricos Reales (WDI 2000-2005): Inflación clavada en 3.0%, desempleo natural 5.0%, "
            "Deuda Pública muy baja (15.0% del PIB) y apertura comercial activa por tratados de libre comercio."
        ),
        "bullets": [
            "🛡️ Régimen Flexible con metas de inflación: El tipo de cambio absorbe shocks externos automáticamente.",
            "🏛️ Regla Fiscal Estructural: Ahorro en épocas de bonanza y estímulo en tiempos difíciles.",
            "📉 Desaceleración global en T3 seguida de un superciclo minero de exportaciones en T6."
        ],
        "winning_recipe": (
            "Aplicar política contracíclica pura: en T3-T4 estimular con Ig ↑ y recortar r_ref; en T6-T9 (superciclo del cobre) "
            "ahorrar conteniendo Gc y reduciendo aranceles al 2% para abaratar importaciones y mantener la inflación en 3%."
        ),
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "c0": 12.0,
            "c1": 0.65,
            "I0": 16.0,
            "b": 0.80,
            "rho_k": 9.0,
            "psi_ci": 0.25,
            "psi_co": 14.0,
            "r0": 5.25,
            "tk0": 0.10,
            "Ig0": 6.0,
            "x0": 18.0,
            "m0": 6.471542,
            "m1": 0.15,
            "epsilon_x": 1.25,
            "epsilon_m": 1.15,
            "eta_x": 20.0,
            "f": 2.00,
            "alpha_PT": 0.40,
            "beta_PT": 0.20,
            "alpha_inf": 0.25,
            "P_star": 1.0,
            "U_n": 0.05,
            "gamma_okun": 0.45,
            "g_pot": 0.030,
            "Ig_dep": 5.0,
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "Gc": 14.0,
            "Ig": 6.0,
            "tc": 0.16,
            "tk": 0.10,
            "r_ref": 5.0,
            "tau": 0.06,
            "sx": 0.00,
            "E": 10.0,
            "regime": "flexible",
            "crawl_rate": 0.00,
            "r_star": 4.0,
            "P_star": 1.0,
            "pi_target": 0.03,
            "G_needed": 0.0,
            "G": 20.0,
            "t": 0.16,
        },
        "initial_state": {
            "Y": 100.0,
            "Y_pot": 100.0,
            "pi": 0.030,
            "pi_e": 0.030,
            "U": 0.050,
            "B": 15.0,
            "R": 60.0,
            "P_NT": 1.0,
            "rho": 0.50,
            "rating": "AA+",
        },
        "scheduled_events": [
            {
                "turn": 3,
                "id": "global_slowdown_chl",
                "title": "Desaceleración Comercial Global",
                "description": "Una recesión en socios comerciales deprime la demanda externa de exportaciones (-4.0).",
                "deltas": {"x0": -4.0},
            },
            {
                "turn": 6,
                "id": "copper_supercycle_chl",
                "title": "Superciclo de Commodities / Boom del Cobre",
                "description": "Fuerte salto en cotizaciones internacionales impulsa la demanda de exportaciones (+8.0).",
                "deltas": {"x0": 8.0},
            }
        ]
    },

    # ─────────────────────────────────────────────────────────────────────────
    # ESCENARIO 3: MÉXICO (1994–1995) — DIFÍCIL
    # ─────────────────────────────────────────────────────────────────────────
    "mexico_tequila": {
        "id": "mexico_tequila",
        "name": "🇲🇽 México (1994–1995) — El Efecto Tequila",
        "country": "México",
        "year": "1994-1995",
        "difficulty": "Difícil",
        "description": (
            "Diciembre de 1994. México sufre una fuga descontrolada de divisas. El tipo de cambio semi-fijo sobrevaluado "
            "ha erosionado las reservas del Banco de México (R = 22 MUSD), mientras la deuda denominada en dólares (Tesobonos) "
            "asfixia las cuentas públicas."
        ),
        "historical_context": (
            "Datos Históricos Reales (WDI / Banxico 1994): Fuerte déficit comercial (NX ≈ -9.0), reservas al borde del colapso, "
            "inflación reprimida en 7.5% y deuda pública del 52% del PIB. Alza de tasas de la Reserva Federal desató el ataque especulativo."
        ),
        "bullets": [
            "⚠️ Sangría inminente de reservas: En régimen fijo sin cambios, las reservas se agotan totalmente en T3.",
            "🚨 Reforma Cambiaria de Emergencia disponible: Se requiere pasar a régimen Flexible o ajustar el tipo de cambio.",
            "⚡ Alerta en T1: Fuga de capitales internacional y salto de prima de riesgo país."
        ],
        "winning_recipe": (
            "T1–T2: Activar Reforma Cambiaria a Régimen Flexible (o devaluar E a 12.5), subir r_ref a 14%-16% para frenar salida de capitales "
            "y recortar gasto corriente Gc a 13.0. T3–T10: Con tipo de cambio competitivo, apoyar exportaciones con sx = 4%, elevar Ig a 7.0 "
            "e ir bajando tasas conforme la credibilidad restablezca la estabilidad."
        ),
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "c0": 12.0,
            "c1": 0.68,
            "I0": 14.0,
            "b": 0.75,
            "rho_k": 10.0,
            "psi_ci": 0.20,
            "psi_co": 18.0,
            "r0": 7.80,
            "tk0": 0.10,
            "Ig0": 4.0,
            "x0": 18.0,
            "m0": 6.527648,
            "m1": 0.18,
            "epsilon_x": 1.30,
            "epsilon_m": 1.20,
            "eta_x": 22.0,
            "f": 2.50,
            "alpha_PT": 0.40,
            "beta_PT": 0.25,
            "alpha_inf": 0.30,
            "P_star": 1.0,
            "U_n": 0.055,
            "gamma_okun": 0.40,
            "g_pot": 0.020,
            "Ig_dep": 4.0,
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "Gc": 16.0,
            "Ig": 4.0,
            "tc": 0.14,
            "tk": 0.10,
            "r_ref": 8.0,
            "tau": 0.05,
            "sx": 0.00,
            "E": 10.0,
            "regime": "fixed",
            "crawl_rate": 0.00,
            "r_star": 5.0,
            "P_star": 1.0,
            "pi_target": 0.04,
            "G_needed": 0.0,
            "G": 20.0,
            "t": 0.14,
        },
        "initial_state": {
            "Y": 98.0,
            "Y_pot": 100.0,
            "pi": 0.075,
            "pi_e": 0.075,
            "U": 0.065,
            "B": 52.0,
            "R": 22.0,
            "P_NT": 1.0,
            "rho": 2.50,
            "rating": "BB",
        },
        "scheduled_events": [
            {
                "turn": 1,
                "id": "capital_flight_mex",
                "title": "Ataque Especulativo y Fuga de Capitales",
                "description": "Inversionistas huyen hacia activos en dólares. La Reserva Federal sube tasas (+2.5%) y la prima de riesgo salta.",
                "deltas": {"r_star": 2.5, "rho": 3.0},
            }
        ]
    },

    # ─────────────────────────────────────────────────────────────────────────
    # ESCENARIO 4: BOLIVIA (1982–1985) — MUY DIFÍCIL
    # ─────────────────────────────────────────────────────────────────────────
    "bolivia_hyper": {
        "id": "bolivia_hyper",
        "name": "🇧🇴 Bolivia (1982–1985) — Hiperinflación y D.S. 21060",
        "country": "Bolivia",
        "year": "1982-1985",
        "difficulty": "Muy Difícil",
        "description": (
            "Agosto de 1985. La economía boliviana se desmorona en una de las hiperinflaciones más agudas de América Latina. "
            "El déficit del sector público supera el 20% del PIB, financiado íntegramente con emisión monetaria inorgánica. "
            "Reservas en 15 MUSD y deuda soberana en zona de default (CCC)."
        ),
        "historical_context": (
            "Datos Históricos Reales (BCB / WDI 1982-1985): Caída acumulada del producto (-8%), inflación galopante (24% por período en el modelo), "
            "recaudación colapsada por rezago Olivera-Tanzi (tc efectivo apenas 8%) y reservas agotadas."
        ),
        "bullets": [
            "🔥 Hiperinflación desatada: Emisión de señoreaje desbocada y espiral precios-salarios-tipo de cambio.",
            "📉 Déficit fiscal crónico: Gasto corriente sobredimensionado (Gc = 22) con recaudación casi nula.",
            "⚖️ Requiere la Terapia de Shock del D.S. 21060: Disciplina de caja única, reforma tributaria y unificación cambiaria."
        ],
        "winning_recipe": (
            "T1–T3 (Terapia de Shock): Recortar Gc de 22 a 14, subir tc a 16% y tk a 10% (Reforma Tributaria Ley 843 para erradicar el déficit), "
            "subir r_ref a 18%-20% (tasa real fuertemente positiva) y bajar el deslizamiento cambiario a 2% o flotar. Esto restituye la credibilidad "
            "a 0.80 y baja la inflación del 24% a <7%. T4–T10: Con estabilidad, bajar tasas a 7%, expandir inversión pública Ig a 8.0 y subsidios sx a 5%."
        ),
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "c0": 10.0,
            "c1": 0.65,
            "I0": 8.0,
            "b": 0.60,
            "rho_k": 8.0,
            "psi_ci": 0.25,
            "psi_co": 10.0,
            "r0": 13.60,
            "tk0": 0.05,
            "Ig0": 2.0,
            "x0": 14.0,
            "m0": 2.608240,
            "m1": 0.16,
            "epsilon_x": 1.20,
            "epsilon_m": 1.10,
            "eta_x": 20.0,
            "f": 1.80,
            "alpha_PT": 0.40,
            "beta_PT": 0.35,
            "alpha_inf": 0.35,
            "P_star": 1.0,
            "U_n": 0.065,
            "gamma_okun": 0.40,
            "g_pot": 0.010,
            "Ig_dep": 3.0,
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "Gc": 22.0,
            "Ig": 2.0,
            "tc": 0.08,
            "tk": 0.05,
            "r_ref": 10.0,
            "tau": 0.10,
            "sx": 0.00,
            "E": 10.0,
            "regime": "crawling_peg",
            "crawl_rate": 0.08,
            "r_star": 3.0,
            "P_star": 1.0,
            "pi_target": 0.05,
            "G_needed": 0.0,
            "G": 24.0,
            "t": 0.08,
        },
        "initial_state": {
            "Y": 92.0,
            "Y_pot": 100.0,
            "pi": 0.240,
            "pi_e": 0.240,
            "U": 0.110,
            "B": 70.0,
            "R": 15.0,
            "P_NT": 1.0,
            "rho": 5.00,
            "rating": "CCC",
        },
        "scheduled_events": [
            {
                "turn": 1,
                "id": "seigniorage_shock_bol",
                "title": "Espiral Inflacionaria y Colapso de Recaudación",
                "description": "El rezago Olivera-Tanzi desintegra la recaudación real, obligando al fisco a monetizar el déficit.",
                "deltas": {"rho": 1.5},
            }
        ]
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# MAPEO DE ALIASES HISTÓRICOS Y DE COMPATIBILIDAD
# ─────────────────────────────────────────────────────────────────────────────
SCENARIOS["Economia_Saludable"] = SCENARIOS["chile_rule"]
SCENARIOS["latam_crisis"] = SCENARIOS["mexico_tequila"]
SCENARIOS["death_spiral"] = SCENARIOS["bolivia_hyper"]


def get_scenario_params(scenario_id: str) -> Tuple[StructuralParams, PolicyInstruments, Dict[str, Any]]:
    """
    Retorna copias profundas de (structural_params, policy_instruments, initial_state)
    para el escenario solicitado. Resuelve automáticamente aliases retrocompatibles.
    """
    if scenario_id not in SCENARIOS:
        scenario_id = "tiger_asia"

    sc = SCENARIOS[scenario_id]
    sp = copy.deepcopy(sc["structural"])
    pi = copy.deepcopy(sc["policy"])
    init = copy.deepcopy(sc["initial_state"])

    return sp, pi, init
