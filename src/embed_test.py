from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

resp = client.embeddings.create(
    model="text-embedding-3-small",
    input="ibuprofen may cause stomach bleeding",
)
vec = resp.data[0].embedding
print(len(vec), vec[:5])