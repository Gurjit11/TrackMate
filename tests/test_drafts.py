import json

import pytest

from app import drafts
from app.delivery import DeliveryNotAllowed


def _use_tmp_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(drafts, "OUTBOX_FILE", tmp_path / "outbox.jsonl")


def test_approval_is_dry_run_by_default_and_idempotent(tmp_path, monkeypatch):
    _use_tmp_storage(tmp_path, monkeypatch)
    monkeypatch.delenv("DELIVERY_MODE", raising=False)
    draft = drafts.create_draft("run-1", "email", "Subject", "Body", "person@example.com")

    approved = drafts.approve_draft(draft["draft_id"])
    repeated = drafts.approve_draft(draft["draft_id"])

    assert approved["delivery_status"] == "dry_run_not_sent"
    assert repeated["delivery_status"] == "dry_run_not_sent"
    assert len((tmp_path / "outbox.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    assert json.loads((tmp_path / "outbox.jsonl").read_text(encoding="utf-8"))["delivery"] == "dry_run_not_sent"


def test_live_whatsapp_requires_opt_in_before_approval(tmp_path, monkeypatch):
    _use_tmp_storage(tmp_path, monkeypatch)
    monkeypatch.setenv("DELIVERY_MODE", "live")
    monkeypatch.setenv("APPROVAL_TOKEN", "test-token")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "test-sid")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test-auth")
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "+14155550100")
    draft = drafts.create_draft("run-2", "whatsapp", None, "Hello", "+14155550101")

    with pytest.raises(DeliveryNotAllowed):
        drafts.approve_draft(draft["draft_id"], whatsapp_opt_in=False)

    saved = json.loads((tmp_path / "drafts" / f"{draft['draft_id']}.json").read_text(encoding="utf-8"))
    assert saved["status"] == "pending_approval"
    assert saved["delivery_status"] == "awaiting_approval"


def test_live_email_sends_once_after_approval(tmp_path, monkeypatch):
    _use_tmp_storage(tmp_path, monkeypatch)
    monkeypatch.setenv("DELIVERY_MODE", "live")
    monkeypatch.setenv("APPROVAL_TOKEN", "test-token")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM", "trackmate@example.com")
    sends = []
    monkeypatch.setattr(
        drafts,
        "send_email",
        lambda recipient, subject, body: sends.append((recipient, subject, body))
        or {"provider": "smtp", "provider_message_id": "test-message"},
    )
    draft = drafts.create_draft("run-3", "email", "Subject", "Body", "person@example.com")

    approved = drafts.approve_draft(draft["draft_id"])
    repeated = drafts.approve_draft(draft["draft_id"])

    assert approved["delivery_status"] == "sent"
    assert repeated["delivery_status"] == "sent"
    assert sends == [("person@example.com", "Subject", "Body")]
    assert len((tmp_path / "outbox.jsonl").read_text(encoding="utf-8").splitlines()) == 1
