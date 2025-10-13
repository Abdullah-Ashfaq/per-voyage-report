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

    # 1️⃣ Fetch voyage signals
    signals_df = get_signals_between(ship_container, voyage["start"], voyage["end"])
    if signals_df.empty:
        print(f"❌ No signals found for voyage {voyage['from']} → {voyage['to']}.")
        return None
    print(f"✅ Loaded {len(signals_df):,} signal rows for this voyage.")

    # 2️⃣ Load metrics + compute KPIs
    metrics = load_metrics_map(metrics_json, ship_name)
    kpi = compute_voyage_kpis(signals_df, metrics, voyage)

    # 3️⃣ Prepare renamed fields (with correct units)
    summary_dict = {
        # --- voyage metadata ---
        "port_from": kpi.voyage_from,
        "port_to": kpi.voyage_to,
        "voyage_start": kpi.voyage_start,
        "voyage_end": kpi.voyage_end,
        "voyage_duration_hours": kpi.voyage_duration_hours,

        # --- navigation ---
        "distance_nm": kpi.distance_nm,
        "avg_sog_kn": kpi.avg_sog,
        "max_sog_kn": kpi.max_sog,

        # --- fuel ---
        "fuel_total_tonnes": kpi.fuel_total_kg,  # now tonnes after conversion
        "fuel_tonnes_per_nm": kpi.fuel_per_nm,
    }

    # --- dynamic fuel_by_signal entries ---
    for name, val in (kpi.fuel_by_signal or {}).items():
        safe_name = name.replace(" ", "_").replace("(", "").replace(")", "").replace(".", "_")
        summary_dict[f"fuel_by_signal_{safe_name}_tonnes"] = val

    # --- energy ---
    summary_dict.update({
        "energy_mwh_total": kpi.energy_kwh_total,
        "energy_mwh_prod": kpi.energy_kwh_prod,
        "energy_mwh_net": kpi.energy_kwh_net,
        "peak_kw": kpi.peak_kw,
        "peak_time": kpi.peak_time,
    })

    # --- WHR ---
    summary_dict.update({
        "whr_total_prod_mwh": kpi.whr_total_prod,
        "whr_total_cons_mwh": kpi.whr_total_cons,
        "whr_util_rate_percent": kpi.whr_util_rate,
    })

    # --- losses & consumers (flatten) ---
    for loss_name, val in (kpi.whr_losses or {}).items():
        safe_name = loss_name.replace(" ", "_").replace("(", "").replace(")", "").replace(".", "_")
        summary_dict[f"whr_loss_{safe_name}_mwh"] = val

    for consumer_name, val in (kpi.whr_consumers or {}).items():
        safe_name = consumer_name.replace(" ", "_").replace("(", "").replace(")", "").replace(".", "_")
        summary_dict[f"whr_consumer_{safe_name}_mwh"] = val

    # --- wind metrics ---
    summary_dict.update({
        "relative_wind_speed_kn": kpi.relative_wind_speed_avg,
        "relative_wind_direction_deg": kpi.relative_wind_direction_avg,
        "true_north_wind_speed_kn": kpi.true_north_wind_speed_avg,
    })

    # --- targeted KPIs ---
    summary_dict.update({
        "target_fuel_tonnes": kpi.total_targeted_fuel_consumption_lngeq,
        "target_lng_tonnes": kpi.total_targeted_lng_consumption,
        "target_electricity_mwh": kpi.total_targeted_electricity_consumption,
        "target_whr_mwh": kpi.total_targeted_whr_consumption,
    })

    # --- engine stats ---
    if kpi.engine_stats:
        for eng in kpi.engine_stats:
            eng_name = eng["name"].replace(" ", "_")
            summary_dict[f"{eng_name}_avg_load_percent"] = eng["avg_load"]

    # 4️⃣ Create DataFrame for saving
    summary = pd.DataFrame([summary_dict])

    # 5️⃣ Save to voyage CSV
    os.makedirs(output_dir, exist_ok=True)
    route_file = (
        f"voyage_{kpi.voyage_from.replace(',', '').replace(' ', '_')}"
        f"_to_{kpi.voyage_to.replace(',', '').replace(' ', '_')}.csv"
    )
    route_path = os.path.join(output_dir, route_file)

    if os.path.exists(route_path):
        existing = pd.read_csv(route_path)
        if "voyage_start" in existing.columns:
            existing_starts = pd.to_datetime(existing["voyage_start"], errors="coerce")
            if kpi.voyage_start in existing_starts.values:
                print(f"⚠️ Voyage starting {kpi.voyage_start} already exists in {route_file}, skipping.")
                return route_path
        summary.to_csv(route_path, mode='a', header=False, index=False)
        print(f"📄 Appended to existing file: {route_file}")
    else:
        summary.to_csv(route_path, index=False)
        print(f"✅ Created new route summary file: {route_file}")

    return route_path
