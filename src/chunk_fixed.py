import psycopg

DSN = "host=localhost port=5434 dbname=pharma user=rag password=rag"
STRATEGY = "fixed_1000_200"
SIZE, OVERLAP = 1000, 200


def split_fixed(text, size, overlap):
    if len(text) <= size:
        return [text]
    step = size - overlap
    return [text[i:i + size] for i in range(0, len(text) - overlap, step)]


with psycopg.connect(DSN) as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id SERIAL PRIMARY KEY,
            section_id INT NOT NULL REFERENCES label_sections(id),
            strategy TEXT NOT NULL,
            chunk_index INT NOT NULL,
            content TEXT NOT NULL
        )
    """)
    conn.execute("DELETE FROM chunks WHERE strategy = %s", (STRATEGY,))

    sections = conn.execute(
        "SELECT id, drug_name, section, content FROM label_sections"
    ).fetchall()

    rows = []
    for sec_id, drug, section, content in sections:
        header = f"Drug: {drug} | Section: {section}\n"
        for i, piece in enumerate(split_fixed(content, SIZE, OVERLAP)):
            rows.append((sec_id, STRATEGY, i, header + piece))

    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO chunks (section_id, strategy, chunk_index, content) VALUES (%s, %s, %s, %s)",
            rows,
        )

print(f"created {len(rows)} chunks")