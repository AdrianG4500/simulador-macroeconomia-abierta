"""
engine/game_state.py
====================
Definición del GameState y tipos de soporte como TypedDicts serializables.

Todo el estado de la simulación vive aquí. No hay lógica de negocio.

Jerarquía de tipos:
    NewsItem        → ítem del feed de noticias
    TurnSnapshot    → snapshot inmutable de un turno completado
    EndgameSummary  → resumen de fin de partida
    GameState       → estado global mutable (única fuente de verdad)

Flujo de datos: config → engine → GameState → ui
Este módulo NO importa de ui/, streamlit, ni engine/core_v2.py.
"""

from __future__ import annotations

from typing import Any, TypedDict


# ─────────────────────────────────────────────────────────────────────────────
# NEWS ITEM
# ─────────────────────────────────────────────────────────────────────────────

class NewsItem(TypedDict):
    """
    Ítem del feed de noticias. Generado por eventos, crisis o políticas.

    Campos
    ------
    t        : Turno en que ocurre el evento
    category : Categoría del evento: "policy" | "event" | "crisis" | "info"
    message  : Texto del mensaje (puede incluir emoji)
    severity : Nivel de severidad: "info" | "warning" | "critical"
    """
    t:        int
    category: str
    message:  str
    severity: str


# ─────────────────────────────────────────────────────────────────────────────
# TURN SNAPSHOT
# ─────────────────────────────────────────────────────────────────────────────

class TurnSnapshot(TypedDict):
    """
    Snapshot inmutable de todas las variables relevantes al final de un turno.

    Incluye variables de flujo (del período) y de stock (acumuladas).
    Se almacena en GameState.history[t].
    """
    # Identificación
    t:              int     # Turno (0 = calibración base, 1–10 = períodos jugados)

    # Mercado de bienes y factores
    Y:              float   # PIB de equilibrio
    r:              float   # Tasa de interés de equilibrio
    C:              float   # Consumo privado
    I_inv:          float   # Inversión privada
    G:              float   # Gasto público (instrumento)
    NX:             float   # Exportaciones netas
    A_domestic:     float   # Absorción doméstica = C + I + G

    # Mercado monetario y cambiario
    E:              float   # Tipo de cambio nominal (exógeno o endógeno según régimen)
    M:              float   # Oferta monetaria (exógena o endógena según régimen)
    P_local:        float   # Nivel de precios local
    q_real:         float   # Tipo de cambio real q = E·P*/P_local

    # Indicadores macroeconómicos del período
    pi:             float   # Inflación del período
    pi_e:           float   # Expectativas de inflación (usadas este turno)
    U:              float   # Tasa de desempleo
    gap:            float   # Brecha del producto = (Y - Y_pot) / Y_pot
    gY:             float   # Tasa de crecimiento del PIB

    # Finanzas públicas (flujos del período)
    recaudacion:    float   # Recaudación impositiva = t · Y
    deficit:        float   # Déficit fiscal = G - recaudacion + intereses deuda

    # Variables de stock (fin del período)
    B:              float   # Deuda pública acumulada
    R:              float   # Reservas internacionales

    # Análisis Salter-Swan
    zone_ss:        str     # Zona de Salter-Swan: "I" | "II" | "III" | "IV"

    # Scoring
    score:          int     # Score del período (0–100)

    # Metadatos del turno
    mult:           float   # Multiplicador keynesiano vigente
    policy_applied: dict    # Copia de PolicyInstruments usados este turno
    events_triggered: list  # Eventos exógenos/endógenos ocurridos


# ─────────────────────────────────────────────────────────────────────────────
# ENDGAME SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

class EndgameSummary(TypedDict):
    """
    Resumen de fin de partida. Calculado por SimStateManagerV2.get_endgame_summary().

    delta_score > 0  → el jugador mejoró la economía → "Gana la reelección"
    delta_score <= 0 → la economía empeoró → "Pierde la reelección"
    """
    total_score:       int    # Suma de scores de los turnos 1–10
    avg_score_per_turn: float  # Media por turno
    delta_score:       float  # score(t_final) − score(t_0)
    t0_snapshot:       Any    # TurnSnapshot del turno 0 (referencia inicial)
    t10_snapshot:      Any    # TurnSnapshot del turno final
    verdict:           str    # "reelected" | "removed" | "impeached"
    dimension_deltas:  dict   # Mejora/empeoramiento por dimensión


# ─────────────────────────────────────────────────────────────────────────────
# GAME STATE
# ─────────────────────────────────────────────────────────────────────────────

class GameState(TypedDict):
    """
    Estado global mutable de la simulación. Única fuente de verdad.

    Solo SimStateManagerV2 puede mutar este objeto.
    La UI lee desde aquí pero NO escribe.

    Campos de metadatos
    -------------------
    scenario_id      : Identificador del escenario ("Economia_Saludable", etc.)
    difficulty       : Nivel de dificultad ("easy" | "hard")
    regime           : Régimen cambiario activo ("fixed" | "flexible" | "crawling_peg")
    t                : Turno actual (0 = calibración, 1–10 = partida en curso)
    status           : Estado de la partida:
                       "init" | "calibrated" | "running" | "endgame" | "game_over"
    game_over_reason : Razón del game over (None si no ha ocurrido)

    Campos de parámetros
    --------------------
    structural       : StructuralParams activos (pueden modificarse por eventos endógenos)
    policy           : PolicyInstruments del turno actual (decididos por el jugador)

    Campos de estado continuo
    -------------------------
    Y_pot            : PIB potencial actual (crece con g_pot cada turno)
    P_local          : Nivel de precios actual
    P_NT             : Precio de bienes no-transables (variable de estado)
    pi_e             : Expectativas de inflación adaptativas
    delta_E_expected : Prima de devaluación esperada (0.25 en crisis de credibilidad)
    j_curve_active   : True si el turno SIGUIENTE debe aplicar efecto J-curve

    Campos de stock
    ---------------
    R                : Reservas internacionales
    B                : Deuda pública acumulada

    Campos de historial
    -------------------
    history          : Lista de TurnSnapshot (history[0] = calibración t=0)
    active_events    : Eventos activos este turno (Fase 3)
    news_feed        : Feed de noticias acumulado (toda la partida)
    advisor_warnings : Alertas del gabinete para el próximo turno

    Campos de scoring
    -----------------
    scores           : Score por turno (scores[0] = baseline t=0)
    delta_score      : Delta score final (calculado en endgame; None antes)
    """
    # Metadatos
    scenario_id:       str
    difficulty:        str
    regime:            str
    t:                 int
    status:            str
    game_over_reason:  str | None

    # Parámetros (tipados como Any para evitar importación circular)
    structural:        Any   # StructuralParams
    policy:            Any   # PolicyInstruments

    # Estado continuo
    Y_pot:             float
    P_local:           float
    P_NT:              float
    pi_e:              float
    delta_E_expected:  float
    j_curve_active:    bool

    # Stock
    R:                 float
    B:                 float

    # Historial
    history:           list   # list[TurnSnapshot]
    active_events:     list   # list[str]
    news_feed:         list   # list[NewsItem]
    advisor_warnings:  list   # list[str]

    # Scoring
    scores:            list   # list[int]
    delta_score:       float | None


# ─────────────────────────────────────────────────────────────────────────────
# FACTORY: estado vacío inicial (antes de calibrar)
# ─────────────────────────────────────────────────────────────────────────────

def make_empty_game_state() -> GameState:
    """
    Retorna un GameState con valores nulos/vacíos.

    Útil para inicializar el state manager antes de calibrate().
    NO está listo para simular; status = "init".
    """
    return {
        "scenario_id":      "unknown",
        "difficulty":       "easy",
        "regime":           "fixed",
        "t":                0,
        "status":           "init",
        "game_over_reason": None,
        "structural":       {},
        "policy":           {},
        "Y_pot":            100.0,
        "P_local":          1.0,
        "P_NT":             1.0,
        "pi_e":             0.03,
        "delta_E_expected": 0.0,
        "j_curve_active":   False,
        "R":                0.0,
        "B":                0.0,
        "history":          [],
        "active_events":    [],
        "news_feed":        [],
        "advisor_warnings": [],
        "scores":           [],
        "delta_score":      None,
    }
