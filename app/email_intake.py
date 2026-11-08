import re
from email import policy
from email.header import decode_header, make_header
from email.parser import BytesParser
from email.utils import parseaddr

from fastapi import HTTPException

MAX_EMAIL_BYTES = 2 * 1024 * 1024
MAX_EMAIL_TEXT_CHARS = 8_000
TRACKING_ID_PATTERN = re.compile(r"\bTM[\s-]?\d{3,}\b", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _decoded_header(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except (LookupError, UnicodeError, ValueError):
        return value


def parse_forwarded_email(raw_message: bytes) -> dict[str, str | None]:
    if not raw_message:
        raise HTTPException(status_code=422, detail="The uploaded email is empty.")
    if len(raw_message) > MAX_EMAIL_BYTES:
        raise HTTPException(status_code=413, detail="Email file exceeds the 2 MB limit.")

    message = BytesParser(policy=policy.default).parsebytes(raw_message)
    if not message.get("From"):
        raise HTTPException(status_code=422, detail="The email must include a From address.")

    _, sender = parseaddr(str(message["From"]))
    if not EMAIL_PATTERN.fullmatch(sender):
        raise HTTPException(status_code=422, detail="The email sender address is invalid.")

    text_parts: list[str] = []
    if message.is_multipart():
        parts = message.walk()
    else:
        parts = [message]

    for part in parts:
        if part.get_content_type() != "text/plain":
            continue
        if part.get_content_disposition() == "attachment":
            continue
        try:
            content = part.get_content()
        except (LookupError, UnicodeError):
            payload = part.get_payload(decode=True) or b""
            content = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if isinstance(content, str) and content.strip():
            text_parts.append(content.strip())

    body = "\n\n".join(text_parts).strip()
    if not body:
        raise HTTPException(
            status_code=422,
            detail="No readable plain-text body was found. Save or forward the message as .eml with a text body.",
        )
    if len(body) > MAX_EMAIL_TEXT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Email body exceeds the {MAX_EMAIL_TEXT_CHARS}-character processing limit.",
        )

    subject = _decoded_header(str(message.get("Subject", ""))).strip()
    tracking_match = TRACKING_ID_PATTERN.search(f"{subject}\n{body}")
    tracking_id = re.sub(r"[\s-]", "", tracking_match.group(0)).upper() if tracking_match else None
    question = f"Subject: {subject}\n\n{body}" if subject else body
    return {
        "sender": sender,
        "subject": subject,
        "tracking_id": tracking_id,
        "question": question,
    }
