"""
validation/test_equilibrium.py
================================
Suite de verificación automática del motor matemático.

Verifica que los equilibrios analíticos de la Sección 3.1 se reproduzcan
exactamente con los parámetros base del modelo.

Valores esperados (parámetros base):
    mult     = 2.5           → 1 / (1 - 0.75 + 0.15) = 1/0.40 = 2.5
    Y_fixed  = 100           → 2.5 * (A + x1*E - b*r*) = 2.5 * (17.5 + 15 - 10) = 55 (revisar)
    M_endo   = 40            → k*Y - h*r* = 0.5*100 - 2*5 = 50 - 10 = 40
    Y_flex   = 100           → (M + h*r*) / k = (40 + 10) / 0.5 = 100
    E_endo   = 10            → ((1-c1+m1)*Y + b*r* - A) / x1

Cálculo explícito de A (base):
    A = c0 - c1*T + I0 + G + NX0
      = 10 - 0.75*20 + 15 + 20 + 5
      = 10 - 15 + 15 + 20 + 5 = 35

Verificación Y_fixed:
    Y = mult * (A + x1*E - b*r*)
      = 2.5 * (35 + 1.5*10 - 2*5)
      = 2.5 * (35 + 15 - 10)
      = 2.5 * 40 = 100  ✓

Verificación E_endo:
    E = ((1-c1+m1)*Y + b*r* - A) / x1
      = (0.40*100 + 2*5 - 35) / 1.5
      = (40 + 10 - 35) / 1.5
      = 15 / 1.5 = 10  ✓
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from config.parameters import get_base_params
from engine.core import (
    autonomous_demand,
    eq_fixed,
    eq_flexible,
    multiplier,
)

# Tolerancia numérica para comparación de floats
_TOLERANCE = 0.01

# Directorio de salida para resultados de validación
_VALIDATION_DIR = Path(__file__).parent.parent / "validation"
_RESULTS_PATH = _VALIDATION_DIR / "results.parquet"


def _step_by_step(p: dict[str, float]) -> None:
    """
    Imprime el cálculo paso a paso del equilibrio base para depuración.

    Parameters
    ----------
    p : dict[str, float]
        Parámetros del modelo.
    """
    A    = autonomous_demand(p["c0"], p["c1"], p["T"], p["I0"], p["G"], p["NX0"])
    mult = multiplier(p["c1"], p["m1"])
    r    = p["r_star"]

    Y_fixed  = mult * (A + p["x1"] * p["E"] - p["b"] * r)
    M_endo   = p["k"] * Y_fixed - p["h"] * r
    Y_flex   = (p["M"] + p["h"] * r) / p["k"]
    E_endo   = ((1 - p["c1"] + p["m1"]) * Y_flex + p["b"] * r - A) / p["x1"]

    print("\n" + "=" * 60)
    print("  CÁLCULO PASO A PASO — PARÁMETROS BASE")
    print("=" * 60)
    print(f"  Parámetros clave:")
    print(f"    c0={p['c0']}, c1={p['c1']}, T={p['T']}, I0={p['I0']}, G={p['G']}, NX0={p['NX0']}")
    print(f"    b={p['b']}, x1={p['x1']}, k={p['k']}, h={p['h']}")
    print(f"    E={p['E']}, r*={p['r_star']}, M={p['M']}, m1={p['m1']}")
    print("-" * 60)
    print(f"  A  = c0 - c1·T + I0 + G + NX0")
    print(f"     = {p['c0']} - {p['c1']}·{p['T']} + {p['I0']} + {p['G']} + {p['NX0']}")
    print(f"     = {A:.4f}")
    print(f"  mult = 1/(1 - c1 + m1) = 1/(1 - {p['c1']} + {p['m1']}) = {mult:.4f}")
    print("-" * 60)
    print(f"  [TC FIJO] Y  = mult·(A + x1·E - b·r*)")
    print(f"               = {mult:.4f}·({A:.4f} + {p['x1']}·{p['E']} - {p['b']}·{r})")
    print(f"               = {Y_fixed:.4f}  (esperado: 100)")
    print(f"  [TC FIJO] M_endo = k·Y - h·r*")
    print(f"                   = {p['k']}·{Y_fixed:.4f} - {p['h']}·{r}")
    print(f"                   = {M_endo:.4f}  (esperado: 40)")
    print("-" * 60)
    print(f"  [TC FLEX] Y  = (M + h·r*) / k")
    print(f"               = ({p['M']} + {p['h']}·{r}) / {p['k']}")
    print(f"               = {Y_flex:.4f}  (esperado: 100)")
    print(f"  [TC FLEX] E_endo = ((1-c1+m1)·Y + b·r* - A) / x1")
    print(f"                   = ({1-p['c1']+p['m1']:.2f}·{Y_flex:.4f} + {p['b']}·{r} - {A:.4f}) / {p['x1']}")
    print(f"                   = {E_endo:.4f}  (esperado: 10)")
    print("=" * 60 + "\n")


def verify_base() -> tuple[dict, dict]:
    """
    Verifica los equilibrios analíticos con los parámetros base.

    Ejecuta eq_fixed y eq_flexible y compara contra valores esperados
    de la Sección 3.1 del documento con tolerancia de 0.01.

    Returns
    -------
    tuple[dict, dict]
        (resultado_fijo, resultado_flexible) si pasa todas las verificaciones.

    Raises
    ------
    ValueError
        Si alguna verificación falla, incluye diagnóstico detallado.
    """
    p = get_base_params()

    # ── Calcular equilibrios ─────────────────────────────────────────────────
    res_fixed    = eq_fixed(p)
    res_flexible = eq_flexible(p)

    # ── Valores esperados según Sección 3.1 ──────────────────────────────────
    expected = {
        "mult":    2.5,
        "Y_fixed": 100.0,
        "M_endo":  40.0,
        "Y_flex":  100.0,
        "E_endo":  10.0,
    }

    # ── Valores calculados ───────────────────────────────────────────────────
    calculated = {
        "mult":    res_fixed["mult"],
        "Y_fixed": res_fixed["Y"],
        "M_endo":  res_fixed["M_endo"],
        "Y_flex":  res_flexible["Y"],
        "E_endo":  res_flexible["E_endo"],
    }

    # ── Verificaciones con tolerancia ────────────────────────────────────────
    failures: list[str] = []

    for key, expected_val in expected.items():
        calc_val = calculated[key]
        diff = abs(calc_val - expected_val)
        if diff > _TOLERANCE:
            failures.append(
                f"  ✗ {key}: calculado={calc_val:.6f}, esperado={expected_val:.6f}, "
                f"diferencia={diff:.6f} > tolerancia={_TOLERANCE}"
            )

    if failures:
        # Imprimir cálculo paso a paso antes de lanzar error
        _step_by_step(p)
        error_msg = (
            "❌ VALIDACIÓN FALLIDA — Motor matemático diverge de solución analítica\n"
            + "\n".join(failures)
            + "\n\nRevise las ecuaciones en engine/core.py contra la Sección 3.1."
        )
        raise ValueError(error_msg)

    # ── Reporte de éxito ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ✅ VALIDACIÓN EXITOSA — Motor matemático verificado")
    print("=" * 60)
    print(f"  mult     = {calculated['mult']:.4f}  (esperado {expected['mult']:.4f})")
    print(f"  Y_fixed  = {calculated['Y_fixed']:.4f}  (esperado {expected['Y_fixed']:.4f})")
    print(f"  M_endo   = {calculated['M_endo']:.4f}  (esperado {expected['M_endo']:.4f})")
    print(f"  Y_flex   = {calculated['Y_flex']:.4f}  (esperado {expected['Y_flex']:.4f})")
    print(f"  E_endo   = {calculated['E_endo']:.4f}  (esperado {expected['E_endo']:.4f})")
    print("=" * 60 + "\n")

    # ── Guardar results.parquet ──────────────────────────────────────────────
    _save_results_parquet(res_fixed, res_flexible)

    return res_fixed, res_flexible


def _save_results_parquet(
    res_fixed: dict,
    res_flexible: dict,
) -> None:
    """
    Serializa los equilibrios base a results.parquet con pyarrow.

    Parameters
    ----------
    res_fixed    : Resultado de eq_fixed con parámetros base.
    res_flexible : Resultado de eq_flexible con parámetros base.
    """
    records = [
        {
            "scenario":  "Base_Fixed",
            "regime":    "fixed",
            "preset":    "base",
            "Y":         res_fixed["Y"],
            "r":         res_fixed["r"],
            "E":         res_fixed["E"],
            "M_endo":    res_fixed["M_endo"],
            "E_endo":    float("nan"),
            "NX":        res_fixed["NX"],
            "C":         res_fixed["C"],
            "I_inv":     res_fixed["I_inv"],
            "mult":      res_fixed["mult"],
        },
        {
            "scenario":  "Base_Flexible",
            "regime":    "flexible",
            "preset":    "base",
            "Y":         res_flexible["Y"],
            "r":         res_flexible["r"],
            "E":         float("nan"),
            "M_endo":    float("nan"),
            "E_endo":    res_flexible["E_endo"],
            "NX":        res_flexible["NX"],
            "C":         res_flexible["C"],
            "I_inv":     res_flexible["I_inv"],
            "mult":      res_flexible["mult"],
        },
    ]

    df = pd.DataFrame(records)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, str(_RESULTS_PATH), compression="snappy")
    print(f"  📄 Resultados base guardados en: {_RESULTS_PATH.name}")
