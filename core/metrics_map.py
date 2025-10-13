import json
import pandas as pd
import numpy as np
from typing import Dict, Any


# ---------------- JSON LOADER ----------------

def load_metrics_map(metrics_json: str, ship_name: str) -> dict:
    """Load the metrics mapping JSON for a specific ship."""
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


# ---------------- CORE METRIC COMPUTATION ----------------
def compute_metric(df: pd.DataFrame, signal: str, method: str, unit: str | None = None) -> float:
    """
    Compute a metric from dataframe based on method and apply unit conversion.
      • method: Sum | Mean | Counter
      • unit: optional engineering unit string (e.g. 'kW', 'kg/h', 'kn')
    """
    if signal not in df.columns:
        return np.nan

    series = pd.to_numeric(df[signal], errors="coerce").dropna()
    if series.empty:
        return np.nan

    # --- Base calculation ---
    method = method.lower()
    if method == "sum":
        total = _integrate_rate(series)
    elif method == "mean":
        total = float(series.mean())
    elif method == "counter":
        total = _sum_positive_diffs(series)
    else:
        raise ValueError(f"Unknown method '{method}' for signal '{signal}'")

    # --- Apply 5-minute-interval unit conversions ---
    if unit:
        u = unit.strip().lower()

        if u == "kn":          # knots → nautical miles (5-min interval)
            return total / 12.0

        if u in ("kg/h", "kgh"):   # kilograms/hour → tonnes
            return total / 1000.0

        if u in ("kw",):       # kilowatts → megawatt-hours (5-min)
            return total / (12.0 * 1000.0)

        if u in ("m³/h", "m3/h", "m3h"):
            return total / 12.0

        if u in ("m³/day", "m3/day", "m3d"):
            return total / (12.0 * 24.0)

        if u in ("m/s", "ms"):
            return total * 3.6

    # No conversion or unknown unit
    return float(total)
