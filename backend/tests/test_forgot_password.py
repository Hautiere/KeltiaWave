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


def reset_token(mail):
    return mail[-1].get_content().split('#token=', 1)[1].split()[0]


def test_reset_flow(client, users, db_session, mail):
    user = users[0]
    user.password_hash = hash_password('original-password')
    db_session.commit()
    old_login = client.post('/api/auth/login', json={'email': user.email, 'password': 'original-password'})
    headers = {'Authorization': 'Bearer ' + old_login.json()['access_token']}
    assert client.post('/api/auth/forgot-password', json={'email': user.email}).status_code == 202
    token = reset_token(mail)
    db_session.refresh(user)
    assert verify_password('original-password', user.password_hash)
    assert token not in user.temporary_password_hash
    assert client.get('/api/auth/me', headers=headers).status_code == 200
    payload = {'token': token, 'new_password': 'replacement-password'}
    assert client.post('/api/auth/reset-password', json=payload).status_code == 200
    assert client.get('/api/auth/me', headers=headers).status_code == 401
    assert client.post('/api/auth/reset-password', json=payload).status_code == 400
    assert client.post('/api/auth/login', json={'email': user.email, 'password': 'original-password'}).status_code == 401
    login = client.post('/api/auth/login', json={'email': user.email, 'password': 'replacement-password'})
    assert login.status_code == 200
    assert not login.json()['user']['must_change_password']
    assert client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + login.json()['access_token']}).status_code == 200


def test_expired_link_rejected(client, users, db_session, mail):
    user = users[0]
    client.post('/api/auth/forgot-password', json={'email': user.email})
    user.temporary_password_expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    assert client.post('/api/auth/reset-password', json={'token': reset_token(mail), 'new_password': 'replacement-password'}).status_code == 400
    db_session.refresh(user)
    assert user.password_hash == 'unused'


def test_latest_link_only_and_password_validation(client, users, mail, monkeypatch):
    client.post('/api/auth/forgot-password', json={'email': users[0].email})
    old = reset_token(mail)
    monkeypatch.setattr(auth, 'reset_limiter', auth.EmailLimiter())
    client.post('/api/auth/forgot-password', json={'email': users[0].email})
    new = reset_token(mail)
    assert client.post('/api/auth/reset-password', json={'token': old, 'new_password': 'replacement-password'}).status_code == 400
    assert client.post('/api/auth/reset-password', json={'token': new, 'new_password': 'short'}).status_code == 422
    assert client.post('/api/auth/reset-password', json={'token': new, 'new_password': 'replacement-password'}).status_code == 200


def test_reset_targets_email_account_despite_other_session(client, users, db_session, mail):
    from app.auth import create_access_token
    other = users[1]
    other.password_hash = hash_password('other-password')
    db_session.commit()
    headers = {'Authorization': 'Bearer ' + create_access_token(other)}
    client.post('/api/auth/forgot-password', json={'email': users[0].email})
    assert client.post('/api/auth/reset-password', headers=headers, json={'token': reset_token(mail), 'new_password': 'replacement-password'}).status_code == 200
    db_session.refresh(other)
    assert verify_password('other-password', other.password_hash)
    assert client.get('/api/auth/me', headers=headers).status_code == 200


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
