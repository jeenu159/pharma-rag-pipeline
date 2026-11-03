import json
import os
import time
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from answer import answer, PROMPT, LLM, client
from search import search

load_dotenv()
API_KEY = os.getenv("API_KEY")
K = int(os.getenv("RAG_K", "3"))

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Pharma RAG API", version="1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def check_key(x_api_key: str = Header(default="")):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing API key")


class Ask(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", dependencies=[Depends(check_key)])
@limiter.limit("10/minute")
def ask(request: Request, body: Ask):
    t0 = time.perf_counter()
    out = answer(body.question)
    u = out["usage"]
    return {
        "answer": out["text"],
        "sources": [{"chunk_id": cid, "preview": content[:200]} for cid, _, content in out["hits"]],
        "latency_s": round(time.perf_counter() - t0, 2),
        "tokens": {"input": u.prompt_tokens, "output": u.completion_tokens},
    }


@app.post("/ask/stream", dependencies=[Depends(check_key)])
@limiter.limit("10/minute")
def ask_stream(request: Request, body: Ask):
    hits = search(body.question, K)
    context = "\n\n".join(f"[{cid}] {content}" for cid, _, content in hits)

    def events():
        stream = client.chat.completions.create(
            model=LLM,
            messages=[{"role": "user", "content": PROMPT.format(context=context, question=body.question)}],
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield f"data: {json.dumps({'token': delta})}\n\n"
        yield f"data: {json.dumps({'done': True, 'sources': [cid for cid, _, _ in hits]})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")