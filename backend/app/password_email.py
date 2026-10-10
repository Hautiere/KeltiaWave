"""SMTP transport and request limits for account password recovery."""
import os
import smtplib
import ssl
import threading
import time
from collections import deque
from email.message import EmailMessage
from fastapi import HTTPException

SENDER = "contact@keltiawave.com"


class EmailLimiter:
    """Small single-process guard; replace with shared quotas before scaling workers."""
    def __init__(self):
        self.lock = threading.Lock()
        self.requests: dict[str, deque[float]] = {}

    def reserve(self, user_id: str) -> None:
        now = time.monotonic()
        with self.lock:
            self.requests = {key: deque(stamp for stamp in values if now - stamp < 3600)
                             for key, values in self.requests.items() if values and now - values[-1] < 3600}
            values = self.requests.setdefault(user_id, deque())
            if len(values) >= 10 or (values and now - values[-1] < 60):
                raise HTTPException(429, "email_rate_limited")
            values.append(now)


limiter = EmailLimiter()


def smtp_settings(enabled_flag: str = "PASSWORD_RESET_EMAIL_ENABLED") -> tuple[str, int, str, str, str]:
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

