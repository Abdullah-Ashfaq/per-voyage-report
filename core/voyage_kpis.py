# core/voyage_kpis.py
from typing import Dict
import pandas as pd
from core.kpis import compute_kpis_from_json, KPIResult

from dataclasses import asdict

def compute_voyage_kpis(
    signals_df: pd.DataFrame,
    metrics: Dict[str, Dict],
    voyage: Dict
) -> Dict:
    """
    Compute KPIs for a voyage timeframe using the main KPI engine (kpis.py).
    Attaches voyage metadata and returns a dict ready for CSV export.
    """
    kpi = compute_kpis_from_json(signals_df, metrics)

    # Attach voyage metadata
    kpi.voyage_from = voyage["from"]
    kpi.voyage_to = voyage["to"]
    kpi.voyage_start = voyage["start"]
    kpi.voyage_end = voyage["end"]
    kpi.voyage_duration_hours = voyage["duration_hours"]

    # Convert dataclass → dict (so we can easily merge with metadata)
    kpi_dict = asdict(kpi)

    # Add metadata fields
    kpi_dict.update({
        "port_from": voyage["from"],
        "port_to": voyage["to"],
        "voyage_start": voyage["start"],
        "voyage_end": voyage["end"],
        "voyage_duration_hours": voyage["duration_hours"],
    })

    return kpi_dict
