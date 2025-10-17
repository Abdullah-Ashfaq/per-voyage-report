# reports/voyage_report_html.py
from types import SimpleNamespace
from jinja2 import Template
import math

# ---------------------------- Helpers ----------------------------

def _is_bad(v):
    return v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))

def _fmt(v, unit="", nd=2):
    if _is_bad(v):
        return "N/A"
    if isinstance(v, (int, float)):
        s = f"{round(v, nd)}"
    else:
        s = str(v)
    return f"{s}{(' ' + unit) if unit else ''}"

def _pct_diff(cur, ref):
    """Return (text, color_class) using ↑/↓/→ and green/red/gray based on sign."""
    if _is_bad(cur) or _is_bad(ref) or ref == 0:
        return "—", "gray"
    diff = (cur - ref) / ref * 100.0
    if diff > 0:
        return f"↑ {round(diff,2)}%", "red"
    elif diff < 0:
        return f"↓ {round(abs(diff),2)}%", "green"
    else:
        return "→ 0%", "gray"

def _svg_pie_slices(values, colors, cx=120, cy=120, r=100):
    """
    Build pure-SVG pie slices (no JS). values: list of floats; colors: same length.
    Returns the SVG <path> markup string.
    """
    total = sum([v for v in values if not _is_bad(v)]) or 1.0
    # Start from -90° (12 o'clock)
    angle = -math.pi / 2
    parts = []
    for idx, v in enumerate(values):
        val = 0 if _is_bad(v) else float(v)
        sweep = (val / total) * 2 * math.pi
        # Compute start and end points
        x1 = cx + r * math.cos(angle)
        y1 = cy + r * math.sin(angle)
        angle2 = angle + sweep
        x2 = cx + r * math.cos(angle2)
        y2 = cy + r * math.sin(angle2)
        # Large arc flag
        large_arc = 1 if sweep > math.pi else 0
        # Path from center -> arc -> back to center (pie slice)
        d = f"M {cx} {cy} L {x1:.3f} {y1:.3f} A {r} {r} 0 {large_arc} 1 {x2:.3f} {y2:.3f} Z"
        parts.append(f'<path d="{d}" fill="{colors[idx]}" stroke="none"></path>')
        angle = angle2
    return "\n".join(parts)

def _engine_svg_pie(kpi):
    # Fixed colors per engine (consistent across voyages)
    colors = ["#60a5fa", "#34d399", "#f87171", "#fbbf24", "#a78bfa", "#4ade80"]
    values = []
    labels = []
    for i in range(1, 7):
        key = f"Avg_ME_{i}_Load_avg_load_percent"
        v = getattr(kpi, key, None)
        v = 0.0 if _is_bad(v) else float(v)
        values.append(v)
        labels.append(f"ME {i}")
    # If all zeros, make a single placeholder slice
    if sum(values) <= 0:
        values = [1]
        colors = ["#2a2f47"]
        labels = ["No data"]
    slices = _svg_pie_slices(values, colors)
    svg = f'''
<svg class="pie-svg" width="240" height="240" viewBox="0 0 240 240" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Engine Load Pie">
  <defs>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="1" stdDeviation="2" flood-opacity="0.25"/>
    </filter>
  </defs>
  <g filter="url(#shadow)">
    {slices}
  </g>
</svg>
'''
    # Legend rows with percent labels
    legend_rows = []
    # Normalize to show % even if total=0
    total = sum(values) or 1.0
    for i, v in enumerate(values):
        pct = (v / total) * 100.0
        name = labels[i] if i < len(labels) else f"ME {i+1}"
        col = colors[i] if i < len(colors) else "#7aa2ff"
        legend_rows.append(
            f'<tr><td><span class="legend-dot" style="background:{col}"></span>{name}</td><td class="right">{round(pct,1)}%</td></tr>'
        )
    legend = f'''
<table class="kv tight">
  <tr><th>Engine</th><th class="right">Share</th></tr>
  {''.join(legend_rows)}
</table>
'''
    return svg, legend

# ---------------------------- Renderer ----------------------------

def render_voyage_html_report(kpi_result, ship_name: str, baseline_data: dict | None = None) -> str:
    """Return a full dark-themed HTML string for the voyage report (no JS, inline SVG pie)."""
    # Object-style access
    if isinstance(kpi_result, dict):
        kpi = SimpleNamespace(**kpi_result)
    else:
        kpi = kpi_result

    baseline = SimpleNamespace(**baseline_data) if isinstance(baseline_data, dict) else None

    # Comparison rows (Actual | Baseline | Δ vs Baseline | Target | Δ vs Target)
    cmp_rows = [
        ("Max SOG (kn)",        getattr(kpi, "max_sog_kn", None),        getattr(baseline, "max_sog_kn", None) if baseline else None,        None),
        ("Avg SOG (kn)",        getattr(kpi, "avg_sog_kn", None),        getattr(baseline, "avg_sog_kn", None) if baseline else None,        None),
        ("Total Fuel (t)",      getattr(kpi, "fuel_total_tonnes", None), getattr(baseline, "fuel_total_tonnes", None) if baseline else None, getattr(kpi, "target_fuel_tonnes", None)),
        ("LNG (t)",             getattr(kpi, "fuel_by_signal_Total_LNG_Consumption_tonnes", None),
                                 getattr(baseline, "fuel_by_signal_Total_LNG_Consumption_tonnes", None) if baseline else None,
                                 getattr(kpi, "target_lng_tonnes", None)),
        ("Electricity Used (MWh)", getattr(kpi, "energy_mwh_total", None),
                                   getattr(baseline, "energy_mwh_total", None) if baseline else None,
                                   getattr(kpi, "target_electricity_mwh", None)),
        ("Electricity Produced (MWh)", getattr(kpi, "energy_mwh_prod", None),
                                       getattr(baseline, "energy_mwh_prod", None) if baseline else None,
                                       None),
        ("Net Energy (MWh)",    getattr(kpi, "energy_mwh_net", None),    getattr(baseline, "energy_mwh_net", None) if baseline else None,    None),
        ("WHR Consumed (MWh)",  getattr(kpi, "whr_total_cons_mwh", None),
                                 getattr(baseline, "whr_total_cons_mwh", None) if baseline else None,
                                 getattr(kpi, "target_whr_mwh", None)),
        ("WHR Utilization (%)", getattr(kpi, "whr_util_rate_percent", None),
                                 getattr(baseline, "whr_util_rate_percent", None) if baseline else None,
                                 None),
        ("Peak Load (kW)",      getattr(kpi, "peak_kw", None),           getattr(baseline, "peak_kw", None) if baseline else None,           None),
    ]

    cmp_prepared = []
    for name, actual, base, target in cmp_rows:
        delta_base_txt, delta_base_cls = _pct_diff(actual, base) if baseline else ("—", "gray")
        delta_tgt_txt,  delta_tgt_cls  = _pct_diff(actual, target) if not _is_bad(target) else ("—", "gray")
        cmp_prepared.append({
            "name": name,
            "actual": _fmt(actual),
            "baseline": _fmt(base),
            "delta_base_txt": delta_base_txt,
            "delta_base_cls": delta_base_cls,
            "target": _fmt(target),
            "delta_tgt_txt": delta_tgt_txt,
            "delta_tgt_cls": delta_tgt_cls
        })

    # Engine SVG + Legend
    engine_svg, engine_legend = _engine_svg_pie(kpi)

    # Inline icons
    ICONS = {
        "summary": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none"
            xmlns="http://www.w3.org/2000/svg"><path d="M3 6h18M3 12h18M3 18h18"
            stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>""",
        "fuel": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none"
            xmlns="http://www.w3.org/2000/svg"><path d="M3 7a2 2 0 012-2h6a2 2 0 012 2v12H3V7z"
            stroke="currentColor" stroke-width="2"/><path d="M15 9l3 3v7a2 2 0 002 2h1"
            stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>""",
        "whr": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none"
            xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="9"
            stroke="currentColor" stroke-width="2"/><path d="M8 12h8M12 8v8"
            stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>""",
        "wind": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none"
            xmlns="http://www.w3.org/2000/svg"><path d="M3 12h13a3 3 0 100-6M3 18h9a3 3 0 110 6"
            transform="translate(0,-6)" stroke="currentColor" stroke-width="2"
            stroke-linecap="round"/></svg>""",
        "compare": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none"
            xmlns="http://www.w3.org/2000/svg"><path d="M4 4h6v16H4zM14 8h6v12h-6z"
            stroke="currentColor" stroke-width="2"/></svg>""",
        "engine": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none"
            xmlns="http://www.w3.org/2000/svg"><path d="M3 10h8l2-3h6v8h-6l-2-3H3z"
            stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>""",
        "target": """<svg width="20" height="20" viewBox="0 0 24 24" fill="none"
            xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="9"
            stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="4"
            stroke="currentColor" stroke-width="2"/></svg>""",
    }

    def card(title, icon_key, inner_html):
        return f"""
        <section class="card">
          <header class="card-head">
            <span class="icon">{ICONS.get(icon_key,'')}</span>
            <h2>{title}</h2>
          </header>
          <div class="card-body">
            {inner_html}
          </div>
        </section>
        """

    # Tables/sections
    summary_tbl = f"""
      <table class="kv">
        <tr><td>From</td><td>{_fmt(getattr(kpi,'port_from',None))}</td></tr>
        <tr><td>To</td><td>{_fmt(getattr(kpi,'port_to',None))}</td></tr>
        <tr><td>Start</td><td>{_fmt(getattr(kpi,'voyage_start',None))}</td></tr>
        <tr><td>End</td><td>{_fmt(getattr(kpi,'voyage_end',None))}</td></tr>
        <tr><td>Duration</td><td>{_fmt(getattr(kpi,'voyage_duration_hours',None),'h')}</td></tr>
        <tr><td>Distance</td><td>{_fmt(getattr(kpi,'distance_nm',None),'NM')}</td></tr>
        <tr><td>Average SOG</td><td>{_fmt(getattr(kpi,'avg_sog_kn',None),'kn')}</td></tr>
        <tr><td>Max SOG</td><td>{_fmt(getattr(kpi,'max_sog_kn',None),'kn')}</td></tr>
      </table>
    """

    fuel_energy_tbl = f"""
      <table class="kv">
        <tr><td>Total Fuel (LNG eq.)</td><td>{_fmt(getattr(kpi,'fuel_total_tonnes',None),'t')}</td></tr>
        <tr><td>Fuel / NM</td><td>{_fmt(getattr(kpi,'fuel_tonnes_per_nm',None),'t/NM')}</td></tr>
        <tr><td>LNG</td><td>{_fmt(getattr(kpi,'fuel_by_signal_Total_LNG_Consumption_tonnes',None),'t')}</td></tr>
        <tr><td>MGO</td><td>{_fmt(getattr(kpi,'fuel_by_signal_Total_MGO_Consumption_tonnes',None),'t')}</td></tr>
        <tr><td>Aux Boiler Fuel</td><td>{_fmt(getattr(kpi,'fuel_by_signal_Total_Auxiliary_Boiler_Fuel_Consumption_tonnes',None),'t')}</td></tr>
        <tr><td>Energy Produced</td><td>{_fmt(getattr(kpi,'energy_mwh_prod',None),'MWh')}</td></tr>
        <tr><td>Energy Used</td><td>{_fmt(getattr(kpi,'energy_mwh_total',None),'MWh')}</td></tr>
        <tr><td>Net Energy</td><td>{_fmt(getattr(kpi,'energy_mwh_net',None),'MWh')}</td></tr>
        <tr><td>Peak Load</td><td>{_fmt(getattr(kpi,'peak_kw',None),'kW')} at {_fmt(getattr(kpi,'peak_time',None))}</td></tr>
      </table>
    """

    whr_tbl = f"""
      <table class="kv">
        <tr><td>WHR Produced</td><td>{_fmt(getattr(kpi,'whr_total_prod_mwh',None),'MWh')}</td></tr>
        <tr><td>WHR Consumed</td><td>{_fmt(getattr(kpi,'whr_total_cons_mwh',None),'MWh')}</td></tr>
        <tr><td>Utilization</td><td>{_fmt(getattr(kpi,'whr_util_rate_percent',None),'%')}</td></tr>
        <tr><td>Losses – HT Dump</td><td>{_fmt(getattr(kpi,'whr_loss_Total_WHR_Losses_HT_Dump_mwh',None),'MWh')}</td></tr>
        <tr><td>Losses – Steam Dump</td><td>{_fmt(getattr(kpi,'whr_loss_Total_WHR_Losses_Steam_Dump_mwh',None),'MWh')}</td></tr>
      </table>
      <h4>Consumers</h4>
      <table class="kv">
        <tr><td>Condensate Heater</td><td>{_fmt(getattr(kpi,'whr_consumer_WHR_Condensate_Heater_mwh',None),'MWh')}</td></tr>
        <tr><td>Evaporators</td><td>{_fmt(getattr(kpi,'whr_consumer_WHR_Evaporators_mwh',None),'MWh')}</td></tr>
        <tr><td>Laundry</td><td>{_fmt(getattr(kpi,'whr_consumer_WHR_Laundry_mwh',None),'MWh')}</td></tr>
        <tr><td>Potable Water Heating</td><td>{_fmt(getattr(kpi,'whr_consumer_WHR_Potable_Water_Heating_mwh',None),'MWh')}</td></tr>
        <tr><td>AC Reheating</td><td>{_fmt(getattr(kpi,'whr_consumer_WHR_AC_Reheating_mwh',None),'MWh')}</td></tr>
        <tr><td>Absorption Chiller</td><td>{_fmt(getattr(kpi,'whr_consumer_WHR_Absorption_Chiller_mwh',None),'MWh')}</td></tr>
        <tr><td>Other Uses</td><td>{_fmt(getattr(kpi,'whr_consumer_WHR_Other_Uses_mwh',None),'MWh')}</td></tr>
      </table>
    """

    wind_tbl = f"""
      <table class="kv">
        <tr><td>Relative Wind Speed</td><td>{_fmt(getattr(kpi,'relative_wind_speed_kn',None),'kn')}</td></tr>
        <tr><td>True North Wind Speed</td><td>{_fmt(getattr(kpi,'true_north_wind_speed_kn',None),'kn')}</td></tr>
        <tr><td>Relative Wind Direction</td><td>{_fmt(getattr(kpi,'relative_wind_direction_deg',None),'°')}</td></tr>
      </table>
    """

    # Unified comparison table (Actual | Baseline | Δ vs Baseline | Target | Δ vs Target)
    comparison_tbl = """
      <table class="kv compare">
        <tr>
          <th>KPI</th>
          <th>Actual</th>
          <th>Baseline</th>
          <th>Δ vs Baseline</th>
          <th>Target</th>
          <th>Δ vs Target</th>
        </tr>
        {% for row in cmp %}
        <tr>
          <td>{{ row.name }}</td>
          <td>{{ row.actual }}</td>
          <td>{{ row.baseline }}</td>
          <td class="delta"><span class="arrow {{ row.delta_base_cls }}">{{ row.delta_base_txt }}</span></td>
          <td>{{ row.target }}</td>
          <td class="delta"><span class="arrow {{ row.delta_tgt_cls }}">{{ row.delta_tgt_txt }}</span></td>
        </tr>
        {% endfor %}
      </table>
    """

    # Baseline raw values table (dedicated card)
    baseline_tbl = ""
    if baseline:
        baseline_tbl = f"""
        <table class="kv">
          <tr><th>KPI</th><th class="right">Baseline</th></tr>
          <tr><td>Duration</td><td class="right">{_fmt(getattr(baseline,'voyage_duration_hours',None),'h')}</td></tr>
          <tr><td>Distance</td><td class="right">{_fmt(getattr(baseline,'distance_nm',None),'NM')}</td></tr>
          <tr><td>Avg SOG</td><td class="right">{_fmt(getattr(baseline,'avg_sog_kn',None),'kn')}</td></tr>
          <tr><td>Max SOG</td><td class="right">{_fmt(getattr(baseline,'max_sog_kn',None),'kn')}</td></tr>
          <tr><td>Total Fuel</td><td class="right">{_fmt(getattr(baseline,'fuel_total_tonnes',None),'t')}</td></tr>
          <tr><td>LNG</td><td class="right">{_fmt(getattr(baseline,'fuel_by_signal_Total_LNG_Consumption_tonnes',None),'t')}</td></tr>
          <tr><td>MGO</td><td class="right">{_fmt(getattr(baseline,'fuel_by_signal_Total_MGO_Consumption_tonnes',None),'t')}</td></tr>
          <tr><td>Aux Boiler Fuel</td><td class="right">{_fmt(getattr(baseline,'fuel_by_signal_Total_Auxiliary_Boiler_Fuel_Consumption_tonnes',None),'t')}</td></tr>
          <tr><td>Energy Used</td><td class="right">{_fmt(getattr(baseline,'energy_mwh_total',None),'MWh')}</td></tr>
          <tr><td>Energy Produced</td><td class="right">{_fmt(getattr(baseline,'energy_mwh_prod',None),'MWh')}</td></tr>
          <tr><td>Net Energy</td><td class="right">{_fmt(getattr(baseline,'energy_mwh_net',None),'MWh')}</td></tr>
          <tr><td>Peak Load</td><td class="right">{_fmt(getattr(baseline,'peak_kw',None),'kW')}</td></tr>
          <tr><td>WHR Consumed</td><td class="right">{_fmt(getattr(baseline,'whr_total_cons_mwh',None),'MWh')}</td></tr>
          <tr><td>WHR Utilization</td><td class="right">{_fmt(getattr(baseline,'whr_util_rate_percent',None),'%')}</td></tr>
          <tr><td>Losses HT Dump</td><td class="right">{_fmt(getattr(baseline,'whr_loss_Total_WHR_Losses_HT_Dump_mwh',None),'MWh')}</td></tr>
          <tr><td>Losses Steam Dump</td><td class="right">{_fmt(getattr(baseline,'whr_loss_Total_WHR_Losses_Steam_Dump_mwh',None),'MWh')}</td></tr>
          <tr><td>Wind Rel Speed</td><td class="right">{_fmt(getattr(baseline,'relative_wind_speed_kn',None),'kn')}</td></tr>
          <tr><td>Wind Rel Dir</td><td class="right">{_fmt(getattr(baseline,'relative_wind_direction_deg',None),'°')}</td></tr>
          <tr><td>True N Wind</td><td class="right">{_fmt(getattr(baseline,'true_north_wind_speed_kn',None),'kn')}</td></tr>
        </table>
        """

    engine_card = f"""
      <div class="engine-flex">
        {engine_svg}
        {engine_legend}
      </div>
    """

    ai_html = ""
    if getattr(kpi, "ai_suggestions", None):
        ai_html = f"""<div class="ai-box">{kpi.ai_suggestions}</div>"""

    # ---------------------------- HTML Template ----------------------------
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Voyage Report – {ship_name}</title>
<style>
:root {{
  --bg: #0f1220;
  --panel: #181b2e;
  --panel-2: #1e2237;
  --text: #e6e8f2;
  --muted: #9aa3b2;
  --brand: #7aa2ff;
  --accent: #6ee7b7;
  --border: #2a2f47;
  --chip: #0c0f1a;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, 'Segoe UI', Tahoma, sans-serif;
  background: radial-gradient(1200px 600px at 20% -10%, #1b2240 0%, var(--bg) 50%) no-repeat, var(--bg);
  color: var(--text);
}}
.header {{
  padding: 24px 28px;
  background: linear-gradient(90deg, rgba(122,162,255,0.12), rgba(110,231,183,0.08));
  border-bottom: 1px solid var(--border);
  # position: fixed; top: 0; z-index: 10;
  text-align: center; /* centered header content */
}}
.header h1 {{
  margin: 0 0 6px 0;
  font-size: 20px;
  letter-spacing: 0.3px;
}}
.header .sub {{
  color: var(--muted);
  font-size: 13px;
}}
.container {{
  padding: 22px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 18px;
  max-width: 1280px;
  margin: 0 auto;
}}
.card {{
  background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.25);
  overflow: hidden;
}}
.card-head {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
  background: rgba(122,162,255,0.06);
}}
.card-head .icon svg {{ color: var(--brand); }}
.card-head h2 {{
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: .2px;
}}
.card-body {{
  padding: 14px 16px 18px;
}}
.kv {{
  width: 100%;
  border-collapse: collapse;
}}
.kv tr td, .kv tr th {{
  border-bottom: 1px dashed var(--border);
  padding: 8px 6px;
  font-size: 13px;
}}
.kv tr th {{
  color: var(--muted);
  text-align: left;
}}
.kv tr td:first-child {{
  color: var(--muted);
}}
.kv tr td:last-child, .kv tr th:last-child {{
  text-align: right;
}}
.kv.tight tr td {{ padding: 6px 4px; font-size: 12.5px; }}
.kv.tight tr th {{ padding: 6px 4px; font-size: 12.5px; color: var(--muted); text-align:left; }}
h4 {{ margin: 12px 0 8px; font-size: 13px; color: var(--brand); }}
.engine-flex {{
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  align-items: center;
  justify-items: center;
}}
.pie-svg {{
  width: 240px; height: 240px; background: var(--chip); border-radius: 12px; border: 1px solid var(--border);
}}
.legend-dot {{
  display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:8px; vertical-align:middle;
}}
.arrow {{
  font-size: 13px;
  padding: 2px 6px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--chip);
}}
.arrow.green {{ color: #34d399; }}
.arrow.red {{ color: #f87171; }}
.arrow.gray {{ color: #9aa3b2; }}
.footer {{
  color: var(--muted); font-size: 12px; text-align: center; padding: 20px 10px;
  border-top: 1px solid var(--border); margin-top: 16px;
}}
.badge {{
  display: inline-block; padding: 3px 8px; border-radius: 999px; background: var(--chip); border: 1px solid var(--border);
  color: var(--brand); font-size: 12px;
}}
.ai-box {{
  background: rgba(110,231,183,0.06); border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; color: var(--text);
  box-shadow: inset 0 0 0 1px rgba(110,231,183,0.08);
}}
/* Comparison tweaks */
.kv.compare th:nth-child(2), .kv.compare td:nth-child(2) {{ text-align:right; }}
.kv.compare th:nth-child(3), .kv.compare td:nth-child(3) {{ text-align:right; }}
.kv.compare th:nth-child(5), .kv.compare td:nth-child(5) {{ text-align:right; }}
.kv.compare td.delta {{ text-align:right; }}
.right {{ text-align:right; }}
</style>
</head>
<body>
  <header class="header">
    <h1>Voyage Report – {ship_name}</h1>
    <div class="sub">{{{{ kpi.port_from }}}} → {{{{ kpi.port_to }}}} </div>
  </header>

  <main class="container">
    {card("Voyage Summary", "summary", summary_tbl)}
    {card("Fuel & Energy", "fuel", fuel_energy_tbl)}
    {card("Waste Heat Recovery", "whr", whr_tbl)}
    {card("Environmental", "wind", wind_tbl)}
    {card("Engine Load Distribution", "engine", engine_card)}
    {card("Actual vs Baseline & Target", "compare", comparison_tbl)}
    {card("Baseline (Averages of Last Voyages)", "target", baseline_tbl) if baseline_tbl else ""}
    {card("AI Insights", "whr", ai_html) if ai_html else ""}
  </main>

  <footer class="footer">
    Generated automatically by Voyage KPI System • © 2025
  </footer>
</body>
</html>
"""
    template = Template(html)
    return template.render(kpi=kpi, cmp=cmp_prepared)
