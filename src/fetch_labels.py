import json
import os
import requests

URL = "https://api.fda.gov/drug/label.json"
OUT = "data/raw/labels.json"

os.makedirs("data/raw", exist_ok=True)

all_labels = []
for skip in range(0, 500, 100):
    resp = requests.get(URL, params={"limit": 100, "skip": skip}, timeout=60)
    resp.raise_for_status()
    batch = resp.json()["results"]
    all_labels.extend(batch)
    print(f"fetched {len(all_labels)} labels")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(all_labels, f)

print(f"saved to {OUT}")