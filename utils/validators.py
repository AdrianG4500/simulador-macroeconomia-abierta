"""
utils/validators.py
===================
Validadores de consistencia macroeconómica para Fase 4.
Complementa config/validation_rules.py con reglas de coherencia cruzada.

Funciones públicas:
    validate_macro_consistency(params) → list[str]
    format_validation_message(errors, warnings) → str
"""

from __future__ import annotations

import math


def validate_macro_consistency(params: dict) -> tuple[list[str], list[str]]:
    """
    Verifica la consistencia macroeconómica interna del conjunto de parámetros.
    Aplica reglas que involucran múltiples variables (no solo rangos individuales).

    Rules:
        1. Multiplicador positivo: (1 - c1 + m1) > 0
        2. Demanda de dinero positiva en equilibrio: k*Y > 0 implícito (k > 0)
        3. Exportaciones elásticas mínimas: x1 > 0 (siempre; error si x1 ≤ 0)
        4. Coherencia fiscal: si G > T*2, déficit fiscal potencialmente insostenible
        5. Coherencia monetaria: M > 0 (si aplica TC flexible)
        6. Sensibilidades positivas: b, k, h > 0

    Parameters
    ----------
    params : dict — parámetros del modelo (del engine/core.py)

    Returns
    -------
    tuple[list[str], list[str]]
        - errors   : condiciones que invalidan el modelo (bloquean simulación)
        - warnings : condiciones preocupantes (no bloquean, solo alertan)
    """
    errors:   list[str] = []
    warnings: list[str] = []

    c1     = params.get("c1",     None)
    m1     = params.get("m1",     None)
    b      = params.get("b",      None)
    k      = params.get("k",      None)
    h      = params.get("h",      None)
    x1     = params.get("x1",     None)
    G      = params.get("G",      None)
    T      = params.get("T",      None)
    M      = params.get("M",      None)
    r_star = params.get("r_star", None)
    NX0    = params.get("NX0",    None)

    # ── Regla 1: Multiplicador positivo ──────────────────────────────────────
    if c1 is not None and m1 is not None:
        denom = 1.0 - c1 + m1
        if denom <= 0:
            errors.append(
                f"❌ Multiplicador indefinido: (1 − c₁ + m₁) = {denom:.4f} ≤ 0. "
                f"El modelo requiere c₁ − m₁ < 1. "
                f"Actual: c₁={c1:.3f}, m₁={m1:.3f}."
            )
        elif denom < 0.05:
            warnings.append(
                f"⚠️ Multiplicador muy alto: 1/(1−c₁+m₁) = {1/denom:.1f}. "
                "Demanda extremadamente elástica; el modelo puede ser inestable."
            )

    # ── Regla 2: Sensibilidades positivas ────────────────────────────────────
    for var_name, val in [("b", b), ("k", k), ("h", h)]:
        if val is not None and val <= 0:
            errors.append(
                f"❌ Parámetro {var_name} = {val:.4f} ≤ 0. "
                "Los parámetros de sensibilidad deben ser estrictamente positivos."
            )

    # ── Regla 3: Elasticidad de exportaciones ────────────────────────────────
    if x1 is not None:
        if x1 <= 0:
            errors.append(
                f"❌ x₁ = {x1:.4f} ≤ 0. La elasticidad de exportaciones debe ser positiva. "
                "Una devaluación debe mejorar la competitividad."
            )
        elif x1 < 0.3:
            warnings.append(
                f"⚠️ x₁ = {x1:.3f} muy bajo. Exportaciones casi inelásticas al tipo de cambio. "
                "La política cambiaria tendrá muy poco impacto sobre NX."
            )

    # ── Regla 4: Coherencia fiscal ────────────────────────────────────────────
    if G is not None and T is not None:
        deficit_ratio = (G - T)
        if deficit_ratio > 15.0:
            warnings.append(
                f"⚠️ Déficit fiscal (G − T) = {deficit_ratio:.1f} es muy elevado. "
                "Puede ser insostenible en el largo plazo. "
                f"G={G:.1f}, T={T:.1f}."
            )
        if T < 0:
            warnings.append(
                f"⚠️ T = {T:.2f} < 0 (subsidio neto). Verifique que este es el escenario deseado."
            )

    # ── Regla 5: Oferta monetaria positiva ───────────────────────────────────
    if M is not None and M <= 0:
        errors.append(
            f"❌ M = {M:.2f} ≤ 0. La oferta monetaria debe ser positiva. "
            "Bajo TC flexible, M = 0 colapsa la demanda agregada."
        )

    # ── Regla 6: Tasa internacional razonable ────────────────────────────────
    if r_star is not None:
        if r_star < 0:
            warnings.append(
                f"⚠️ r* = {r_star:.2f}% < 0 (tasa internacional negativa). "
                "Posible bajo ZIRP/NIRP, pero inusual para economías emergentes."
            )
        if r_star > 20:
            warnings.append(
                f"⚠️ r* = {r_star:.2f}% muy alta. "
                "Refleja situación de crisis de deuda severa o hiperinflación."
            )

    # ── Regla 7: NX autónomo muy negativo ────────────────────────────────────
    if NX0 is not None and NX0 < -10:
        warnings.append(
            f"⚠️ NX₀ = {NX0:.2f} indica déficit comercial estructural muy severo. "
            "Combinado con TC fijo, puede agotar reservas internacionales rápidamente."
        )

    # ── Regla 8: PMgC + PMgM ≥ 1 (implicación del multiplicador) ─────────────
    if c1 is not None and m1 is not None:
        if c1 + m1 > 1.0:
            warnings.append(
                f"⚠️ c₁ + m₁ = {c1+m1:.3f} > 1. "
                "El multiplicador sigue siendo válido (requiere solo c₁ − m₁ < 1), "
                "pero implica que ante un aumento del ingreso, consumo+importaciones "
                "superan el ingreso adicional. Economía de alta propensión al gasto."
            )

    return errors, warnings


def format_validation_message(errors: list[str], warnings: list[str]) -> str:
    """
    Formatea errores y advertencias en un string Markdown legible para st.markdown().

    Parameters
    ----------
    errors   : list[str] — errores (bloquean simulación)
    warnings : list[str] — advertencias (solo informativas)

    Returns
    -------
    str : Mensaje formateado en Markdown.
    """
    parts = []

    if errors:
        parts.append("### ❌ Errores de validación (bloquean simulación)")
        for e in errors:
            parts.append(f"- {e}")

    if warnings:
        parts.append("### ⚠️ Advertencias (no bloquean)")
        for w in warnings:
            parts.append(f"- {w}")

    if not errors and not warnings:
        return "✅ Todos los parámetros son consistentes y están en rango válido."

    return "\n".join(parts)


def quick_validate(params: dict) -> tuple[bool, str]:
    """
    Validación rápida combinada: reglas individuales + consistencia cruzada.
    Útil para mostrar ✅/⚠️/❌ en sidebar.

    Returns
    -------
    tuple[bool, str]
        - is_ok     : True si no hay errores (warnings no cuentan)
        - status_emoji : "✅" | "⚠️" | "❌"
    """
    from config.validation_rules import validate_params as _vp
    _, range_errors, range_warnings = _vp(params)
    cross_errors, cross_warnings    = validate_macro_consistency(params)

    all_errors   = range_errors + cross_errors
    all_warnings = range_warnings + cross_warnings

    if all_errors:
        return False, "❌"
    if all_warnings:
        return True, "⚠️"
    return True, "✅"
