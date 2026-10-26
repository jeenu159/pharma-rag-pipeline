import os
import re
import sys
import time
import cohere
import psycopg
from dotenv import load_dotenv
from openai import OpenAI
from rank_bm25 import BM25Okapi

load_dotenv()
client = OpenAI()
co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))

DSN = "host=localhost port=5434 dbname=pharma user=rag password=rag"
MODEL = "text-embedding-3-small"
RERANK_MODEL = "rerank-v3.5"
STRATEGY = os.getenv("RAG_STRATEGY", "fixed_1000_200")
MODE = os.getenv("RAG_SEARCH", "vector")          # vector | hybrid | bm25_hybrid
RERANK = os.getenv("RAG_RERANK", "none")          # none | cohere
RERANK_MIN_GAP = float(os.getenv("RERANK_MIN_GAP", "6.5"))  # seconds; trial key ~10 calls/min
CANDIDATES = 20   # results fetched before fusion or reranking
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
_last_rerank = 0.0


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


def first_stage(question, q_vec, k):
    """Retrieve k results with the configured search mode (no reranking)."""
    if MODE == "bm25_hybrid":
        return bm25_hybrid(question, q_vec, k)
    params = {"vec": str(q_vec), "strategy": STRATEGY, "k": k,
              "question": question, "cand": CANDIDATES, "rrf": RRF_K}
    with psycopg.connect(DSN) as conn:
        return conn.execute(HYBRID_SQL if MODE == "hybrid" else VECTOR_SQL, params).fetchall()


def cohere_rerank(question, candidates, k):
    """Reorder candidates with Cohere Rerank and keep the top k."""
    global _last_rerank
    wait = RERANK_MIN_GAP - (time.time() - _last_rerank)
    if wait > 0:
        time.sleep(wait)
    resp = co.rerank(model=RERANK_MODEL, query=question,
                     documents=[content for _, _, content in candidates], top_n=k)
    _last_rerank = time.time()
    return [(candidates[r.index][0], r.relevance_score, candidates[r.index][2]) for r in resp.results]


def search(question, k=5):
    q_vec = client.embeddings.create(model=MODEL, input=question).data[0].embedding
    if RERANK == "cohere":
        return cohere_rerank(question, first_stage(question, q_vec, CANDIDATES), k)
    return first_stage(question, q_vec, k)


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    print(f"mode={MODE}  rerank={RERANK}  strategy={STRATEGY}\n")
    for cid, score, content in search(question):
        print(f"[{cid}] score={score:.4f}")
        print(content[:200].replace("\n", " "))
        print("-" * 60)