import os
import re
import smtplib
from email.message import EmailMessage
from typing import Any

import httpx


class DeliveryConfigurationError(RuntimeError):
    pass


class DeliveryError(RuntimeError):
    pass


class DeliveryNotAllowed(RuntimeError):
    pass


def delivery_mode() -> str:
    mode = os.getenv("DELIVERY_MODE", "dry_run").strip().casefold()
    if mode not in {"dry_run", "live"}:
        raise DeliveryConfigurationError("DELIVERY_MODE must be 'dry_run' or 'live'.")
    return mode


def validate_live_delivery(channel: str, recipient: str, whatsapp_opt_in: bool) -> None:
    if not recipient.strip():
        raise DeliveryConfigurationError("A delivery recipient must be supplied.")
    if channel == "email":
        required = ["SMTP_HOST", "SMTP_FROM"]
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise DeliveryConfigurationError(
                f"Configure the following SMTP settings before sending: {', '.join(missing)}."
            )
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient.strip()):
            raise DeliveryConfigurationError("The email recipient address is invalid.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", os.environ["SMTP_FROM"]):
            raise DeliveryConfigurationError("SMTP_FROM must be a valid email address.")
        try:
            port = int(os.getenv("SMTP_PORT", "587"))
        except ValueError as error:
            raise DeliveryConfigurationError("SMTP_PORT must be a valid port number.") from error
        if not 1 <= port <= 65535:
            raise DeliveryConfigurationError("SMTP_PORT must be between 1 and 65535.")
        if not os.getenv("APPROVAL_TOKEN"):
            raise DeliveryConfigurationError(
                "APPROVAL_TOKEN must be configured before live delivery can be enabled."
            )
    elif channel == "whatsapp":
        required = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM"]
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise DeliveryConfigurationError(
                f"Configure the following Twilio settings before sending: {', '.join(missing)}."
            )
        if not re.fullmatch(r"\+[1-9]\d{7,14}", recipient.strip().removeprefix("whatsapp:")):
            raise DeliveryConfigurationError("The WhatsApp recipient must be an E.164 phone number.")
        from_number = os.environ["TWILIO_WHATSAPP_FROM"].strip().removeprefix("whatsapp:")
        if not re.fullmatch(r"\+[1-9]\d{7,14}", from_number):
            raise DeliveryConfigurationError("TWILIO_WHATSAPP_FROM must be an E.164 phone number.")
        if not whatsapp_opt_in:
            raise DeliveryNotAllowed(
                "Confirm that the recipient opted in to WhatsApp messages before approval."
            )
        if not os.getenv("APPROVAL_TOKEN"):
            raise DeliveryConfigurationError(
                "APPROVAL_TOKEN must be configured before live delivery can be enabled."
            )
    else:
        raise DeliveryConfigurationError(f"Unsupported delivery channel: {channel}.")


def send_email(recipient: str, subject: str, body: str) -> dict[str, Any]:
    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    sender = os.environ["SMTP_FROM"]
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    use_ssl = os.getenv("SMTP_USE_SSL", "false").strip().casefold() == "true"
    use_starttls = os.getenv("SMTP_STARTTLS", "true").strip().casefold() == "true"

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject or "TrackMate delivery update"
    message.set_content(body)

    try:
        client_type = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with client_type(host, port, timeout=20) as client:
            if not use_ssl and use_starttls:
                client.starttls()
            if username:
                client.login(username, password or "")
            client.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError) as error:
        raise DeliveryError(f"SMTP delivery failed: {error}") from error
    return {"provider": "smtp", "provider_message_id": message.get("Message-ID")}


def send_whatsapp(recipient: str, body: str) -> dict[str, Any]:
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    sender = os.environ["TWILIO_WHATSAPP_FROM"].strip()
    to_number = recipient.strip().removeprefix("whatsapp:")
    from_number = sender if sender.startswith("whatsapp:") else f"whatsapp:{sender}"
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    try:
        response = httpx.post(
            url,
            auth=(account_sid, auth_token),
            data={"From": from_number, "To": f"whatsapp:{to_number}", "Body": body},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise DeliveryError(f"Twilio WhatsApp delivery failed: {error}") from error
    return {"provider": "twilio_whatsapp", "provider_message_id": data.get("sid")}
