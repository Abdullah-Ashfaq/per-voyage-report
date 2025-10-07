# pipelines/run_voyage_report.py
import os
from core.datalake import get_voyage_data, get_signals_between
from core.voyage_detection import detect_voyages, add_voyage_durations
from core.process_voyage import process_and_save_voyage
from core.voyage_state import load_last_voyage_end, save_last_voyage_end, append_voyage_log
from core.voyage_kpis import compute_voyage_kpis
from core.metrics_map import load_metrics_map
from reports.voyage_report_html import render_voyage_html_report
from reports.emailer import send_html_report   # ⬅️ import emailer

def run_voyage_report(
    ship_container: str,
    ship_name: str,
    metrics_json: str,
    output_dir: str = "./voyage_reports",
    email_enabled: bool = True
):
    """
    Real-time voyage reporting pipeline:
    - Detects new voyage completions
    - Saves voyage CSV + HTML
    - Emails the report (optional)
    - Updates state + log
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1️⃣ Load last processed voyage
    last_end = load_last_voyage_end()
    print(f"📌 Last processed voyage end: {last_end}")

    # 2️⃣ Get port data
    port_df = get_voyage_data(ship_container)
    if port_df.empty:
        print("❌ No port data found.")
        return

    # 3️⃣ Detect voyages
    voyages = detect_voyages(port_df)
    voyages = add_voyage_durations(voyages)
    if not voyages:
        print("❌ No voyages detected.")
        return

    # 4️⃣ Filter only new voyages
    new_voyages = [v for v in voyages if last_end is None or v["end"] > last_end]
    if not new_voyages:
        print("ℹ️ No new voyages since last run.")
        return

    print(f"🔎 Found {len(new_voyages)} new voyages to process...")

    metrics = load_metrics_map(metrics_json, ship_name)


    # 5️⃣ Process new voyages
    for voyage in new_voyages:
        print(f"\n➡️ Processing {voyage['from']} → {voyage['to']} "
              f"({voyage['start']} → {voyage['end']})")

        try:
            # a) Fetch signals
            signals_df = get_signals_between(ship_container, voyage["start"], voyage["end"])
            if signals_df.empty:
                print("⚠️ No signals found, skipping.")
                continue

            # b) Compute KPIs
            kpi_result = compute_voyage_kpis(signals_df, metrics, voyage)

            # c) Save CSV
            csv_path = process_and_save_voyage(
                voyage,
                ship_container=ship_container,
                ship_name=ship_name,
                metrics_json=metrics_json,
                output_dir=os.path.join(output_dir, "csv")
            )

            # d) Save HTML
            html = render_voyage_html_report(kpi_result, ship_name=ship_name)
            os.makedirs(os.path.join(output_dir, "html"), exist_ok=True)
            start_date_str = voyage["start"].strftime("%Y-%m-%d")
            html_file = f"voyage_{voyage['from']}_to_{voyage['to']}_{start_date_str}.html"
            html_path = os.path.join(output_dir, "html", html_file)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"✅ Saved voyage HTML report: {html_path}")

            # e) Email report (optional)
            if email_enabled:
                subject = f"Voyage Report: {voyage['from']} → {voyage['to']} ({start_date_str})"
                try:
                    send_html_report(
                        subject=subject,
                        html_body=html,
                        from_addr=None,  # will use EMAIL_FROM env
                        to_addrs=None,   # will use EMAIL_TO env
                        attach_html_path=html_path
                    )
                    print(f"📧 Voyage report emailed: {subject}")
                except Exception as e:
                    print(f"⚠️ Failed to send email: {e}")

            # f) Update state + log
            save_last_voyage_end(voyage["end"])
            append_voyage_log(voyage, csv_path)

        except Exception as e:
            print(f"⚠️ Skipping voyage due to error: {e}")

    print("\n✅ Voyage reporting pipeline complete.")


if __name__ == "__main__":
    # Example config
    SHIP_CONTAINER = "icon1"
    SHIP_NAME = "icon1"
    METRICS_JSON = "config/icon1_metrics_map.json"

    run_voyage_report(
        ship_container=SHIP_CONTAINER,
        ship_name=SHIP_NAME,
        metrics_json=METRICS_JSON,
        output_dir="./voyage_reports",
        email_enabled=True
    )
