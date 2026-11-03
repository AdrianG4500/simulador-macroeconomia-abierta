"""
config_simple/scoring.py
========================
Sistema de Evaluación de Percepción Pública (Scoring) y Blindaje Anti-Bucle de Game Over.
Edición: The Economic War Room (V1.2 SIMPLE).

Principios Fundamentales (Sección 4 de master_spec.md):
1. Regla 1 (Blindaje Anti-Bucle y Gracia Inicial):
   - Período de gracia: En los Turnos 1 y 2 está ESTRICTAMENTE PROHIBIDO el Game Over.
   - A partir del Turno 3: El Game Over requiere persistencia de 2 turnos consecutivos en zona crítica.
   - En el primer turno de infracción se emite una Alerta Roja Crítica preventiva.
2. Regla 2 (Score Ponderado de Aprobación Ciudadana):
   - Score = 100 - [1.2·|Gap·100| + 2.0·max(0, (U - Un)·100) + 1.5·|π - 0.03|·100 + 0.5·max(0, RatioDeuda·100 - 60)]
   - Inercia ciudadana 70/30 acotada entre 0 y 100 puntos.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# UMBRALES DE ALERTA ROJA Y GAME OVER (Sección 4 de master_spec.md)
# ─────────────────────────────────────────────────────────────────────────────

CRITICAL_ALERT_THRESHOLDS = {
    "debt_ratio_max": 1.35,      # Deuda / PIB Nominal > 135%
    "reserves_min": 8.0,         # Reservas < 8.0 MUSD
    "pi_max": 0.35,              # Inflación > 35.0%
    "U_max": 0.22,               # Desempleo > 22.0%
    "gY_min": -0.15,             # Contracción del PIB > 15% en 1 turno
}

GAME_OVER_THRESHOLDS = {
    "debt_ratio_max": 1.50,      # Deuda / PIB Nominal > 150% por 2 turnos
    "reserves_min": 2.0,         # Reservas <= 2.0 MUSD por 2 turnos
    "pi_max": 0.50,              # Inflación > 50.0% por 2 turnos
    "U_max": 0.25,               # Desempleo > 25.0% por 2 turnos
}

# Compatibilidad con definiciones previas
GAME_OVER_THRESHOLDS["B_Y_ratio_max"] = GAME_OVER_THRESHOLDS["debt_ratio_max"]


# ─────────────────────────────────────────────────────────────────────────────
# OBJETO DE RESULTADO DE EVALUACIÓN DE GAME OVER
# ─────────────────────────────────────────────────────────────────────────────

class GameOverResult:
    """
    Contenedor de evaluación de estado crítico.
    Permite desempaque estilo tupla (is_game_over, reason) para retrocompatibilidad
    y acceso a atributos de alerta roja y contadores consecutivos.
    """

    def __init__(
        self,
        is_game_over: bool,
        reason: Optional[str],
        red_alert_active: bool = False,
        red_alert_reason: str = "",
        counters: Optional[Dict[str, int]] = None,
    ) -> None:
        self.is_game_over: bool = is_game_over
        self.reason: Optional[str] = reason
        self.red_alert_active: bool = red_alert_active
        self.red_alert_reason: str = red_alert_reason
        self.counters: Dict[str, int] = counters or {
            "debt": 0,
            "reserves": 0,
            "inflation": 0,
            "unemployment": 0,
        }

    def __iter__(self):
        """Desempaque clásico (is_game_over, reason)."""
        yield self.is_game_over
        yield self.reason

    def __repr__(self) -> str:
        return (
            f"GameOverResult(is_game_over={self.is_game_over}, "
            f"reason={self.reason!r}, "
            f"red_alert_active={self.red_alert_active}, "
            f"red_alert_reason={self.red_alert_reason!r})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# REGLA 1: EVALUACIÓN DE GAME OVER Y ALERTA ROJA (PERSISTENCIA DE 2 TURNOS)
# ─────────────────────────────────────────────────────────────────────────────

def check_game_over(
    turn: int = 1,
    debt_ratio_nominal: float = 0.0,
    reserves: float = 50.0,
    pi: float = 0.03,
    U: float = 0.05,
    gY: float = 0.0,
    consecutive_danger_turns: Optional[Dict[str, int]] = None,
    **kwargs: Any,
) -> GameOverResult:
    """
    Evalúa si la economía entra en Alerta Roja Crítica o en Game Over definitivo.

    Reglas de Hierro:
    1. Turnos 1 y 2: PERÍODO DE GRACIA. Nunca hay Game Over en t <= 2.
    2. A partir de Turno 3: Game Over SOLO si la condición letal persiste durante
       2 turnos consecutivos.
    3. Primer turno de cruce: Emite Alerta Roja preventiva sin terminar la partida.

    Parameters
    ----------
    turn : int
        Turno actual de la simulación.
    debt_ratio_nominal : float
        Ratio de Deuda Pública sobre PIB Nominal (B / (Y · P_local)).
    reserves : float
        Nivel actual de Reservas Internacionales en MUSD.
    pi : float
        Tasa de inflación anualizada del período (fracción, ej. 0.03 = 3%).
    U : float
        Tasa de desempleo (fracción, ej. 0.05 = 5%).
    gY : float
        Tasa de crecimiento del PIB (fracción).
    consecutive_danger_turns : Optional[Dict[str, int]]
        Diccionario acumulador de turnos consecutivos en zona crítica.
    """
    # Mapeo de argumentos heredados
    if "B_Y_ratio" in kwargs:
        debt_ratio_nominal = kwargs["B_Y_ratio"]
    if "R" in kwargs:
        reserves = kwargs["R"]

    # Inicializar contadores si no se proporcionan
    counters = copy_counters(consecutive_danger_turns)

    alert_active = False
    alert_reasons = []

    # 1. Insolvencia Soberana (Default)
    if debt_ratio_nominal > GAME_OVER_THRESHOLDS["debt_ratio_max"]:
        counters["debt"] += 1
        if counters["debt"] == 1:
            alert_active = True
            alert_reasons.append(
                f"🚨 ALERTA CRÍTICA DE DEFAULT: Ratio Deuda/PIB Nominal en {debt_ratio_nominal*100:.1f}% "
                f"(umbral letal: >150%). Aplique consolidación fiscal inmediata para evitar la cesación de pagos."
            )
    elif debt_ratio_nominal > CRITICAL_ALERT_THRESHOLDS["debt_ratio_max"]:
        counters["debt"] = 0
        alert_active = True
        alert_reasons.append(
            f"⚠️ RIESGO FISCAL ELEVADO: Ratio Deuda/PIB Nominal en {debt_ratio_nominal*100:.1f}% "
            f"(alerta preventiva >135%)."
        )
    else:
        counters["debt"] = 0

    # 2. Crisis de Balanza de Pagos
    if reserves <= GAME_OVER_THRESHOLDS["reserves_min"]:
        counters["reserves"] += 1
        if counters["reserves"] == 1:
            alert_active = True
            alert_reasons.append(
                f"🚨 ALERTA CRÍTICA DE RESERVAS / CRISIS DE BALANZA DE PAGOS: Reservas en {reserves:.1f} MUSD "
                f"(umbral letal: ≤2.0 MUSD). Ajuste el tipo de cambio o suba tasas para frenar el colapso externo."
            )
    elif reserves < CRITICAL_ALERT_THRESHOLDS["reserves_min"]:
        counters["reserves"] = 0
        alert_active = True
        alert_reasons.append(
            f"⚠️ RESERVAS EN ZONA DE VULNERABILIDAD: {reserves:.1f} MUSD (alerta preventiva <8.0 MUSD)."
        )
    else:
        counters["reserves"] = 0

    # 3. Espiral Hiperinflacionaria
    if pi > GAME_OVER_THRESHOLDS["pi_max"]:
        counters["inflation"] += 1
        if counters["inflation"] == 1:
            alert_active = True
            alert_reasons.append(
                f"🚨 ALERTA CRÍTICA DE HIPERINFLACIÓN: Inflación en {pi*100:.1f}% "
                f"(umbral letal: >50.0%). Aplique shock monetario y anclaje fiscal urgente."
            )
    elif pi > CRITICAL_ALERT_THRESHOLDS["pi_max"]:
        counters["inflation"] = 0
        alert_active = True
        alert_reasons.append(
            f"⚠️ PRESIÓN INFLACIONARIA AGUDA: Inflación en {pi*100:.1f}% (alerta preventiva >35.0%)."
        )
    else:
        counters["inflation"] = 0

    # 4. Estallido Social / Depresión Severa
    if U > GAME_OVER_THRESHOLDS["U_max"]:
        counters["unemployment"] += 1
        if counters["unemployment"] == 1:
            alert_active = True
            alert_reasons.append(
                f"🚨 ALERTA CRÍTICA DE DESEMPLEO: Desempleo en {U*100:.1f}% "
                f"(umbral letal: >25.0%). El tejido productivo y social está en colapso."
            )
    elif U > CRITICAL_ALERT_THRESHOLDS["U_max"] or gY < CRITICAL_ALERT_THRESHOLDS["gY_min"]:
        counters["unemployment"] = 0
        alert_active = True
        desc = f"Desempleo en {U*100:.1f}%" if U > CRITICAL_ALERT_THRESHOLDS["U_max"] else f"Contracción económica de {gY*100:.1f}%"
        alert_reasons.append(f"⚠️ CONFLICTIVIDAD SOCIAL / RECESIÓN: {desc}.")
    else:
        counters["unemployment"] = 0

    full_alert_msg = " | ".join(alert_reasons) if alert_reasons else ""

    # REGLA DE GRACIA INICIAL: Jamás Game Over en Turnos 1 y 2
    if turn <= 2:
        return GameOverResult(
            is_game_over=False,
            reason=None,
            red_alert_active=alert_active,
            red_alert_reason=full_alert_msg,
            counters=counters,
        )

    # REGLA DE PERSISTENCIA: Game Over requiere 2 turnos consecutivos en condición letal
    if counters["debt"] >= 2:
        reason = (
            f"💥 DEFAULT SOBERANO (2 turnos consecutivos con Deuda/PIB Nominal > 150%). "
            f"El país ha perdido acceso total a los mercados financieros internacionales."
        )
        return GameOverResult(True, reason, alert_active, full_alert_msg, counters)

    if counters["reserves"] >= 2:
        reason = (
            f"💥 CRISIS DE BALANZA DE PAGOS (2 turnos consecutivos con Reservas ≤ 2.0 MUSD). "
            f"El Banco Central se ha quedado sin dólares para respaldar importaciones básicas."
        )
        return GameOverResult(True, reason, alert_active, full_alert_msg, counters)

    if counters["inflation"] >= 2:
        reason = (
            f"💥 ESPIRAL HIPERINFLACIONARIA (2 turnos consecutivos con Inflación > 50.0%). "
            f"El signo monetario nacional ha colapsado y los precios han perdido todo anclaje."
        )
        return GameOverResult(True, reason, alert_active, full_alert_msg, counters)

    if counters["unemployment"] >= 2:
        reason = (
            f"💥 ESTALLIDO SOCIAL Y QUIEBRA DEL EMPLEO (2 turnos consecutivos con Desempleo > 25.0%). "
            f"La crisis laboral ha generado una parálisis socioeconómica total."
        )
        return GameOverResult(True, reason, alert_active, full_alert_msg, counters)

    # Si no persiste 2 turnos, la partida sigue activa
    return GameOverResult(
        is_game_over=False,
        reason=None,
        red_alert_active=alert_active,
        red_alert_reason=full_alert_msg,
        counters=counters,
    )


def copy_counters(counters: Optional[Dict[str, int]]) -> Dict[str, int]:
    """Crea una copia segura de los contadores consecutivos."""
    base = {"debt": 0, "reserves": 0, "inflation": 0, "unemployment": 0}
    if counters:
        for k in base:
            base[k] = int(counters.get(k, 0))
    return base


# ─────────────────────────────────────────────────────────────────────────────
# REGLA 2: SCORE PONDERADO DE APROBACIÓN CIUDADANA (0 A 100)
# ─────────────────────────────────────────────────────────────────────────────

def calc_period_score(
    gap: float,
    U: float,
    pi: float,
    gY: float = 0.0,
    prev_score: Optional[float] = None,
    debt_ratio: float = 0.0,
    Un: float = 0.05,
    **kwargs: Any,
) -> float:
    """
    Calcula el puntaje de Aprobación Ciudadana según la fórmula de Sección 4:

    Score_calc = 100 - [
        1.2 · |Gap · 100| +
        2.0 · max(0, (U - Un) · 100) +
        1.5 · |π - 0.03| · 100 +
        0.5 · max(0, RatioDeuda · 100 - 60)
    ]

    Inercia suave:
        Score_t = 0.70 · Score_calc + 0.30 · Score_{t-1}
        Acotado estrictamente en [0.0, 100.0].
    """
    # Mapeo de argumentos alternativos
    if "debt_to_gdp_nominal" in kwargs:
        debt_ratio = kwargs["debt_to_gdp_nominal"]
    elif "B_Y_ratio" in kwargs:
        debt_ratio = kwargs["B_Y_ratio"]
    if "U_n" in kwargs:
        Un = kwargs["U_n"]

    # 1. Penalidad por Brecha del Producto (|Gap| en puntos porcentuales)
    penalidad_gap = 1.2 * abs(gap * 100.0)

    # 2. Penalidad por exceso de desempleo sobre NAIRU
    exceso_desempleo = max(0.0, (U - Un) * 100.0)
    penalidad_empleo = 2.0 * exceso_desempleo

    # 3. Penalidad por desviación de la meta de inflación (3.0%)
    desviacion_inflacion = abs((pi - 0.03) * 100.0)
    penalidad_inflacion = 1.5 * desviacion_inflacion

    # 4. Penalidad por exceso de deuda pública (> 60% del PIB)
    exceso_deuda = max(0.0, (debt_ratio * 100.0) - 60.0)
    penalidad_deuda = 0.5 * exceso_deuda

    penalidad_total = penalidad_gap + penalidad_empleo + penalidad_inflacion + penalidad_deuda
    score_calc = max(0.0, min(100.0, 100.0 - penalidad_total))

    # Suavizado de inercia ciudadana 70/30
    if prev_score is not None:
        score_final = 0.70 * score_calc + 0.30 * prev_score
    else:
        score_final = score_calc

    return round(float(max(0.0, min(100.0, score_final))), 2)
