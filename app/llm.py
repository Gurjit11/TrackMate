import time
from typing import Any, Type, TypeVar
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import GOOGLE_API_KEY, GEMINI_MODEL

T = TypeVar("T", bound=BaseModel)

def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0,
        api_version="v1beta",
    )

def call_structured(messages: list[Any], schema: Type[T]) -> T:
    llm = get_llm()
    structured_llm = llm.with_structured_output(schema)

    delays = [1.0, 2.0, 4.0]
    for attempt in range(len(delays) + 1):
        try:
            return structured_llm.invoke(messages)
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = "429" in err_str or "resource_exhausted" in err_str or "rate" in err_str
            is_server_error = "500" in err_str or "502" in err_str or "503" in err_str or "504" in err_str or "internal" in err_str

            if (is_rate_limit or is_server_error) and attempt < len(delays):
                time.sleep(delays[attempt])
                continue
            raise e

