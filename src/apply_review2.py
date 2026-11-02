import json

DRAFT = "eval/golden_draft2.jsonl"
GOLDEN = "eval/golden.jsonl"

DELETE = {48}
REWRITES = {
    49: "Can nizatidine affect my liver?",
    53: "How does hydrocortisone work in the body?",
    69: "What is clopidogrel prescribed for?",
    71: "Is doxorubicin used to treat breast cancer?",
    79: "Does etoposide need a lower dose for people with kidney problems?",
}
REFERENCE_FIXES = {
    50: "Drowsiness is common when starting or after a dose increase; headache, fatigue and weakness can also occur. "
        "More serious effects can involve the heart, liver, blood cells (including destruction of red blood cells) and mood.",
}

# (new_id, based_on_id(s), type, question)
HARD = [
    (87, [70], "hard_misspell", "what is buspiron for"),
    (88, [66], "hard_misspell", "ambian dose for elderly"),
    (89, [76], "hard_misspell", "is glimeperide ok for kids with diabetes"),
    (90, [65], "hard_misspell", "when to stop dipyridamol before a stress test"),
    (91, [78], "hard_lay", "I put lidocaine gel in my mouth for a sore. How long until I can eat?"),
    (92, [56], "hard_lay", "My 10 year old is in a lot of pain. Can he have tramadol?"),
    (93, [84], "hard_lay", "Can I put dibucaine ointment on my baby?"),
    (94, [83], "hard_lay", "I have TB and just found out I'm pregnant. Can I keep taking isoniazid?"),
    (95, [60], "hard_multipart", "How much Plaquenil do I take to prevent malaria, and when do I start and stop?"),
    (96, [85], "hard_multipart", "When should I stop using Mentholatum Pain Relieving, and how long can I use it before seeing a doctor?"),
    (97, [75, 76], "hard_comparison", "Can children take tamsulosin or glimepiride?"),
    (98, [66, 67], "hard_comparison", "Do older adults need lower doses of Ambien and of atenolol?"),
]

UNANSWERABLE = [
    (99,  "What is the price of clopidogrel in India?"),
    (100, "Which brand of sertraline is the best?"),
    (101, "Can I buy metformin without a prescription in Delhi?"),
    (102, "Does insurance usually cover Plaquenil?"),
    (103, "How many people take atenolol worldwide?"),
    (104, "Which company makes the cheapest famotidine?"),
]

with open(GOLDEN, encoding="utf-8") as f:
    existing = {json.loads(line)["id"] for line in f if line.strip()}

with open(DRAFT, encoding="utf-8") as f:
    drafts = [json.loads(line) for line in f if line.strip()]

new_items = []
for item in drafts:
    if item["id"] in DELETE:
        continue
    if item["id"] in REWRITES:
        item["question"] = REWRITES[item["id"]]
        item["source"] = "reviewed"
    if item["id"] in REFERENCE_FIXES:
        item["reference_answer"] = REFERENCE_FIXES[item["id"]]
        item["source"] = "reviewed"
    new_items.append(item)

by_id = {item["id"]: item for item in new_items}
for new_id, base_ids, qtype, question in HARD:
    bases = [by_id[b] for b in base_ids]
    new_items.append({
        "id": new_id,
        "question": question,
        "section_ids": [s for b in bases for s in b["section_ids"]],
        "type": qtype,
        "reference_answer": " ".join(b["reference_answer"] for b in bases),
        "drug": bases[0]["drug"] if len(bases) == 1 else "",
        "section": bases[0]["section"] if len(bases) == 1 else "",
        "source": "handwritten",
        "based_on": base_ids,
    })

for qid, question in UNANSWERABLE:
    new_items.append({"id": qid, "question": question, "section_ids": [], "type": "unanswerable",
                      "reference_answer": "Not found in the provided labels.", "source": "handwritten"})

added = 0
with open(GOLDEN, "a", encoding="utf-8") as f:
    for item in new_items:
        if item["id"] in existing:
            continue
        f.write(json.dumps(item) + "\n")
        added += 1

with open(GOLDEN, encoding="utf-8") as f:
    total = sum(1 for line in f if line.strip())
print(f"added {added} questions; golden set now has {total}")