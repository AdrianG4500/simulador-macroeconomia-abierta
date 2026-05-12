"""
config/scenarios.py
===================
Gestión de escenarios macroeconómicos con pandas + pyarrow.

Responsabilidades:
    - Ejecutar el modelo bajo distintos regímenes y presets.
    - Serializar resultados en formato Parquet para lectura eficiente.
    - Proveer load_all_scenarios() para Streamlit/Plotly en Fase 2.

Convención de archivos Parquet:
    .scenarios/{regime}_{preset_key}.parquet
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from config.parameters import apply_shocks, get_base_params
from engine.core import eq_fixed, eq_flexible

# ── Directorio de salida ─────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent
_SCENARIOS_DIR = _PROJECT_ROOT / ".scenarios"
_SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)

# Tipo literal para régimen cambiario
Regime = Literal["fixed", "flexible"]


# ── Schema pyarrow para validación de tipos ──────────────────────────────────
_SCENARIO_SCHEMA = pa.schema([
    pa.field("scenario",  pa.string()),
    pa.field("regime",    pa.string()),
    pa.field("preset",    pa.string()),
    pa.field("Y",         pa.float64()),
    pa.field("r",         pa.float64()),
    pa.field("M_endo",    pa.float64()),   # solo TC fijo
    pa.field("E_endo",    pa.float64()),   # solo TC flexible
    pa.field("E_fixed",   pa.float64()),   # solo TC fijo
    pa.field("M_fixed",   pa.float64()),   # solo TC flexible
    pa.field("NX",        pa.float64()),
    pa.field("C",         pa.float64()),
    pa.field("I_inv",     pa.float64()),
    pa.field("mult",      pa.float64()),
])


# ── Funciones públicas ────────────────────────────────────────────────────────

def run_scenario(
    regime: Regime,
    preset_key: str,
    base_params: dict[str, float] | None = None,
) -> pd.DataFrame:
    """
    Ejecuta el modelo bajo un régimen y preset dados, y persiste en Parquet.

    Parameters
    ----------
    regime : "fixed" | "flexible"
        Régimen cambiario a simular.
    preset_key : str
        Clave del preset en CRISIS_PRESETS, o "base" para usar parámetros base.
    base_params : dict | None
        Parámetros base. Si None, usa get_base_params().

    Returns
    -------
    pd.DataFrame : DataFrame tipado con resultados del equilibrio.
    """
    if base_params is None:
        base_params = get_base_params()

    # Aplicar shocks si no es escenario base
    if preset_key.lower() == "base":
        params = dict(base_params)
    else:
        params = apply_shocks(base_params, preset_key)

    # Calcular equilibrio según régimen
    if regime == "fixed":
        result = eq_fixed(params)
        row = {
            "scenario":  f"{preset_key}_{regime}",
            "regime":    regime,
            "preset":    preset_key,
            "Y":         result["Y"],
            "r":         result["r"],
            "M_endo":    result["M_endo"],
            "E_endo":    float("nan"),           # No aplica en TC fijo
            "E_fixed":   result["E"],
            "M_fixed":   float("nan"),
            "NX":        result["NX"],
            "C":         result["C"],
            "I_inv":     result["I_inv"],
            "mult":      result["mult"],
        }
    else:  # flexible
        result = eq_flexible(params)
        row = {
            "scenario":  f"{preset_key}_{regime}",
            "regime":    regime,
            "preset":    preset_key,
            "Y":         result["Y"],
            "r":         result["r"],
            "M_endo":    float("nan"),
            "E_endo":    result["E_endo"],
            "E_fixed":   float("nan"),
            "M_fixed":   result["M"],
            "NX":        result["NX"],
            "C":         result["C"],
            "I_inv":     result["I_inv"],
            "mult":      result["mult"],
        }

    # Construir DataFrame con tipo pyarrow
    df = pd.DataFrame([row])

    # Serializar a Parquet
    parquet_path = _SCENARIOS_DIR / f"{preset_key}_{regime}.parquet"
    table = pa.Table.from_pandas(df, schema=_SCENARIO_SCHEMA, preserve_index=False)
    pq.write_table(table, str(parquet_path), compression="snappy")

    return df


def load_all_scenarios() -> pd.DataFrame:
    """
    Carga todos los escenarios Parquet disponibles y los concatena.

    Returns
    -------
    pd.DataFrame
        DataFrame unificado con todos los escenarios guardados.
        Retorna DataFrame vacío si no hay archivos Parquet.
    """
    parquet_files = sorted(_SCENARIOS_DIR.glob("*.parquet"))

    if not parquet_files:
        return pd.DataFrame()

    tables = [pq.read_table(str(f)) for f in parquet_files]
    combined = pa.concat_tables(tables)
    return combined.to_pandas()


def run_all_base_scenarios(
    base_params: dict[str, float] | None = None,
) -> pd.DataFrame:
    """
    Ejecuta los 4 escenarios canónicos del modelo:
        - Base × Fijo
        - Base × Flexible
        - Bolivia_2024_Stagflation × Fijo
        - Bolivia_2024_Stagflation × Flexible

    Parameters
    ----------
    base_params : dict | None
        Parámetros base. Si None, usa get_base_params().

    Returns
    -------
    pd.DataFrame : Tabla comparativa de los 4 escenarios.
    """
    if base_params is None:
        base_params = get_base_params()

    frames = []
    for preset in ["base", "Bolivia_2024_Stagflation"]:
        for regime in ("fixed", "flexible"):
            df = run_scenario(regime=regime, preset_key=preset, base_params=base_params)
            frames.append(df)

    return pd.concat(frames, ignore_index=True)
