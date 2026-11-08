import datetime
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Optional
import uuid

from app.delivery import (
    DeliveryConfigurationError,
    DeliveryError,
    DeliveryNotAllowed,
    delivery_mode,
    send_email,
    send_whatsapp,
    validate_live_delivery,
)

DRAFTS_DIR = Path(__file__).resolve().parent.parent / "drafts"
OUTBOX_FILE = Path(__file__).resolve().parent.parent / "outbox.jsonl"
_DRAFT_LOCK = threading.Lock()


def create_draft(
    run_id: str,
    channel: str,
    subject: Optional[str],
    body: str,
    recipient: Optional[str] = None,
) -> dict[str, Any]:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    draft_id = uuid.uuid4().hex
    record: dict[str, Any] = {
        "draft_id": draft_id,
        "run_id": run_id,
        "channel": channel,
        "subject": subject,
        "body": body,
        "recipient": recipient,
        "status": "pending_approval",
        "delivery_status": "awaiting_approval",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    file_path = DRAFTS_DIR / f"{draft_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    return record


def _write_record(file_path: Path, record: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=DRAFTS_DIR, delete=False
    ) as temporary:
        json.dump(record, temporary, indent=2)
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, file_path)


def _append_outbox(record: dict[str, Any]) -> None:
    entry = {
        "draft_id": record["draft_id"],
        "run_id": record["run_id"],
        "channel": record["channel"],
        "recipient": record.get("recipient"),
        "subject": record.get("subject"),
        "body": record["body"],
        "approved_at": record["approved_at"],
        "delivery": record.get("delivery_status"),
        "provider": record.get("provider"),
        "provider_message_id": record.get("provider_message_id"),
        "delivery_error": record.get("delivery_error"),
    }
    with open(OUTBOX_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry) + "\n")


def approve_draft(
    draft_id: str,
    *,
    recipient: Optional[str] = None,
    whatsapp_opt_in: bool = False,
) -> Optional[dict[str, Any]]:
    if not all(char in "0123456789abcdef" for char in draft_id) or len(draft_id) != 32:
        return None
    file_path = DRAFTS_DIR / f"{draft_id}.json"
    with _DRAFT_LOCK:
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as file:
            record: dict[str, Any] = json.load(file)
        if record.get("status") != "pending_approval":
            return record

        resolved_recipient = recipient.strip() if recipient and recipient.strip() else record.get("recipient")
        mode = delivery_mode()
        if mode == "live":
            validate_live_delivery(
                record["channel"], resolved_recipient or "", whatsapp_opt_in
            )

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        record["recipient"] = resolved_recipient
        record["status"] = "approved"
        record["approved_at"] = now

        if mode == "dry_run":
            record["delivery_status"] = "dry_run_not_sent"
            _write_record(file_path, record)
            _append_outbox(record)
            return record

        record["delivery_status"] = "sending"
        _write_record(file_path, record)
        try:
            if record["channel"] == "email":
                delivery = send_email(
                    resolved_recipient or "",
                    record.get("subject") or "TrackMate delivery update",
                    record["body"],
                )
            elif record["channel"] == "whatsapp":
                delivery = send_whatsapp(resolved_recipient or "", record["body"])
            else:
                raise DeliveryConfigurationError(
                    f"Unsupported delivery channel: {record['channel']}."
                )
        except DeliveryNotAllowed:
            record["delivery_status"] = "awaiting_approval"
            record["status"] = "pending_approval"
            record.pop("approved_at", None)
            _write_record(file_path, record)
            raise
        except DeliveryConfigurationError:
            record["delivery_status"] = "awaiting_approval"
            record["status"] = "pending_approval"
            record.pop("approved_at", None)
            _write_record(file_path, record)
            raise
        except DeliveryError as error:
            record["delivery_status"] = "delivery_failed"
            record["delivery_error"] = str(error)
            record["delivery_finished_at"] = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
            _write_record(file_path, record)
            _append_outbox(record)
            raise

        record["delivery_status"] = "sent"
        record["provider"] = delivery["provider"]
        record["provider_message_id"] = delivery.get("provider_message_id")
        record["delivery_finished_at"] = datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat()
        _write_record(file_path, record)
        _append_outbox(record)
        return record
