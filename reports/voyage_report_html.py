# reports/voyage_report_html.py
from datetime import datetime
from core.kpis import KPIResult

def render_voyage_html_report(k: KPIResult, ship_name: str = "ICON-1") -> str:
    """
    Render a voyage report in dark theme (like daily report).
    Input: KPIResult (with voyage_from, voyage_to, voyage_start, voyage_end, voyage_duration_hours)
    """
    start_str = k.voyage_start.strftime("%Y-%m-%d %H:%M")
    end_str = k.voyage_end.strftime("%Y-%m-%d %H:%M")

    html = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #1e1e2f;
                color: #f1f1f1;
                padding: 20px;
            }}
            h1 {{ color: #4fc3f7; text-align: center; }}
            h2 {{ color: #ffca28; }}
            .section {{
                background: #2a2a40;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0px 4px 8px rgba(0,0,0,0.3);
            }}
            .card {{
                display: inline-block;
                width: 28%;
                margin: 1%;
                padding: 15px;
                background: #33334d;
                border-radius: 10px;
                text-align: center;
            }}
            .metric-value {{
                font-size: 22px;
                font-weight: bold;
                color: #4fc3f7;
            }}
            ul {{ margin: 0; padding-left: 20px; }}
        </style>
    </head>
    <body>
        <h1>🚢 Voyage Report: {k.voyage_from} → {k.voyage_to}</h1>

        <div class="section">
            <h2>Voyage Info</h2>
            <p><b>Ship:</b> {ship_name}</p>
            <p><b>From:</b> {k.voyage_from}</p>
            <p><b>To:</b> {k.voyage_to}</p>
            <p><b>Start:</b> {start_str}</p>
            <p><b>End:</b> {end_str}</p>
            <p><b>Duration:</b> {k.voyage_duration_hours:.2f} hours</p>
        </div>

        <div class="section">
            <h2>Navigation</h2>
            <div class="card"><p>Distance (nm)</p><p class="metric-value">{_fmt(k.distance_nm)}</p></div>
            <div class="card"><p>Avg SOG (kn)</p><p class="metric-value">{_fmt(k.avg_sog)}</p></div>
            <div class="card"><p>Max SOG (kn)</p><p class="metric-value">{_fmt(k.max_sog)}</p></div>
        </div>

        <div class="section">
            <h2>Fuel</h2>
            <div class="card"><p>Total Fuel (kg)</p><p class="metric-value">{_fmt(k.fuel_total_kg)}</p></div>
            <div class="card"><p>Fuel per nm (kg/nm)</p><p class="metric-value">{_fmt(k.fuel_per_nm, 2)}</p></div>
            <h3>Fuel Breakdown</h3>
            <ul>
                {"".join([f"<li>{name}: {val:.1f} kg</li>" for name,val in (k.fuel_by_signal or {}).items()])}
            </ul>
        </div>

        <div class="section">
            <h2>Electrical</h2>
            <div class="card"><p>Total Consumed (kWh)</p><p class="metric-value">{_fmt(k.energy_kwh_total)}</p></div>
            <div class="card"><p>Total Produced (kWh)</p><p class="metric-value">{_fmt(k.energy_kwh_prod)}</p></div>
            <div class="card"><p>Net (kWh)</p><p class="metric-value">{_fmt(k.energy_kwh_net)}</p></div>
            <div class="card"><p>Peak Demand (kW)</p><p class="metric-value">{_fmt(k.peak_kw)}</p></div>
            <p><b>Peak Time:</b> {k.peak_time if k.peak_time else "-"}</p>
            <h3>Top Consumers</h3>
            <ul>
                {"".join([f"<li>{name}: {val:.1f} kWh</li>" for name,val in (k.energy_top or [])])}
            </ul>
        </div>

        <div class="section">
            <h2>Waste Heat Recovery (WHR)</h2>
            <div class="card"><p>Total Prod (kWh)</p><p class="metric-value">{_fmt(k.whr_total_prod)}</p></div>
            <div class="card"><p>Total Cons (kWh)</p><p class="metric-value">{_fmt(k.whr_total_cons)}</p></div>
            <div class="card"><p>Util Rate (%)</p><p class="metric-value">{_fmt(k.whr_util_rate, 1)}</p></div>
            <h3>Losses</h3>
            <ul>
                {"".join([f"<li>{name}: {val:.1f}</li>" for name,val in (k.whr_losses or {}).items()])}
            </ul>
            <h3>Consumers</h3>
            <ul>
                {"".join([f"<li>{name}: {val:.1f}</li>" for name,val in (k.whr_consumers or {}).items()])}
            </ul>
        </div>

        <div class="section">
            <h2>Engine Loads</h2>
            <ul>
                {"".join([f"<li>{e['name']}: {e['avg_load']:.1f}%</li>" for e in (k.engine_stats or [])])}
            </ul>
        </div>

        <div class="section">
            <h2>AI Insights</h2>
            <p>{k.ai_suggestions if k.ai_suggestions else "⚡ No AI insights available"}</p>
        </div>

        <p style="color:gray; font-size:12px;">Generated on {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
    </body>
    </html>
    """
    return html


def _fmt(val, digits=1):
    """Format float values with safe fallback"""
    if val is None:
        return "-"
    try:
        return f"{val:.{digits}f}"
    except Exception:
        return str(val)
