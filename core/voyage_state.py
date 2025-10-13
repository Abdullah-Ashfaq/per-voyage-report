# core/voyage_state.py
import os, json, pandas as pd
from datetime import datetime
from typing import Optional
from core.datalake import get_voyage_data, get_signals_between
from core.voyage_detection import detect_voyages, add_voyage_durations
from core.process_voyage import process_and_save_voyage
from core.metrics_map import load_metrics_map

STATE_FILE = "voyage_tracker.json"
VOYAGE_LOG = "voyage_log.csv"


def load_last_voyage_end() -> Optional[datetime]:
    """Return the timestamp of the last completed voyage (UTC)."""
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
    return pd.to_datetime(state.get("last_end"), utc=True) if state.get("last_end") else None


def save_last_voyage_end(end_time: datetime, ship_name: str = None):
    """Persist last voyage end + metadata."""
    state = {
        "last_end": end_time.isoformat(),
        "last_updated": datetime.utcnow().isoformat(),
        "ship": ship_name,
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"🧭 Updated voyage tracker → {STATE_FILE}")


def append_voyage_log(voyage: dict, report_file: str):
    """Append voyage metadata to voyage_log.csv for auditing."""
    log_entry = {
        "from": voyage["from"],
        "to": voyage["to"],
        "start": voyage["start"].isoformat(),
        "end": voyage["end"].isoformat(),
        "duration_hours": voyage.get("duration_hours"),
        "report_file": report_file,
    }
    df_entry = pd.DataFrame([log_entry])
    if os.path.exists(VOYAGE_LOG):
        df_entry.to_csv(VOYAGE_LOG, mode="a", index=False, header=False)
    else:
        df_entry.to_csv(VOYAGE_LOG, index=False)


def detect_and_process_new_voyages(
    ship_container: str,
    ship_name: str,
    metrics_json: str,
    output_dir: str = "./voyage_csvs",
):
    """
    Main helper for scheduler or real-time loop:
    - Detect new voyages after last_end
    - Compute KPIs
    - Save CSV
    - Update state + log
    Returns the path to the latest CSV if a new voyage was processed, else None.
    """
    last_end = load_last_voyage_end()
    print(f"⏱ Last processed voyage ended at: {last_end}")

    # 1️⃣ Load and detect voyages
    port_df = get_voyage_data(ship_container)
    voyages = add_voyage_durations(detect_voyages(port_df))
    new_voyages = [v for v in voyages if last_end is None or v["end"] > last_end]

    if not new_voyages:
        print("🟡 No new voyages detected since last run.")
        return None

    # 2️⃣ Process the latest new voyage only
    latest_voyage = new_voyages[-1]
    print(f"🚢 New voyage found: {latest_voyage['from']} → {latest_voyage['to']}")

    metrics = load_metrics_map(metrics_json, ship_name)
    csv_path = process_and_save_voyage(
        voyage=latest_voyage,
        ship_container=ship_container,
        ship_name=ship_name,
        metrics_json=metrics_json,
        output_dir=output_dir,
    )

    # 3️⃣ Update state + log
    save_last_voyage_end(latest_voyage["end"], ship_name=ship_name)
    append_voyage_log(latest_voyage, csv_path)

    return csv_path
