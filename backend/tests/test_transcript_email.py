from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.record import email


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(email.router, prefix="/api/record")
    app.dependency_overrides[email.email_identity] = lambda: SimpleNamespace(id=42)
    monkeypatch.setattr(email, "limiter", email.EmailLimiter())
    monkeypatch.setenv("TRANSCRIPT_EMAIL_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_USERNAME", "test-user")
    monkeypatch.setenv("SMTP_PASSWORD", "test-password")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_SECURITY", "ssl")
    return TestClient(app)


def payload(**values):
    return {"recipient": "reader@example.test", "transcript": "Demat deoc’h.", "locale": "br", **values}


def test_authentication_required():
    app = FastAPI()
    app.include_router(email.router, prefix="/api/record")
    assert TestClient(app).post("/api/record/email", json=payload()).status_code == 401


def test_disabled_does_not_send(client, monkeypatch):
    monkeypatch.setenv("TRANSCRIPT_EMAIL_ENABLED", "false")
    send = MagicMock()
    monkeypatch.setattr(email, "deliver", send)
    assert client.post("/api/record/email", json=payload()).status_code == 503
    send.assert_not_called()


@pytest.mark.parametrize("locale", ["fr", "en", "br", "cy"])
def test_fixed_sender_plain_text_and_thanks(client, monkeypatch, locale):
    send = MagicMock()
    monkeypatch.setattr(email, "deliver", send)
    response = client.post("/api/record/email", json=payload(locale=locale))
    assert response.status_code == 202
    message = send.call_args.args[0]
    assert message["From"] == "KeltiaWave <contact@keltiawave.com>"
    assert message["Reply-To"] == "contact@keltiawave.com"
    assert message["To"] == "reader@example.test"
    assert message["Subject"] == email.COPY[locale][0]
    assert message.get_content_type() == "text/plain"
    assert "Demat deoc’h." in message.get_content()
    assert message.get_content().endswith(email.COPY[locale][1] + "\nKeltiaWave\n")


@pytest.mark.parametrize("changes", [
    {"recipient": "a@example.test\r\nBcc: other@example.test"},
    {"recipient": "a@example.test,b@example.test"},
    {"recipient": "invalid"}, {"transcript": "   "},
    {"transcript": "x" * 200001}, {"locale": "other"},
    {"sender": "attacker@example.test"},
])
def test_rejects_invalid_requests(client, monkeypatch, changes):
    send = MagicMock()
    monkeypatch.setattr(email, "deliver", send)
    assert client.post("/api/record/email", json=payload(**changes)).status_code == 422
    send.assert_not_called()


def test_rate_limit(client, monkeypatch):
    send = MagicMock()
    monkeypatch.setattr(email, "deliver", send)
    assert client.post("/api/record/email", json=payload()).status_code == 202
    assert client.post("/api/record/email", json=payload()).status_code == 429
    assert send.call_count == 1


def test_provider_error_redacted(client, monkeypatch):
    monkeypatch.setattr(email, "deliver", MagicMock(side_effect=email.smtplib.SMTPException("private SMTP details")))
    response = client.post("/api/record/email", json=payload())
    assert response.status_code == 502
    assert response.json() == {"detail": "email_delivery_failed"}


def test_starttls_precedes_login(monkeypatch):
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    smtp.send_message.return_value = {}
    factory = MagicMock(return_value=smtp)
    monkeypatch.setattr(email.smtplib, "SMTP", factory)
    email.deliver(email.compose_message(email.TranscriptEmail(**payload())), ("smtp.example.test", 587, "test", "test", "starttls"))
    methods = [call[0] for call in smtp.mock_calls]
    assert methods.index("starttls") < methods.index("login") < methods.index("send_message")
    assert smtp.send_message.call_args.kwargs["from_addr"] == email.SENDER


def test_device_auth_is_staging_only(monkeypatch):
    import hashlib
    from starlette.requests import Request
    credential = 'test-device-' + 'x' * 40
    monkeypatch.setenv('STAGING_RECORD_DEVICE_SHA256', hashlib.sha256(credential.encode()).hexdigest())
    monkeypatch.setattr(email, 'get_current_user', lambda **kw: (_ for _ in ()).throw(email.HTTPException(401)))
    def request(host='record.staging.keltiawave.com', path='/api/record/email', token=credential):
        return Request({'type':'http','method':'POST','scheme':'https','path':path,'headers':[(b'host',host.encode()),(b'authorization',('Bearer '+token).encode())],'query_string':b''})
    monkeypatch.setenv('DEPLOY_SLOT','staging')
    assert email.email_identity(request(), db=None).id == -1
    for req in [request(host='record.keltiawave.com'), request(path='/api/other'), request(token='wrong')]:
        with pytest.raises(email.HTTPException): email.email_identity(req, db=None)
    monkeypatch.setenv('DEPLOY_SLOT','production')
    with pytest.raises(email.HTTPException): email.email_identity(request(), db=None)
