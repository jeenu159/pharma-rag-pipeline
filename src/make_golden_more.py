import json
import psycopg
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

DSN = "host=localhost port=5434 dbname=pharma user=rag password=rag"
LLM = "gpt-5-mini"
GOLDEN = "eval/golden.jsonl"
OUT = "eval/golden_draft2.jsonl"
PER_SECTION = 3

SECTIONS = [
    "indications_and_usage", "dosage_and_administration", "warnings",
    "adverse_reactions", "contraindications", "drug_interactions",
    "overdosage", "pregnancy", "pediatric_use", "geriatric_use",
    "clinical_pharmacology", "description", "precautions",
]

PROMPT = """You are writing test questions for a drug-label search system.

Drug: {drug}
Section: {section}
Text:
{text}

Write ONE question a patient, caregiver or pharmacist would realistically ask that this text answers.
Rules:
- Mention the drug by name, the way a normal person would write it.
- Use everyday wording. Do NOT copy any phrase of 3 or more consecutive words from the text.
- Do NOT ask about clinical trial details, patient counts, statistics or animal studies.
- The answer must be fully contained in the text.
- If a specific number (dose, age, duration, amount) makes a good answer, prefer it and set type to "numeric". Otherwise type is "factual".

Return JSON only: {{"question": "...", "reference_answer": "1-2 sentences in your own words", "type": "factual or numeric"}}"""

with open(GOLDEN, encoding="utf-8") as f:
    golden = [json.loads(line) for line in f if line.strip()]
used_sections = list({sid for g in golden for sid in g["section_ids"]})
next_id = max(g["id"] for g in golden) + 1

with psycopg.connect(DSN) as conn:
    used_generics = [r[0] for r in conn.execute(
        "SELECT DISTINCT generic_name FROM label_sections WHERE id = ANY(%s)", (used_sections,))]
    rows = conn.execute("""
        SELECT id, drug_name, section, content FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY section ORDER BY random()) AS rn
            FROM label_sections
            WHERE section = ANY(%s)
              AND LENGTH(content) > 300
              AND generic_name <> ALL(%s)
        ) t
        WHERE rn <= %s
    """, (SECTIONS, used_generics, PER_SECTION)).fetchall()

with open(OUT, "w", encoding="utf-8") as f:
    for i, (sec_id, drug, section, content) in enumerate(rows, start=next_id):
        resp = client.chat.completions.create(
            model=LLM,
            messages=[{"role": "user", "content": PROMPT.format(drug=drug, section=section, text=content[:3000])}],
            response_format={"type": "json_object"},
        )
        item = json.loads(resp.choices[0].message.content)
        record = {
            "id": i,
            "question": item["question"],
            "section_ids": [sec_id],
            "type": item["type"],
            "reference_answer": item["reference_answer"],
            "drug": drug,
            "section": section,
            "source": "llm_draft",
        }
        f.write(json.dumps(record) + "\n")
        print(f"{i}. [{section}] ({drug}) {item['question']}")

print(f"wrote {len(rows)} drafts to {OUT}")