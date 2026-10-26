import json
import psycopg
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

DSN = "host=localhost port=5434 dbname=pharma user=rag password=rag"
LLM = "gpt-5-mini"
OUT = "eval/golden_draft.jsonl"

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

Write ONE question a patient, pharmacist or doctor might realistically ask that this text answers.
Rules:
- Mention the drug by name.
- Use everyday wording. Do NOT copy phrases from the text.
- The answer must be fully contained in the text.
- If a specific number (dose, percentage, age, duration) makes a good answer, prefer it and set type to "numeric". Otherwise type is "factual".

Return JSON only: {{"question": "...", "reference_answer": "1-2 sentences", "type": "factual or numeric"}}"""

with psycopg.connect(DSN) as conn:
    rows = conn.execute("""
        SELECT id, drug_name, section, content FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY section ORDER BY random()) AS rn
            FROM label_sections
            WHERE section = ANY(%s) AND drug_name <> 'unknown' AND LENGTH(content) > 300
        ) t
        WHERE rn <= 2
    """, (SECTIONS,)).fetchall()

with open(OUT, "w", encoding="utf-8") as f:
    for i, (sec_id, drug, section, content) in enumerate(rows, start=3):
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
        print(f"{i}. [{section}] {item['question']}")

print(f"wrote {len(rows)} drafts to {OUT}")