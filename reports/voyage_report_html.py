from jinja2 import Template
from types import SimpleNamespace

def _compare_with_baseline(kpi_value, baseline_value):
    """Compares KPI value to baseline and returns an arrow and percentage difference."""
    if kpi_value is None or baseline_value is None:
        return "", "N/A"

    # Calculate percentage difference
    difference = ((kpi_value - baseline_value) / baseline_value) * 100

    # Determine color and arrow
    if difference > 0:
        return f"↑ {round(difference, 2)}%", "green"
    elif difference < 0:
        return f"↓ {round(abs(difference), 2)}%", "red"
    else:
        return "→ 0%", "gray"

def render_voyage_html_report(kpi_result, ship_name: str, baseline_data: dict = None) -> str:
    # Ensure object-style access
    if isinstance(kpi_result, dict):
        kpi_result = SimpleNamespace(**kpi_result)

    # Prepare comparison with baseline
    baseline_comparison = {}
    if baseline_data:
        # Baseline values to compare
        baseline_comparison["max_sog_kn"] = _compare_with_baseline(kpi_result.max_sog_kn, baseline_data.get('max_sog_kn'))
        baseline_comparison["avg_sog_kn"] = _compare_with_baseline(kpi_result.avg_sog_kn, baseline_data.get('avg_sog_kn'))
        baseline_comparison["fuel_total_tonnes"] = _compare_with_baseline(kpi_result.fuel_total_tonnes, baseline_data.get('fuel_total_tonnes'))
        baseline_comparison["energy_mwh_prod"] = _compare_with_baseline(kpi_result.energy_mwh_prod, baseline_data.get('energy_mwh_prod'))
        baseline_comparison["whr_util_rate_percent"] = _compare_with_baseline(kpi_result.whr_util_rate_percent, baseline_data.get('whr_util_rate_percent'))

    # HTML Template with full sections
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Voyage Report - {{ ship_name }}</title>
<style>
    /* Same styles as before */
    body {
        font-family: 'Segoe UI', Tahoma, sans-serif;
        background-color: #0f1220;
        color: #e6e8f2;
        margin: 0;
        padding: 0;
    }
    .header {
        padding: 24px 28px;
        background: linear-gradient(90deg, rgba(122,162,255,0.12), rgba(110,231,183,0.08));
        border-bottom: 1px solid #2a2f47;
        position: sticky; top: 0; z-index: 10;
    }
    .header h1 {
        margin: 0 0 6px 0;
        font-size: 20px;
        letter-spacing: 0.3px;
    }
    .header .sub {
        color: #9aa3b2;
        font-size: 13px;
    }
    .container {
        padding: 22px;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 18px;
        max-width: 1280px;
        margin: 0 auto;
    }
    .card {
        background: linear-gradient(180deg, #181b2e 0%, #1e2237 100%);
        border: 1px solid #2a2f47;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        overflow: hidden;
    }
    .card-head {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 14px 16px;
        border-bottom: 1px solid #2a2f47;
        background: rgba(122,162,255,0.06);
    }
    .card-head .icon svg { color: #7aa2ff; }
    .card-head h2 {
        margin: 0;
        font-size: 15px;
        font-weight: 600;
        letter-spacing: .2px;
    }
    .card-body {
        padding: 14px 16px 18px;
    }
    .kv {
        width: 100%;
        border-collapse: collapse;
    }
    .kv tr td, .kv tr th {
        border-bottom: 1px dashed #2a2f47;
        padding: 8px 6px;
        font-size: 13px;
    }
    .kv tr td:first-child {
        color: #9aa3b2;
    }
    .kv tr td:last-child, .kv tr th:last-child {
        text-align: right;
    }
    .kv.tight tr td { padding: 6px 4px; font-size: 12.5px; }
    .kv.tight tr th { padding: 6px 4px; font-size: 12.5px; color: #9aa3b2; text-align:left; }
    h4 { margin: 12px 0 8px; font-size: 13px; color: #7aa2ff; }
    .arrow {
        font-size: 18px;
    }
    .arrow.green {
        color: green;
    }
    .arrow.red {
        color: red;
    }
    .arrow.gray {
        color: gray;
    }
    .footer {
        color: #9aa3b2;
        font-size: 12px;
        text-align: center;
        padding: 20px 10px;
        border-top: 1px solid #2a2f47;
        margin-top: 16px;
    }
    .badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 999px;
        background: #0c0f1a;
        border: 1px solid #2a2f47;
        color: #7aa2ff;
        font-size: 12px;
    }
</style>
</head>
<body>
  <header class="header">
    <h1>Voyage Report – {{ ship_name }}</h1>
    <div class="sub">{{ kpi.port_from }} → {{ kpi.port_to }} • <span class="badge">Dark Mode</span></div>
  </header>

  <main class="container">
  
    <!-- Baseline Comparison Section -->
    <section class="card">
        <header class="card-head">
            <span class="icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></span>
            <h2>Baseline Comparison</h2>
        </header>
        <div class="card-body">
            <table class="kv">
                <tr><td>Max Speed (kn)</td><td>{{ kpi.max_sog_kn|round(2) }}</td><td>{{ baseline_data.max_sog_kn|round(2) }}</td><td><span class="arrow {{ baseline_comparison.max_sog_kn[1] }}">{{ baseline_comparison.max_sog_kn[0] }}</span></td></tr>
                <tr><td>Avg Speed (kn)</td><td>{{ kpi.avg_sog_kn|round(2) }}</td><td>{{ baseline_data.avg_sog_kn|round(2) }}</td><td><span class="arrow {{ baseline_comparison.avg_sog_kn[1] }}">{{ baseline_comparison.avg_sog_kn[0] }}</span></td></tr>
                <tr><td>Total Fuel (tonnes)</td><td>{{ kpi.fuel_total_tonnes|round(2) }}</td><td>{{ baseline_data.fuel_total_tonnes|round(2) }}</td><td><span class="arrow {{ baseline_comparison.fuel_total_tonnes[1] }}">{{ baseline_comparison.fuel_total_tonnes[0] }}</span></td></tr>
                <tr><td>Energy Produced (MWh)</td><td>{{ kpi.energy_mwh_prod|round(2) }}</td><td>{{ baseline_data.energy_mwh_prod|round(2) }}</td><td><span class="arrow {{ baseline_comparison.energy_mwh_prod[1] }}">{{ baseline_comparison.energy_mwh_prod[0] }}</span></td></tr>
                <tr><td>Utilization Rate (%)</td><td>{{ kpi.whr_util_rate_percent|round(2) }}</td><td>{{ baseline_data.whr_util_rate_percent|round(2) }}</td><td><span class="arrow {{ baseline_comparison.whr_util_rate_percent[1] }}">{{ baseline_comparison.whr_util_rate_percent[0] }}</span></td></tr>
            </table>
        </div>
    </section>

    <!-- Engine Load Pie Chart Section -->
    <section class="card">
        <header class="card-head">
            <span class="icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></span>
            <h2>Engine Load Pie Chart</h2>
        </header>
        <div class="card-body">
            <!-- Pie Chart (dynamically generated and displayed here) -->
            <img src="engine_load_pie_chart.png" alt="Engine Load Distribution" />
        </div>
    </section>

    <!-- Wind/Environment Section -->
    <section class="card">
        <header class="card-head">
            <span class="icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></span>
            <h2>Wind/Environment Data</h2>
        </header>
        <div class="card-body">
            <table class="kv">
                <tr><td>Relative Wind Speed (kn)</td><td>{{ kpi.relative_wind_speed_kn|round(2) }} kn</td></tr>
                <tr><td>Wind Direction (deg)</td><td>{{ kpi.relative_wind_direction_deg|round(2) }}°</td></tr>
                <tr><td>True North Wind Speed (kn)</td><td>{{ kpi.true_north_wind_speed_kn|round(2) }} kn</td></tr>
            </table>
        </div>
    </section>

    <!-- Fuel Comparison Section -->
    <section class="card">
        <header class="card-head">
            <span class="icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></span>
            <h2>Fuel Consumption</h2>
        </header>
        <div class="card-body">
            <table class="kv">
                <tr><td>Total Fuel (tonnes)</td><td>{{ kpi.fuel_total_tonnes|round(2) }}</td></tr>
                <tr><td>Fuel by Signal (LNG)</td><td>{{ kpi.fuel_by_signal_Total_LNG_Consumption_tonnes|round(2) }}</td></tr>
                <tr><td>Fuel by Signal (MGO)</td><td>{{ kpi.fuel_by_signal_Total_MGO_Consumption_tonnes|round(2) }}</td></tr>
            </table>
        </div>
    </section>

    <!-- Electricity Section -->
    <section class="card">
        <header class="card-head">
            <span class="icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></span>
            <h2>Electricity Production</h2>
        </header>
        <div class="card-body">
            <table class="kv">
                <tr><td>Total Energy Produced (MWh)</td><td>{{ kpi.energy_mwh_prod|round(2) }} MWh</td></tr>
                <tr><td>Net Energy (MWh)</td><td>{{ kpi.energy_mwh_net|round(2) }} MWh</td></tr>
            </table>
        </div>
    </section>

  </main>

  <footer class="footer">
    Generated automatically by Voyage KPI System | © 2025
  </footer>

</body>
</html>
"""

    # Rendering the template with provided kpi_result and baseline data
    template = Template(html_template)
    return template.render(kpi=kpi_result, ship_name=ship_name, baseline_data=baseline_data, baseline_comparison=baseline_comparison)
