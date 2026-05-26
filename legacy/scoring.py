def check_crisis_conditions(gY: float, U: float, pi: float, def_pct: float, R: float = 0.0) -> tuple[bool, str]:
    """Retorna (True, motivo) si se cruza un umbral de crisis macroeconómica."""
    if gY < -0.10: return True, "Colapso económico (gY < -10%)"
    if gY > 0.20:  return True, "Sobrecalentamiento extremo (gY > 20%)"
    if U > 0.50 or U < 0.01: return True, "Desempleo imposible o negativo"
    if pi > 0.50 or pi < -0.10: return True, "Hiperinflación o deflación severa"
    if def_pct > 0.20 or def_pct < -0.15: return True, "Crisis fiscal insostenible"
    if R <= 0: return True, "Reservas internacionales agotadas"
    return False, ""

def calc_period_score(gY: float, U: float, pi: float, def_pct: float, R: float = 0.0) -> int:
    is_crisis, _ = check_crisis_conditions(gY, U, pi, def_pct, R)
    if is_crisis: return 0  # Score 0 automático por ruptura macroeconómica

    score = 0
    # gY: Crecimiento real (%)
    if gY > 0.025: score += 25
    elif 0.010 <= gY <= 0.025: score += 10

    # U: Desempleo (%)
    if U < 0.05: score += 25
    elif 0.050 <= U <= 0.080: score += 10

    # pi: Inflación (%)
    if 0.001 <= pi <= 0.029: score += 25
    elif 0.030 <= pi <= 0.050: score += 10

    # def: Déficit fiscal (% del PIB)
    if def_pct < 0.030: score += 25
    elif 0.030 <= def_pct <= 0.060: score += 10

    return score

def get_score_color(score: int) -> str:
    if score >= 70: return "🟢"
    if score >= 40: return "🟡"
    return "🔴"

def get_crisis_warning(gY, U, pi, def_pct, R) -> str:
    is_crisis, reason = check_crisis_conditions(gY, U, pi, def_pct, R)
    return f"⚠️ {reason}" if is_crisis else ""
