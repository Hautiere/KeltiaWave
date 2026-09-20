from datetime import datetime, timedelta
import smtplib

import pytest

from app.api.endpoints import auth
from app.auth import hash_password, verify_password


@pytest.fixture
def mail(monkeypatch):
    sent = []
    monkeypatch.setattr(auth, 'reset_limiter', auth.EmailLimiter())
    monkeypatch.setattr(auth, 'smtp_settings', lambda flag: ())
    monkeypatch.setattr(auth, 'deliver', lambda message, settings: sent.append(message))
    return sent


def test_reset_flow(client, users, db_session, mail):
    user = users[0]
    user.password_hash = hash_password('original-password')
    db_session.commit()
    assert client.post('/api/auth/forgot-password', json={'email': user.email}).status_code == 202
    password = mail[0].get_content().splitlines()[0].split(': ', 1)[1]
    db_session.refresh(user)
    assert verify_password('original-password', user.password_hash)
    assert verify_password(password, user.temporary_password_hash)
    login = client.post('/api/auth/login', json={'email': user.email, 'password': password})
    assert login.status_code == 200
    assert login.json()['user']['must_change_password']
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    assert client.get('/api/auth/users', headers=headers).status_code == 403
    assert client.post('/api/auth/change-password', headers=headers, json={'new_password': 'replacement-password'}).status_code == 200
    assert client.get('/api/auth/users', headers=headers).status_code == 200
    assert client.post('/api/auth/login', json={'email': user.email, 'password': password}).status_code == 401
    assert client.post('/api/auth/login', json={'email': user.email, 'password': 'replacement-password'}).status_code == 200


def test_expired_password_rejected(client, users, db_session):
    user = users[0]
    user.temporary_password_hash = hash_password('expired-password')
    user.temporary_password_expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    assert client.post('/api/auth/login', json={'email': user.email, 'password': 'expired-password'}).status_code == 401


def test_unknown_and_failed_delivery_preserve_account(client, users, mail, monkeypatch, db_session):
    response = client.post('/api/auth/forgot-password', json={'email': 'unknown@example.test'})
    assert response.status_code == 202 and not mail
    monkeypatch.setattr(auth, 'reset_limiter', auth.EmailLimiter())
    def fail(*args):
        raise smtplib.SMTPException('unavailable')
    monkeypatch.setattr(auth, 'deliver', fail)
    assert client.post('/api/auth/forgot-password', json={'email': users[0].email}).json() == response.json()
    db_session.refresh(users[0])
    assert users[0].password_hash == 'unused'
    assert users[0].temporary_password_hash is None


def test_reset_rate_limit(client, users, mail):
    payload = {'email': users[0].email}
    assert client.post('/api/auth/forgot-password', json=payload).status_code == 202
    assert client.post('/api/auth/forgot-password', json=payload).status_code == 429
    assert len(mail) == 1


def test_reset_disabled(client, monkeypatch):
    monkeypatch.setenv('PASSWORD_RESET_EMAIL_ENABLED', 'false')
    assert client.post('/api/auth/forgot-password', json={'email': 'unknown@example.test'}).status_code == 503
