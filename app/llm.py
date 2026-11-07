import os
import time
from typing import Any, Type, TypeVar
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import GOOGLE_API_KEY, GEMINI_MODEL

T = TypeVar("T", bound=BaseModel)

_last_call_timestamp: float = 0.0


def pace_llm_call() -> None:
    global _last_call_timestamp
    min_gap = float(os.getenv("EVAL_MIN_GAP_SECONDS", "13.0"))
    if min_gap > 0 and _last_call_timestamp > 0:
        elapsed = time.time() - _last_call_timestamp
        if elapsed < min_gap:
            time.sleep(min_gap - elapsed)
    _last_call_timestamp = time.time()


def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0,
        api_version="v1beta",
        max_retries=0,
    )


def call_structured(messages: list[Any], schema: Type[T]) -> T:
    llm = get_llm()
    structured_llm = llm.with_structured_output(schema)

    delays = [1.0, 2.0, 4.0]
    for attempt in range(len(delays) + 1):
        try:
            pace_llm_call()
            return structured_llm.invoke(messages)
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = "429" in err_str or "resource_exhausted" in err_str or "rate" in err_str
            is_server_error = "500" in err_str or "502" in err_str or "503" in err_str or "504" in err_str or "internal" in err_str

            if (is_rate_limit or is_server_error) and attempt < len(delays):
                time.sleep(delays[attempt])
                continue
            raise e
