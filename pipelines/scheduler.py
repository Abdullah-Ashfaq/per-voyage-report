import schedule
import time
from datetime import datetime
from pipelines.run_voyage_report import run_voyage_report

def job():
    print(f"[{datetime.now()}] Running nightly voyage report...")
    try:
        run_voyage_report(
            ship_container="icon1",
            ship_name="icon1",
            metrics_json="config/icon1_metrics_map.json",
            output_dir="./voyage_csvs",
            email_enabled=True,
        )
        print(f"[{datetime.now()}]  Voyage report successfully generated.")
    except Exception as e:
        print(f"[{datetime.now()}]  Voyage report failed: {e}")


def main():
    schedule.every().day.at("00:00").do(job)
    # schedule.every(1).minutes.do(job)  # For testing purposes
    print("Scheduler started — waiting for scheduled runs...")
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()