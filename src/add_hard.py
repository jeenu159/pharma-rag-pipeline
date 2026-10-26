import json

PATH = "eval/golden.jsonl"

with open(PATH, encoding="utf-8") as f:
    golden = [json.loads(line) for line in f if line.strip()]
by_id = {g["id"]: g for g in golden}

# (new_id, based_on_id(s), type, new question)
HARD = [
    (33, [3],  "hard_misspell",  "can prednizone mess with my eyesight"),
    (34, [14], "hard_misspell",  "is it ok to take trazadone with an maoi"),
    (35, [17], "hard_misspell",  "what is memantin used for"),
    (36, [10], "hard_misspell",  "how much famotadine is in one tablet"),
    (37, [21], "hard_misspell",  "naproxin dose for kids over 2"),
    (38, [4],  "hard_lay",       "My dad is on perphenazine and his tongue keeps moving on its own. Is that the medicine?"),
    (39, [19], "hard_lay",       "Could taking too many bupropion XL pills cause a fit?"),
    (40, [25], "hard_lay",       "I'm pregnant and was given tranexamic acid. Does it get to my baby?"),
    (41, [15], "hard_lay",       "My grandmother is 80. Does she need a smaller lacosamide dose because of her age?"),
    (42, [12], "hard_lay",       "When should I put on Botnia sunscreen before heading out?"),
    (43, [24], "hard_multipart", "At what blood count should perphenazine be stopped, and what other blood counts should be watched?"),
    (44, [11], "hard_multipart", "What's the highest daily amphetamine sulfate dose for a child with ADHD, and is going above it common?"),
    (45, [22], "hard_multipart", "Has memantine been tested in children, and at what ages?"),
    (46, [7, 8],  "hard_comparison", "Who should avoid metoclopramide, and who should avoid azithromycin?"),
    (47, [1, 25], "hard_comparison", "Are there pregnancy concerns for ziprasidone and for tranexamic acid?"),
]

existing = {g["id"] for g in golden}
added = 0
with open(PATH, "a", encoding="utf-8") as f:
    for new_id, base_ids, qtype, question in HARD:
        if new_id in existing:
            continue
        bases = [by_id[b] for b in base_ids]
        record = {
            "id": new_id,
            "question": question,
            "section_ids": [s for b in bases for s in b["section_ids"]],
            "type": qtype,
            "reference_answer": " ".join(b["reference_answer"] for b in bases),
            "drug": bases[0]["drug"] if len(bases) == 1 else "",
            "section": bases[0]["section"] if len(bases) == 1 else "",
            "source": "handwritten",
            "based_on": base_ids,
        }
        f.write(json.dumps(record) + "\n")
        added += 1

print(f"added {added} hard questions")