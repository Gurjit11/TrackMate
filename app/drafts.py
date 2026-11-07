import datetime
import json
from pathlib import Path
from typing import Any, Optional
import uuid

DRAFTS_DIR = Path(__file__).resolve().parent.parent / "drafts"
OUTBOX_FILE = Path(__file__).resolve().parent.parent / "outbox.jsonl"


def create_draft(
    run_id: str, channel: str, subject: Optional[str], body: str
) -> dict[str, Any]:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    draft_id = uuid.uuid4().hex
    record: dict[str, Any] = {
        "draft_id": draft_id,
        "run_id": run_id,
        "channel": channel,
        "subject": subject,
        "body": body,
        "status": "pending_approval",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    file_path = DRAFTS_DIR / f"{draft_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    return record


def approve_draft(draft_id: str) -> Optional[dict[str, Any]]:
    file_path = DRAFTS_DIR / f"{draft_id}.json"
    if not file_path.exists():
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        record: dict[str, Any] = json.load(f)

    if record.get("status") == "approved":
        return record

    record["status"] = "approved"
    record["approved_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    outbox_entry = {
        "draft_id": record["draft_id"],
        "run_id": record["run_id"],
        "channel": record["channel"],
        "subject": record.get("subject"),
        "body": record["body"],
        "approved_at": record["approved_at"],
        "delivery": "dry_run_not_sent",
    }
    with open(OUTBOX_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(outbox_entry) + "\n")

    return record

