"""
ui/narrative.py — Narrativa económica automática para cada régimen.
Explica los mecanismos de ajuste en lenguaje académico accesible.
"""
from __future__ import annotations


def generate_fixed_narrative(
    delta_G: float,
    delta_T: float,
    delta_E: float,
    delta_rs: float,
    Y: float,
    M_endo: float,
    NX: float,
    mult: float,
) -> str:
    """
    Genera narrativa para el régimen de tipo de cambio FIJO.

    Mecanismo Mundell-Fleming (TC fijo, movilidad perfecta):
    - Política fiscal es EFECTIVA → ↑G desplaza IS → ↑Y, ↑r → entrada capital → BC interviene → ↑M
    - Política monetaria INEFECTIVA → banco central pierde control de M (endógena)
    - Devaluación → ↑E → IS se desplaza derecha → ↑Y (efecto gasto en exportaciones)
    """
    lines: list[str] = []

    # --- Transmisión del Gasto Público ---
    if abs(delta_G) > 0.5:
        dir_g = "aumentó" if delta_G > 0 else "redujo"
        effect_g = "expansión" if delta_G > 0 else "contracción"
        lines.append(
            f"**Política Fiscal [{'+' if delta_G>0 else ''}{delta_G:.0f} en G]:** "
            f"El gasto público se {dir_g} en {abs(delta_G):.0f} unidades. "
            f"Bajo tipo de cambio fijo con movilidad perfecta de capitales, "
            f"la {effect_g} fiscal es **plenamente efectiva**: la curva IS se desplaza, "
            f"el ingreso sube temporalmente, la presión al alza en r induce "
            f"entrada de capitales, y el banco central debe intervenir vendiendo moneda "
            f"extranjera para mantener E fijo, aumentando la oferta monetaria endógenamente. "
            f"Resultado neto: M endógena = {M_endo:.2f}, Y = {Y:.2f}."
        )

    # --- Transmisión de Impuestos ---
    if abs(delta_T) > 0.5:
        dir_t = "aumentaron" if delta_T > 0 else "redujeron"
        lines.append(
            f"**Política Tributaria [{'+' if delta_T>0 else ''}{delta_T:.0f} en T]:** "
            f"Los impuestos se {dir_t}. Dado que c₁ < 1, el efecto sobre la IS "
            f"es menor que un cambio equivalente en G (multiplicador tributario = −c₁·mult). "
            f"El mecanismo de ajuste es análogo: r → BP → intervención cambiaria → M endógena."
        )

    # --- Transmisión Cambiaria ---
    if abs(delta_E) > 0.1:
        dir_e = "devaluó" if delta_E > 0 else "revaluó"
        lines.append(
            f"**Política Cambiaria [{'+' if delta_E>0 else ''}{delta_E:.1f} en E]:** "
            f"La autoridad {dir_e} el tipo de cambio. "
            f"{'Una devaluación' if delta_E > 0 else 'Una revaluación'} "
            f"{'encarece las importaciones y abarata las exportaciones, desplazando la IS a la derecha.' if delta_E > 0 else 'abarata importaciones y encarece exportaciones, contrayendo la IS.'} "
            f"Exportaciones netas actuales: NX = {NX:.2f}."
        )

    # --- Shock externo ---
    if abs(delta_rs) > 0.1:
        dir_r = "subió" if delta_rs > 0 else "bajó"
        lines.append(
            f"**Shock Externo [{'+' if delta_rs>0 else ''}{delta_rs:.1f} en r*]:** "
            f"La tasa internacional {dir_r}. La curva BP se desplaza "
            f"{'hacia arriba' if delta_rs > 0 else 'hacia abajo'}, "
            f"generando {'salida' if delta_rs > 0 else 'entrada'} de capitales. "
            f"El banco central {'pierde' if delta_rs > 0 else 'acumula'} reservas para mantener E."
        )

    # --- Resultado síntesis ---
    lines.append(
        f"\n**Equilibrio actual:** Y = {Y:.2f} | r = r* | "
        f"M_endo = {M_endo:.2f} | NX = {NX:.2f} | Multiplicador = {mult:.3f}"
    )

    if Y <= 0:
        lines.append(
            "\n⚠️ **Advertencia:** El ingreso de equilibrio es negativo. "
            "Los shocks aplicados exceden la capacidad de ajuste del modelo. "
            "Reduzca la intensidad de los shocks o revise la coherencia de los parámetros."
        )

    return "\n\n".join(lines) if lines else "Ajuste los controles para generar la narrativa."


def generate_flexible_narrative(
    delta_G: float,
    delta_T: float,
    delta_M: float,
    delta_rs: float,
    Y: float,
    E_endo: float,
    NX: float,
    mult: float,
) -> str:
    """
    Genera narrativa para el régimen de tipo de cambio FLEXIBLE.

    Mecanismo Mundell-Fleming (TC flexible, movilidad perfecta):
    - Política fiscal INEFECTIVA → ↑G → ↑r → entrada capital → apreciación de E →
      ↓NX → IS retrocede → crowding-out cambiario completo
    - Política monetaria EFECTIVA → ↑M → LM se desplaza → ↓r → salida capital →
      depreciación de E → ↑NX → IS se desplaza → ↑Y
    """
    lines: list[str] = []

    if abs(delta_G) > 0.5:
        dir_g = "aumentó" if delta_G > 0 else "redujo"
        lines.append(
            f"**Política Fiscal [{'+' if delta_G>0 else ''}{delta_G:.0f} en G]:** "
            f"El gasto público se {dir_g}. Bajo tipo de cambio flexible, "
            f"la política fiscal es **completamente inefectiva** (neutralidad fiscal). "
            f"El mecanismo: ↑G desplaza IS → presión al alza en r → entrada de capitales → "
            f"apreciación cambiaria (↓E_endo) → caída de exportaciones netas → "
            f"la IS retrocede hasta su posición original. "
            f"**Crowding-out cambiario total**: Y no cambia, solo cambia la composición del gasto. "
            f"E_endo actual = {E_endo:.3f}."
        )

    if abs(delta_T) > 0.5:
        lines.append(
            f"**Política Tributaria [{'+' if delta_T>0 else ''}{delta_T:.0f} en T]:** "
            f"Análogo a G: el ajuste en T tampoco modifica Y bajo TC flexible. "
            f"El tipo de cambio absorbe el shock fiscal vía el mecanismo de movilidad de capitales."
        )

    if abs(delta_M) > 0.5:
        dir_m = "expandió" if delta_M > 0 else "contrajo"
        lines.append(
            f"**Política Monetaria [{'+' if delta_M>0 else ''}{delta_M:.0f} en M]:** "
            f"La oferta monetaria se {dir_m}. Bajo TC flexible, la política monetaria "
            f"es **plenamente efectiva**: ↑M desplaza LM → ↓r → salida de capitales → "
            f"depreciación cambiaria (↑E_endo) → ↑NX → IS se desplaza a la derecha → ↑Y. "
            f"Resultado: Y = {Y:.2f}, E_endo = {E_endo:.3f}, NX = {NX:.2f}."
        )

    if abs(delta_rs) > 0.1:
        dir_r = "subió" if delta_rs > 0 else "bajó"
        lines.append(
            f"**Shock Externo [{'+' if delta_rs>0 else ''}{delta_rs:.1f} en r*]:** "
            f"La tasa internacional {dir_r}. La LM determina Y = (M + h·r*)/k, "
            f"por lo que el shock se transmite directamente al ingreso de equilibrio. "
            f"El tipo de cambio se ajusta endógenamente para limpiar el mercado externo."
        )

    lines.append(
        f"\n**Equilibrio actual:** Y = {Y:.2f} | r = r* | "
        f"E_endo = {E_endo:.3f} | NX = {NX:.2f} | Multiplicador = {mult:.3f}"
    )

    if Y <= 0:
        lines.append(
            "\n⚠️ **Advertencia:** Ingreso negativo. Reduzca la intensidad de los shocks."
        )

    return "\n\n".join(lines) if lines else "Ajuste los controles para generar la narrativa."


def generate_salter_narrative(zone: str, A: float, q: float, q_IB: float, q_EB: float) -> str:
    """
    Genera narrativa para el modelo Salter-Swan.

    El espacio (A, q) divide la economía en cuatro zonas de desequilibrio.
    El análisis identifica cuál instrumento (absorción o tipo de cambio real)
    y en qué dirección debe aplicarse la política económica.
    """
    _ZONE_TEXT = {
        "I": {
            "estado": "**Zona I — Superávit Externo + Sobreempleo (Inflación)**",
            "desc": (
                "La economía opera por encima del pleno empleo con un superávit de cuenta corriente. "
                "Hay presiones inflacionarias internas mientras el sector externo acumula divisas. "
                "El tipo de cambio real está **demasiado depreciado** y la absorción "
                "**demasiado alta** para ambos equilibrios simultáneamente."
            ),
            "policy": (
                "**Política recomendada:** Apreciar el tipo de cambio real (revaluar E) "
                "**y/o** contraer la absorción doméstica (política fiscal restrictiva). "
                "El mix óptimo depende de cuánto desequilibrio externo e interno existe. "
                "Si la inflación es el problema dominante, priorice la contracción de A."
            ),
        },
        "II": {
            "estado": "**Zona II — Superávit Externo + Desempleo (Capacidad ociosa)**",
            "desc": (
                "La economía tiene exceso de oferta: hay desempleo y simultáneamente "
                "un saldo positivo de cuenta corriente. Esto es la zona de 'paradoja del ahorro': "
                "el país ahorra demasiado en relación a su demanda interna. "
                "El tipo de cambio real está **demasiado apreciado** para el balance externo "
                "pero la absorción es **insuficiente** para el empleo pleno."
            ),
            "policy": (
                "**Política recomendada:** Expandir la absorción doméstica (política fiscal expansiva) "
                "para estimular la demanda interna. El tipo de cambio puede mantenerse o apreciarse "
                "moderadamente. Esta zona es relativamente 'cómoda': hay espacio de política sin "
                "restricción externa inmediata."
            ),
        },
        "III": {
            "estado": "**Zona III — Déficit Externo + Desempleo (El peor escenario)**",
            "desc": (
                "La economía enfrenta el dilema de política más severo: desempleo interno "
                "y déficit de cuenta corriente simultáneos. Las políticas que estimulan el empleo "
                "empeoran el balance externo, y las que corrigen el externo profundizan el desempleo. "
                "Bolivia en 2024 es un ejemplo paradigmático de esta zona: caída de reservas, "
                "presión sobre el tipo de cambio y capacidad productiva ociosa."
            ),
            "policy": (
                "**Política recomendada (difícil):** Depreciar el tipo de cambio real "
                "(↑q = devaluación) para mejorar la competitividad exportadora, "
                "combinado con contención moderada de la absorción para reducir importaciones. "
                "⚠️ **Riesgo crítico:** la devaluación puede generar inflación importada, "
                "especialmente si hay deuda en moneda extranjera (hoja de balance). "
                "Se requiere secuenciación cuidadosa de reformas."
            ),
        },
        "IV": {
            "estado": "**Zona IV — Déficit Externo + Sobreempleo (Economía recalentada)**",
            "desc": (
                "Alta demanda interna presiona simultáneamente los precios y las importaciones. "
                "La economía está por encima del pleno empleo y tiene un déficit externo. "
                "El tipo de cambio real está **demasiado apreciado** y la absorción "
                "**demasiado alta**."
            ),
            "policy": (
                "**Política recomendada:** Contracción de la absorción (política fiscal restrictiva) "
                "**y** depreciación del tipo de cambio real. La política dual es necesaria: "
                "reducir A corrige la inflación y parte del déficit; depreciar q corrige el resto "
                "del déficit externo. Sin la devaluación, el ajuste solo via contracción sería "
                "excesivamente recesivo."
            ),
        },
    }

    info = _ZONE_TEXT.get(zone, {"estado": f"Zona {zone}", "desc": "", "policy": ""})

    texto = f"""{info['estado']}

**Posición actual:** A = {A:.1f} | q = {q:.3f}
**Umbrales:** q_IB = {q_IB:.3f} | q_EB = {q_EB:.3f}

{info['desc']}

{info['policy']}

---
**Cómo leer el gráfico:** Las curvas IB (azul) y EB (naranja) se cruzan en el punto bliss (A=100, q=1.0), el único punto de equilibrio simultáneo interno y externo. La pendiente de IB es negativa (más absorción requiere moneda más apreciada para el equilibrio interno) y la de EB es positiva (más absorción requiere mayor depreciación para equilibrio externo).
"""
    return texto
