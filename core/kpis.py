# core/kpis.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Helpers from metrics_map.py (no integrate now)
from core.metrics_map import compute_metric


# ========================== Dataclass ==========================
@dataclass
class KPIResult:
    distance_nm: Optional[float]
    avg_sog: Optional[float]
    max_sog: Optional[float]

    fuel_total_kg: Optional[float]
    fuel_per_nm: Optional[float]
    fuel_by_signal: Dict[str, float]

    energy_kwh_total: Optional[float]
    energy_kwh_prod: Optional[float]
    energy_kwh_net: Optional[float]
    peak_kw: Optional[float]
    peak_time: Optional[pd.Timestamp]
    energy_top: List[Tuple[str, float]]

    whr_total_prod: Optional[float] = None
    whr_total_cons: Optional[float] = None
    whr_util_rate: Optional[float] = None
    whr_losses: Dict[str, float] = None
    whr_consumers: Dict[str, float] = None

    chw_delta_t: Optional[float] = None
    cop_proxy: Optional[float] = None
    ai_suggestions: Optional[str] = None

    # wind & targeted KPIs
    relative_wind_speed_avg: Optional[float] = None
    relative_wind_direction_avg: Optional[float] = None
    true_north_wind_speed_avg: Optional[float] = None

    total_targeted_fuel_consumption_lngeq: Optional[float] = None
    total_targeted_lng_consumption: Optional[float] = None
    total_targeted_electricity_consumption: Optional[float] = None
    total_targeted_whr_consumption: Optional[float] = None

    engine_stats: List[Dict] = None


# ========================== Core compute ==========================
def _get_series(df: pd.DataFrame, signal: Optional[str]) -> Optional[pd.Series]:
    if not signal or signal not in df.columns:
        return None
    s = pd.to_numeric(df[signal], errors="coerce")
    s.index = pd.to_datetime(df.index, utc=True)
    return s


def compute_kpis_from_json(
    df24: pd.DataFrame,
    metrics: Dict[str, Dict],
) -> KPIResult:
    """
    Compute KPIs from JSON-defined metrics, applying unit conversions where needed.
    (Distance is now calculated later using avg_sog × duration.)
    """
    df = df24.copy()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    # ----- Navigation -----
    sog_meta = metrics.get("Avg Speed (SOG)") or metrics.get("Avg Speed")
    sog = _get_series(df, sog_meta["Signal"]) if sog_meta else None
    avg_sog = float(sog.mean()) if sog is not None else None
    max_sog = float(sog.max()) if sog is not None else None

    # Skip distance_nm here — handled in voyage_kpis.py
    distance_nm = None

    # ----- Fuel -----
    fuel_keys = [
        "Total Fuel Consumption (LNG eq.)",
        "Total LNG Consumption",
        "Total MGO Consumption",
        "Total Auxiliary Boiler Fuel Consumption",
    ]
    fuel_by_signal: Dict[str, float] = {}
    for key in fuel_keys:
        meta = metrics.get(key)
        if not meta:
            continue
        val = compute_metric(df, meta["Signal"], meta.get("Method", "Sum"), meta.get("Unit"))
        if val is not None and not np.isnan(val):
            fuel_by_signal[key] = float(val)

    fuel_total_kg = (
        fuel_by_signal.get("Total Fuel Consumption (LNG eq.)")
        or sum(fuel_by_signal.values()) if fuel_by_signal else None
    )

    fuel_per_nm = (fuel_total_kg / distance_nm) if (fuel_total_kg and distance_nm and distance_nm > 0) else None

    # ----- Electrical -----
    cons_meta = metrics.get("Total Electricity Consumption")
    prod_meta = metrics.get("Total Electricity Production")

    energy_kwh_total = (
        compute_metric(df, cons_meta["Signal"], cons_meta.get("Method", "Sum"), cons_meta.get("Unit"))
        if cons_meta else None
    )
    energy_kwh_prod = (
        compute_metric(df, prod_meta["Signal"], prod_meta.get("Method", "Sum"), prod_meta.get("Unit"))
        if prod_meta else None
    )
    energy_kwh_net = (
        (energy_kwh_total - energy_kwh_prod)
        if (energy_kwh_total is not None and energy_kwh_prod is not None)
        else None
    )

    # ----- Peak demand -----
    peak_components = [
        "Avg Propulsion Power",
        "Avg Service Power",
        "Avg Hotel Power",
        "Avg Machinery Power",
        "Avg AC Chiller Power",
    ]
    total_power = None
    for key in peak_components:
        meta = metrics.get(key)
        if not meta:
            continue
        s = _get_series(df, meta["Signal"])
        if s is None:
            continue
        total_power = s if total_power is None else total_power.add(s, fill_value=0.0)

    peak_kw = peak_time = None
    if total_power is not None and not total_power.empty:
        peak_time = total_power.idxmax()
        peak_kw = float(total_power.loc[peak_time])

    # Compute total energy of top components directly (using compute_metric)
    energy_top: List[Tuple[str, float]] = []
    for key in peak_components:
        meta = metrics.get(key)
        if not meta:
            continue
        val = compute_metric(df, meta["Signal"], meta.get("Method", "Sum"), meta.get("Unit"))
        energy_top.append((key, float(val)))
    energy_top.sort(key=lambda x: -x[1])
    energy_top = energy_top[:5]

    # ----- WHR -----
    whr_total_prod = whr_total_cons = whr_util_rate = None
    whr_losses, whr_consumers = {}, {}

    if "Total WHR Production" in metrics:
        m = metrics["Total WHR Production"]
        whr_total_prod = compute_metric(df, m["Signal"], m["Method"], m.get("Unit"))

    if "Total WHR Consumption" in metrics:
        m = metrics["Total WHR Consumption"]
        whr_total_cons = compute_metric(df, m["Signal"], m["Method"], m.get("Unit"))

    if "WHR Utilization Rate" in metrics:
        m = metrics["WHR Utilization Rate"]
        whr_util_rate = compute_metric(df, m["Signal"], m["Method"], m.get("Unit"))

    for loss in ["Total WHR Losses (HT Dump)", "Total WHR Losses (Steam Dump)"]:
        if loss in metrics:
            m = metrics[loss]
            val = compute_metric(df, m["Signal"], m["Method"], m.get("Unit"))
            if val is not None:
                whr_losses[loss] = val

    whr_consumer_keys = [
        "WHR Absorption Chiller",
        "WHR Condensate Heater",
        "WHR Evaporators",
        "WHR Laundry",
        "WHR Potable Water Heating",
        "WHR AC Reheating",
        "WHR Other Uses",
    ]
    for key in whr_consumer_keys:
        if key in metrics:
            m = metrics[key]
            val = compute_metric(df, m["Signal"], m["Method"], m.get("Unit"))
            if val is not None:
                whr_consumers[key] = val

    # ----- Engine Loads -----
    engine_stats: List[Dict] = []
    for key, meta in metrics.items():
        if key.startswith("Avg ME") and "Load" in key:
            s = _get_series(df, meta["Signal"])
            if s is not None and not s.empty:
                avg_val = float(s.mean())
                engine_stats.append({"name": key, "avg_load": avg_val})

    # ----- Targeted Signals -----
    targeted_signals = {
        "Total Targeted Fuel Consumption (LNG eq.)": "total_targeted_fuel_consumption_lngeq",
        "Total Targeted LNG Consumption": "total_targeted_lng_consumption",
        "Total Targeted Electricity Consumption": "total_targeted_electricity_consumption",
        "Total Targeted WHR Consumption": "total_targeted_whr_consumption",
    }
    targeted_values = {}
    for key, attr in targeted_signals.items():
        if key in metrics:
            m = metrics[key]
            val = compute_metric(df, m["Signal"], m["Method"], m.get("Unit"))
            if val is not None:
                targeted_values[attr] = val

    # ----- Wind Data -----
    wind_signals = {
        "Relative Wind Speed": "relative_wind_speed_avg",
        "Relative Wind Direction": "relative_wind_direction_avg",
        "True North Wind Speed": "true_north_wind_speed_avg",
    }
    wind_values = {}
    for key, attr in wind_signals.items():
        if key in metrics:
            m = metrics[key]
            s = _get_series(df, m["Signal"])
            if s is not None and not s.empty:
                avg_val = float(s.mean())
                wind_values[attr] = avg_val

    # ----- Return KPIResult -----
    return KPIResult(
        distance_nm=distance_nm,
        avg_sog=avg_sog,
        max_sog=max_sog,
        fuel_total_kg=fuel_total_kg,
        fuel_per_nm=fuel_per_nm,
        fuel_by_signal=fuel_by_signal,
        energy_kwh_total=energy_kwh_total,
        energy_kwh_prod=energy_kwh_prod,
        energy_kwh_net=energy_kwh_net,
        peak_kw=peak_kw,
        peak_time=peak_time,
        energy_top=energy_top,
        whr_total_prod=whr_total_prod,
        whr_total_cons=whr_total_cons,
        whr_util_rate=whr_util_rate,
        whr_losses=whr_losses,
        whr_consumers=whr_consumers,
        engine_stats=engine_stats,
        **targeted_values,
        **wind_values,
    )
