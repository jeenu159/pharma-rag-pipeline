import psycopg
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

DSN = "host=localhost port=5434 dbname=pharma user=rag password=rag"
MODEL = "text-embedding-3-small"
STRATEGY = "fixed_1000_200"
BATCH = 200

with psycopg.connect(DSN) as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS emb_te3_small (
            chunk_id INT PRIMARY KEY REFERENCES chunks(id),
            embedding vector(1536) NOT NULL
        )
    """)
    conn.commit()

    todo = conn.execute("""
        SELECT c.id, c.content
        FROM chunks c
        LEFT JOIN emb_te3_small e ON e.chunk_id = c.id
        WHERE c.strategy = %s AND e.chunk_id IS NULL
        ORDER BY c.id
    """, (STRATEGY,)).fetchall()
    print(f"{len(todo)} chunks to embed")

    for start in range(0, len(todo), BATCH):
        batch = todo[start:start + BATCH]
        resp = client.embeddings.create(model=MODEL, input=[text for _, text in batch])
        rows = [(cid, str(d.embedding)) for (cid, _), d in zip(batch, resp.data)]
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO emb_te3_small (chunk_id, embedding) VALUES (%s, %s::vector)",
                rows,
            )
        conn.commit()
        print(f"embedded {start + len(batch)} / {len(todo)}")

print("done")