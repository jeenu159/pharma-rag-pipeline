import json
import os
import random
import sys
import textwrap

RUN = sys.argv[1] if len(sys.argv) > 1 else "eval/runs/answers_20261102_1216.jsonl"
OUT = "eval/human_labels.jsonl"
N_RANDOM = 16

with open(RUN, encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

answerable = [r for r in records if r["type"] != "unanswerable"]
flagged = [r for r in answerable if r["faithful"] == "no"]
others = [r for r in answerable if r["faithful"] != "no"]

random.seed(42)
sample = flagged + random.sample(others, min(N_RANDOM, len(others)))
random.shuffle(sample)   # hides which ones the judge flagged

done = set()
if os.path.exists(OUT):
    with open(OUT, encoding="utf-8") as f:
        done = {json.loads(line)["id"] for line in f if line.strip()}


def ask(prompt, options):
    while True:
        a = input(prompt).strip().lower()
        if a in options:
            return a


for i, r in enumerate(sample, start=1):
    if r["id"] in done:
        continue
    print("=" * 100)
    print(f"[{i}/{len(sample)}]  Q{r['id']}: {r['question']}\n")
    print(f"REFERENCE: {r['reference_answer']}\n")
    print("CONTEXT (what the LLM saw):")
    for cid, content in r["context"]:
        print(f"\n--- [{cid}] ---")
        print(textwrap.fill(content, 100))
    print(f"\nANSWER:\n{textwrap.fill(r['answer'], 100)}\n")

    f_ans = ask("Faithful? Is EVERY claim in the answer supported by the CONTEXT? (y/n, q = quit): ", {"y", "n", "q"})
    if f_ans == "q":
        break
    c_ans = ask("Correct vs REFERENCE? (y = has key facts / p = partial / n = wrong): ", {"y", "p", "n"})

    with open(OUT, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "id": r["id"],
            "run": RUN,
            "human_faithful": "yes" if f_ans == "y" else "no",
            "human_correct": {"y": "yes", "p": "partial", "n": "no"}[c_ans],
        }) + "\n")

print(f"\nlabels saved to {OUT}")