"""
config/validation_rules_v2.py
==============================
Fuente única de verdad para rangos y metadatos de todos los parámetros del modelo V2.0.

Extiende validation_rules.py con 8 nuevas variables V2.0:
    t, epsilon_x, epsilon_m, f, alpha_PT, beta_PT, g_pot, crawl_rate

La UI consumirá estos rangos dinámicamente (Fase 2).
El motor V2 valida sus inputs contra estos rangos.

Flujo unidireccional: config → engine → state → ui.
Este módulo NO importa de engine/ ni de ui/.
"""

from __future__ import annotations

# ── Reglas de validación V2.0 ─────────────────────────────────────────────────
# Formato: {variable: {min, max, step, unit, label, warning, rationale}}

VALIDATION_RULES_V2: dict[str, dict] = {

    # ── Bloque consumo ──────────────────────────────────────────────────────
    "c0": {
        "min": 0.0, "max": 50.0, "step": 1.0,
        "unit": "Unid.",
        "label": "Consumo autónomo (c₀)",
        "warning": "",
        "rationale": (
            "Consumo de subsistencia + gasto crediticio base. "
            "Independiente del ingreso disponible."
        ),
    },
    "c1": {
        "min": 0.30, "max": 0.95, "step": 0.01,
        "unit": "Adim.",
        "label": "Propensión marginal a consumir (c₁)",
        "warning": "c₁ > 0.90 implica ahorro muy bajo; inestabilidad del multiplicador.",
        "rationale": (
            "Fracción de cada unidad adicional de ingreso disponible que se destina "
            "al consumo. Valores típicos: 0.65–0.85 en economías en desarrollo."
        ),
    },

    # ── Bloque fiscal — NUEVO V2.0 ──────────────────────────────────────────
    "t": {
        "min": 0.05, "max": 0.50, "step": 0.01,
        "unit": "Fracción",
        "label": "Tasa impositiva proporcional (t)",
        "warning": "t > 0.40 implica carga tributaria muy alta; riesgo de evasión.",
        "rationale": (
            "Fracción del ingreso captada como impuesto. En V2.0 reemplaza el "
            "impuesto lump-sum T. Afecta directamente el multiplicador: "
            "k_m = 1/(1 - c₁·(1-t) + m₁). Mayor t → menor multiplicador."
        ),
    },

    # ── Bloque inversión ────────────────────────────────────────────────────
    "I0": {
        "min": -20.0, "max": 50.0, "step": 1.0,
        "unit": "Unid.",
        "label": "Inversión autónoma (I₀)",
        "warning": "",
        "rationale": (
            "Inversión independiente de r. Negativo = contracción por crisis "
            "de confianza."
        ),
    },
    "b": {
        "min": 0.5, "max": 10.0, "step": 0.1,
        "unit": "Adim.",
        "label": "Sensibilidad inversión a r (b)",
        "warning": "",
        "rationale": (
            "Reacción empresarial a costos financieros. ↑b → IS más plana → "
            "política monetaria más potente."
        ),
    },

    # ── Bloque externo — Condición Marshall-Lerner ──────────────────────────
    "NX0": {
        "min": -20.0, "max": 50.0, "step": 1.0,
        "unit": "Unid.",
        "label": "Exportaciones netas autónomas (NX₀)",
        "warning": "",
        "rationale": (
            "Saldo comercial estructural. Negativo = déficit comercial crónico."
        ),
    },
    "epsilon_x": {
        "min": 0.05, "max": 3.00, "step": 0.05,
        "unit": "Adim.",
        "label": "Elasticidad precio exportaciones (ε_x)",
        "warning": (
            "Si ε_x + ε_m < 1, la condición Marshall-Lerner NO se cumple: "
            "una devaluación empeorará la balanza comercial."
        ),
        "rationale": (
            "Sensibilidad de la demanda externa a variaciones en el tipo de cambio real. "
            "Economías exportadoras de commodities: 0.1–0.4 (inelástica). "
            "Condición M-L requiere ε_x + ε_m > 1."
        ),
    },
    "epsilon_m": {
        "min": 0.05, "max": 2.00, "step": 0.05,
        "unit": "Adim.",
        "label": "Elasticidad precio importaciones (ε_m)",
        "warning": (
            "Si ε_x + ε_m < 1, la condición Marshall-Lerner NO se cumple."
        ),
        "rationale": (
            "Sensibilidad de la demanda de importaciones al tipo de cambio real. "
            "Importaciones esenciales (energía, alimentos): baja elasticidad."
        ),
    },
    "m1": {
        "min": 0.05, "max": 0.45, "step": 0.01,
        "unit": "Adim.",
        "label": "Propensión marginal a importar (m₁)",
        "warning": "",
        "rationale": (
            "Dependencia de importaciones. ↑m₁ → ↓multiplicador (fuga externa). "
            "Economías pequeñas abiertas: 0.15–0.35."
        ),
    },

    # ── Bloque monetario ────────────────────────────────────────────────────
    "k": {
        "min": 0.10, "max": 1.00, "step": 0.05,
        "unit": "Adim.",
        "label": "Sensibilidad demanda de dinero a Y (k)",
        "warning": "",
        "rationale": (
            "Intensidad monetaria del PIB. Controla pendiente de la curva LM. "
            "↑k → LM más empinada."
        ),
    },
    "h": {
        "min": 0.50, "max": 5.00, "step": 0.10,
        "unit": "Adim.",
        "label": "Sensibilidad demanda de dinero a r (h)",
        "warning": "",
        "rationale": (
            "Preferencia por liquidez vs. bonos. ↑h → LM más plana → "
            "política monetaria menos potente sobre la tasa de interés."
        ),
    },

    # ── Bloque movilidad de capitales — NUEVO V2.0 ──────────────────────────
    "f": {
        "min": 0.1, "max": 100.0, "step": 0.5,
        "unit": "Adim.",
        "label": "Movilidad de capitales (f)",
        "warning": (
            "f < 1: movilidad muy baja; política fiscal efectiva bajo TC flexible. "
            "f > 50: aproxima movilidad perfecta (Mundell-Fleming clásico)."
        ),
        "rationale": (
            "Parámetro de movilidad de capitales en la BP con pendiente positiva. "
            "r_BP = r* + ΔEₑ - NX/f. f → ∞ recupera caso de movilidad perfecta. "
            "Economías emergentes con controles de capital: f ∈ [0.5, 5]."
        ),
    },

    # ── Bloque pass-through cambiario — NUEVO V2.0 ─────────────────────────
    "alpha_PT": {
        "min": 0.0, "max": 1.0, "step": 0.05,
        "unit": "Fracción",
        "label": "Peso bienes transables en precios (α_PT)",
        "warning": "α_PT > 0.7: economía muy expuesta al tipo de cambio.",
        "rationale": (
            "Fracción de la canasta de precios compuesta por bienes transables "
            "(precio = E·P*). (1-α_PT) es el peso de no-transables. "
            "P_local = α_PT·E·P* + (1-α_PT)·P_NT."
        ),
    },
    "beta_PT": {
        "min": 0.0, "max": 0.5, "step": 0.01,
        "unit": "Fracción",
        "label": "Coeficiente pass-through en Phillips (β_PT)",
        "warning": "β_PT > 0.4: alta inercia inflacionaria cambiaria.",
        "rationale": (
            "Fracción de la variación nominal del tipo de cambio que se traslada "
            "a la inflación en el mismo período. π = πₑ + α·gap + β_PT·(ΔE/E)."
        ),
    },

    # ── Bloque producto potencial — NUEVO V2.0 ──────────────────────────────
    "g_pot": {
        "min": 0.0, "max": 0.08, "step": 0.005,
        "unit": "Fracción/año",
        "label": "Crecimiento PIB potencial (g_pot)",
        "warning": "g_pot > 0.06: crecimiento muy optimista para economías en desarrollo.",
        "rationale": (
            "Tasa de crecimiento anual del PIB potencial. "
            "Y_pot_t = Y_pot_{t-1}·(1 + g_pot + shock_endógeno). "
            "Economías emergentes estables: 0.02–0.04."
        ),
    },

    # ── Bloque dinámicas ────────────────────────────────────────────────────
    "Y_pot": {
        "min": 50.0, "max": 200.0, "step": 1.0,
        "unit": "Unid.",
        "label": "PIB potencial (Y_pot)",
        "warning": "",
        "rationale": (
            "Capacidad productiva estructural. Referencia para brecha del producto. "
            "gap = (Y - Y_pot) / Y_pot."
        ),
    },
    "U_n": {
        "min": 0.03, "max": 0.10, "step": 0.01,
        "unit": "Fracción",
        "label": "Desempleo natural / NAIRU (U_n)",
        "warning": "",
        "rationale": (
            "Fricción + estructural mínima. Referencia para Ley de Okun V2: "
            "U = U_n - γ_okun·gap (usa gap, no gY)."
        ),
    },

    # ── Bloque instrumentos de política ─────────────────────────────────────
    "G": {
        "min": 5.0, "max": 60.0, "step": 0.5,
        "unit": "% PIB norm.",
        "label": "Gasto público (G)",
        "warning": "",
        "rationale": (
            "Instrumento fiscal: ↑G desplaza IS→. Muy efectivo bajo TC fijo "
            "(multiplicador pleno), neutral bajo TC flexible con movilidad perfecta."
        ),
    },
    "E": {
        "min": 1.0, "max": 30.0, "step": 0.1,
        "unit": "Bs/USD",
        "label": "Tipo de cambio nominal (E)",
        "warning": "",
        "rationale": (
            "Instrumento cambiario (TC fijo / crawling peg): ↑E = devaluación. "
            "Bajo TC flexible, E se determina endógenamente."
        ),
    },
    "M": {
        "min": 10.0, "max": 500.0, "step": 1.0,
        "unit": "Unid. modelo",
        "label": "Oferta monetaria (M)",
        "warning": "",
        "rationale": (
            "Instrumento monetario (TC flexible): ↑M desplaza LM→ → ↓r → ↑Y. "
            "Endógena bajo TC fijo (el banco central acomoda para mantener E)."
        ),
    },
    "r_star": {
        "min": 0.0, "max": 15.0, "step": 0.1,
        "unit": "% anual",
        "label": "Tasa de interés internacional (r*)",
        "warning": "",
        "rationale": (
            "Tasa libre de riesgo internacional + prima de riesgo soberano. "
            "Afecta la condición de paridad de intereses (curva BP)."
        ),
    },

    # ── Crawling peg — NUEVO V2.0 ───────────────────────────────────────────
    "crawl_rate": {
        "min": 0.001, "max": 0.05, "step": 0.001,
        "unit": "Fracción/período",
        "label": "Tasa de deslizamiento cambiario (crawl_rate)",
        "warning": "crawl_rate > 0.03: deslizamiento agresivo; riesgo de desanclar expectativas.",
        "rationale": (
            "Tasa de depreciación programada bajo crawling peg: "
            "E_t = E_{t-1}·(1 + crawl_rate). "
            "Las expectativas se anclan al ritmo del crawl: ΔEₑ = crawl_rate."
        ),
    },
}


def get_param_range(param: str) -> tuple[float, float]:
    """
    Retorna el rango (min, max) para un parámetro dado.

    Parameters
    ----------
    param : str
        Nombre del parámetro.

    Returns
    -------
    tuple[float, float]
        (min, max)

    Raises
    ------
    KeyError
        Si el parámetro no tiene regla de validación definida.
    """
    if param not in VALIDATION_RULES_V2:
        raise KeyError(
            f"Parámetro '{param}' sin regla de validación. "
            f"Disponibles: {list(VALIDATION_RULES_V2.keys())}"
        )
    rule = VALIDATION_RULES_V2[param]
    return rule["min"], rule["max"]


def validate_param(param: str, value: float) -> list[str]:
    """
    Valida un valor contra su rango y retorna lista de advertencias.

    Parameters
    ----------
    param : str
        Nombre del parámetro.
    value : float
        Valor a validar.

    Returns
    -------
    list[str]
        Lista de mensajes de advertencia (vacía si no hay problemas).
    """
    if param not in VALIDATION_RULES_V2:
        return []

    rule = VALIDATION_RULES_V2[param]
    warnings: list[str] = []

    if value < rule["min"]:
        warnings.append(
            f"[{param}] Valor {value} < mínimo {rule['min']}. "
            f"{rule['label']} fuera de rango."
        )
    if value > rule["max"]:
        warnings.append(
            f"[{param}] Valor {value} > máximo {rule['max']}. "
            f"{rule['label']} fuera de rango."
        )
    if rule["warning"] and (value > rule["max"] * 0.9 or value < rule["min"] * 1.1):
        warnings.append(f"[ADVERTENCIA] {rule['warning']}")

    return warnings


VALIDATION_RULES = VALIDATION_RULES_V2
