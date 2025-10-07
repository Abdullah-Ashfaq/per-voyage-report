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
    Attaches voyage metadata for convenience.
    """
    kpi = compute_kpis_from_json(signals_df, metrics)

    # Attach voyage metadata
    kpi.voyage_from = voyage["from"]
    kpi.voyage_to = voyage["to"]
    kpi.voyage_start = voyage["start"]
    kpi.voyage_end = voyage["end"]
    kpi.voyage_duration_hours = voyage["duration_hours"]

    return kpi
