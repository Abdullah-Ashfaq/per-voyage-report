# core/voyage_state.py
import os
import json
import pandas as pd
from datetime import datetime
from typing import Optional

STATE_FILE = "voyage_state.json"
VOYAGE_LOG = "voyage_log.csv"

def load_last_voyage_end() -> Optional[datetime]:
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
    if "last_end" not in state:
        return None
    return pd.to_datetime(state["last_end"], utc=True)

def save_last_voyage_end(end_time: datetime):
    state = {"last_end": end_time.isoformat()}
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def append_voyage_log(voyage: dict, report_file: str):
    log_entry = {
        "from": voyage["from"],
        "to": voyage["to"],
        "start": voyage["start"].isoformat(),
        "end": voyage["end"].isoformat(),
        "duration_hours": voyage.get("duration_hours", None),
        "report_file": report_file,
    }
    df_entry = pd.DataFrame([log_entry])
    if os.path.exists(VOYAGE_LOG):
        df_entry.to_csv(VOYAGE_LOG, mode="a", index=False, header=False)
    else:
        df_entry.to_csv(VOYAGE_LOG, index=False)
