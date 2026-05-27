"""
config/scenarios_v2.py
======================
Presets de escenarios de onboarding calibrados para el Simulador Macroeconómico V2.0 (Fase 5).

Cada preset define:
  - name         : Nombre del escenario
  - difficulty   : Dificultad sugerida ("Fácil", "Medio", "Difícil", "Muy difícil")
  - description  : Breve sinopsis del escenario
  - bullets      : 3 puntos clave de contexto narrativo/KPI inicial
  - structural   : Parámetros estructurales base modificados para el escenario
  - policy       : Instrumentos de política iniciales
  - initial_state: Variables de estado t=0 iniciales (R, B, pi_e, Y_pot, etc.)
"""

from __future__ import annotations

from config.parameters_v2 import DEFAULT_POLICY_INSTRUMENTS, DEFAULT_STRUCTURAL_PARAMS

SCENARIO_PRESETS_V3: dict[str, dict] = {
    "tiger_asia": {
        "name": "🐯 El Tigre Asiático",
        "difficulty": "Fácil",
        "description": "Una economía dinámica y de rápido crecimiento con bases macroeconómicas muy sólidas. Su principal desafío como Ministro es evitar el recalentamiento económico ante un fuerte crecimiento potencial y flujos constantes de divisas.",
        "bullets": [
            "📈 Crecimiento potencial estructural alto (g_pot = 4%).",
            "💼 Desempleo inicial extremadamente bajo de U = 3%.",
            "🏦 Sólidas reservas internacionales de R = 150 MM, con excelente reputación crediticia."
        ],
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "c0": 15.0,          # Calibrado para Y0 estable ~ 105
            "I0": 15.0,          # Calibrado para Y0 estable ~ 105
            "x0": 12.0,         # Sector externo desagregado calibrado
            "x1": 0.10,
            "Y_star": 30.0,
            "m0": 7.0,
            "g_pot": 0.03,
            "U_n": 0.03,
            "f": 10.0,         # Alta movilidad de capitales
            "alpha_PT": 0.35,  # Baja exposición a precios importados
            "beta_PT": 0.15,   # Bajo pass-through
            "m1": 0.03,        # Calibrado para drenaje de reservas lento
            "pi_0": 0.0,
            "G_needed": 0.0,
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "G_c": 20.0,
            "I_g": 0.0,
            "G": 20.0,
            "E": 10.0,
            "M": 45.0,
            "r_star": 4.0,
            "regime": "fixed",
        },
        "initial_state": {
            "Y_pot": 100.0,
            "P_NT": 1.0,
            "pi_e": 0.03,      # 3% inflación inicial
            "R": 150.0,        # Calibrado para evitar quiebre de reservas
            "B": 15.0,         # Baja deuda soberana inicial
        }
    },
    "trade_deficit": {
        "name": "📉 Desequilibrio Comercial",
        "difficulty": "Medio",
        "description": "Una economía mediana expuesta a una severa brecha comercial autónoma y reservas en declive continuo. Su labor es formular una política comercial y cambiaria adecuada para recomponer las reservas internacionales sin estrangular el crecimiento doméstico.",
        "bullets": [
            "💔 Fuerte brecha comercial inicial debido a un déficit autónomo de NX0 = -10.",
            "🏦 Reservas internacionales limitadas de R = 120 MM, con riesgo de crisis cambiaria.",
            "💸 Tasa impositiva moderada de t = 25% para estimular recaudación fiscal."
        ],
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "c0": 10.0,
            "I0": 20.0,
            "x0": 12.0,         # Sector externo desagregado calibrado
            "x1": 0.10,
            "Y_star": 30.0,
            "m0": 7.0,
            "NX0": -10.0,
            "t": 0.25,         # Mayor recaudación para evitar default soberano antes que R
            "m1": 0.20,        # Drenaje controlado de reservas
            "f": 4.0,          # Movilidad imperfecta moderada
            "pi_0": 0.0,
            "G_needed": 0.0,
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "G": 20.0,
            "E": 10.0,
            "M": 40.0,
            "r_star": 5.0,
            "regime": "fixed",
        },
        "initial_state": {
            "Y_pot": 100.0,
            "P_NT": 1.0,
            "pi_e": 0.03,
            "R": 120.0,        # Calibrado para durar de 6 a 8 turnos
            "B": 10.0,         # Deuda inicial muy baja
        }
    },
    "latam_crisis": {
        "name": "🔥 Crisis Latinoamericana",
        "difficulty": "Difícil",
        "description": "Una economía que padece de estanflación clásica: inflación y desempleo elevados de forma simultánea, y reservas internacionales reducidas a su mínima expresión. Las expectativas de devaluación e inflación amenazan con espirales descontroladas.",
        "bullets": [
            "📈 Inflación inicial elevada de pi = 18% con alta inercia (expectativas).",
            "💼 Desempleo inicial preocupante de U = 12% por debajo del potencial.",
            "🚨 Reservas internacionales críticas de R = 15 MM, al borde del default externo."
        ],
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "c0": 26.0,        # Calibrado para Y0 ~ 81 y U0 ~ 15%
            "I0": 20.0,        # Calibrado para Y0 ~ 81 y U0 ~ 15%
            "x0": 12.0,         # Sector externo desagregado calibrado
            "x1": 0.10,
            "Y_star": 30.0,
            "m0": 7.0,
            "c1": 0.65,
            "t": 0.20,
            "m1": 0.15,
            "NX0": -5.0,
            "epsilon_x": 0.40,  # Bienes primarios inelásticos
            "epsilon_m": 0.45,
            "f": 2.0,           # Baja movilidad de capitales
            "alpha_PT": 0.50,   # Fuerte exposición externa
            "beta_PT": 0.35,    # Alto pass-through cambiario
            "U_n": 0.06,
            "pi_0": 0.0,
            "G_needed": 0.0,
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "G": 22.0,
            "E": 10.0,
            "M": 42.0,
            "r_star": 7.0,
            "regime": "fixed",
        },
        "initial_state": {
            "Y_pot": 100.0,
            "P_NT": 1.0,
            "pi_e": 0.15,      # Calibrado para inercia inflacionaria
            "R": 15.0,         # Calibrado
            "B": 35.0,         # Calibrado
        }
    },
    "death_spiral": {
        "name": "💀 Espiral de la Muerte",
        "difficulty": "Muy difícil",
        "description": "El peor de los escenarios macroeconómicos. Su país se encuentra sumido en una hiperinflación rampante combinada con recesión profunda y desempleo masivo. Las reservas se encuentran al límite absoluto y la deuda pública amenaza con un default soberano inminente en pocos turnos.",
        "bullets": [
            "📈 Expectativas e inercia hiperinflacionaria devastadora del pi = 80%.",
            "💼 Desempleo masivo de U = 20% con colapso de la inversión productiva autónoma (I0 = -15).",
            "💀 Reservas críticas de R = 10 MM y deuda pública desbocada de B = 45 MM."
        ],
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "c0": 20.0,        # Calibrado para U0 ~ 22%
            "I0": 15.0,        # Calibrado para U0 ~ 22%
            "x0": 12.0,         # Sector externo desagregado calibrado
            "x1": 0.10,
            "Y_star": 30.0,
            "m0": 7.0,
            "c1": 0.60,
            "t": 0.25,
            "NX0": -12.0,
            "epsilon_x": 0.30,  # Exportaciones rígidas
            "epsilon_m": 0.35,
            "f": 1.5,           # Fuga de capitales latente
            "alpha_PT": 0.60,   # Exposición cambiaria extrema
            "beta_PT": 0.45,    # Pass-through muy elevado
            "U_n": 0.08,
            "g_pot": -0.01,     # Destrucción de capacidad productiva
            "pi_0": 0.0,
            "G_needed": 0.0,
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "G": 25.0,
            "E": 10.0,
            "M": 50.0,
            "r_star": 9.0,
            "regime": "fixed",
        },
        "initial_state": {
            "Y_pot": 100.0,
            "P_NT": 1.0,
            "pi_e": 0.70,      # Calibrado para alta inercia
            "R": 10.0,         # Calibrado
            "B": 60.0,         # Calibrado
        }
    }
}
