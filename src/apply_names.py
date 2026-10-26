import json
import psycopg

DSN = "host=localhost port=5434 dbname=pharma user=rag password=rag"

with open("data/raw/labels.json", encoding="utf-8") as f:
    labels = json.load(f)
with open("data/raw/extracted_names.json", encoding="utf-8") as f:
    extracted = json.load(f)

updates = []
for label in labels:
    fda = label.get("openfda", {})
    if label["id"] in extracted:
        brand = extracted[label["id"]]["brand_name"]
        generic = extracted[label["id"]]["generic_name"]
    else:
        brand = (fda.get("brand_name") or fda.get("generic_name"))[0]
        generic = (fda.get("generic_name") or fda.get("brand_name"))[0]
    updates.append((brand, generic.strip().lower(), label["id"]))

with psycopg.connect(DSN) as conn:
    conn.execute("ALTER TABLE label_sections ADD COLUMN IF NOT EXISTS generic_name TEXT")
    with conn.cursor() as cur:
        cur.executemany("""
            UPDATE label_sections
            SET drug_name = CASE WHEN drug_name = 'unknown' THEN %s ELSE drug_name END,
                generic_name = %s
            WHERE label_id = %s
        """, updates)
    left = conn.execute("SELECT COUNT(*) FROM label_sections WHERE drug_name = 'unknown'").fetchone()[0]

print(f"updated {len(updates)} labels; sections still unknown: {left}")