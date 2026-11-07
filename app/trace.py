import json
import uuid
from pathlib import Path
from typing import Any, Optional

TRACES_DIR = Path(__file__).resolve().parent.parent / "traces"

def new_run_id() -> str:
    return uuid.uuid4().hex

def save_trace(trace: dict[str, Any]) -> None:
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    run_id = trace["run_id"]
    file_path = TRACES_DIR / f"{run_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2)

def load_trace(run_id: str) -> Optional[dict[str, Any]]:
    file_path = TRACES_DIR / f"{run_id}.json"
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

