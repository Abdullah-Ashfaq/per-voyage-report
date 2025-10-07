# metrics_map.py
import json
import pandas as pd
import numpy as np
from typing import Dict, Any


# ---------------- JSON LOADER ----------------

import json

def load_metrics_map(metrics_json: str, ship_name: str) -> dict:
    with open(metrics_json, "r") as f:
        all_map = json.load(f)
    return all_map.get(ship_name, {})


# ---------------- HELPERS ----------------
def _dt_hours(idx: pd.DatetimeIndex) -> np.ndarray:
    """Return delta-t in hours for a datetime index."""
    if len(idx) < 2:
        return np.array([0.0] * len(idx))
    return idx.to_series().diff().dt.total_seconds().fillna(0).values / 3600.0


def _integrate_rate(series: pd.Series) -> float:
    """Integrate a per-hour rate (e.g., kg/h, kW) → total quantity (kg, kWh)."""
    if series.empty:
        return 0.0
    series = pd.to_numeric(series, errors="coerce").fillna(0.0)
    dt = _dt_hours(series.index)
    return float(np.nansum(series.values * dt))


def _sum_positive_diffs(series: pd.Series, scale: float = 1.0) -> float:
    """For cumulative counters → sum of positive diffs."""
    if series.empty:
        return 0.0
    s = pd.to_numeric(series, errors="coerce")
    diffs = s.diff().clip(lower=0)
    return float(diffs.sum() * scale)


def compute_metric(df: pd.DataFrame, signal: str, method: str) -> float:
    """
    Compute a metric from dataframe based on method:
    - "Sum" → integrate a rate signal
    - "Mean" → average
    - "Counter" → positive diffs of counter
    """
    if signal not in df.columns:
        return np.nan

    series = df[signal].dropna()

    if method.lower() == "sum":
        return _integrate_rate(series)
    elif method.lower() == "mean":
        return float(series.mean())
    elif method.lower() == "counter":
        return _sum_positive_diffs(series)
    else:
        raise ValueError(f"Unknown method '{method}' for signal '{signal}'")
