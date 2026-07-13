"""Posts a stratified sample of real UNSW-NB15 rows to the running API so the
dashboard has real, model-scored data to show. Run `uvicorn main:app` first.

Note: the public UNSW-NB15 feature CSV does not include source/destination
IPs (only the raw pcap capture does). We generate plausible private-range IPs
per row purely for display — every other field, and the detection result, is
the model scoring the real dataset row.
"""

import os
import random
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env")
from detection.features import ALL_FEATURES  # noqa: E402

API_URL = "http://127.0.0.1:8000/events/ingest"
DATA_PATH = Path(__file__).parent.parent / "data" / "UNSW_NB15_training-set.csv"
SAMPLE_PER_CATEGORY = 15
INGEST_API_KEY = os.environ.get("INGEST_API_KEY")


def random_private_ip() -> str:
    return f"10.0.{random.randint(0, 255)}.{random.randint(1, 254)}"


def main() -> None:
    if not INGEST_API_KEY:
        raise SystemExit("INGEST_API_KEY not set in backend/.env — see .env.example.")

    df = pd.read_csv(DATA_PATH)
    df["attack_cat"] = df["attack_cat"].str.strip()

    sample = (
        df.groupby("attack_cat", group_keys=False)
        .apply(lambda g: g.sample(min(len(g), SAMPLE_PER_CATEGORY), random_state=7))
        .sample(frac=1, random_state=7)  # shuffle so it isn't grouped by category
        .reset_index(drop=True)
    )

    sent, threats = 0, 0
    for _, row in sample.iterrows():
        payload = {
            "source_ip": random_private_ip(),
            "dest_ip": random_private_ip(),
            "protocol": row["proto"],
            "bytes": int(row["sbytes"] + row["dbytes"]),
            "features": {k: row[k] for k in ALL_FEATURES},
        }
        resp = requests.post(API_URL, json=payload, headers={"X-API-Key": INGEST_API_KEY}, timeout=10)
        resp.raise_for_status()
        body = resp.json()
        sent += 1
        threats += len(body.get("threats", []))

    print(f"Ingested {sent} events, {threats} scored as threats.")


if __name__ == "__main__":
    main()
