import os
import sys
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: Missing required environment variable: GOOGLE_API_KEY", file=sys.stderr)
    sys.exit(1)

client = genai.Client(api_key=api_key)

text_models = []
embedding_models = []

for model in client.models.list():
    actions = model.supported_actions or []
    name = model.name
    if any("generateContent" in a or "generate_content" in a for a in actions):
        text_models.append(name)
    if any("embedContent" in a or "embed_content" in a for a in actions):
        embedding_models.append(name)

print("=== Models supporting text generation ===")
for m in text_models:
    print(m)

print("\n=== Models supporting embeddings ===")
for m in embedding_models:
    print(m)

