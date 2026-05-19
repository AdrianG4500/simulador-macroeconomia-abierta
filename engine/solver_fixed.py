from typing import Dict
from engine.core import eq_fixed

def solve_fixed(p: Dict[str, float]) -> Dict[str, float]:
    """
    Resuelve el equilibrio para Tipo de Cambio Fijo (M endógena).
    Usa exactamente las ecuaciones de engine.core.
    """
    res = eq_fixed(p)
    return dict(res)
