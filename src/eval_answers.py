import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from answer import answer

load_dotenv()
client = OpenAI()

JUDGE = "gpt-5"
PRICE_IN, PRICE_OUT = 0.25, 2.00  # USD per 1M tokens for gpt-5-mini; update if pricing changes

JUDGE_PROMPT = """You are grading an answer from a drug-label Q&A system.

Question: {question}
Reference answer: {reference}

Retrieved context:
{context}

System answer:
{answer}

Grade two things:
1. faithful: "yes" if EVERY claim in the system answer is supported by the retrieved context, otherwise "no".
2. correct: compared with the reference answer, "yes" if it has the key facts, "partial" if some are missing, "no" if wrong or missing.

Return JSON only: {{"faithful": "yes or no", "correct": "yes or partial or no", "reason": "one short sentence"}}"""

with open("eval/golden.jsonl", encoding="utf-8") as f:
    golden = [json.loads(line) for line in f if line.strip()]

os.makedirs("eval/runs", exist_ok=True)
run_file = f"eval/runs/answers_{datetime.now():%Y%m%d_%H%M}.jsonl"
records = []

for item in golden:
    t0 = time.perf_counter()
    out = answer(item["question"])
    latency = time.perf_counter() - t0
    u = out["usage"]
    cost = (u.prompt_tokens * PRICE_IN + u.completion_tokens * PRICE_OUT) / 1_000_000

    if item["type"] == "unanswerable":
        refused = "not found" in out["text"].lower()
        grade = {"faithful": "yes" if refused else "no",
                 "correct": "yes" if refused else "no",
                 "reason": "abstained correctly" if refused else "answered an unanswerable question"}
    else:
        context = "\n\n".join(f"[{cid}] {content}" for cid, _, content in out["hits"])
        resp = client.chat.completions.create(
            model=JUDGE,
            messages=[{"role": "user", "content": JUDGE_PROMPT.format(
                question=item["question"], reference=item["reference_answer"],
                context=context, answer=out["text"])}],
            response_format={"type": "json_object"},
        )
        grade = json.loads(resp.choices[0].message.content)

    rec = {"id": item["id"], "type": item["type"], "latency_s": round(latency, 2),
           "cost_usd": cost, **grade, "answer": out["text"]}
    records.append(rec)
    print(f"{item['id']:>3}  faithful={grade['faithful']:<3}  correct={grade['correct']:<7}  {latency:4.1f}s  {grade['reason'][:60]}")

with open(run_file, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec) + "\n")

n = len(records)
answerable = [r for r in records if r["type"] != "unanswerable"]
unanswerable = [r for r in records if r["type"] == "unanswerable"]
latencies = sorted(r["latency_s"] for r in records)

print(f"\nfaithfulness      = {sum(r['faithful'] == 'yes' for r in answerable) / len(answerable):.2f}")
print(f"correct (full)    = {sum(r['correct'] == 'yes' for r in answerable) / len(answerable):.2f}")
print(f"correct (partial) = {sum(r['correct'] == 'partial' for r in answerable) / len(answerable):.2f}")
print(f"abstention        = {sum(r['correct'] == 'yes' for r in unanswerable)}/{len(unanswerable)}")
print(f"latency median    = {latencies[n // 2]:.1f}s   max = {latencies[-1]:.1f}s")
print(f"cost per query    = ${sum(r['cost_usd'] for r in records) / n:.5f}")
print(f"saved to {run_file}")