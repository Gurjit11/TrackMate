import os
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from app.config import GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_EMBEDDING_MODEL

chat_model = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    google_api_key=GOOGLE_API_KEY,
    temperature=0,
)

response = chat_model.invoke("Reply with the single word: ready")
print(f"Chat reply: {response.content.strip()}")

embedding_model = GoogleGenerativeAIEmbeddings(
    model=GEMINI_EMBEDDING_MODEL,
    google_api_key=GOOGLE_API_KEY,
)

vector = embedding_model.embed_query("hello")
print(f"Embedding vector length: {len(vector)}")
