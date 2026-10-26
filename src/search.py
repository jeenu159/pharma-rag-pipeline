import os
import re
import sys
import psycopg
from dotenv import load_dotenv
from openai import OpenAI
from rank_bm25 import BM25Okapi

load_dotenv()
client = OpenAI()

DSN = "host=localhost port=5434 dbname=pharma user=rag password=rag"
MODEL = "text-embedding-3-small"
STRATEGY = os.getenv("RAG_STRATEGY", "fixed_1000_200")
MODE = os.getenv("RAG_SEARCH", "vector")   # vector | hybrid | bm25_hybrid
CANDIDATES = 20   # how many results each search contributes before fusion
RRF_K = 60        # standard RRF constant
KW_WEIGHT = float(os.getenv("RAG_KW_WEIGHT", "1.0"))

VECTOR_SQL = """
    SELECT c.id, e.embedding <=> %(vec)s::vector AS score, c.content
    FROM emb_te3_small e
    JOIN chunks c ON c.id = e.chunk_id
    WHERE c.strategy = %(strategy)s
    ORDER BY score
    LIMIT %(k)s
"""

HYBRID_SQL = """
    WITH vec AS (
        SELECT c.id, ROW_NUMBER() OVER (ORDER BY e.embedding <=> %(vec)s::vector) AS r
        FROM emb_te3_small e
        JOIN chunks c ON c.id = e.chunk_id
        WHERE c.strategy = %(strategy)s
        ORDER BY r
        LIMIT %(cand)s
    ),
    query AS (
        SELECT replace(plainto_tsquery('english', %(question)s)::text, '&', '|')::tsquery AS q
    ),
    kw AS (
        SELECT c.id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(c.tsv, query.q) DESC) AS r
        FROM chunks c, query
        WHERE c.strategy = %(strategy)s AND c.tsv @@ query.q
        ORDER BY r
        LIMIT %(cand)s
    ),
    fused AS (
        SELECT id, SUM(1.0 / (%(rrf)s + r)) AS score
        FROM (SELECT id, r FROM vec UNION ALL SELECT id, r FROM kw) both_lists
        GROUP BY id
    )
    SELECT c.id, f.score, c.content
    FROM fused f
    JOIN chunks c ON c.id = f.id
    ORDER BY f.score DESC
    LIMIT %(k)s
"""

STOPWORDS = {
    "a", "an", "the", "is", "it", "i", "to", "of", "and", "or", "in", "on", "for",
    "with", "can", "my", "me", "be", "do", "does", "if", "at", "by", "what", "how",
    "when", "who", "are", "was", "this", "that", "ok", "should", "there", "any",
    "as", "from", "about",
}
_bm25 = None


def tokenize(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


def load_bm25():
    """Build the BM25 index once per run (about 11k chunks, a few seconds)."""
    global _bm25
    if _bm25 is None:
        with psycopg.connect(DSN) as conn:
            rows = conn.execute(
                "SELECT id, content FROM chunks WHERE strategy = %s ORDER BY id", (STRATEGY,)
            ).fetchall()
        ids = [cid for cid, _ in rows]
        index = BM25Okapi([tokenize(content) for _, content in rows])
        _bm25 = (index, ids, dict(rows))
    return _bm25


def bm25_hybrid(question, q_vec, k):
    index, ids, content = load_bm25()
    scores = index.get_scores(tokenize(question))
    top = scores.argsort()[::-1][:CANDIDATES]
    kw = [ids[i] for i in top if scores[i] > 0]

    with psycopg.connect(DSN) as conn:
        vec_rows = conn.execute(
            VECTOR_SQL, {"vec": str(q_vec), "strategy": STRATEGY, "k": CANDIDATES}
        ).fetchall()
    vec = [cid for cid, _, _ in vec_rows]

    fused = {}
    for weight, ranked in ((1.0, vec), (KW_WEIGHT, kw)):
        for rank, cid in enumerate(ranked, start=1):
            fused[cid] = fused.get(cid, 0) + weight / (RRF_K + rank)

    best = sorted(fused, key=fused.get, reverse=True)[:k]
    return [(cid, fused[cid], content[cid]) for cid in best]


def search(question, k=5):
    q_vec = client.embeddings.create(model=MODEL, input=question).data[0].embedding
    if MODE == "bm25_hybrid":
        return bm25_hybrid(question, q_vec, k)
    params = {"vec": str(q_vec), "strategy": STRATEGY, "k": k,
              "question": question, "cand": CANDIDATES, "rrf": RRF_K}
    with psycopg.connect(DSN) as conn:
        return conn.execute(HYBRID_SQL if MODE == "hybrid" else VECTOR_SQL, params).fetchall()


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    print(f"mode={MODE}  strategy={STRATEGY}\n")
    for cid, score, content in search(question):
        print(f"[{cid}] score={score:.4f}")
        print(content[:200].replace("\n", " "))
        print("-" * 60)