import json
from collections import defaultdict
import psycopg
from search import search, DSN, STRATEGY, MODE, RERANK

K = 5

with open("eval/golden.jsonl", encoding="utf-8") as f:
    golden = [json.loads(line) for line in f if line.strip()]


def scores(ranks):
    n = len(ranks)
    return (sum(r == 1 for r in ranks) / n,
            sum(r is not None for r in ranks) / n,
            sum(1 / r for r in ranks if r) / n)


results = []
with psycopg.connect(DSN) as conn:
    all_ids = list({sid for g in golden for sid in g["section_ids"]})
    pair = {sid: (gen, sec) for sid, gen, sec in conn.execute(
        "SELECT id, generic_name, section FROM label_sections WHERE id = ANY(%s)", (all_ids,))}

    for item in golden:
        if item["type"] == "unanswerable":
            continue
        relevant = {pair[sid] for sid in item["section_ids"]}
        chunk_ids = [cid for cid, _, _ in search(item["question"], K)]
        rows = conn.execute("""
            SELECT c.id, s.generic_name, s.section
            FROM chunks c
            JOIN label_sections s ON s.id = c.section_id
            WHERE c.id = ANY(%s)
        """, (chunk_ids,)).fetchall()
        meta = {cid: (gen, sec) for cid, gen, sec in rows}

        rank = next((i + 1 for i, cid in enumerate(chunk_ids) if meta[cid] in relevant), None)
        results.append((item["type"], rank))
        print(f"{item['id']:>3}  rank={rank or '-'}  [{item['type']}]  {item['question'][:60]}")

groups = defaultdict(list)
for qtype, rank in results:
    groups["ALL"].append(rank)
    groups["hard (all)" if qtype.startswith("hard_") else "easy"].append(rank)
    if qtype.startswith("hard_"):
        groups[qtype].append(rank)

print(f"\nstrategy = {STRATEGY}  mode = {MODE}  rerank = {RERANK}")
print(f"{'group':<18}{'n':>4}{'R@1':>7}{'R@5':>7}{'MRR':>7}")
for name in ["ALL", "easy", "hard (all)", "hard_misspell", "hard_lay", "hard_multipart", "hard_comparison"]:
    if name in groups:
        r1, r5, mrr = scores(groups[name])
        print(f"{name:<18}{len(groups[name]):>4}{r1:>7.2f}{r5:>7.2f}{mrr:>7.2f}")