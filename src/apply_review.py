import json

DRAFT = "eval/golden_draft.jsonl"
OUT = "eval/golden.jsonl"

REWRITES = {
    3: "Can prednisone cause eye problems?",
    4: "Can perphenazine cause problems with body movements?",
    6: "How does prednisone work in the body?",
    7: "Is metoclopramide safe for someone with a blocked or bleeding gut?",
    14: "Can I take trazodone together with an MAOI antidepressant?",
    20: "How is a potassium chloride overdose treated?",
    25: "Does tranexamic acid reach the baby if taken during pregnancy?",
    27: "When should I see a doctor about a sore mouth while using Equate Honey Lemon cough drops?",
}
DELETE = {13, 16, 29, 30, 31, 32}

HANDWRITTEN = [
    {"id": 1, "question": "Is there a pregnancy registry for patients taking ziprasidone, and how do doctors enroll them?",
     "section_ids": [3516], "type": "factual", "drug": "ziprasidone", "section": "pregnancy", "source": "handwritten",
     "reference_answer": "Yes. The National Pregnancy Registry for Atypical Antipsychotics monitors outcomes; providers can enroll patients by calling 1-866-961-2388 or online at womensmentalhealth.org."},
    {"id": 2, "question": "Who should not use Flovent Diskus?",
     "section_ids": [854], "type": "factual", "drug": "Flovent Diskus", "section": "contraindications", "source": "handwritten",
     "reference_answer": "Not as primary treatment for status asthmaticus or acute asthma needing intensive measures, or in people with severe milk-protein hypersensitivity or hypersensitivity to fluticasone propionate."},
]

UNANSWERABLE = [
    (29, "How much does a month of ziprasidone cost?"),
    (30, "Which pharmacies in Delhi stock Flovent Diskus?"),
    (31, "What do patients say about ibuprofen in online reviews?"),
    (32, "Who is the CEO of the company that makes amlodipine?"),
]

with open(DRAFT, encoding="utf-8") as f:
    drafts = [json.loads(line) for line in f if line.strip()]

final = list(HANDWRITTEN)
for item in drafts:
    if item["id"] in DELETE:
        continue
    if item["id"] in REWRITES:
        item["question"] = REWRITES[item["id"]]
        item["source"] = "reviewed"
    final.append(item)

for qid, question in UNANSWERABLE:
    final.append({"id": qid, "question": question, "section_ids": [], "type": "unanswerable",
                  "reference_answer": "Not found in the provided labels.", "source": "handwritten"})

with open(OUT, "w", encoding="utf-8") as f:
    for item in final:
        f.write(json.dumps(item) + "\n")

print(f"wrote {len(final)} questions to {OUT}")