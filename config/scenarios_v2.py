"""
config/scenarios_v2.py
======================
Presets de escenarios de onboarding calibrados históricamente para el Simulador Macroeconómico V2.0 (Fase V3.2).

Cada preset define:
  - name         : Nombre del escenario con su anclaje histórico.
  - difficulty   : Dificultad sugerida.
  - description  : Breve sinopsis histórica y del desafío.
  - bullets      : 3 puntos clave de contexto narrativo/KPI inicial.
  - structural   : Parámetros estructurales base modificados para el escenario.
  - policy       : Instrumentos de política iniciales heredados.
  - initial_state: Variables de estado t=0 iniciales (R, B, pi_e, Y_pot, etc.)
"""

from __future__ import annotations

from config.parameters_v2 import DEFAULT_POLICY_INSTRUMENTS, DEFAULT_STRUCTURAL_PARAMS

SCENARIO_PRESETS_V3: dict[str, dict] = {
    "tiger_asia": {
        "name": "🐯 Milagro Coreano: El Salto del Tigre (1985)",
        "difficulty": "Fácil",
        "description": "Es 1985. Corea del Sur se encuentra en el umbral de transformarse de una economía agraria devastada a una potencia tecnológica industrial. Su misión como Ministro es liderar una agresiva estrategia orientada a las exportaciones y a la inversión en infraestructura productiva, en alianza con los Chaebols privados, manteniendo baja inflación y acumulación de reservas.",
        "bullets": [
            "🚀 Industrialización acelerada impulsada por alta productividad tecnológica (PIB potencial pujante).",
            "💼 Pleno empleo de la mano de obra con una tasa de desempleo natural de apenas 4.0%.",
            "🏦 Blindaje financiero masivo: Reservas Netas de 120.0 MM USD y baja deuda pública acumulada."
        ],
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "c0": 12.00,
            "c1": 0.65,
            "t": 0.18,
            "lambda_h": 0.2010,
            "I0": 16.00,
            "b": 1.20,
            "psi_ci": 0.35,
            "psi_co": 0.05,
            "NX0": 4.00,
            "m1": 0.14,
            "epsilon_x": 1.50,
            "epsilon_m": 1.20,
            "f": 12.0,
            "beta_PT": 0.10,
            "alpha_nonlinear": 1.5,
            "U_n": 0.04
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "G_c": 12.0,
            "I_g": 8.0,
            "G": 20.0,
            "t_c": 0.18,
            "t_k": 0.0,
            "r_ref": 7.50,
            "M": 65.0,
            "E": 10.0,
            "crawl_rate": 0.00,
            "regime": "fixed",
            "r_star": 4.0,
            "tau": 0.0,
            "s_x": 0.0,
            "k_c": 0.0
        },
        "initial_state": {
            "Y_pot": 100.00,
            "B": 20.0,
            "R": 120.0,
            "K_g": 80.0,
            "P_NT": 1.0,
            "pi_e": 0.03
        }
    },
    "Economia_Saludable": {
        "name": "🏛️ Estabilidad Chilena: La Regla de Oro (2005)",
        "difficulty": "Fácil",
        "description": "Año 2005. Chile goza de una reputación impecable basada en la responsabilidad fiscal y la independencia monetaria. Como Ministro de Hacienda, debe sostener este estado estacionario de pleno empleo, administrando de forma prudente los shocks externos, controlando el déficit bajo la regla del superávit estructural y cuidando la estabilidad social.",
        "bullets": [
            "⚖️ Pleno empleo macroeconómico con Output Gap de inicio exactamente en 0.00%.",
            "💼 Desempleo anclado en su tasa natural de 5.0% y expectativas inflacionarias controladas.",
            "🏦 Estabilidad fiscal con deuda pública baja de B = 15.0 MM USD que garantiza solvencia absoluta."
        ],
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "c0": 14.00,
            "c1": 0.60,
            "t": 0.20,
            "lambda_h": 0.4030,
            "I0": 12.00,
            "b": 1.50,
            "psi_ci": 0.20,
            "psi_co": 0.10,
            "NX0": 0.00,
            "m1": 0.15,
            "epsilon_x": 1.16,
            "epsilon_m": 1.01,
            "f": 5.0,
            "beta_PT": 0.20,
            "alpha_nonlinear": 2.0,
            "U_n": 0.05
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "G_c": 15.0,
            "I_g": 5.0,
            "G": 20.0,
            "t_c": 0.20,
            "t_k": 0.0,
            "r_ref": 5.00,
            "M": 60.0,
            "E": 10.0,
            "crawl_rate": 0.00,
            "regime": "fixed",
            "r_star": 5.0,
            "tau": 0.0,
            "s_x": 0.0,
            "k_c": 0.0
        },
        "initial_state": {
            "Y_pot": 100.0,
            "B": 15.0,
            "R": 60.0,
            "K_g": 50.0,
            "P_NT": 1.0,
            "pi_e": 0.03
        }
    },
    "latam_crisis": {
        "name": "📉 Crisis de Deuda Mexicana: La Década Perdida (1982)",
        "difficulty": "Difícil",
        "description": "Es agosto de 1982. El secretario de Hacienda anuncia que México no puede cumplir con el servicio de su inmensa deuda externa. Con las tasas de interés en EE.UU. en niveles récord, se desata una fuga masiva de capitales y pánico financiero en toda la región. Asume un ministerio sin divisas, con la balanza comercial en rojo y el crédito internacional totalmente cortado.",
        "bullets": [
            "💔 Rigidez comercial extrema debido a elasticidades Marshall-Lerner bajas (fuga inminente de divisas).",
            "🚨 Reservas internacionales críticas en estado agónico de R = 25.0 MM USD y alta deuda pública ex-ante.",
            "💸 Tasas de interés de paridad elevadas debido a un riesgo país disparado y fuga de depósitos."
        ],
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "c0": 8.00,
            "c1": 0.70,
            "t": 0.12,
            "lambda_h": 0.4655,
            "I0": 6.50,
            "b": 0.80,
            "psi_ci": 0.10,
            "psi_co": 0.25,
            "NX0": -3.00,
            "m1": 0.20,
            "epsilon_x": 0.48,
            "epsilon_m": 0.52,
            "f": 4.0,
            "beta_PT": 0.35,
            "alpha_nonlinear": 1.2,
            "U_n": 0.06
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "G_c": 14.0,
            "I_g": 2.0,
            "G": 16.0,
            "t_c": 0.18,
            "t_k": 0.0,
            "r_ref": 16.00,
            "M": 35.0,
            "E": 10.0,
            "crawl_rate": 0.00,
            "regime": "flexible",
            "r_star": 7.0,
            "tau": 0.0,
            "s_x": 0.0,
            "k_c": 0.0
        },
        "initial_state": {
            "Y_pot": 104.0,
            "B": 55.0,
            "R": 25.0,
            "K_g": 25.0,
            "P_NT": 1.0,
            "pi_e": 0.08
        }
    },
    "death_spiral": {
        "name": "🔥 Hiperinflación Boliviana: La Espiral de la Muerte (1982)",
        "difficulty": "Muy difícil",
        "description": "Año 1982. Bolivia se sumerge en una de las crisis inflacionarias más dramáticas del siglo. El déficit fiscal crónico financiado con emisión inorgánica ha alimentado expectativas hiperinflacionarias incontrolables. Como Ministro de Planificación, debe enfrentar la indexación salarial inercial y reservas agotadas antes de que la economía social colapse por completo.",
        "bullets": [
            "📈 Inercia y expectativas inflacionarias iniciales desancladas (pi_e = 10.0% semestral).",
            "💀 Reservas críticas al borde de la extinción total y deuda externa insostenible.",
            "⚙️ Deslizamiento cambiario (crawling peg al 8%) que retroalimenta la espiral inflacionaria ex-ante."
        ],
        "structural": {
            **DEFAULT_STRUCTURAL_PARAMS,
            "c0": 6.00,
            "c1": 0.75,
            "t": 0.08,
            "lambda_h": 0.30,
            "I0": 4.00,
            "b": 0.40,
            "psi_ci": 0.00,
            "psi_co": 0.40,
            "NX0": -5.00,
            "m1": 0.25,
            "epsilon_x": 0.38,
            "epsilon_m": 0.42,
            "f": 0.8,
            "beta_PT": 0.35,
            "alpha_nonlinear": 1.5,
            "U_n": 0.07,
            "debt_velocity_threshold": 0.15
        },
        "policy": {
            **DEFAULT_POLICY_INSTRUMENTS,
            "G_c": 14.0,
            "I_g": 1.0,
            "G": 15.0,
            "t_c": 0.20,
            "t_k": 0.0,
            "r_ref": 12.00,
            "M": 30.0,
            "E": 10.0,
            "crawl_rate": 0.08,
            "regime": "flexible",
            "r_star": 5.0,
            "tau": 0.0,
            "s_x": 0.0,
            "k_c": 0.0
        },
        "initial_state": {
            "Y_pot": 95.50,
            "B": 65.0,
            "R": 25.0,
            "K_g": 10.0,
            "P_NT": 1.0,
            "pi_e": 0.10
        }
    }
}
