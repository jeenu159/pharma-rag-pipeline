import asyncio
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory
from ragas.metrics.collections import Faithfulness, ContextPrecision, ContextRecall, AnswerRelevancy

load_dotenv()

RUN = sys.argv[1] if len(sys.argv) > 1 else "eval/runs/answers_20261102_1431.jsonl"
LIMIT = int(os.getenv("RAGAS_LIMIT", "0"))          # 0 = all questions
RAGAS_LLM = os.getenv("RAGAS_LLM", "gpt-4.1-mini")

client = AsyncOpenAI()
llm = llm_factory(RAGAS_LLM, client=client)
emb = embedding_factory("openai", model="text-embedding-3-small", client=client)

faithfulness = Faithfulness(llm=llm)
context_precision = ContextPrecision(llm=llm)
context_recall = ContextRecall(llm=llm)
answer_relevancy = AnswerRelevancy(llm=llm, embeddings=emb)

with open(RUN, encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]
records = [r for r in records if r["type"] != "unanswerable"]
if LIMIT:
    records = records[:LIMIT]

sem = asyncio.Semaphore(4)   # at most 4 questions scored at once


async def score(r):
    contexts = [content for _, content in r["context"]]
    out = {"id": r["id"], "type": r["type"],
           "judge_faithful": r["faithful"], "judge_correct": r["correct"]}
    async with sem:
        try:
            out["faithfulness"] = (await faithfulness.ascore(
                user_input=r["question"], response=r["answer"], retrieved_contexts=contexts)).value
            out["context_precision"] = (await context_precision.ascore(
                user_input=r["question"], reference=r["reference_answer"], retrieved_contexts=contexts)).value
            out["context_recall"] = (await context_recall.ascore(
                user_input=r["question"], retrieved_contexts=contexts, reference=r["reference_answer"])).value
            out["answer_relevancy"] = (await answer_relevancy.ascore(
                user_input=r["question"], response=r["answer"])).value
        except Exception as e:
            out["error"] = f"{type(e).__name__}: {e}"[:300]
    if "error" in out:
        print(f"{r['id']:>3}  ERROR {out['error']}")
    else:
        print(f"{r['id']:>3}  faith={out['faithfulness']:.2f}  ctx_prec={out['context_precision']:.2f}  "
              f"ctx_rec={out['context_recall']:.2f}  relev={out['answer_relevancy']:.2f}  judge={r['faithful']}")
    return out


async def main():
    results = await asyncio.gather(*(score(r) for r in records))
    ok = [r for r in results if "error" not in r]

    print(f"\nscored {len(ok)}/{len(results)} questions with {RAGAS_LLM}")
    for m in ["faithfulness", "context_precision", "context_recall", "answer_relevancy"]:
        if ok:
            print(f"{m:<18} = {sum(r[m] for r in ok) / len(ok):.3f}")

    # RAGAS faithfulness vs the GPT-5 judge: RAGAS < 1.0 means at least one unsupported claim
    both = [r for r in ok if r["faithfulness"] < 1.0 and r["judge_faithful"] == "no"]
    ragas_only = [r for r in ok if r["faithfulness"] < 1.0 and r["judge_faithful"] == "yes"]
    judge_only = [r for r in ok if r["faithfulness"] == 1.0 and r["judge_faithful"] == "no"]
    print(f"\nflagged unfaithful by both:        {len(both):>3}  {[r['id'] for r in both]}")
    print(f"flagged by RAGAS only:             {len(ragas_only):>3}  {[r['id'] for r in ragas_only]}")
    print(f"flagged by judge only:             {len(judge_only):>3}  {[r['id'] for r in judge_only]}")
    print(f"agreement on faithful vs not:      {(len(ok) - len(ragas_only) - len(judge_only)) / max(len(ok), 1):.2f}")

    os.makedirs("eval/runs", exist_ok=True)
    out_file = f"eval/runs/ragas_{datetime.now():%Y%m%d_%H%M}.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"saved to {out_file}")


asyncio.run(main())