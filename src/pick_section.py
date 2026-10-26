import sys
import psycopg

DSN = "host=localhost port=5434 dbname=pharma user=rag password=rag"
section = sys.argv[1] if len(sys.argv) > 1 else None

with psycopg.connect(DSN) as conn:
    if section:
        row = conn.execute("""
            SELECT id, drug_name, section, content FROM label_sections
            WHERE section = %s ORDER BY random() LIMIT 1
        """, (section,)).fetchone()
    else:
        row = conn.execute("""
            SELECT id, drug_name, section, content FROM label_sections
            WHERE LENGTH(content) > 300 ORDER BY random() LIMIT 1
        """).fetchone()

sec_id, drug, sec, content = row
print(f"section_id={sec_id} | drug={drug} | section={sec}\n")
print(content[:2000])