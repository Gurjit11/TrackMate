from email.message import EmailMessage
from email.policy import SMTP

import pytest
from fastapi import HTTPException

from app.email_intake import parse_forwarded_email


def _email_bytes() -> bytes:
    message = EmailMessage(policy=SMTP)
    message["From"] = "Customer <customer@example.com>"
    message["To"] = "support@example.com"
    message["Subject"] = "Where is order TM-1018?"
    message.set_content("Could you check the delayed parcel?")
    return message.as_bytes()


def test_parse_forwarded_email_extracts_sender_subject_tracking_and_body():
    parsed = parse_forwarded_email(_email_bytes())

    assert parsed == {
        "sender": "customer@example.com",
        "subject": "Where is order TM-1018?",
        "tracking_id": "TM1018",
        "question": "Subject: Where is order TM-1018?\n\nCould you check the delayed parcel?",
    }


def test_parse_forwarded_email_rejects_missing_sender():
    message = EmailMessage(policy=SMTP)
    message.set_content("No sender header")

    with pytest.raises(HTTPException) as error:
        parse_forwarded_email(message.as_bytes())

    assert error.value.status_code == 422


def test_parse_forwarded_email_rejects_oversized_file():
    with pytest.raises(HTTPException) as error:
        parse_forwarded_email(b"x" * (2 * 1024 * 1024 + 1))

    assert error.value.status_code == 413
