"""
config/scoring_v2.py
====================
Sistema de scoring ampliado V2.0. Reemplaza config/scoring.py.

Cambios respecto a V1.0:
- Scoring lineal por tramos (no binario).
- Usa `gap` en lugar de `gY` para evaluar output.
- Agrega dimensión de reservas internacionales.
- Game Over diferenciado: 4 condiciones + circuit breaker separado.
- Delta score endgame para evaluar la gestión completa (10 turnos).

Principio de diseño: funciones PURAS (sin estado global).

Jerarquía de imports permitidos:
    Este módulo no importa de engine/, ui/, ni streamlit.
"""

from __future__ import annotations

import math


# ─────────────────────────────────────────────────────────────────────────────
# UMBRALES DE GAME OVER
# ─────────────────────────────────────────────────────────────────────────────

GAME_OVER_THRESHOLDS: dict[str, float] = {
    "gY_min":      -0.20,   # Contracción > 20% → Depresión económica
    "U_max":        0.35,   # Desempleo > 35% → Colapso social
    "pi_max":       1.50,   # Inflación > 150% → Hiperinflación
    "B_Y_ratio_max": 2.00,  # Deuda/PIB > 200% → Default soberano
}

# Nota: R <= 0 bajo TC Fijo → Circuit Breaker (NO es game_over inmediato)
# El circuit breaker fuerza flexible y continúa la simulación.


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE SCORING LINEAL POR TRAMOS
# ─────────────────────────────────────────────────────────────────────────────

def _score_bounded(
    value: float,
    opt_lo: float,
    opt_hi: float,
    acc_lo: float,
    acc_hi: float,
    max_pts: int,
) -> int:
    """
    Scoring lineal por tramos para una dimensión con rango óptimo acotado.

    Regla:
    - Si value ∈ [opt_lo, opt_hi]: puntaje máximo (max_pts).
    - Si value ∈ [acc_lo, opt_lo): interpolación lineal 0 → max_pts.
    - Si value ∈ (opt_hi, acc_hi]: interpolación lineal max_pts → 0.
    - Si value fuera del rango aceptable: 0.

    Parameters
    ----------
    value   : Valor observado de la variable
    opt_lo  : Límite inferior del rango óptimo
    opt_hi  : Límite superior del rango óptimo
    acc_lo  : Límite inferior del rango aceptable
    acc_hi  : Límite superior del rango aceptable
    max_pts : Puntuación máxima de la dimensión

    Returns
    -------
    int : Puntuación de 0 a max_pts
    """
    if opt_lo <= value <= opt_hi:
        return max_pts
    if acc_lo <= value < opt_lo:
        rng = opt_lo - acc_lo
        fraction = (value - acc_lo) / rng if rng > 0 else 0.0
        return max(0, int(max_pts * fraction))
    if opt_hi < value <= acc_hi:
        rng = acc_hi - opt_hi
        fraction = (acc_hi - value) / rng if rng > 0 else 0.0
        return max(0, int(max_pts * fraction))
    return 0


def _score_upper_bounded(
    value: float,
    opt_threshold: float,
    acc_threshold: float,
    max_pts: int,
) -> int:
    """
    Scoring para dimensiones donde "menor es mejor" (e.g., déficit, desempleo).

    - Si value ≤ opt_threshold: max_pts (pleno puntaje).
    - Si opt_threshold < value ≤ acc_threshold: interpolación lineal.
    - Si value > acc_threshold: 0.

    Parameters
    ----------
    value          : Valor observado
    opt_threshold  : Umbral óptimo (arriba de éste el puntaje cae)
    acc_threshold  : Umbral aceptable máximo
    max_pts        : Puntuación máxima

    Returns
    -------
    int : Puntuación de 0 a max_pts
    """
    if value <= opt_threshold:
        return max_pts
    if value <= acc_threshold:
        rng = acc_threshold - opt_threshold
        fraction = (acc_threshold - value) / rng if rng > 0 else 0.0
        return max(0, int(max_pts * fraction))
    return 0


def _score_lower_bounded(
    value: float,
    opt_threshold: float,
    acc_threshold: float,
    max_pts: int,
) -> int:
    """
    Scoring para dimensiones donde "mayor es mejor" (e.g., reservas).

    - Si value ≥ opt_threshold: max_pts.
    - Si acc_threshold ≤ value < opt_threshold: interpolación lineal.
    - Si value < acc_threshold: 0.

    Parameters
    ----------
    value          : Valor observado
    opt_threshold  : Umbral óptimo (abajo de éste el puntaje cae)
    acc_threshold  : Umbral aceptable mínimo
    max_pts        : Puntuación máxima

    Returns
    -------
    int : Puntuación de 0 a max_pts
    """
    if value >= opt_threshold:
        return max_pts
    if value >= acc_threshold:
        rng = opt_threshold - acc_threshold
        fraction = (value - acc_threshold) / rng if rng > 0 else 0.0
        return max(0, int(max_pts * fraction))
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# SCORING PRINCIPAL DEL PERÍODO
# ─────────────────────────────────────────────────────────────────────────────

def calc_period_score_v2(
    gap: float,
    U: float,
    pi: float,
    gY: float = 0.0,          # <-- NUEVO: Tasa de crecimiento (Y_t - Y_t-1)/Y_t-1
    deficit_pct: float = 0.0, # Mantener por retrocompatibilidad, no usar en cálculo
    R: float = 50.0,          # Mantener por retrocompatibilidad, no usar en cálculo
    R_0: float = 50.0,        # Mantener por retrocompatibilidad, no usar en cálculo
    scenario_id: str = "unknown",
    current_turn: int = 0,
    has_real_fiscal_surplus: bool = False,
    prev_score: Optional[float] = None,
) -> float:
    """
    Calcula la PERCEPCIÓN PÚBLICA (Aprobación Ciudadana) de 0 a 100.
    Diseño "Suavizado": Se enfoca solo en lo que el votante siente.
    Permite recuperaciones y no castiga variables tecnocráticas directamente.
    """
    # 1. SCORE DE DESEMPLEO (Peso 40%)
    # Ideal: <= 4% (100 pts). V3.5: Tolerancia de 2% (hasta 6% sin penalidad) y degradación más suave (1000 en vez de 1250)
    diff_U = max(0.0, U - 0.04)
    if diff_U < 0.02:
        penalty_U = 0.0
    else:
        penalty_U = (diff_U - 0.02) * 1000.0
    
    # 2. SCORE DE INFLACIÓN (Peso 40%)
    # V3.6: Asimetría con zona de no-castigo hasta -2% para deflación
    desviacion_pi = pi - 0.03
    if desviacion_pi < 0:
        # Deflación: penalidad reducida y con zona de no-castigo hasta -2%
        penalty_pi = max(0.0, abs(desviacion_pi) - 0.04) * 80.0
    else:
        # Inflación/Hiperinflación: penalidad estricta e inalterada
        penalty_pi = desviacion_pi * 333.0

    # Paso B: Vincular la Responsabilidad Fiscal al Score
    if has_real_fiscal_surplus:
        penalty_U *= 0.5

    # Paso A: Ventana de Gracia en turnos 1, 2 y 3 para crisis profundas
    if scenario_id in ["latam_crisis", "death_spiral"] and 1 <= current_turn <= 3:
        penalty_U *= 0.5
        penalty_pi *= 0.5

    score_U = max(0.0, 100.0 - penalty_U)
    score_pi = max(0.0, 100.0 - penalty_pi)
    
    # 3. SCORE DE CRECIMIENTO (Peso 20%)
    # Base 50 pts (neutral). Sube con crecimiento, baja con recesión.
    # 0% = 50 pts, 5% = 100 pts, -5% = 0 pts
    score_gY = max(0.0, min(100.0, 50.0 + (gY * 1000)))
    
    # Ponderación final (score del turno presente)
    score_present = (score_U * 0.40) + (score_pi * 0.40) + (score_gY * 0.20)
    
    # Paso C: Suavizado por Media Móvil (60% actual, 40% anterior)
    if prev_score is not None:
        percepcion_publica = 0.60 * score_present + 0.40 * prev_score
    else:
        percepcion_publica = score_present
        
    return round(percepcion_publica, 2)


# ─────────────────────────────────────────────────────────────────────────────
# GAME OVER: VERIFICACIÓN DE UMBRALES CRÍTICOS
# ─────────────────────────────────────────────────────────────────────────────

def check_game_over(
    gY:    float,
    U:     float,
    pi:    float,
    R:     float,
    regime: str,
    B:     float,
    Y:     float,
    history: list = None,
) -> tuple[bool, str | None]:
    """
    Verifica si se cruza algún umbral de Game Over.

    Criterios de Game Over:
    ┌───────────────────┬──────────┬──────────────────────────────────┐
    │ Variable          │ Umbral   │ Condición                        │
    ├───────────────────┼──────────┼──────────────────────────────────┤
    │ gY (crecimiento)  │ < -15%   │ Depresión económica              │
    │ U (desempleo)     │ > 35%    │ Colapso social                   │
    │ π (inflación)     │ > 150%   │ Hiperinflación                   │
    │ B/Y (deuda/PIB)   │ > 150%   │ Default soberano                 │
    └───────────────────┴──────────┴──────────────────────────────────┘

    Nota: R ≤ 0 bajo TC Fijo → Circuit Breaker (NO es Game Over inmediato).
    El circuit breaker se gestiona por separado en check_reserve_circuit_breaker.

    Parameters
    ----------
    gY     : Tasa de crecimiento del PIB del período
    U      : Tasa de desempleo
    pi     : Inflación del período
    R      : Reservas internacionales (post-turno)
    regime : Régimen cambiario activo
    B      : Deuda pública acumulada (post-turno)
    Y      : PIB de equilibrio del período

    Returns
    -------
    tuple[bool, str | None]
        (game_over, reason) donde reason es None si no hay game over.
    """
    thr = GAME_OVER_THRESHOLDS
    gY_min = thr["gY_min"]
    U_max = thr["U_max"]

    # Evaluar medias móviles de los últimos dos períodos para evitar game overs por rebotes contables transitorios
    gY_smoothed = gY
    U_smoothed = U
    if history and len(history) >= 2:
        gY_smoothed = 0.5 * gY + 0.5 * history[-2].get("gY", gY)
        U_smoothed = 0.5 * U + 0.5 * history[-2].get("U", U)

    # 1. Depresión económica
    if gY_smoothed < gY_min:
        return True, (
            f"💀 DEPRESIÓN ECONÓMICA: La economía se contrajo {abs(gY_smoothed):.1%} en un "
            f"solo período (umbral: {gY_min:.1%}). La actividad colapsó."
        )

    # 2. Colapso social
    if U_smoothed > U_max:
        return True, (
            f"🔥 COLAPSO SOCIAL: El desempleo alcanzó {U_smoothed:.1%} "
            f"(umbral: {U_max:.0%}). Estallido social inevitable."
        )

    # 3. Hiperinflación
    if pi > thr["pi_max"]:
        return True, (
            f"📈 HIPERINFLACIÓN: La inflación alcanzó {pi:.1%} "
            f"(umbral: {thr['pi_max']:.0%}). El sistema monetario colapsó."
        )

    # 4. Default soberano (B/Y)
    if Y > 0.0:
        B_Y_ratio = B / Y
        if B_Y_ratio > thr["B_Y_ratio_max"]:
            return True, (
                f"💸 DEFAULT SOBERANO: La deuda pública alcanzó {B_Y_ratio:.1%} del PIB "
                f"(umbral: {thr['B_Y_ratio_max']:.0%}). El país no puede honrar sus compromisos."
            )

    return False, None


# ─────────────────────────────────────────────────────────────────────────────
# DELTA SCORE: EVALUACIÓN DE LA GESTIÓN COMPLETA
# ─────────────────────────────────────────────────────────────────────────────

def calc_endgame_delta_score(history: list) -> float:
    """
    Calcula el delta score entre el turno 0 (línea base) y el turno final.

    delta_score = score(t_final) − score(t_0)

    Si delta_score > 0: el jugador mejoró la economía respecto al punto de partida.
    Si delta_score ≤ 0: la economía empeoró o quedó igual.

    Parameters
    ----------
    history : Lista de TurnSnapshot (history[0] = t=0, history[-1] = turno final)

    Returns
    -------
    float : Delta score (puede ser negativo)
    """
    if len(history) < 2:
        return 0.0

    snap_0 = history[0]
    snap_f = history[-1]

    return float(snap_f["score"] - snap_0["score"])


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES DE VISUALIZACIÓN (sin dependencias de streamlit)
# ─────────────────────────────────────────────────────────────────────────────

def get_score_emoji(score: int) -> str:
    """Emoji de semáforo según el puntaje del período."""
    if score >= 70:
        return "🟢"
    if score >= 40:
        return "🟡"
    return "🔴"


def get_score_label(score: int) -> str:
    """Etiqueta de texto según el puntaje del período."""
    if score >= 80:
        return "Excelente"
    if score >= 60:
        return "Bueno"
    if score >= 40:
        return "Regular"
    if score >= 20:
        return "Malo"
    return "Crítico"


def get_dimension_scores(
    gap: float,
    U: float,
    pi: float,
    deficit_pct: float = 0.0,
    R: float = 50.0,
    R_0: float = 50.0,
    gY: float = 0.0,  # V3.1: crecimiento real
    scenario_id: str = "unknown",
    current_turn: int = 0,
    has_real_fiscal_surplus: bool = False,
) -> dict[str, int]:
    """
    Retorna el desglose del score por dimensión.
    Unificado con calc_period_score_v2 (Opción B: Empleo 40%, Precios 40%, Crecimiento 20%).

    Returns
    -------
    dict con claves: 'U', 'pi', 'gY', 'total'
    """
    # 1. SCORE DE DESEMPLEO (Peso 40%)
    diff_U = max(0.0, U - 0.04)
    if diff_U < 0.02:
        penalty_U = 0.0
    else:
        # V3.5: degradación 1000.0
        penalty_U = (diff_U - 0.02) * 1000.0

    # 2. SCORE DE INFLACIÓN (Peso 40%)
    desviacion_pi = pi - 0.03
    if desviacion_pi < 0:
        penalty_pi = max(0.0, abs(desviacion_pi) - 0.04) * 80.0
    else:
        # V3.6: penalidad 333.0
        penalty_pi = desviacion_pi * 333.0

    # Paso B: Vincular la Responsabilidad Fiscal al Score
    if has_real_fiscal_surplus:
        penalty_U *= 0.5

    # Paso A: Ventana de Gracia en turnos 1, 2 y 3 para crisis profundas
    if scenario_id in ["latam_crisis", "death_spiral"] and 1 <= current_turn <= 3:
        penalty_U *= 0.5
        penalty_pi *= 0.5

    s_U = int(round(max(0.0, 100.0 - penalty_U) * 0.40))
    s_pi = int(round(max(0.0, 100.0 - penalty_pi) * 0.40))
    s_gY = int(round(max(0.0, min(100.0, 50.0 + (gY * 1000))) * 0.20))

    total = min(100, s_U + s_pi + s_gY)

    return {
        "gap": 0,       # Legacy placeholder
        "deficit": 0,   # Legacy placeholder
        "reservas": 0,  # Legacy placeholder
        "U": s_U,
        "pi": s_pi,
        "gY": s_gY,
        "total": total,
    }
