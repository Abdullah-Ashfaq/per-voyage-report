import json
import pandas as pd
import numpy as np


def load_metrics_map(metrics_json: str, ship_name: str) -> dict:
    """Load ship-specific metrics mapping from JSON config."""
    with open(metrics_json, "r") as f:
        all_map = json.load(f)
    return all_map.get(ship_name, {})


def _sum_positive_diffs(series: pd.Series) -> float:
    """Sum of positive diffs for counter-type signals."""
    if series.empty:
        return 0.0
    s = pd.to_numeric(series, errors="coerce")
    return float(s.diff().clip(lower=0).sum())


def compute_metric(df: pd.DataFrame, signal: str, method: str, unit: str | None = None) -> float:
    """
    Compute a metric from the DataFrame signal column.
    Handles integration and unit conversion directly.
    """
    if signal not in df.columns:
        return np.nan

    series = pd.to_numeric(df[signal], errors="coerce").dropna()
    if series.empty:
        return np.nan

    method = method.lower().strip()
    total = None

    if method == "sum":
        total = series.sum()
    elif method == "mean":
        total = float(series.mean())
    elif method == "counter":
        total = _sum_positive_diffs(series)
    else:
        raise ValueError(f"Unknown method '{method}' for signal '{signal}'")

    if not unit:
        return float(total)

    unit = unit.lower().strip()

    # --- Apply unit-specific scaling ---
    if unit == "kn":           # knots (distance per hour)
        total = total / 12.0   # -> nautical miles (NM)
    elif unit in ["kw", "mw"]:  # power → energy
        total = total / 12.0   # each 5-min = 1/12 hr
        if unit == "kw":
            total /= 1000.0    # -> MWh
    elif unit in ["kg/h", "kgph"]:
        total = total / 1000.0  # kg → tonnes (no /12)
    elif unit == "kg/s":
        total = total * 3.6 / 1000.0  # kg/s → tonnes (per hour basis)
    elif unit in ["m³/h", "m3/h"]:
        total = total / 12.0
    elif unit in ["m³/day", "m3/day"]:
        total = total / (12.0 * 24.0)
    elif unit == "m/s":
        total = total * 3.6
    else:
        total = total

    return float(total)
