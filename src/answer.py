import sys
from dotenv import load_dotenv
from openai import OpenAI
from search import search

load_dotenv()
client = OpenAI()

LLM = "gpt-5-mini"

PROMPT = """Answer the question using ONLY the context below.
Cite the chunk IDs you used in square brackets, like [8417].
If the context does not contain the answer, say "Not found in the provided labels."

Context:
{context}

Question: {question}"""


def answer(question, k=5):
    hits = search(question, k)
    context = "\n\n".join(f"[{cid}] {content}" for cid, _, content in hits)
    resp = client.chat.completions.create(
        model=LLM,
        messages=[{"role": "user", "content": PROMPT.format(context=context, question=question)}],
    )
    return resp.choices[0].message.content


if __name__ == "__main__":
    print(answer(" ".join(sys.argv[1:])))