import json
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("RAG_URL", "http://localhost:8080")
question = " ".join(sys.argv[1:]) or "Can I take trazodone with an MAOI?"

with requests.post(f"{URL}/ask/stream", json={"question": question},
                   headers={"X-API-Key": os.getenv("API_KEY")}, stream=True, timeout=120) as r:
    r.raise_for_status()
    for line in r.iter_lines(decode_unicode=True):
        if not line.startswith("data: "):
            continue
        event = json.loads(line[len("data: "):])
        if "token" in event:
            print(event["token"], end="", flush=True)
        if event.get("done"):
            print(f"\n\n[sources: {event['sources']}]")