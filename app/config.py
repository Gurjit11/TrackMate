import os
from dotenv import load_dotenv

load_dotenv()

for _var in ["GOOGLE_API_KEY", "GEMINI_MODEL", "GEMINI_EMBEDDING_MODEL"]:
    if not os.getenv(_var):
        raise ValueError(f"Missing required environment variable: {_var}")

GOOGLE_API_KEY: str = os.environ["GOOGLE_API_KEY"]
GEMINI_MODEL: str = os.environ["GEMINI_MODEL"]
GEMINI_EMBEDDING_MODEL: str = os.environ["GEMINI_EMBEDDING_MODEL"]

AS_OF_DATE: str = "2026-11-02"
RAG_TOP_K: int = 3
MAX_AGENT_STEPS: int = 6
EVAL_MIN_GAP_SECONDS: float = float(os.getenv("EVAL_MIN_GAP_SECONDS", "0"))

