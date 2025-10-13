# pipelines/run_voyage_report.py
import os
from core.voyage_state import detect_and_process_new_voyages
from reports.voyage_report_html import render_voyage_html_report
from reports.emailer import send_voyage_report_email


def run_voyage_report(
    ship_container: str,
    ship_name: str,
    metrics_json: str,
    output_dir: str = "./voyage_reports",
    email_enabled: bool = True
):
    """
    Automated voyage reporting pipeline:
    - Detects new voyage completions (after last processed one)
    - Saves voyage CSV via process_voyage
    - Generates HTML voyage report
    - Emails the report (optional)
    - Updates voyage_state.json and voyage_log.csv
    """

    os.makedirs(output_dir, exist_ok=True)

    # 1️⃣ Detect and process new voyages
    print("🚢 Checking for new completed voyages...")
    route_path = detect_and_process_new_voyages(
        ship_container=ship_container,
        ship_name=ship_name,
        metrics_json=metrics_json,
        output_dir=os.path.join(output_dir, "csv"),
    )

    if not route_path:
        print("⏸️ No new voyages since last run.")
        return

    print(f"✅ New voyage processed and saved to CSV: {route_path}")

    # 2️⃣ Generate voyage HTML report
    try:
        print("📄 Generating voyage HTML report...")
        from core.voyage_kpis import KPIResult  # ensure type availability
        import pandas as pd

        # Load the latest voyage CSV to render HTML
        voyage_df = pd.read_csv(route_path)
        latest_voyage_row = voyage_df.iloc[-1].to_dict()
        print(f"Latest voyage data to see : {latest_voyage_row}")
        html = render_voyage_html_report(latest_voyage_row, ship_name=ship_name)

        # Save HTML
        os.makedirs(os.path.join(output_dir, "html"), exist_ok=True)
        voyage_from = latest_voyage_row.get("port_from", "Unknown").replace(",", "")
        voyage_to = latest_voyage_row.get("port_to", "Unknown").replace(",", "")
        start_str = str(latest_voyage_row.get("voyage_start", "")).split("T")[0]
        html_filename = f"voyage_{voyage_from}_to_{voyage_to}_{start_str}.html"
        html_path = os.path.join(output_dir, "html", html_filename)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"✅ Saved HTML report: {html_path}")

        # 3️⃣ Email the report (optional)
        if email_enabled:
            try:
                send_voyage_report_email(html_path)
            except Exception as e:
                print(f"⚠️ Email sending failed: {e}")

    except Exception as e:
        print(f"⚠️ Failed to generate voyage HTML report: {e}")

    print("\n🏁 Voyage reporting pipeline complete.")

def main():
    SHIP_CONTAINER = "icon1"
    SHIP_NAME = "icon1"
    METRICS_JSON = "config/icon1_metrics_map.json"
    run_voyage_report(
        ship_container=SHIP_CONTAINER,
        ship_name=SHIP_NAME,
        metrics_json=METRICS_JSON,
        output_dir="./voyage_reports",
        email_enabled=True,
    )

if __name__ == "__main__":
    main()
