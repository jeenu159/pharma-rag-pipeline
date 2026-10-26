import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

LLM = "gpt-5-mini"
CACHE = "data/raw/extracted_names.json"

PROMPT = """From this drug label text, extract the product's brand name and generic (active ingredient) name.

Product data: {product}
Package label: {package}

If there is no separate brand name, use the generic name for both.
Return JSON only: {{"brand_name": "...", "generic_name": "..."}}"""

with open("data/raw/labels.json", encoding="utf-8") as f:
    labels = json.load(f)

names = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}

todo = [x for x in labels
        if not x.get("openfda", {}).get("brand_name")
        and not x.get("openfda", {}).get("generic_name")
        and x["id"] not in names]
print(f"{len(todo)} labels to name")

for i, label in enumerate(todo, start=1):
    product = " ".join(label.get("spl_product_data_elements", []))[:400]
    package = " ".join(label.get("package_label_principal_display_panel", []))[:400]
    resp = client.chat.completions.create(
        model=LLM,
        messages=[{"role": "user", "content": PROMPT.format(product=product, package=package)}],
        response_format={"type": "json_object"},
    )
    names[label["id"]] = json.loads(resp.choices[0].message.content)

    if i % 25 == 0 or i == len(todo):
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(names, f, indent=1)
        print(f"named {i} / {len(todo)}  e.g. {names[label['id']]}")

print("done")