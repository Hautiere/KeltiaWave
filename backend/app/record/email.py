"""Account-authenticated transcript email. Disabled until SMTP is configured."""
from __future__ import annotations

import hashlib
import hmac
from types import SimpleNamespace
import os
import re
import smtplib
import ssl
import threading
import time
from collections import deque
from email.message import EmailMessage
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth import get_current_user
from app.models.user import User
from app.db import get_db

router = APIRouter()
SENDER = "contact@keltiawave.com"
COPY = {
    "fr": ("Votre transcription KeltiaWave", "Merci d’utiliser KeltiaWave et de faire vivre les langues brittoniques !"),
    "en": ("Your KeltiaWave transcript", "Thank you for using KeltiaWave and helping Brittonic languages thrive!"),
    "br": ("Ho treuzskrivadur KeltiaWave", "Trugarez da implijout KeltiaWave ha da lakaat ar yezhoù predenek da vevañ!"),
    "cy": ("Eich trawsgrifiad KeltiaWave", "Diolch am ddefnyddio KeltiaWave ac am helpu’r ieithoedd Brythonaidd i ffynnu!"),
}


class TranscriptEmail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipient: str = Field(min_length=3, max_length=254)
    transcript: str = Field(min_length=1, max_length=200_000)
    locale: Literal["fr", "en", "br", "cy"] = "fr"

    @field_validator("recipient")
    @classmethod
    def valid_recipient(cls, value: str) -> str:
        # One mailbox only; headers, display names, CC and BCC are not accepted.
        if any(char in value for char in "\r\n\x00"):
            raise ValueError("Invalid recipient")
        value = value.strip()
        pattern = r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+"
        if not re.fullmatch(pattern, value) or len(value.split("@", 1)[0]) > 64:
            raise ValueError("Invalid recipient")
        return value

    @field_validator("transcript")
    @classmethod
    def nonempty_transcript(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Empty transcript")
        return value.strip()


def compose_message(payload: TranscriptEmail) -> EmailMessage:
    subject, thanks = COPY[payload.locale]
    message = EmailMessage()
    message["From"] = f"KeltiaWave <{SENDER}>"
    message["Reply-To"] = SENDER
    message["To"] = payload.recipient
    message["Subject"] = subject
    message.set_content(f"{payload.transcript}\n\n—\n{thanks}\nKeltiaWave\n")
    return message


class EmailLimiter:
    """Small single-process guard; replace with shared quotas before scaling workers."""
    def __init__(self):
        self.lock = threading.Lock()
        self.requests: dict[int, deque[float]] = {}

    def reserve(self, user_id: int) -> None:
        now = time.monotonic()
        with self.lock:
            self.requests = {key: deque(stamp for stamp in values if now - stamp < 3600)
                             for key, values in self.requests.items() if values and now - values[-1] < 3600}
            values = self.requests.setdefault(user_id, deque())
            if len(values) >= 10 or (values and now - values[-1] < 60):
                raise HTTPException(429, "email_rate_limited")
            values.append(now)


limiter = EmailLimiter()


def smtp_settings(enabled_flag: str = "TRANSCRIPT_EMAIL_ENABLED") -> tuple[str, int, str, str, str]:
    if os.getenv(enabled_flag, "false").lower() != "true":
        raise HTTPException(503, "email_not_configured")
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    mode = os.getenv("SMTP_SECURITY", "ssl")
    try:
        port = int(os.getenv("SMTP_PORT", "465"))
    except ValueError:
        raise HTTPException(503, "email_not_configured") from None
    if not host or not username or not password or mode not in {"ssl", "starttls"} or not 1 <= port <= 65535:
        raise HTTPException(503, "email_not_configured")
    return host, port, username, password, mode


def deliver(message: EmailMessage, settings: tuple[str, int, str, str, str]) -> None:
    host, port, username, password, mode = settings
    context = ssl.create_default_context()
    if mode == "ssl":
        connection = smtplib.SMTP_SSL(host, port, timeout=15, context=context)
    else:
        connection = smtplib.SMTP(host, port, timeout=15)
    with connection as smtp:
        if mode == "starttls":
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
        smtp.login(username, password)
        refused = smtp.send_message(message, from_addr=SENDER, to_addrs=[str(message["To"])])
        if refused:
            raise smtplib.SMTPException("Recipient refused")


def email_identity(request: Request, db=Depends(get_db)):
    authorization = request.headers.get("authorization", "")
    digest = os.getenv("STAGING_RECORD_DEVICE_SHA256", "")
    if (os.getenv("DEPLOY_SLOT") == "staging"
            and request.url.hostname == "record.staging.keltiawave.com"
            and request.url.path == "/api/record/email"
            and authorization.startswith("Bearer ") and 39 <= len(authorization) <= 256
            and len(digest) == 64
            and hmac.compare_digest(hashlib.sha256(authorization[7:].encode()).hexdigest(), digest)):
        return SimpleNamespace(id=-1)
    return get_current_user(authorization=authorization, db=db)


@router.post("/email", status_code=202)
def send_transcript_email(payload: TranscriptEmail, user: User = Depends(email_identity)):
    settings = smtp_settings()
    limiter.reserve(user.id)
    try:
        deliver(compose_message(payload), settings)
    except (smtplib.SMTPException, OSError):
        # Do not return SMTP responses: they may contain account or recipient data.
        raise HTTPException(502, "email_delivery_failed") from None
    return {"status": "accepted"}
