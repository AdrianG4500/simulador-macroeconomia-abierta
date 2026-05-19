"""
engine/scenario_builder.py
==========================
Constructor de "historias económicas" para la Fase 4.
Combina presets base, overrides manuales y secuencias de shocks temporales.

Funciones públicas:
    build_economic_story(base_preset, custom_overrides, policy_shocks) → dict
    generate_narrative_for_story(story_metadata) → str
    apply_temporal_shock(params, shock_dict) → dict
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from config.bolivia_data import BOLIVIA_PRESETS, get_bolivia_params
from config.parameters import get_base_params


# ── Tipos de shocks predefinidos ──────────────────────────────────────────────
# Cada shock_dict tiene la estructura:
#   {
#       "name":        str,          — nombre descriptivo
#       "t":           int,          — paso temporal (t=0, t=1, t=2, ...)
#       "description": str,          — narrativa del shock
#       "overrides":   dict[str,float] — parámetros a sobrescribir
#   }

PREDEFINED_SHOCKS: dict[str, dict] = {
    "caida_exportaciones": {
        "name":        "Caída de Exportaciones (x₁↓)",
        "description": (
            "Reducción de la elasticidad de exportaciones al tipo de cambio, "
            "típica cuando socios comerciales reducen demanda o caen precios de materias primas."
        ),
        "overrides":   {"x1": -0.3, "NX0": -2.0},  # deltas a aplicar
        "is_delta":    True,  # si True, los overrides son deltas (no valores absolutos)
    },
    "fuga_capitales": {
        "name":        "Fuga de Capitales (r*↑)",
        "description": (
            "Aumento de la prima de riesgo país, elevando la tasa de interés internacional "
            "efectiva que enfrenta la economía. Genera salida de capitales."
        ),
        "overrides":   {"r_star": 3.0},
        "is_delta":    True,
    },
    "expansion_fiscal": {
        "name":        "Expansión Fiscal (G↑10)",
        "description": (
            "Aumento del gasto público de 10 unidades. Bajo TC fijo: desplaza IS a la derecha "
            "y el BC acomoda la oferta monetaria (M endógena)."
        ),
        "overrides":   {"G": 10.0},
        "is_delta":    True,
    },
    "contraccion_monetaria": {
        "name":        "Contracción Monetaria (M↓)",
        "description": (
            "Reducción de la oferta monetaria (TC flexible). Desplaza LM a la izquierda, "
            "apreciando el tipo de cambio y reduciendo Y."
        ),
        "overrides":   {"M": -5.0},
        "is_delta":    True,
    },
    "devaluacion": {
        "name":        "Devaluación (E↑15%)",
        "description": (
            "Aumento del tipo de cambio nominal en 15%. Bajo TC fijo: requiere decisión "
            "deliberada del BC. Mejora competitividad pero puede generar presión inflacionaria."
        ),
        "overrides":   {"E": 1.15},  # multiplicador
        "is_delta":    False,        # valor absoluto (multiplica E actual)
        "is_multiplicative": True,
    },
    "subida_impuestos": {
        "name":        "Aumento de Impuestos (T↑5)",
        "description": "Aumento de 5 unidades en impuestos lump-sum. Contrae la demanda agregada.",
        "overrides":   {"T": 5.0},
        "is_delta":    True,
    },
    "mejora_confianza": {
        "name":        "Mejora de Confianza (I₀↑)",
        "description": "Recuperación de la inversión privada autónoma por mejora del clima de negocios.",
        "overrides":   {"I0": 5.0},
        "is_delta":    True,
    },
    "reduccion_consumo": {
        "name":        "Reducción del Consumo (c₁↓)",
        "description": "Caída de la propensión marginal a consumir por incertidumbre o austeridad.",
        "overrides":   {"c1": -0.05},
        "is_delta":    True,
    },
}


# ── Funciones públicas ────────────────────────────────────────────────────────

def build_economic_story(
    base_preset: str,
    custom_overrides: dict[str, float] | None = None,
    policy_shocks: list[dict] | None = None,
) -> tuple[dict[str, float], dict]:
    """
    Construye una "historia económica" combinando preset base, overrides manuales
    y una secuencia de shocks temporales.

    Paso 1: Carga preset base (Bolivia o estándar)
    Paso 2: Aplica overrides manuales del usuario
    Paso 3: Aplica secuencia de shocks (en orden de t)

    Parameters
    ----------
    base_preset : str
        Clave del preset base. Puede ser clave de BOLIVIA_PRESETS
        o "base" para usar get_base_params().
    custom_overrides : dict | None
        Parámetros a sobrescribir manualmente (ej. {"c1": 0.70}).
    policy_shocks : list[dict] | None
        Secuencia de shocks. Cada dict: {"key": str, "t": int}.
        "key" debe ser clave de PREDEFINED_SHOCKS.

    Returns
    -------
    tuple[dict[str, float], dict]
        - params_final : Parámetros finales listos para eq_fixed/eq_flexible
        - story_metadata : Metadatos de la historia para narrativa
    """
    custom_overrides = custom_overrides or {}
    policy_shocks    = policy_shocks or []

    # ── Paso 1: Cargar preset base ────────────────────────────────────────────
    if base_preset in BOLIVIA_PRESETS:
        params = get_bolivia_params(base_preset)
        base_label = BOLIVIA_PRESETS[base_preset].get("_meta", {}).get("label", base_preset)
    elif base_preset == "base":
        params = get_base_params()
        base_label = "Parámetros base (Sección 3.1)"
    else:
        # Intentar como preset de CRISIS_PRESETS (config/parameters.py)
        from config.parameters import apply_shocks, get_base_params as _gbp
        try:
            params = apply_shocks(_gbp(), base_preset)
            base_label = base_preset
        except KeyError:
            params = get_base_params()
            base_label = "Parámetros base"

    params = deepcopy(params)

    # ── Paso 2: Aplicar overrides manuales ───────────────────────────────────
    applied_overrides = {}
    for key, val in custom_overrides.items():
        if key in params:
            applied_overrides[key] = {"antes": params[key], "despues": val}
        params[key] = val

    # ── Paso 3: Aplicar shocks temporales ────────────────────────────────────
    # Ordenar por t (campo "t" opcional; si no existe, usar orden de lista)
    shocks_sorted = sorted(policy_shocks, key=lambda x: x.get("t", 0))
    applied_shocks = []

    for shock_ref in shocks_sorted:
        shock_key = shock_ref.get("key", "")
        shock_def = PREDEFINED_SHOCKS.get(shock_key)
        if shock_def is None:
            # Shock custom inline con "overrides" directo
            if "overrides" in shock_ref:
                shock_def = {
                    "name":        shock_ref.get("name", "Shock personalizado"),
                    "description": shock_ref.get("description", ""),
                    "overrides":   shock_ref["overrides"],
                    "is_delta":    shock_ref.get("is_delta", False),
                    "is_multiplicative": shock_ref.get("is_multiplicative", False),
                }
            else:
                continue

        params = apply_temporal_shock(params, shock_def)
        applied_shocks.append({
            "t":    shock_ref.get("t", len(applied_shocks)),
            "name": shock_def["name"],
            "desc": shock_def["description"],
        })

    # ── Metadatos de la historia ──────────────────────────────────────────────
    story_metadata = {
        "base_preset":       base_preset,
        "base_label":        base_label,
        "custom_overrides":  applied_overrides,
        "applied_shocks":    applied_shocks,
        "params_final":      dict(params),
    }

    return params, story_metadata


def apply_temporal_shock(params: dict[str, float], shock_def: dict) -> dict[str, float]:
    """
    Aplica un shock a un diccionario de parámetros.

    Soporta tres modos:
        is_delta=True         : override_value es un delta (+/-) a sumar al parámetro actual
        is_multiplicative=True: override_value es un multiplicador (* parámetro actual)
        ninguno               : override_value reemplaza directamente el parámetro

    Parameters
    ----------
    params    : dict — parámetros actuales del modelo
    shock_def : dict — definición del shock (de PREDEFINED_SHOCKS o custom)

    Returns
    -------
    dict : Nuevos parámetros con el shock aplicado (copia defensiva)
    """
    result = deepcopy(params)
    overrides  = shock_def.get("overrides", {})
    is_delta   = shock_def.get("is_delta", False)
    is_mult    = shock_def.get("is_multiplicative", False)

    for key, val in overrides.items():
        current = result.get(key, 0.0)
        if is_mult:
            result[key] = current * val
        elif is_delta:
            result[key] = current + val
        else:
            result[key] = val

    return result


def generate_narrative_for_story(story_metadata: dict) -> str:
    """
    Genera un texto explicativo estructurado para una historia económica.

    Parameters
    ----------
    story_metadata : dict — retornado por build_economic_story()

    Returns
    -------
    str : Narrativa en Markdown explicando la configuración de la historia.
    """
    base_label      = story_metadata.get("base_label", "—")
    overrides       = story_metadata.get("custom_overrides", {})
    shocks          = story_metadata.get("applied_shocks", [])
    params_final    = story_metadata.get("params_final", {})

    lines = [
        "### 📖 Narrativa de la Historia Económica",
        "",
        f"**Punto de partida**: {base_label}",
        "",
    ]

    if overrides:
        lines.append("**Ajustes manuales aplicados:**")
        for var, change in overrides.items():
            antes   = change.get("antes", "?")
            despues = change.get("despues", "?")
            lines.append(f"- `{var}`: {antes:.4g} → **{despues:.4g}**")
        lines.append("")

    if shocks:
        lines.append("**Secuencia de shocks de política:**")
        for sh in shocks:
            t    = sh.get("t", "?")
            name = sh.get("name", "—")
            desc = sh.get("desc", "")
            lines.append(f"- t={t}: **{name}** — {desc}")
        lines.append("")

    # Multiplicador resultante
    c1 = params_final.get("c1", float("nan"))
    m1 = params_final.get("m1", float("nan"))
    try:
        mult = 1.0 / (1.0 - c1 + m1)
        lines.append(f"**Multiplicador keynesiano resultante**: `1/(1−{c1:.2f}+{m1:.2f}) = {mult:.3f}`")
    except ZeroDivisionError:
        lines.append("**Multiplicador**: indefinido (denominador = 0)")

    # Resumen de parámetros clave
    lines += [
        "",
        "**Parámetros finales clave:**",
        f"| Variable | Valor |",
        f"|----------|-------|",
        f"| G (Gasto público) | {params_final.get('G', '—'):.2f} |",
        f"| T (Impuestos) | {params_final.get('T', '—'):.2f} |",
        f"| r* (Tasa internacional) | {params_final.get('r_star', '—'):.2f}% |",
        f"| c₁ (PMgC) | {params_final.get('c1', '—'):.3f} |",
        f"| m₁ (PMgM) | {params_final.get('m1', '—'):.3f} |",
        f"| x₁ (Elast. export.) | {params_final.get('x1', '—'):.2f} |",
    ]

    return "\n".join(lines)
