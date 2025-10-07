# core/voyage_detection.py
import pandas as pd
from typing import List, Dict

def detect_voyages(port_df: pd.DataFrame) -> List[Dict]:
    """
    Detect voyages based on harbor → sea → harbor transitions.
    Works even if columns are lowercase or uppercase.
    Returns a list of voyages with metadata:
      {from, to, start, end}
    """
    if port_df.empty:
        return []

    # ✅ Normalize column names (case-insensitive)
    port_df.columns = [c.strip().lower() for c in port_df.columns]

    # ✅ Use index if already datetime, otherwise detect timestamp column
    if isinstance(port_df.index, pd.DatetimeIndex):
        port_df = port_df.reset_index().rename(columns={"index": "ts"})
    elif "ts" in port_df.columns:
        port_df["ts"] = pd.to_datetime(port_df["ts"], errors="coerce", utc=True)
    elif "timestamp" in port_df.columns:
        port_df["ts"] = pd.to_datetime(port_df["timestamp"], errors="coerce", utc=True)
    else:
        raise ValueError("Expected a 'ts' or 'timestamp' column in port data")

    # ✅ Clean + sort chronologically
    port_df = port_df.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)

    voyages = []
    in_voyage = None
    last_port = None

    for _, row in port_df.iterrows():
        ts = row["ts"]
        sea = int(row.get("sea", 0))
        harbor = int(row.get("harbor", 0))
        port_name = row.get("location_name", None)

        # Start voyage when ship leaves harbor → sea
        if harbor == 0 and sea == 1 and in_voyage is None and last_port:
            in_voyage = {"from": last_port, "start": ts}

        # End voyage when ship re-enters harbor
        if harbor == 1 and sea == 0 and in_voyage is not None:
            in_voyage["to"] = port_name
            in_voyage["end"] = ts
            voyages.append(in_voyage)
            in_voyage = None

        # Track last known port
        if harbor == 1 and port_name:
            last_port = port_name

    if not voyages:
        print("⚠️ No voyages detected — check if 'sea'/'harbor' transitions exist.")

    return voyages


def add_voyage_durations(voyages: List[Dict]) -> List[Dict]:
    """Add duration (in hours) to each voyage dictionary."""
    for voyage in voyages:
        if isinstance(voyage["start"], pd.Timestamp) and isinstance(voyage["end"], pd.Timestamp):
            voyage["duration_hours"] = (voyage["end"] - voyage["start"]).total_seconds() / 3600
        else:
            voyage["duration_hours"] = None
    return voyages
