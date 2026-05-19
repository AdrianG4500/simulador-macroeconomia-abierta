STRUCTURED_SHOCKS = {
    "commodity_drop": {"name": "Caída de commodities", "overrides": {"x1": -0.3, "NX0": -2.0}, "prob": 0.20},
    "fed_hike": {"name": "Subida de tasas FED", "overrides": {"r_star": 2.0}, "prob": 0.25},
    "competitive_up": {"name": "Mejora competitiva", "overrides": {"x1": 0.4, "m1": -0.05}, "prob": 0.15},
    "confidence_crisis": {"name": "Crisis de confianza", "overrides": {"c1": -0.08, "I0": -3.0}, "prob": 0.10}
}

def apply_shocks_for_period(params: dict, t: int, shock_key: str = None) -> dict:
    if not shock_key or shock_key not in STRUCTURED_SHOCKS:
        return params.copy()

    adjusted = params.copy()
    shock = STRUCTURED_SHOCKS[shock_key]
    for k, v in shock["overrides"].items():
        if k in adjusted:
            adjusted[k] += v
    return adjusted
