import json
from collections import defaultdict
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


def scores(ranks):
    n = len(ranks)
    return (sum(r == 1 for r in ranks) / n,
            sum(r is not None for r in ranks) / n,
            sum(1 / r for r in ranks if r) / n)


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
        results.append((item["type"], rank))
        print(f"{item['id']:>3}  rank={rank or '-'}  [{item['type']}]  {item['question'][:60]}")

groups = defaultdict(list)
for qtype, rank in results:
    groups["ALL"].append(rank)
    groups["hard (all)" if qtype.startswith("hard_") else "easy"].append(rank)
    if qtype.startswith("hard_"):
        groups[qtype].append(rank)

print(f"\n{'group':<18}{'n':>4}{'R@1':>7}{'R@5':>7}{'MRR':>7}")
for name in ["ALL", "easy", "hard (all)", "hard_misspell", "hard_lay", "hard_multipart", "hard_comparison"]:
    if name in groups:
        r1, r5, mrr = scores(groups[name])
        print(f"{name:<18}{len(groups[name]):>4}{r1:>7.2f}{r5:>7.2f}{mrr:>7.2f}")