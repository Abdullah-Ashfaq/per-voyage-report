# Kpis.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Helpers come from metrics_map.py (JSON loader + math helpers)
from core.metrics_map import (
    _dt_hours,          # dt in hours
    _integrate_rate,    # integrate a rate (kW, kg/h) -> kWh, kg
    compute_metric,     # compute(df, signal, method)
)

# ========================== Dataclass ==========================
@dataclass
class KPIResult:
    distance_nm: Optional[float]
    avg_sog: Optional[float]
    max_sog: Optional[float]

    fuel_total_kg: Optional[float]
    fuel_per_nm: Optional[float]
    fuel_by_signal: Dict[str, float]  # metric-name -> kg

    energy_kwh_total: Optional[float]
    energy_kwh_prod: Optional[float]
    energy_kwh_net: Optional[float]
    peak_kw: Optional[float]
    peak_time: Optional[pd.Timestamp]
    energy_top: List[Tuple[str, float]]  # (metric-name, kWh)
    whr_total_prod: Optional[float] = None
    whr_total_cons: Optional[float] = None
    whr_util_rate: Optional[float] = None
    whr_losses: Dict[str, float] = None
    whr_consumers: Dict[str, float] = None

    # kept for compatibility (not used if HVAC dropped)
    chw_delta_t: Optional[float] = None
    cop_proxy: Optional[float] = None
    # AI Suggestions 
    ai_suggestions: Optional[str] = None
    # wind data
    relative_wind_speed_avg: Optional[float] = None
    relative_wind_direction_avg: Optional[float] = None
    true_north_wind_speed_avg: Optional[float] = None

    # targeted signals
    total_targeted_fuel_consumption_lngeq: Optional[float] = None
    total_targeted_lng_consumption: Optional[float] = None
    total_targeted_electricity_consumption: Optional[float] = None
    total_targeted_whr_consumption: Optional[float] = None

    # optional extras
    engine_stats: List[Dict] = None   # NEW: [{name, avg_load}]


# ========================== Core compute ==========================
def _get_series(df: pd.DataFrame, signal: Optional[str]) -> Optional[pd.Series]:
    if not signal or signal not in df.columns:
        return None
    s = pd.to_numeric(df[signal], errors="coerce")
    # ensure UTC index
    idx = pd.to_datetime(df.index, utc=True)
    s.index = idx
    return s


def compute_kpis_from_json(
    df24: pd.DataFrame,
    metrics: Dict[str, Dict],   # output of load_metrics_map(...)[ship]
) -> KPIResult:
    """
    Compute KPIs strictly from JSON-defined signals.
    """
    df = df24.copy()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    # ----- Navigation -----
    sog_meta = metrics.get("Avg Speed (SOG)") or metrics.get("Avg Speed")
    sog = _get_series(df, sog_meta["Signal"]) if sog_meta else None
    avg_sog = float(sog.mean()) if sog is not None else None
    max_sog = float(sog.max()) if sog is not None else None
    distance_nm = float(_integrate_rate(sog)) if sog is not None else None  # kn * h -> nm

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
        val = compute_metric(df, meta["Signal"], meta.get("Method", "Sum"))
        if val is None or (isinstance(val, float) and np.isnan(val)):
            continue
        fuel_by_signal[key] = float(val)

    if "Total Fuel Consumption (LNG eq.)" in fuel_by_signal:
        fuel_total_kg = fuel_by_signal["Total Fuel Consumption (LNG eq.)"]
    else:
        fuel_total_kg = float(sum(fuel_by_signal.values())) if fuel_by_signal else None

    fuel_per_nm = (fuel_total_kg / distance_nm) if (fuel_total_kg and distance_nm and distance_nm > 0) else None

    # ----- Electrical -----
    cons_meta = metrics.get("Total Electricity Consumption")
    prod_meta = metrics.get("Total Electricity Production")

    energy_kwh_total = compute_metric(df, cons_meta["Signal"], cons_meta.get("Method", "Sum")) if cons_meta else None
    energy_kwh_prod  = compute_metric(df, prod_meta["Signal"],  prod_meta.get("Method", "Sum")) if prod_meta else None
    energy_kwh_net   = (
        (energy_kwh_total - energy_kwh_prod)
        if (energy_kwh_total is not None and energy_kwh_prod is not None)
        else None
    )

    # Peak demand
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

    peak_kw = None
    peak_time = None
    if total_power is not None and not total_power.empty:
        peak_time = total_power.idxmax()
        peak_kw = float(total_power.loc[peak_time])

    # Top electricity consumers
    energy_top: List[Tuple[str, float]] = []
    for key in peak_components:
        meta = metrics.get(key)
        if not meta:
            continue
        s = _get_series(df, meta["Signal"])
        if s is None:
            continue
        kwh = _integrate_rate(s)
        energy_top.append((key, float(kwh)))
    energy_top.sort(key=lambda x: -x[1])
    energy_top = energy_top[:5]
    # ----- WHR (Waste Heat Recovery) -----
    whr_total_prod = None
    whr_total_cons = None
    whr_util_rate  = None
    whr_losses: Dict[str, float] = {}
    whr_consumers: Dict[str, float] = {}

    # Total production
    if "Total WHR Production" in metrics:
        m = metrics["Total WHR Production"]
        whr_total_prod = compute_metric(df, m["Signal"], m["Method"])

    # Total consumption
    if "Total WHR Consumption" in metrics:
        m = metrics["Total WHR Consumption"]
        whr_total_cons = compute_metric(df, m["Signal"], m["Method"])

    # Utilization rate (%)
    if "WHR Utilization Rate" in metrics:
        m = metrics["WHR Utilization Rate"]
        whr_util_rate = compute_metric(df, m["Signal"], m["Method"])

    # Losses
    for loss in ["Total WHR Losses (HT Dump)", "Total WHR Losses (Steam Dump)"]:
        if loss in metrics:
            m = metrics[loss]
            val = compute_metric(df, m["Signal"], m["Method"])
            if val is not None:
                whr_losses[loss] = val

    # Consumers
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
            val = compute_metric(df, m["Signal"], m["Method"])
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
    # ----- targered signals -----
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
            val = compute_metric(df, m["Signal"], m["Method"])
            if val is not None:
                targeted_values[attr] = val
    # ----- Wind data -----
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
        chw_delta_t=None,
        cop_proxy=None,
        engine_stats=engine_stats,
        whr_total_prod=whr_total_prod,
        whr_total_cons=whr_total_cons,
        whr_util_rate=whr_util_rate,
        whr_losses=whr_losses,
        whr_consumers=whr_consumers,
        **targeted_values,
        **wind_values,
    )


# ========================== Baselines & report ==========================
def daily_baselines(
    df7d: pd.DataFrame,
    metrics: Dict[str, Dict],
    exclude_today: bool = True
) -> Dict[str, float]:
    if df7d.empty:
        return {}
    today = pd.Timestamp.utcnow().date()
    results: List[KPIResult] = []
    for day, g in df7d.groupby(df7d.index.date):
        if exclude_today and day == today:
            continue
        results.append(compute_kpis_from_json(g, metrics))
    if not results:
        return {}

    def _med(values: List[Optional[float]]) -> Optional[float]:
        xs = [v for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))]
        return float(np.median(xs)) if xs else None

    baseline = {
        "fuel_total_kg_med": _med([k.fuel_total_kg for k in results]),
        "energy_kwh_total_med": _med([k.energy_kwh_total for k in results]),
        "distance_nm_med": _med([k.distance_nm for k in results]),
        "fuel_per_nm_med": _med([k.fuel_per_nm for k in results]),
        "peak_kw_med": _med([k.peak_kw for k in results]),
        "energy_kwh_prod_med": _med([k.energy_kwh_prod for k in results]),
        "energy_kwh_net_med": _med([k.energy_kwh_net for k in results]),
        "energy_kwh_net_med": _med([k.energy_kwh_net for k in results]),
        "whr_total_prod_med": _med([k.whr_total_prod for k in results]),
        "whr_total_cons_med": _med([k.whr_total_cons for k in results]),
        "whr_util_rate_med":  _med([k.whr_util_rate for k in results]),
    }

    # ---- Engine loads baseline ----
    engine_names = set()
    for r in results:
        for e in r.engine_stats or []:
            engine_names.add(e["name"])

    for name in engine_names:
        baseline[f"{name}_med"] = _med([
            next((e["avg_load"] for e in r.engine_stats if e["name"] == name), None)
            for r in results
        ])

    return baseline
