# core/voyage_kpis.py
from typing import Dict
import pandas as pd
from core.kpis import compute_kpis_from_json, KPIResult

def compute_voyage_kpis(
    signals_df: pd.DataFrame,
    metrics: Dict[str, Dict],
    voyage: Dict
) -> KPIResult:
    """
    Compute KPIs for a voyage timeframe using the main KPI engine (kpis.py).
    Attaches voyage metadata and flattens all dict-based KPIs for easy CSV export.
    """
    kpi = compute_kpis_from_json(signals_df, metrics)

    # Attach voyage metadata
    kpi.voyage_from = voyage.get("from")
    kpi.voyage_to = voyage.get("to")
    kpi.voyage_start = voyage.get("start")
    kpi.voyage_end = voyage.get("end")
    kpi.voyage_duration_hours = voyage.get("duration_hours")

    # Flatten nested dicts
    flattened = {}
    for key, val in kpi.__dict__.items():
        if isinstance(val, dict):
            for subkey, subval in val.items():
                clean = (
                    subkey.replace(" ", "_")
                    .replace("(", "")
                    .replace(")", "")
                    .replace("/", "_")
                )
                flattened[f"{key}_{clean}"] = subval
        else:
            flattened[key] = val

    # Attach flattened metrics as top-level attributes
    for k, v in flattened.items():
        setattr(kpi, k, v)

    # Convert timestamps to ISO strings for readable CSVs
    for t in ["voyage_start", "voyage_end", "peak_time"]:
        val = getattr(kpi, t, None)
        if isinstance(val, pd.Timestamp):
            setattr(kpi, t, val.isoformat())

    return kpi
