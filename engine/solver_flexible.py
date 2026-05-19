from typing import Dict
from engine.core import eq_flexible

def solve_flexible(p: Dict[str, float]) -> Dict[str, float]:
    """
    Resuelve el equilibrio para Tipo de Cambio Flexible (E endógena).
    Usa exactamente las ecuaciones de engine.core.
    """
    res = eq_flexible(p)
    return dict(res)
