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
    "gY_min":      -0.15,   # Contracción > 15% → Depresión económica
    "U_max":        0.35,   # Desempleo > 35% → Colapso social
    "pi_max":       1.50,   # Inflación > 150% → Hiperinflación
    "B_Y_ratio_max": 1.50,  # Deuda/PIB > 150% → Default soberano
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
    deficit_pct: float,
    R: float,
    R_0: float,
) -> int:
    """
    Puntaje del período: 0–100 puntos, suma de 5 dimensiones.

    Dimensiones y pesos:
    ┌────────────────┬──────┬───────────────────┬──────────────────┐
    │ Dimensión      │ Peso │ Óptimo            │ Aceptable        │
    ├────────────────┼──────┼───────────────────┼──────────────────┤
    │ Output Gap     │  25  │ gap ∈ [-1%, +3%]  │ gap ∈ [-3%, +5%]│
    │ Desempleo U    │  25  │ U < 5%            │ U < 8%           │
    │ Inflación π    │  25  │ π ∈ [1%, 4%]      │ π ∈ [0%, 6%]    │
    │ Déficit/PIB    │  15  │ déficit < 3%      │ déficit < 6%     │
    │ Reservas R/R₀  │  10  │ R > 80% R₀       │ R > 50% R₀       │
    └────────────────┴──────┴───────────────────┴──────────────────┘

    Parameters
    ----------
    gap        : Brecha del producto = (Y - Y_pot) / Y_pot
    U          : Tasa de desempleo
    pi         : Inflación del período
    deficit_pct: Déficit fiscal como fracción del PIB
    R          : Reservas internacionales del período
    R_0        : Reservas iniciales (referencia en t=0)

    Returns
    -------
    int : Score del período (0–100)
    """
    score = 0

    # 1. Output Gap (25 pts): óptimo [-0.01, 0.03], aceptable [-0.03, 0.05]
    score += _score_bounded(gap, -0.01, 0.03, -0.03, 0.05, 25)

    # 2. Desempleo (25 pts): óptimo [0, 0.05], aceptable [0, 0.08]
    score += _score_bounded(U, 0.0, 0.05, 0.0, 0.08, 25)

    # 3. Inflación (25 pts): óptimo [0.01, 0.04], aceptable [0.0, 0.06]
    score += _score_bounded(pi, 0.01, 0.04, 0.0, 0.06, 25)

    # 4. Déficit/PIB (15 pts): menor es mejor
    score += _score_upper_bounded(deficit_pct, 0.03, 0.06, 15)

    # 5. Reservas relativas (10 pts): mayor es mejor
    R_ratio = R / max(R_0, 1.0)
    score += _score_lower_bounded(R_ratio, 0.80, 0.50, 10)

    return min(100, max(0, score))


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

    # 1. Depresión económica
    if gY < thr["gY_min"]:
        return True, (
            f"💀 DEPRESIÓN ECONÓMICA: La economía se contrajo {abs(gY):.1%} en un "
            "solo período (umbral: −15%). La actividad colapsó."
        )

    # 2. Colapso social
    if U > thr["U_max"]:
        return True, (
            f"🔥 COLAPSO SOCIAL: El desempleo alcanzó {U:.1%} "
            f"(umbral: {thr['U_max']:.0%}). Estallido social inevitable."
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
    deficit_pct: float,
    R: float,
    R_0: float,
) -> dict[str, int]:
    """
    Retorna el desglose del score por dimensión.
    Útil para el panel de diagnóstico de la UI.

    Returns
    -------
    dict con claves: 'gap', 'U', 'pi', 'deficit', 'reservas', 'total'
    """
    s_gap    = _score_bounded(gap, -0.01, 0.03, -0.03, 0.05, 25)
    s_U      = _score_bounded(U, 0.0, 0.05, 0.0, 0.08, 25)
    s_pi     = _score_bounded(pi, 0.01, 0.04, 0.0, 0.06, 25)
    s_def    = _score_upper_bounded(deficit_pct, 0.03, 0.06, 15)
    R_ratio  = R / max(R_0, 1.0)
    s_res    = _score_lower_bounded(R_ratio, 0.80, 0.50, 10)

    total = min(100, s_gap + s_U + s_pi + s_def + s_res)

    return {
        "gap":      s_gap,
        "U":        s_U,
        "pi":       s_pi,
        "deficit":  s_def,
        "reservas": s_res,
        "total":    total,
    }
