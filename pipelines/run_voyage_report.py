# pipelines/run_voyage_report.py
import os
import pandas as pd
import numpy as np
from core.voyage_state import detect_and_process_new_voyages
from reports.voyage_report_html import render_voyage_html_report
from reports.emailer import send_voyage_report_email


def run_voyage_report(
    ship_container: str,
    ship_name: str,
    metrics_json: str,
    output_dir: str = "./voyage_csvs",
    email_enabled: bool = True
):

    os.makedirs(output_dir, exist_ok=True)

    # Detect and process new voyages
    print("🚢 Checking for new completed voyages...")
    route_path = detect_and_process_new_voyages(
        ship_container=ship_container,
        ship_name=ship_name,
        metrics_json=metrics_json,
        output_dir=output_dir,
    )

    if not route_path:
        print("No new voyages since last run.")
        return

    print(f"New voyage processed and saved to CSV: {route_path}")

    try:
        # Load latest voyage
        print(" Generating voyage HTML report...")
        voyage_df = pd.read_csv(route_path)
        latest_voyage_row = voyage_df.iloc[-1].to_dict()
        print(f" Latest voyage data: {latest_voyage_row}")

        # --- Fix missing fuel_tonnes_per_nm ---
        if pd.isna(latest_voyage_row.get("fuel_tonnes_per_nm")):
            ft = latest_voyage_row.get("fuel_total_tonnes")
            dn = latest_voyage_row.get("distance_nm")
            if isinstance(ft, (int, float)) and isinstance(dn, (int, float)) and dn > 0:
                latest_voyage_row["fuel_tonnes_per_nm"] = ft / dn

       

# Compute rolling baseline (last 7 voyages, excluding current)
        baseline = None
        try:
            hist_df = voyage_df.copy().iloc[:-1]  # exclude current voyage
            if not hist_df.empty:
            # Convert to numeric (ignore non-numeric columns)
                numeric_df = hist_df.apply(pd.to_numeric, errors="coerce")

                # Drop NaN-only columns (clean data before averaging)
                numeric_df = numeric_df.dropna(axis=1, how="all")

                # Keep only last 7 voyages
                baseline_df = numeric_df.tail(7)
                print(f"Using average of last {len(baseline_df)} voyages as baseline (excluding current).")

                # Compute numeric averages
                baseline_avg = baseline_df.mean(numeric_only=True).to_dict()

                # Carry metadata from last historical voyage
                last_meta = hist_df.iloc[-1]
                baseline_avg["port_from"] = last_meta.get("port_from")
                baseline_avg["port_to"] = last_meta.get("port_to")

                baseline = baseline_avg

                # print the baseline for debugging
                print(f"🔍 Baseline averages: {baseline}")
            else:
                print("Not enough voyages for baseline calculation.")
        except Exception as e:
            print(f"Baseline computation failed: {e}")

        # Generate HTML report
        print("Rendering voyage report with baseline comparison...")
        html = render_voyage_html_report(
            latest_voyage_row,
            ship_name=ship_name,
            baseline_data=baseline
        )

        # Save HTML
        os.makedirs(os.path.join(output_dir, "html"), exist_ok=True)
        voyage_from = str(latest_voyage_row.get("port_from", "Unknown")).strip().replace(",", "").replace(":", "_")
        voyage_to = str(latest_voyage_row.get("port_to", "Unknown")).strip().replace(",", "").replace(":", "_")
        start_str = str(latest_voyage_row.get("voyage_start", "")).split("T")[0].replace(":", "_").strip()

        # Debugging logs to ensure correct types and values
        print(f"Voyage From: {voyage_from} (type: {type(voyage_from)})")
        print(f"Voyage To: {voyage_to} (type: {type(voyage_to)})")
        print(f"Start Date: {start_str} (type: {type(start_str)})")

        # Generate the HTML filename
        html_filename = f"voyage_{voyage_from}_to_{voyage_to}_{start_str}.html"
        html_path = os.path.join(output_dir, "html", html_filename)

        # Save the HTML report
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Saved HTML report: {html_path}")

        # Email the report (optional)
        if email_enabled:
            try:
                send_voyage_report_email(html_path)
                print(f"Voyage report emailed successfully → {voyage_from} to {voyage_to} ({start_str})")
            except Exception as e:
                print(f"Email sending failed: {e}")

    except Exception as e:
        print(f"Failed to generate voyage HTML report: {e}")

    print("\n Voyage reporting pipeline complete.")


def main():
    SHIP_CONTAINER = "icon1"
    SHIP_NAME = "icon1"
    METRICS_JSON = "config/icon1_metrics_map.json"
    run_voyage_report(
        ship_container=SHIP_CONTAINER,
        ship_name=SHIP_NAME,
        metrics_json=METRICS_JSON,
        output_dir="./voyage_csvs",
        email_enabled=True,
    )


if __name__ == "__main__":
    main()
