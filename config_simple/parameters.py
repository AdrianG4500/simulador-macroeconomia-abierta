"""
config_simple/parameters.py
===========================
Parámetros estructurales y tipos de datos del Simulador Macroeconómico Simplificado.
Edición: The Economic War Room (V1.2 SIMPLE).

Principios:
- 8 Palancas de Política Económica distribuidas en 3 bloques ministeriales.
- Parámetros estructurales puros para resolución analítica cerrada (sin solvers iterativos).
- Identidad contable nacional exacta: Y = C + I + G + NX (error < 1e-12).
- Tipos de datos TypedDict estrictos y serializables para integración con Supabase y Canvas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class StructuralParams(TypedDict):
    """Parámetros estructurales fundamentales de la economía abierta."""
    # Consumo
    c0: float         # Consumo autónomo familiar
    c1: float         # Propensión marginal a consumir (0 < c1 < 1)

    # Inversión privada
    I0: float         # Inversión privada autónoma base
    b: float          # Sensibilidad de la inversión a la tasa de interés doméstica
    rho_k: float      # Sensibilidad de la inversión al impuesto corporativo tk
    psi_ci: float     # Sensibilidad de crowding-in por inversión pública Ig
    psi_co: float     # Sensibilidad de crowding-out por exceso de deuda (> 60% PIB)
    r0: float         # Tasa de interés de referencia neutral
    tk0: float        # Tasa de impuesto corporativo base
    Ig0: float        # Inversión pública base de referencia

    # Sector externo
    x0: float         # Exportaciones autónomas base
    m0: float         # Importaciones autónomas base
    m1: float         # Propensión marginal a importar (0 < m1 < 1)
    epsilon_x: float  # Elasticidad-precio de las exportaciones respecto a q
    epsilon_m: float  # Elasticidad-precio de las importaciones respecto a q
    eta_x: float      # Sensibilidad de las exportaciones al subsidio sx
    f: float          # Sensibilidad del flujo de capitales KA a diferenciales de tasa

    # Precios e inflación
    alpha_PT: float   # Peso de transables en la canasta (0.40 según especificación)
    beta_PT: float    # Pass-through de la depreciación cambiaria a inflación
    alpha_inf: float  # Sensibilidad de la inflación a la brecha del producto (Phillips)
    P_star: float     # Nivel de precios externo base

    # Mercado laboral y PIB potencial
    U_n: float        # Tasa natural de desempleo (NAIRU)
    gamma_okun: float # Sensibilidad del desempleo a la brecha del producto (Okun)
    g_pot: float      # Tasa de crecimiento natural del PIB potencial
    Ig_dep: float     # Inversión pública mínima de reposición / depreciación


class PolicyInstruments(TypedDict):
    """
    Las 8 palancas de política económica y variables de control del estudiante.
    
    Bloque Fiscal:
      1. Gc: Gasto Público Corriente [5.0, 35.0]
      2. Ig: Inversión Pública en Infraestructura [0.0, 25.0]
      3. tc: Impuesto a la Renta / Consumo [0.05, 0.40]
      4. tk: Impuesto Corporativo a Empresas [0.00, 0.35]
    Bloque Monetario:
      5. r_ref: Tasa de Política Monetaria TPM en p.p. [1.0, 30.0]
    Bloque Comercial:
      6. tau: Arancel a las Importaciones [0.00, 0.30]
      7. sx: Subsidio a las Exportaciones [0.00, 0.20]
    Bloque Cambiario:
      8. E: Tipo de Cambio Nominal [5.0, 25.0] o crawl_rate [0.0, 0.25]
    """
    # 1. Fiscal
    Gc: float          # Gasto público corriente
    Ig: float          # Inversión pública en infraestructura
    tc: float          # Impuesto a la renta y al consumo (tasa efectiva)
    tk: float          # Impuesto a las utilidades corporativas
    
    # 2. Monetario
    r_ref: float       # Tasa de Política Monetaria TPM en puntos porcentuales (ej. 6.0 = 6.0%)

    # 3. Comercial
    tau: float         # Arancel nominal a las importaciones
    sx: float          # Subsidio porcentual a las exportaciones

    # 4. Cambiario
    E: float           # Tipo de cambio nominal (exógeno en fijo/crawling, flotante en flexible)
    regime: str        # "fixed" | "flexible" | "crawling_peg"
    crawl_rate: float  # Tasa de deslizamiento cambiario mensual/período (solo crawling_peg)

    # Entorno internacional y metas
    r_star: float      # Tasa de interés externa de referencia (puntos porcentuales)
    P_star: float      # Nivel de precios internacional
    pi_target: float   # Meta de inflación del Banco Central (ej. 0.03 = 3%)
    G_needed: float    # Gasto de emergencia adicional (por eventos o desastres)

    # Aliases de compatibilidad
    G: float           # Gasto total (Gc + Ig + G_needed)
    t: float           # Alias de tc


class Equilibrium(TypedDict):
    """Resultado instantáneo del equilibrio macroeconómico analítico cerrado."""
    Y: float           # PIB Real de equilibrio suavizado (Y_t)
    Y_eq: float        # PIB Real analítico instantáneo antes de inercia
    r: float           # Tasa de interés doméstica efectiva
    E_endo: float      # Tipo de cambio endógeno resultante
    NX: float          # Exportaciones netas (X - M_imp)
    X: float           # Exportaciones brutas
    M_imp: float       # Importaciones brutas
    C: float           # Consumo privado familiar
    I_priv: float      # Inversión privada (absorbe ajuste de inventarios post-inercia)
    Gc: float          # Gasto corriente aplicado
    Ig: float          # Inversión pública aplicada
    G: float           # Gasto público total (Gc + Ig)
    mult: float        # Multiplicador keynesiano ampliado k_m
    P_local: float     # Nivel de precios doméstico P_local
    P_T: float         # Nivel de precios de bienes transables
    P_NT: float        # Nivel de precios de bienes no transables
    q_real: float      # Tipo de cambio real q = (E/10 · P*) / P_local
    gap: float         # Brecha del producto (Y - Y_pot) / Y_pot
    A_domestic: float  # Absorción doméstica A = C + I_priv + G
    PIB_nominal: float # PIB Nominal = Y * P_local


class SalterSwanResult(TypedDict):
    """Resultado del análisis de equilibrio interno y externo de Salter-Swan."""
    zone: str          # "I", "II", "III", "IV"
    diagnosis: str     # Diagnóstico didáctico del desequilibrio
    policy: str        # Recomendación didáctica de política económica
    q_actual: float    # TCR actual
    A_actual: float    # Absorción doméstica actual
    q_IB_at_A: float   # Umbral de balance interno dado A
    q_EB_at_A: float   # Umbral de balance externo dado A
    slope_IB: float    # Pendiente de la curva IB
    slope_EB: float    # Pendiente de la curva EB
    ml_satisfied: bool # ¿Cumple la condición Marshall-Lerner?


class TurnSnapshot(TypedDict):
    """Fotografía inmutable de todas las variables al cierre de un turno (t = 0..10)."""
    t: int                     # Turno (0 = base, 1-10 = jugado)
    Y: float                   # PIB Real resuelto
    Y_pot: float               # PIB Potencial vigente
    r: float                   # Tasa de interés doméstica efectiva (%)
    C: float                   # Consumo privado familiar
    I_priv: float              # Inversión privada efectiva
    I_inv: float               # Alias de I_priv para compatibilidad
    Gc: float                  # Gasto corriente del gobierno
    Ig: float                  # Inversión pública en infraestructura
    G: float                   # Gasto total (Gc + Ig)
    NX: float                  # Exportaciones netas
    X: float                   # Exportaciones brutas
    M_imp: float               # Importaciones brutas
    A_domestic: float          # Absorción doméstica (C + I_priv + G)
    E: float                   # Tipo de cambio nominal
    P_local: float             # Nivel de precios general
    P_T: float                 # Precios transables
    P_NT: float                # Precios no transables
    q_real: float              # Tipo de cambio real normalizado en base 10
    pi: float                  # Inflación del período (fracción, ej. 0.03)
    pi_e: float                # Expectativas de inflación para el siguiente turno
    theta: float               # Coeficiente de credibilidad del Banco Central [0.40, 0.80]
    U: float                   # Tasa de desempleo (fracción, ej. 0.05)
    gap: float                 # Brecha del producto (Y - Y_pot)/Y_pot
    gY: float                  # Tasa de crecimiento del PIB (Y_t - Y_{t-1})/Y_{t-1}
    recaudacion: float         # Recaudación fiscal total = (tc + tk)*Y + tau*M_imp
    costo_subsidios: float     # Gasto en fomento exportador = sx * X
    intereses_deuda: float     # Intereses de la deuda = ((r* + rho)/100) * B_{t-1}
    deficit: float             # Déficit fiscal total
    B: float                   # Stock de deuda pública acumulada
    PIB_nominal: float         # PIB Nominal = Y * P_local
    debt_to_gdp_nominal: float # Ratio Deuda / PIB Nominal = B / PIB_nominal
    R: float                   # Reservas internacionales del Banco Central
    KA: float                  # Flujo neto de capitales externos
    rho: float                 # Prima de riesgo soberano (en puntos porcentuales)
    rating: str                # Calificación crediticia soberana (AAA .. D)
    zone_ss: str               # Cuadrante de Salter-Swan ("I", "II", "III", "IV")
    score: float               # Aprobación ciudadana ponderada (0 - 100)
    red_alert_active: bool     # Indicador de alerta roja crítica en el turno actual
    red_alert_reason: str      # Mensaje descriptivo si se encuentra en zona de peligro
    consecutive_alert_turns: int # Contador de turnos consecutivos en estado crítico
    policy_applied: Dict[str, Any] # Copia de las 8 palancas aplicadas este turno
    events_triggered: List[str]    # Lista de eventos ocurridos en el turno


# ─────────────────────────────────────────────────────────────────────────────
# VALORES POR DEFECTO BASE (Calibración Neutral)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_STRUCTURAL_PARAMS: StructuralParams = {
    # Consumo
    "c0": 12.0,
    "c1": 0.65,
    
    # Inversión privada
    "I0": 16.0,
    "b": 0.80,
    "rho_k": 10.0,
    "psi_ci": 0.25,
    "psi_co": 15.0,
    "r0": 5.0,
    "tk0": 0.10,
    "Ig0": 6.0,

    # Sector externo
    "x0": 18.0,
    "m0": 6.5,
    "m1": 0.15,
    "epsilon_x": 1.20,
    "epsilon_m": 1.10,
    "eta_x": 20.0,
    "f": 2.0,

    # Precios e inflación
    "alpha_PT": 0.40,
    "beta_PT": 0.20,
    "alpha_inf": 0.25,
    "P_star": 1.0,

    # Mercado laboral y PIB potencial
    "U_n": 0.05,
    "gamma_okun": 0.45,
    "g_pot": 0.025,
    "Ig_dep": 5.0,
}


DEFAULT_POLICY_INSTRUMENTS: PolicyInstruments = {
    # Bloque Fiscal
    "Gc": 14.0,
    "Ig": 6.0,
    "tc": 0.16,
    "tk": 0.10,

    # Bloque Monetario
    "r_ref": 5.0,

    # Bloque Comercial
    "tau": 0.05,
    "sx": 0.00,

    # Bloque Cambiario
    "E": 10.0,
    "regime": "fixed",
    "crawl_rate": 0.00,

    # Contexto macroeconómico
    "r_star": 4.5,
    "P_star": 1.0,
    "pi_target": 0.03,
    "G_needed": 0.0,

    # Aliases
    "G": 20.0,
    "t": 0.16,
}
