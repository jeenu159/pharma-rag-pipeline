import json
import psycopg

DSN = "host=localhost port=5434 dbname=pharma user=rag password=rag"

SECTIONS = [
    "indications_and_usage", "dosage_and_administration", "warnings",
    "adverse_reactions", "contraindications", "drug_interactions",
    "clinical_pharmacology", "overdosage", "pregnancy", "pediatric_use",
    "geriatric_use", "precautions", "description", "do_not_use",
    "stop_use", "ask_doctor", "when_using", "purpose", "active_ingredient",
]

with open("data/raw/labels.json", encoding="utf-8") as f:
    labels = json.load(f)

rows = []
for label in labels:
    fda = label.get("openfda", {})
    name = (fda.get("brand_name") or fda.get("generic_name") or ["unknown"])[0]
    for sec in SECTIONS:
        if sec in label:
            text = " ".join(label[sec]).strip()
            if text:
                rows.append((label["id"], name, sec, text))

with psycopg.connect(DSN) as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS label_sections (
            id SERIAL PRIMARY KEY,
            label_id TEXT NOT NULL,
            drug_name TEXT NOT NULL,
            section TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)
    conn.execute("TRUNCATE label_sections")
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO label_sections (label_id, drug_name, section, content) VALUES (%s, %s, %s, %s)",
            rows,
        )

print(f"inserted {len(rows)} sections")