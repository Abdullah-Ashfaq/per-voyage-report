import os
import pandas as pd
from core.datalake import get_signals_between
from core.voyage_kpis import compute_voyage_kpis
from core.metrics_map import load_metrics_map


def process_and_save_voyage(
    voyage: dict,
    ship_container: str,
    ship_name: str,
    metrics_json: str,
    output_dir: str = "./voyage_csvs"
) -> str | None:

    print(
        f"\n Processing voyage {voyage['from']} → {voyage['to']} "
        f"({voyage['start']} → {voyage['end']}) | "
        f"Duration: {voyage['duration_hours']:.2f}h"
    )

    # Fetch signals for this voyage
    signals_df = get_signals_between(ship_container, voyage["start"], voyage["end"])

    if signals_df.empty:
        print(f" No signals found for voyage {voyage['from']} → {voyage['to']}. Skipping.")
        return None

    print(f" Loaded {len(signals_df):,} signal rows for this voyage.")

    # Load metrics mapping
    metrics = load_metrics_map(metrics_json, ship_name)

    # Compute voyage KPIs
    kpi_result = compute_voyage_kpis(signals_df, metrics, voyage)

    # Build voyage summary row
    summary = pd.DataFrame([{
        "port_from": kpi_result.voyage_from,
        "port_to": kpi_result.voyage_to,
        "voyage_start": kpi_result.voyage_start,
        "voyage_end": kpi_result.voyage_end,
        "voyage_duration_hours": kpi_result.voyage_duration_hours,
        "distance_nm": kpi_result.distance_nm,
        "avg_sog": kpi_result.avg_sog,
        "max_sog": kpi_result.max_sog,
        "fuel_total_kg": kpi_result.fuel_total_kg,
        "fuel_per_nm": kpi_result.fuel_per_nm,
        "energy_kwh_total": kpi_result.energy_kwh_total,
        "energy_kwh_prod": kpi_result.energy_kwh_prod,
        "energy_kwh_net": kpi_result.energy_kwh_net,
        "peak_kw": kpi_result.peak_kw,
        "peak_time": kpi_result.peak_time,
        "whr_total_prod": kpi_result.whr_total_prod,
        "whr_total_cons": kpi_result.whr_total_cons,
        "whr_util_rate": kpi_result.whr_util_rate,
    }])

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Define per-route filename
    route_file = f"voyage_{kpi_result.voyage_from.replace(',', '').replace(' ', '_')}_to_{kpi_result.voyage_to.replace(',', '').replace(' ', '_')}.csv"
    route_path = os.path.join(output_dir, route_file)

    # Append if exists, otherwise create
    if os.path.exists(route_path):
        existing = pd.read_csv(route_path)
        if "voyage_start" in existing.columns:
            existing_starts = pd.to_datetime(existing["voyage_start"], errors="coerce")
            if kpi_result.voyage_start in existing_starts.values:
                print(f"⚠️ Voyage starting {kpi_result.voyage_start} already exists in {route_file}, skipping append.")
                return route_path

        summary.to_csv(route_path, mode='a', header=False, index=False)
        print(f"📄 Appended voyage to existing file: {route_file}")
    else:
        summary.to_csv(route_path, index=False)
        print(f"Created new route summary file: {route_file}")

    return route_path
