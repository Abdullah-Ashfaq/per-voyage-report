# reports/voyage_report_html.py
from jinja2 import Template
from types import SimpleNamespace

def render_voyage_html_report(kpi_result, ship_name: str) -> str:
    # Ensure object-style access
    if isinstance(kpi_result, dict):
        kpi_result = SimpleNamespace(**kpi_result)

    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Voyage Report - {{ ship_name }}</title>
<style>
    body {
        font-family: 'Segoe UI', Tahoma, sans-serif;
        background-color: #f5f7fa;
        color: #222;
        margin: 0; padding: 0;
    }
    .header {
        background-color: #002b5b;
        color: white;
        padding: 16px 30px;
    }
    .header h1 {
        margin: 0;
        font-size: 22px;
    }
    .header .subtitle {
        font-size: 14px;
        color: #b0d0ff;
    }
    .container {
        padding: 20px 40px;
    }
    .section {
        background: white;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        padding: 20px;
    }
    .section h2 {
        margin-top: 0;
        border-bottom: 2px solid #004b8d;
        padding-bottom: 6px;
        font-size: 18px;
        color: #004b8d;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }
    th, td {
        text-align: left;
        padding: 8px 10px;
        border-bottom: 1px solid #eee;
    }
    th {
        background-color: #004b8d;
        color: white;
        font-size: 13px;
    }
    tr:hover {
        background-color: #f0f6ff;
    }
    .metric-name { width: 60%; }
    .metric-value { text-align: right; font-weight: 600; }
    .footer {
        text-align: center;
        color: #666;
        font-size: 12px;
        padding: 10px;
        margin-top: 40px;
    }
</style>
</head>
<body>
<div class="header">
    <h1>Voyage Report - {{ ship_name }}</h1>
    <div class="subtitle">{{ kpi.port_from }} → {{ kpi.port_to }}</div>
</div>

<div class="container">

    <div class="section">
        <h2>Voyage Summary</h2>
        <table>
            <tr><th>Parameter</th><th>Value</th></tr>
            <tr><td>From</td><td>{{ kpi.port_from }}</td></tr>
            <tr><td>To</td><td>{{ kpi.port_to }}</td></tr>
            <tr><td>Start</td><td>{{ kpi.voyage_start }}</td></tr>
            <tr><td>End</td><td>{{ kpi.voyage_end }}</td></tr>
            <tr><td>Duration</td><td>{{ kpi.voyage_duration_hours|round(2) }} h</td></tr>
            <tr><td>Distance</td><td>{{ kpi.distance_nm|round(2) }} NM</td></tr>
            <tr><td>Average Speed</td><td>{{ kpi.avg_sog_kn|round(2) }} kn</td></tr>
            <tr><td>Max Speed</td><td>{{ kpi.max_sog_kn|round(2) }} kn</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Fuel & Energy KPIs</h2>
        <table>
            <tr><th class="metric-name">Metric</th><th>Value</th></tr>
            <tr><td>Total Fuel Used</td><td>{{ kpi.fuel_total_tonnes|round(2) }} tonnes</td></tr>
            <tr><td>Fuel per Nautical Mile</td><td>{{ kpi.fuel_tonnes_per_nm|round(2) }} t/NM</td></tr>
            <tr><td>Electricity Produced</td><td>{{ kpi.energy_mwh_prod|round(2) }} MWh</td></tr>
            <tr><td>Electricity Consumed</td><td>{{ kpi.energy_mwh_total|round(2) }} MWh</td></tr>
            <tr><td>Net Energy</td><td>{{ kpi.energy_mwh_net|round(2) }} MWh</td></tr>
            <tr><td>Peak Power</td><td>{{ kpi.peak_kw|round(2) }} kW at {{ kpi.peak_time }}</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Waste Heat Recovery (WHR)</h2>
        <table>
            <tr><th>Parameter</th><th>Value</th></tr>
            <tr><td>WHR Produced</td><td>{{ kpi.whr_total_prod_mwh or 'N/A' }}</td></tr>
            <tr><td>WHR Consumed</td><td>{{ kpi.whr_total_cons_mwh or 'N/A' }}</td></tr>
            <tr><td>Utilization Rate</td><td>{{ kpi.whr_util_rate_percent|round(2) }} %</td></tr>
            <tr><td>Losses (Steam Dump)</td><td>{{ kpi.whr_loss_Total_WHR_Losses_Steam_Dump_mwh or 'N/A' }}</td></tr>
            <tr><td>Losses (HT Dump)</td><td>{{ kpi.whr_loss_Total_WHR_Losses_HT_Dump_mwh or 'N/A' }}</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Environmental Conditions</h2>
        <table>
            <tr><th>Parameter</th><th>Value</th></tr>
            <tr><td>Relative Wind Speed</td><td>{{ kpi.relative_wind_speed_kn|round(2) }} kn</td></tr>
            <tr><td>True North Wind Speed</td><td>{{ kpi.true_north_wind_speed_kn|round(2) }} kn</td></tr>
            <tr><td>Relative Wind Direction</td><td>{{ kpi.relative_wind_direction_deg|round(1) }}°</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Target Comparison</h2>
        <table>
            <tr><th>Target KPI</th><th>Actual</th><th>Target</th></tr>
            <tr><td>Fuel (Tonnes)</td><td>{{ kpi.fuel_total_tonnes|round(2) }}</td><td>{{ kpi.target_fuel_tonnes|round(2) }}</td></tr>
            <tr><td>LNG (Tonnes)</td><td>{{ kpi.fuel_by_signal_Total_LNG_Consumption_tonnes|round(2) }}</td><td>{{ kpi.target_lng_tonnes|round(2) }}</td></tr>
            <tr><td>Electricity (MWh)</td><td>{{ kpi.energy_mwh_total|round(2) }}</td><td>{{ kpi.target_electricity_mwh|round(2) }}</td></tr>
            <tr><td>WHR (MWh)</td><td>{{ kpi.whr_total_cons_mwh|round(2) }}</td><td>{{ kpi.target_whr_mwh|round(2) }}</td></tr>
        </table>
    </div>

    {% if kpi.ai_suggestions %}
    <div class="section">
        <h2>AI Insights</h2>
        <p>{{ kpi.ai_suggestions|safe }}</p>
    </div>
    {% endif %}

</div>

<div class="footer">
    Generated automatically by Voyage KPI System | © 2025
</div>
</body>
</html>
"""
    template = Template(html_template)
    return template.render(kpi=kpi_result, ship_name=ship_name)
