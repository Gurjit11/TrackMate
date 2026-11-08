from email.message import EmailMessage
from email.policy import SMTP

from fastapi.testclient import TestClient

from app import drafts, main
from app.schemas import AgentResult, Draft, FinalAnswer


client = TestClient(main.app)


def _email_bytes() -> bytes:
    message = EmailMessage(policy=SMTP)
    message["From"] = "Customer <customer@example.com>"
    message["To"] = "trackmate@example.com"
    message["Subject"] = "Delivery status TM1001"
    message.set_content("Please check the status of my shipment.")
    return message.as_bytes()


def test_email_intake_passes_extracted_tracking_and_sender_to_draft(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(drafts, "OUTBOX_FILE", tmp_path / "outbox.jsonl")
    calls = []

    def fake_run_agent(tracking_id, question, *, source):
        calls.append((tracking_id, question, source))
        return AgentResult(
            run_id="email-run",
            final=FinalAnswer(
                decision="ask_info",
                reply_to_user="Please confirm the address.",
                missing_info=["delivery address"],
                draft_message=Draft(
                    channel="email",
                    subject="Information needed",
                    body="Please confirm your delivery address.",
                ),
            ),
        )

    monkeypatch.setattr(main, "run_agent", fake_run_agent)
    response = client.post(
        "/intake/email",
        files={"file": ("order.eml", _email_bytes(), "message/rfc822")},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["tracking_id"] == "TM1001"
    assert result["draft"]["recipient"] == "customer@example.com"
    assert calls[0][0] == "TM1001"
    assert calls[0][2] == "email"


def test_live_approval_requires_token_and_sends_only_once(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(drafts, "OUTBOX_FILE", tmp_path / "outbox.jsonl")
    monkeypatch.setenv("DELIVERY_MODE", "live")
    monkeypatch.setenv("APPROVAL_TOKEN", "test-token")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM", "trackmate@example.com")
    sends = []
    monkeypatch.setattr(
        drafts,
        "send_email",
        lambda recipient, subject, body: sends.append(recipient)
        or {"provider": "smtp", "provider_message_id": "test-provider-id"},
    )
    draft = drafts.create_draft("api-run", "email", "Subject", "Body", "customer@example.com")

    unauthorized = client.post(f"/approve/{draft['draft_id']}", json={})
    approved = client.post(
        f"/approve/{draft['draft_id']}",
        json={},
        headers={"Authorization": "Bearer test-token"},
    )
    repeated = client.post(
        f"/approve/{draft['draft_id']}",
        json={},
        headers={"Authorization": "Bearer test-token"},
    )

    assert unauthorized.status_code == 401
    assert approved.status_code == 200
    assert approved.json()["delivery_status"] == "sent"
    assert repeated.json()["delivery_status"] == "sent"
    assert sends == ["customer@example.com"]
