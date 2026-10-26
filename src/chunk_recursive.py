import psycopg

DSN = "host=localhost port=5434 dbname=pharma user=rag password=rag"
STRATEGY = "recursive_1000_200"
SIZE, OVERLAP = 1000, 200
SEPS = ["\n\n", "\n", ". ", " "]


def recursive_split(text, size=SIZE, overlap=OVERLAP, seps=SEPS):
    if len(text) <= size:
        return [text]

    sep = next((s for s in seps if s in text), None)
    if sep is None:  # no separator left: hard cut as a last resort
        return [text[i:i + size] for i in range(0, len(text), size - overlap)]
    remaining = seps[seps.index(sep) + 1:]

    # split on this separator, keeping it attached to each piece
    pieces = [p + sep for p in text.split(sep)]
    pieces[-1] = pieces[-1][:-len(sep)]

    # any piece still too big gets split again with the next separator
    units = []
    for p in pieces:
        units.extend(recursive_split(p, size, overlap, remaining) if len(p) > size else [p])

    # pack small units back together up to `size`, carrying a tail forward as overlap
    chunks, current = [], []
    for u in units:
        if current and sum(map(len, current)) + len(u) > size:
            chunks.append("".join(current).strip())
            tail = []
            while current and sum(map(len, tail)) + len(current[-1]) <= overlap:
                tail.insert(0, current.pop())
            current = tail
        current.append(u)
    if current:
        chunks.append("".join(current).strip())
    return [c for c in chunks if c]


with psycopg.connect(DSN) as conn:
    conn.execute("DELETE FROM chunks WHERE strategy = %s", (STRATEGY,))
    sections = conn.execute(
        "SELECT id, drug_name, section, content FROM label_sections"
    ).fetchall()

    rows = []
    for sec_id, drug, section, content in sections:
        header = f"Drug: {drug} | Section: {section}\n"
        for i, piece in enumerate(recursive_split(content)):
            rows.append((sec_id, STRATEGY, i, header + piece))

    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO chunks (section_id, strategy, chunk_index, content) VALUES (%s, %s, %s, %s)",
            rows,
        )

print(f"created {len(rows)} chunks")