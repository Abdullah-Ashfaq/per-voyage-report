# pipelines/bootstrap_historical.py
import os
from core.datalake import get_voyage_data, debug_list_blobs
from core.voyage_detection import detect_voyages, add_voyage_durations
from core.process_voyage import process_and_save_voyage


def bootstrap_historical_voyages(
    ship_container: str,
    ship_name: str,
    metrics_json: str,
    output_dir: str = "./voyage_csvs"
):
    """
    Backfill baseline voyage CSVs from historical port data.
    """
    os.makedirs(output_dir, exist_ok=True)

    # 👀 Debug: list some blobs to confirm they exist
    print("\n📂 DEBUG: Listing blobs from container before fetching port data…")
    debug_list_blobs("csvportmonthly", ship_container, limit=20)
    debug_list_blobs("csvdatamonthly", "icon1", limit=20)


    # 1️⃣ Load port data
    port_df = get_voyage_data(ship_container)
    if port_df.empty:
        print("❌ No port data found.")
        return

    # 2️⃣ Detect voyages
    voyages = detect_voyages(port_df)
    voyages = add_voyage_durations(voyages)
    if not voyages:
        print("❌ No voyages detected.")
        return

    print(f"🔎 Found {len(voyages)} voyages to process...")

    # 3️⃣ Process each voyage
    for idx, voyage in enumerate(voyages, start=1):
        print(f"\n➡️ [{idx}/{len(voyages)}] {voyage['from']} → {voyage['to']} "
              f"({voyage['start']} → {voyage['end']}) | Duration: {voyage['duration_hours']:.2f}h")
        try:
            process_and_save_voyage(
                voyage,
                ship_container=ship_container,
                ship_name=ship_name,
                metrics_json=metrics_json,
                output_dir=output_dir
            )
        except Exception as e:
            print(f"⚠️ Skipping voyage due to error: {e}")

    print("\n✅ Bootstrapping complete. All historical voyages saved as CSVs.")


if __name__ == "__main__":
    # Example configuration
    SHIP_CONTAINER = "icon1"
    SHIP_NAME = "icon1"
    METRICS_JSON = "config/icon1_metrics_map.json"

    bootstrap_historical_voyages(
        ship_container=SHIP_CONTAINER,
        ship_name=SHIP_NAME,
        metrics_json=METRICS_JSON,
        output_dir="./voyage_csvs"
    )
