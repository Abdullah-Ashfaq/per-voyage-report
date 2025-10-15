# pipelines/scheduler.py
import os
import time
from datetime import datetime
from pipelines.run_voyage_report import run_voyage_report

# Interval for automatic run (in seconds)
SCHEDULER_INTERVAL = int(os.getenv("SCHEDULER_INTERVAL", 3600))  # 1 hour default


def run_scheduler(ship_container: str, ship_name: str, metrics_json: str, output_dir: str):
    """
    Continuous scheduler loop:
    - Runs the voyage reporting pipeline every N seconds (default 1h)
    - Keeps logs timestamped
    """
    print("🕒 Voyage Report Scheduler started")
    print(f"  Interval: {SCHEDULER_INTERVAL/60:.1f} minutes")
    print(f"  Ship: {ship_name}\n")

    while True:
        print("\n==============================================")
        print(f"🚀 Running scheduled voyage check @ {datetime.utcnow().isoformat()} UTC")

        try:
            run_voyage_report(
                ship_container=ship_container,
                ship_name=ship_name,
                metrics_json=metrics_json,
                output_dir=output_dir,
                email_enabled=True,
            )
        except Exception as e:
            print(f"❌ Scheduler run failed: {e}")

        print(f"🕑 Sleeping for {SCHEDULER_INTERVAL/60:.1f} minutes...")
        time.sleep(SCHEDULER_INTERVAL)


def run_once(ship_container: str, ship_name: str, metrics_json: str, output_dir: str):
    """
    Manual test mode: run once immediately.
    """
    print("⚙️ Manual voyage report run (testing mode)")
    run_voyage_report(
        ship_container=ship_container,
        ship_name=ship_name,
        metrics_json=metrics_json,
        output_dir=output_dir,
        email_enabled=False,  # disable emails during tests if desired
    )


if __name__ == "__main__":
    SHIP_CONTAINER = "icon1"
    SHIP_NAME = "icon1"
    METRICS_JSON = "config/icon1_metrics_map.json"
    OUTPUT_DIR = "./voyage_csvs"

    mode = os.getenv("RUN_MODE", "manual").lower()  # 'manual' or 'auto'

    if mode == "auto":
        run_scheduler(SHIP_CONTAINER, SHIP_NAME, METRICS_JSON, OUTPUT_DIR)
    else:
        run_once(SHIP_CONTAINER, SHIP_NAME, METRICS_JSON, OUTPUT_DIR)
