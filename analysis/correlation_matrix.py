"""
analysis/correlation_matrix.py
===============================
Módulo de Análisis Estadístico V3.0 (Fase B).

Calcula la Matriz de Correlaciones de Pearson entre las variables de
TurnSnapshot como herramienta de auditoría interna de consistencia teórica.

Diseño:
  - Módulo completamente aislado del motor y de Streamlit.
  - Lee el historial de snapshots directamente (list[TurnSnapshot]).
  - Procesa series de tiempo de UNA sola partida (no mezcla sesiones).
  - Identifica firmas de signos esperados por la teoría económica de EAB.

Relaciones teóricas esperadas verificadas:
  Corr(r, I_inv) < 0     → Curva de inversión (IS)
  Corr(gap, pi) > 0      → Curva de Phillips
  Corr(q_real, NX) > 0   → Condición de Marshall-Lerner
  Corr(B, rho) > 0       → Riesgo soberano creciente con deuda
  Corr(U, pi) < 0        → Relación clásica Phillips (U - inflación)
  Corr(gY, U) < 0        → Ley de Okun (crecimiento reduce desempleo)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    pass


# Variables incluidas en la matriz de correlaciones
CORRELATION_VARIABLES: list[str] = [
    # Sector Real
    "Y", "gap", "gY", "C", "I_inv", "G", "NX", "X", "M_imp",
    # Monetario/Financiero
    "r", "M", "mult", "q_real", "A_domestic",
    # Precios
    "pi", "P_local", "E",
    # Laboral
    "U",
    # Fiscal/Externo
    "B", "R", "deficit", "recaudacion", "rho", "capital_flows_eq",
]

# Firmas teóricas esperadas (variable_a, variable_b, signo_esperado)
EXPECTED_CORRELATIONS: list[tuple[str, str, str, str]] = [
    ("r", "I_inv", "<0", "IS: mayor tasa → menor inversión privada"),
    ("gap", "pi", ">0", "Phillips: brecha positiva → mayor inflación"),
    ("q_real", "NX", ">0", "Marshall-Lerner: depreciación real → mejora exportaciones netas"),
    ("B", "rho", ">0", "Riesgo soberano: mayor deuda → mayor prima de riesgo"),
    ("U", "pi", "<0", "Phillips: menor desempleo → presión inflacionaria"),
    ("gY", "U", "<0", "Okun: crecimiento → reducción del desempleo"),
    ("M", "pi", ">0", "Cantidad de dinero: mayor M → mayor inflación"),
    ("R", "rho", "<0", "Reservas como colchón: más reservas → menor riesgo"),
    ("gap", "gY", ">0", "Brecha y crecimiento en la misma dirección"),
    ("capital_flows_eq", "R", ">0", "Flujos positivos → acumulan reservas"),
]


def build_correlation_matrix(history: list[dict]) -> "dict[str, dict[str, float]]":
    """
    Construye la matriz de correlaciones de Pearson entre las variables del historial.

    Requiere al menos 3 observaciones para producir correlaciones significativas.
    Con 10 turnos del juego se obtienen correlaciones válidas para diagnóstico.

    Parameters
    ----------
    history : list[TurnSnapshot]
        Historial de snapshots del juego (history[0] = t=0, history[-1] = turno final).

    Returns
    -------
    dict[str, dict[str, float]]
        Matriz de correlaciones como dict anidado. {var_i: {var_j: corr_ij}}.
        Valores faltantes o no calculables se devuelven como None.
    """
    if len(history) < 3:
        return {}

    # Extraer series de tiempo por variable
    series: dict[str, list[float]] = {}
    for var in CORRELATION_VARIABLES:
        vals = []
        for snap in history:
            v = snap.get(var)
            if v is not None and v == v:  # excluir None y NaN
                vals.append(float(v))
            else:
                vals.append(float("nan"))
        series[var] = vals

    # Filtrar variables con suficientes datos no-NaN
    valid_vars = []
    for var, vals in series.items():
        clean = [v for v in vals if v == v]  # eliminar NaN
        if len(clean) >= 3:
            valid_vars.append(var)

    # Calcular correlaciones de Pearson pairwise
    matrix: dict[str, dict[str, float]] = {}
    for var_a in valid_vars:
        matrix[var_a] = {}
        for var_b in valid_vars:
            if var_a == var_b:
                matrix[var_a][var_b] = 1.0
            else:
                corr = _pearson_correlation(series[var_a], series[var_b])
                matrix[var_a][var_b] = corr

    return matrix


def _pearson_correlation(x: list[float], y: list[float]) -> float:
    """
    Calcula el coeficiente de correlación de Pearson entre dos series.

    Maneja NaN por exclusión de pares (listwise deletion para pares).

    Parameters
    ----------
    x, y : Dos series de longitud igual.

    Returns
    -------
    float : Coeficiente r ∈ [-1, 1], o float('nan') si no calculable.
    """
    # Filtrar pares donde ambos tienen valor válido
    pairs = [(a, b) for a, b in zip(x, y) if a == a and b == b]
    n = len(pairs)

    if n < 3:
        return float("nan")

    x_vals = [p[0] for p in pairs]
    y_vals = [p[1] for p in pairs]

    mean_x = sum(x_vals) / n
    mean_y = sum(y_vals) / n

    cov = sum((a - mean_x) * (b - mean_y) for a, b in zip(x_vals, y_vals))
    std_x = (sum((a - mean_x) ** 2 for a in x_vals)) ** 0.5
    std_y = (sum((b - mean_y) ** 2 for b in y_vals)) ** 0.5

    if std_x < 1e-10 or std_y < 1e-10:
        return float("nan")  # Variable constante: correlación indefinida

    return cov / (std_x * std_y)


def identify_key_relationships(
    matrix: dict[str, dict[str, float]],
    threshold: float = 0.65,
) -> list[dict]:
    """
    Identifica correlaciones fuertes (|r| > threshold) y las clasifica.

    Para cada par (var_a, var_b) con |r| > threshold, determina:
    - Si la correlación es consistente con la teoría económica esperada.
    - Si es una anomalía no esperada (correlación sorpresa).

    Parameters
    ----------
    matrix    : Matriz de correlaciones (output de build_correlation_matrix).
    threshold : Umbral de magnitud para considerar correlación fuerte (default: 0.65).

    Returns
    -------
    list[dict] : Lista de relaciones encontradas, ordenadas por |r| descendente.
        Cada elemento: {var_a, var_b, corr, type, theory_note}
    """
    # Construir lookup de relaciones esperadas
    expected_lookup: dict[tuple[str, str], tuple[str, str]] = {}
    for var_a, var_b, sign, note in EXPECTED_CORRELATIONS:
        expected_lookup[(var_a, var_b)] = (sign, note)
        expected_lookup[(var_b, var_a)] = (sign, note)

    results = []
    seen_pairs: set[tuple[str, str]] = set()

    for var_a, row in matrix.items():
        for var_b, corr in row.items():
            if var_a == var_b:
                continue
            pair = tuple(sorted([var_a, var_b]))
            if pair in seen_pairs:
                continue
            if corr != corr:  # NaN
                continue
            if abs(corr) < threshold:
                continue
            seen_pairs.add(pair)  # type: ignore[arg-type]

            # Determinar tipo
            key = (var_a, var_b)
            if key in expected_lookup:
                sign_exp, note = expected_lookup[key]
                if sign_exp == ">0" and corr > 0:
                    rel_type = "✅ Confirmada"
                elif sign_exp == "<0" and corr < 0:
                    rel_type = "✅ Confirmada"
                else:
                    rel_type = "⚠️ Signo Invertido"
            else:
                rel_type = "🔍 No Esperada"
                note = ""

            results.append({
                "var_a": var_a,
                "var_b": var_b,
                "corr": round(corr, 4),
                "abs_corr": abs(corr),
                "type": rel_type,
                "theory_note": note,
            })

    return sorted(results, key=lambda x: x["abs_corr"], reverse=True)


def get_model_consistency_score(
    matrix: dict[str, dict[str, float]],
) -> dict[str, float]:
    """
    Calcula un score de consistencia teórica del modelo (0-100).

    Verifica cuántas de las relaciones esperadas tienen el signo correcto.

    Returns
    -------
    dict con:
        'score'    : Porcentaje de relaciones con signo correcto (0-100)
        'correct'  : Número de relaciones confirmadas
        'total'    : Total de relaciones verificables con datos
        'details'  : Lista de verificaciones individuales
    """
    correct = 0
    total = 0
    details = []

    for var_a, var_b, sign_exp, note in EXPECTED_CORRELATIONS:
        if var_a not in matrix or var_b not in matrix.get(var_a, {}):
            details.append({"relationship": f"{var_a} vs {var_b}",
                            "status": "⬜ Sin datos", "expected": sign_exp, "corr": None})
            continue

        corr = matrix[var_a][var_b]
        if corr != corr:  # NaN
            details.append({"relationship": f"{var_a} vs {var_b}",
                            "status": "⬜ Sin datos", "expected": sign_exp, "corr": None})
            continue

        total += 1
        if sign_exp == ">0" and corr > 0:
            correct += 1
            status = "✅ Correcta"
        elif sign_exp == "<0" and corr < 0:
            correct += 1
            status = "✅ Correcta"
        else:
            status = f"❌ Invertida (r={corr:.2f})"

        details.append({
            "relationship": f"{var_a} vs {var_b}",
            "status": status,
            "expected": sign_exp,
            "corr": round(corr, 4),
            "note": note,
        })

    score = (correct / max(total, 1)) * 100.0

    return {
        "score": round(score, 1),
        "correct": correct,
        "total": total,
        "details": details,
    }
