import sys
import os
import psycopg
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

DSN = "host=localhost port=5434 dbname=pharma user=rag password=rag"
MODEL = "text-embedding-3-small"
STRATEGY = os.getenv("RAG_STRATEGY", "fixed_1000_200")


def search(question, k=5):
    q_vec = client.embeddings.create(model=MODEL, input=question).data[0].embedding
    with psycopg.connect(DSN) as conn:
        return conn.execute("""
            SELECT c.id, e.embedding <=> %s::vector AS distance, c.content
            FROM emb_te3_small e
            JOIN chunks c ON c.id = e.chunk_id
            WHERE c.strategy = %s
            ORDER BY distance
            LIMIT %s
        """, (str(q_vec), STRATEGY, k)).fetchall()
    
if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    for cid, dist, content in search(question):
        print(f"[{cid}] distance={dist:.3f}")
        print(content[:200].replace("\n", " "))
        print("-" * 60)