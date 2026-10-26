import json
import psycopg
from search import search, DSN

K = 5

with open("eval/golden.jsonl", encoding="utf-8") as f:
    golden = [json.loads(line) for line in f if line.strip()]


def is_hit(meta, item):
    sec_id, drug, section = meta
    if sec_id in item["section_ids"]:
        return True
    same_drug = drug.strip().lower() == item.get("drug", "").strip().lower()
    return same_drug and section == item.get("section")


results = []
with psycopg.connect(DSN) as conn:
    for item in golden:
        if item["type"] == "unanswerable":
            continue
        chunk_ids = [cid for cid, _, _ in search(item["question"], K)]
        rows = conn.execute("""
            SELECT c.id, s.id, s.drug_name, s.section
            FROM chunks c
            JOIN label_sections s ON s.id = c.section_id
            WHERE c.id = ANY(%s)
        """, (chunk_ids,)).fetchall()
        meta = {cid: (sid, drug, sec) for cid, sid, drug, sec in rows}

        rank = next((i + 1 for i, cid in enumerate(chunk_ids) if is_hit(meta[cid], item)), None)
        results.append((item["id"], rank))
        print(f"{item['id']:>3}  rank={rank or '-'}  {item['question'][:70]}")

n = len(results)
recall_1 = sum(1 for _, r in results if r == 1) / n
recall_5 = sum(1 for _, r in results if r) / n
mrr = sum(1 / r for _, r in results if r) / n

print(f"\nquestions={n}  recall@1={recall_1:.2f}  recall@5={recall_5:.2f}  MRR={mrr:.2f}")