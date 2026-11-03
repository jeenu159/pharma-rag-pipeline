import json
import psycopg

SRC_DSN = "host=localhost port=5434 dbname=pharma user=rag password=rag"
ADMIN_DSN = "host=localhost port=5434 dbname=postgres user=rag password=rag"
SMOKE_DSN = "host=localhost port=5434 dbname=pharma_smoke user=rag password=rag"
STRATEGY = "fixed_1000_200"
SMOKE_IDS = {1, 2, 3, 5, 8, 10, 14, 17, 18, 21, 24, 33, 34, 38, 46}   # mix of easy, misspelt, lay, comparison
N_DISTRACTORS = 300

# 1. the smoke question set
with open("eval/golden.jsonl", encoding="utf-8") as f:
    golden = [json.loads(line) for line in f if line.strip()]
smoke = [g for g in golden if g["id"] in SMOKE_IDS]
with open("eval/smoke.jsonl", "w", encoding="utf-8") as f:
    for g in smoke:
        f.write(json.dumps(g) + "\n")
section_ids = [s for g in smoke for s in g["section_ids"]]

# 2. pick which sections to keep: every section of the smoke drugs, plus random distractors
with psycopg.connect(SRC_DSN) as src:
    generics = [r[0] for r in src.execute(
        "SELECT DISTINCT generic_name FROM label_sections WHERE id = ANY(%s)", (section_ids,))]
    keep = [r[0] for r in src.execute(
        "SELECT id FROM label_sections WHERE generic_name = ANY(%s)", (generics,))]
    keep += [r[0] for r in src.execute(
        "SELECT id FROM label_sections WHERE NOT (generic_name = ANY(%s)) ORDER BY random() LIMIT %s",
        (generics, N_DISTRACTORS))]
    sections = src.execute(
        "SELECT id, label_id, drug_name, section, content, generic_name FROM label_sections WHERE id = ANY(%s)",
        (keep,)).fetchall()
    chunks = src.execute(
        "SELECT id, section_id, strategy, chunk_index, content FROM chunks WHERE section_id = ANY(%s) AND strategy = %s",
        (keep, STRATEGY)).fetchall()
    embs = src.execute(
        "SELECT e.chunk_id, e.embedding::text FROM emb_te3_small e JOIN chunks c ON c.id = e.chunk_id "
        "WHERE c.section_id = ANY(%s) AND c.strategy = %s", (keep, STRATEGY)).fetchall()

# 3. create a fresh smoke database with the same schema, keeping the ORIGINAL ids
with psycopg.connect(ADMIN_DSN, autocommit=True) as admin:
    admin.execute("DROP DATABASE IF EXISTS pharma_smoke")
    admin.execute("CREATE DATABASE pharma_smoke")

with psycopg.connect(SMOKE_DSN) as dst:
    dst.execute("CREATE EXTENSION IF NOT EXISTS vector")
    dst.execute("""CREATE TABLE label_sections (
        id INT PRIMARY KEY, label_id TEXT, drug_name TEXT, section TEXT, content TEXT, generic_name TEXT)""")
    dst.execute("""CREATE TABLE chunks (
        id INT PRIMARY KEY, section_id INT REFERENCES label_sections(id), strategy TEXT,
        chunk_index INT, content TEXT,
        tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED)""")
    dst.execute("""CREATE TABLE emb_te3_small (
        chunk_id INT PRIMARY KEY REFERENCES chunks(id), embedding vector(1536) NOT NULL)""")
    with dst.cursor() as cur:
        cur.executemany("INSERT INTO label_sections VALUES (%s, %s, %s, %s, %s, %s)", sections)
        cur.executemany("INSERT INTO chunks (id, section_id, strategy, chunk_index, content) "
                        "VALUES (%s, %s, %s, %s, %s)", chunks)
        cur.executemany("INSERT INTO emb_te3_small VALUES (%s, %s::vector)", embs)

print(f"smoke questions: {len(smoke)}  sections: {len(sections)}  chunks: {len(chunks)}  embeddings: {len(embs)}")