import os
import sys
from collections import defaultdict
import psycopg
from dotenv import load_dotenv
from openai import OpenAI
from search import search, DSN

load_dotenv()
client = OpenAI()

LLM = "gpt-5-mini"
NEIGHBOURS = os.getenv("RAG_NEIGHBOURS", "0") == "1"

PROMPT = """Answer the question using ONLY the context below.
Cite the chunk IDs you used in square brackets, like [8417].
If the context does not contain the answer, say "Not found in the provided labels."

Context:
{context}

Question: {question}"""


def expand_neighbours(hits):
    """For each hit, add the chunk before and after it from the same section, keeping hit order."""
    ids = [cid for cid, _, _ in hits]
    with psycopg.connect(DSN) as conn:
        rows = conn.execute("""
            SELECT c1.id, c2.id, c2.content
            FROM chunks c1
            JOIN chunks c2
              ON c2.section_id = c1.section_id
             AND c2.strategy = c1.strategy
             AND c2.chunk_index BETWEEN c1.chunk_index - 1 AND c1.chunk_index + 1
            WHERE c1.id = ANY(%s)
            ORDER BY c2.chunk_index
        """, (ids,)).fetchall()

    around = defaultdict(list)
    for anchor, cid, content in rows:
        around[anchor].append((cid, content))

    expanded, seen = [], set()
    for cid, score, _ in hits:
        for nid, content in around[cid]:
            if nid not in seen:
                seen.add(nid)
                expanded.append((nid, score, content))
    return expanded


def answer(question, k=int(os.getenv("RAG_K", "3"))):
    hits = search(question, k)
    if NEIGHBOURS:
        hits = expand_neighbours(hits)
    context = "\n\n".join(f"[{cid}] {content}" for cid, _, content in hits)
    resp = client.chat.completions.create(
        model=LLM,
        messages=[{"role": "user", "content": PROMPT.format(context=context, question=question)}],
    )
    return {"text": resp.choices[0].message.content, "hits": hits, "usage": resp.usage}


if __name__ == "__main__":
    print(answer(" ".join(sys.argv[1:]))["text"])