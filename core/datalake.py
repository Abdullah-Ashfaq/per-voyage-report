# core/datalake.py
import os
import io 
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from dateutil.relativedelta import relativedelta

import pandas as pd
from dotenv import load_dotenv
from azure.storage.filedatalake import DataLakeServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions

# Load env vars automatically
load_dotenv("config/settings.env")

# ----------------- CONFIG -----------------
WORKERS = int(os.getenv("DL_DOWNLOAD_WORKERS", "8"))

# ----------------- LOGGING -----------------
def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ----------------- ENV / CONNECTION -----------------
def _extract_account_details():
    """Reads Azure storage account + container names."""
    global account_name, account_key, container_signals, container_ports
    account_name = os.environ["DataLakeAccountName"]
    account_key  = os.environ["DataLakeAccountKey"]
    container_ports   = "csvportmonthly"
    container_signals = "csvdatamonthly"

def _connection_string():
    return (
        "DefaultEndpointsProtocol=https;"
        f"AccountName={account_name};"
        f"AccountKey={account_key};"
        "EndpointSuffix=core.windows.net"
    )

def get_sas_url(container: str, blob_name: str) -> str:
    sas_i = generate_blob_sas(
        account_name=account_name,
        container_name=container,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    return f"https://{account_name}.blob.core.windows.net/{container}/{blob_name}?{sas_i}"

# ----------------- HELPERS -----------------
def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _read_csv_any(url: str) -> pd.DataFrame:
    """Ultra-robust CSV/ZIP reader — handles mixed encodings, delimiters, and malformed lines."""
    _log(f"🔎 Reading CSV from: {url}")
    encodings = ["utf-8", "utf-16", "latin1", "ISO-8859-1"]
    seps = [",", ";"]
    name = url.lower()

    for enc in encodings:
        for sep in seps:
            try:
                if name.endswith(".zip"):
                    df = pd.read_csv(
                        url,
                        compression="zip",
                        encoding=enc,
                        sep=sep,
                        on_bad_lines="skip",  # 👈 skip malformed rows
                        low_memory=False
                    )
                else:
                    df = pd.read_csv(
                        url,
                        encoding=enc,
                        sep=sep,
                        on_bad_lines="skip",
                        low_memory=False
                    )
                _log(f"✅ Successfully read with encoding={enc}, sep='{sep}', rows={len(df)}")
                return df
            except Exception as e:
                _log(f"⚠️ Retry failed (enc={enc}, sep='{sep}'): {e}")
                continue

    _log(f"❌ Could not decode or parse {url} with any fallback combination.")
    return pd.DataFrame()

def _read_blob_to_df(container_name: str, blob_name: str) -> pd.DataFrame | None:
    """Reads a CSV or ZIP-compressed CSV blob from Azure into a DataFrame."""
    dlsc = DataLakeServiceClient.from_connection_string(_connection_string())
    fs = dlsc.get_file_system_client(container_name)
    blob = fs.get_file_client(blob_name)

    try:
        stream = io.BytesIO(blob.download_file().readall())

        # ✅ If ZIP, extract the first CSV inside
        if blob_name.lower().endswith(".zip"):
            with zipfile.ZipFile(stream) as zf:
                # Pick first .csv inside ZIP
                csv_files = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                if not csv_files:
                    _log(f"⚠️ No CSV found inside ZIP: {blob_name}")
                    return None
                with zf.open(csv_files[0]) as f:
                    return pd.read_csv(f, encoding="utf-8", on_bad_lines="skip")

        # ✅ Else, read directly as CSV
        return pd.read_csv(stream, encoding="utf-8", on_bad_lines="skip")

    except Exception as e:
        _log(f"⚠️ Failed to read blob {blob_name}: {e}")
        return None
def _recent_months_path(base_path: str, months_back: int = 3) -> List[str]:
    """Return list of year/month subpaths for the last N months."""
    today = datetime.now(timezone.utc)
    months = []
    for i in range(months_back):
        dt = today - relativedelta(months=i)
        months.append(f"{base_path}/{dt.year}/{dt.month:02d}")
    return months

# ----------------- DEBUG LIST -----------------
def debug_list_blobs(container: str, ship_container: str, limit: int = 20):
    """
    List the first `limit` blobs under a container+ship path.
    Example:
      debug_list_blobs("csvportmonthly", "icon1", 20)
      debug_list_blobs("csvdatamonthly", "icon1", 20)
    """
    _extract_account_details()
    dlsc = DataLakeServiceClient.from_connection_string(_connection_string())
    fs = dlsc.get_file_system_client(container)

    print(f"📂 Listing first {limit} blobs under container '{container}/{ship_container}'…")
    count = 0
    for p in fs.get_paths(path=ship_container, recursive=True):
        if getattr(p, "is_directory", False):
            continue
        print(f" - {p.name}")
        count += 1
        if count >= limit:
            break

# ----------------- VOYAGE / PORT DATA -----------------
def get_voyage_data(ship_container: str) -> pd.DataFrame:
    """
    Load monthly port-data CSVs for the last 3 months:
      csvportmonthly/{ship}/port-data/YYYY/MM/port-data-YYYY-MM.csv

    Ensures:
    - 'timestamp' → 'ts' column normalization
    - 'ts' is timezone-aware (UTC)
    - Sorted index for downstream voyage detection
    """

    _extract_account_details()
    dlsc = DataLakeServiceClient.from_connection_string(_connection_string())
    fs = dlsc.get_file_system_client(container_ports)

    base_path = f"{ship_container}/port-data"
    month_paths = _recent_months_path(base_path, 6)
    _log(f"📂 Scanning last 3 months of port-data under: {container_ports}/{base_path}")

    names: List[str] = []
    for mp in month_paths:
        for p in fs.get_paths(path=mp, recursive=True):
            if getattr(p, "is_directory", False):
                continue
            if p.name.lower().endswith(".csv"):
                names.append(p.name)

    if not names:
        _log("❌ No voyage port-data files found.")
        return pd.DataFrame()

    _log(f"📥 Found {len(names)} port-data files, fetching…")

    dfs: List[pd.DataFrame] = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(_read_blob_to_df, container_ports, n) for n in names]
        for fut in as_completed(futs):
            df_i = fut.result()
            if df_i is not None and not df_i.empty:
                dfs.append(df_i)

    if not dfs:
        _log("❌ No usable port-data files after reading.")
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    # Normalize timestamp column
    ts_col = None
    for cand in ("ts", "timestamp", "Timestamp", "TIMESTAMP"):
        if cand in df.columns:
            ts_col = cand
            break

    if ts_col:
        # Standardize column name
        if ts_col != "ts":
            df.rename(columns={ts_col: "ts"}, inplace=True)

        # Convert to UTC datetime and set as index
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce", utc=True)
        df = (
            df.dropna(subset=["ts"])
            .sort_values("ts")
            .set_index("ts")
        )
        _log(f"✅ Normalized 'ts' column and set as index. Rows: {len(df)}")
    else:
        _log("⚠️ No timestamp-like column found. 'detect_voyages()' may fail.")

    _log(f"✅ Port data shape: {df.shape}")
    return df

# ----------------- SIGNAL DATA -----------------
def get_signals_between(ship_container: str, start: datetime, end: datetime) -> pd.DataFrame:
    """
    Fetch signals between voyage start and end from:
      csvdatamonthly/{ship}/YYYY/MM/*.csv or *.zip

    ✅ Updated logic:
      - Identify months covering the voyage window.
      - Fetch only those monthly CSVs.
      - Filter rows based on timestamp column (ts/timestamp).
      - Return precise time-sliced DataFrame.
    """
    _extract_account_details()
    dlsc = DataLakeServiceClient.from_connection_string(_connection_string())
    fs = dlsc.get_file_system_client(container_signals)

    start = _as_utc(start)
    end = _as_utc(end)

    _log(f"🔍 Searching signals within voyage window {start} → {end} for {ship_container}…")

    # 🧮 Determine year-month folders for voyage duration
    months = pd.period_range(start=start.to_period("M"), end=end.to_period("M"), freq="M")
    paths = [f"{ship_container}/{d.year:04d}/{d.month:02d}" for d in months]

    names: List[str] = []
    for p in paths:
        for blob in fs.get_paths(path=p, recursive=True):
            if getattr(blob, "is_directory", False):
                continue
            if blob.name.lower().endswith((".csv", ".zip")):
                names.append(blob.name)

    if not names:
        _log(f"❌ No signal files found for months {[str(m) for m in months]} in {ship_container}")
        return pd.DataFrame()

    _log(f"📥 Found {len(names)} signals files, fetching…")

    dfs: List[pd.DataFrame] = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(_read_blob_to_df, container_signals, blob) for blob in names]
        for fut in as_completed(futs):
            df_i = fut.result()
            if df_i is None or df_i.empty:
                continue

            # Normalize timestamp column
            ts_col = None
            for cand in ("ts", "timestamp", "Timestamp", "TIMESTAMP"):
                if cand in df_i.columns:
                    ts_col = cand
                    break
            if ts_col:
                df_i["ts"] = pd.to_datetime(df_i[ts_col], errors="coerce", utc=True)
                df_i = df_i.dropna(subset=["ts"]).set_index("ts")
                df_i = df_i.sort_index()
                df_i = df_i.loc[(df_i.index >= start) & (df_i.index <= end)]
                if not df_i.empty:
                    dfs.append(df_i)
            else:
                _log(f"⚠️ Skipping {blob}: No timestamp column found")

    if not dfs:
        _log(f"⚠️ No usable signal data within window {start} → {end}")
        return pd.DataFrame()

    df = pd.concat(dfs, axis=0)
    _log(f"✅ Signals windowed shape: {df.shape}")
    return df
