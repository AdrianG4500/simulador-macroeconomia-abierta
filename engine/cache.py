"""
engine/cache.py
===============
Sistema de caché de equilibrios usando joblib.Memory.

Propósito:
    - Evitar recalcular equilibrios idénticos en reruns de Streamlit.
    - Serializar resultados a disco para persistencia entre sesiones.
    - Proporcionar un decorador @cache_equilibrium listo para Fase 2.

Ruta de caché: .cache/equilibrium_cache
    (relativa al directorio raíz del proyecto)
"""

from __future__ import annotations

import functools
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, TypeVar

import joblib

# ── Configuración del directorio de caché ────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent
_CACHE_DIR = _PROJECT_ROOT / ".cache" / "equilibrium_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Instancia de memoria joblib
memory = joblib.Memory(
    location=str(_CACHE_DIR),
    verbose=0,   # Sin output en consola (Streamlit-friendly)
    backend="local",
)

# ── Tipo genérico para decoradores ───────────────────────────────────────────
F = TypeVar("F", bound=Callable[..., Any])


# ── Funciones cacheadas ──────────────────────────────────────────────────────

@memory.cache
def _cached_eq_fixed(params_frozen: str) -> dict[str, float]:
    """
    Versión cacheada interna de eq_fixed.
    Recibe los parámetros serializados como JSON string (hasheable por joblib).
    """
    from engine.core import eq_fixed  # Import local para evitar circularidad
    params = json.loads(params_frozen)
    return dict(eq_fixed(params))


@memory.cache
def _cached_eq_flexible(params_frozen: str) -> dict[str, float]:
    """
    Versión cacheada interna de eq_flexible.
    Recibe los parámetros serializados como JSON string (hasheable por joblib).
    """
    from engine.core import eq_flexible
    params = json.loads(params_frozen)
    return dict(eq_flexible(params))


def _freeze_params(params: dict[str, float]) -> str:
    """
    Serializa un dict de parámetros a JSON ordenado para uso como clave de caché.

    Parameters
    ----------
    params : dict[str, float]
        Parámetros del modelo.

    Returns
    -------
    str : JSON string ordenado (deterministico).
    """
    return json.dumps(params, sort_keys=True)


# ── API pública ──────────────────────────────────────────────────────────────

def cached_eq_fixed(params: dict[str, float]) -> dict[str, float]:
    """
    Calcula el equilibrio IS-LM-BP bajo tipo de cambio FIJO con caché.

    Si los parámetros ya fueron calculados en una sesión anterior, devuelve
    el resultado desde disco sin re-ejecutar el motor matemático.

    Parameters
    ----------
    params : dict[str, float]
        Parámetros del modelo (ver engine.core.eq_fixed).

    Returns
    -------
    dict[str, float] : Resultado del equilibrio (cacheado o calculado).
    """
    return _cached_eq_fixed(_freeze_params(params))


def cached_eq_flexible(params: dict[str, float]) -> dict[str, float]:
    """
    Calcula el equilibrio IS-LM-BP bajo tipo de cambio FLEXIBLE con caché.

    Parameters
    ----------
    params : dict[str, float]
        Parámetros del modelo (ver engine.core.eq_flexible).

    Returns
    -------
    dict[str, float] : Resultado del equilibrio (cacheado o calculado).
    """
    return _cached_eq_flexible(_freeze_params(params))


def cache_equilibrium(func: F) -> F:
    """
    Decorador para cachear funciones de equilibrio con parámetros dict.

    Uso en Fase 2 (Streamlit):
        @cache_equilibrium
        def mi_calculo_personalizado(params: dict) -> dict:
            ...

    El primer argumento de la función decorada debe ser un dict de parámetros.
    La clave de caché se genera del hash SHA-256 del JSON de los parámetros.

    Parameters
    ----------
    func : Callable
        Función a cachear. Debe aceptar dict como primer argumento.

    Returns
    -------
    Callable : Función envuelta con lógica de caché.
    """
    @functools.wraps(func)
    def wrapper(params: dict[str, float], *args: Any, **kwargs: Any) -> Any:
        # Genera una clave única basada en función + parámetros
        cache_key = hashlib.sha256(
            f"{func.__qualname__}:{_freeze_params(params)}".encode()
        ).hexdigest()[:16]

        cache_file = _CACHE_DIR / f"{func.__name__}_{cache_key}.json"

        # Hit de caché: devuelve resultado guardado
        if cache_file.exists():
            with cache_file.open("r", encoding="utf-8") as f:
                return json.load(f)

        # Miss de caché: calcula y persiste
        result = func(params, *args, **kwargs)
        with cache_file.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        return result

    return wrapper  # type: ignore[return-value]


def clear_cache() -> None:
    """
    Limpia toda la caché de equilibrios.
    Útil al cambiar la versión del modelo o durante desarrollo.
    """
    memory.clear(warn=False)
    # También elimina archivos JSON del decorador manual
    for json_file in _CACHE_DIR.glob("*.json"):
        json_file.unlink()
    print(f"🗑️  Caché limpiada en: {_CACHE_DIR}")
