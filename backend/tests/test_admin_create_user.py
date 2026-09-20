from app.auth import verify_password
from app.models.user import User


PAYLOAD = dict(email='new@example.test', display_name='New User', password='initial-password', role='teacher')


def test_admin_creates_account_without_switching_identity(client, auth_headers, db_session):
    response = client.post('/api/auth/users', headers=auth_headers['admin'], json=PAYLOAD)
    assert response.status_code == 201
    assert response.json()['role'] == 'teacher'
    assert response.json()['must_change_password'] is True
    assert 'access_token' not in response.json()
    user = db_session.query(User).filter(User.email == PAYLOAD['email']).one()
    assert verify_password(PAYLOAD['password'], user.password_hash)
    assert client.get('/api/auth/me', headers=auth_headers['admin']).json()['role'] == 'admin'
    assert client.post('/api/auth/login', json={'email': PAYLOAD['email'], 'password': PAYLOAD['password']}).status_code == 200


def test_creation_requires_admin(client, auth_headers):
    assert client.post('/api/auth/users', json=PAYLOAD).status_code == 401
    assert client.post('/api/auth/users', headers=auth_headers['learner'], json=PAYLOAD).status_code == 403


def test_creation_rejects_duplicates_and_invalid_fields(client, auth_headers):
    headers = auth_headers['admin']
    assert client.post('/api/auth/users', headers=headers, json=PAYLOAD).status_code == 201
    assert client.post('/api/auth/users', headers=headers, json={**PAYLOAD, 'email': 'NEW@example.test'}).status_code == 409
    for patch in ({'email': 'invalid'}, {'password': 'short'}, {'role': 'superuser'}, {'display_name': '   '}):
        assert client.post('/api/auth/users', headers=headers, json={**PAYLOAD, **patch}).status_code == 422
