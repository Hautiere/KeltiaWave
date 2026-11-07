from app.auth import verify_password


def test_connected_user_changes_only_own_password(client, users, auth_headers, db_session):
    admin, learner = users
    admin.must_change_password = True
    db_session.commit()
    response = client.post('/api/auth/change-password', headers=auth_headers['admin'],
                           json={'new_password': 'new-test-password', 'id': learner.id})
    assert response.status_code == 200
    assert response.json()['must_change_password'] is False
    db_session.refresh(admin)
    db_session.refresh(learner)
    assert verify_password('new-test-password', admin.password_hash)
    assert learner.password_hash == 'unused'


def test_password_change_requires_session(client):
    assert client.post('/api/auth/change-password', json={'new_password': 'new-test-password'}).status_code == 401


def test_password_change_rejects_short_password(client, auth_headers, users):
    before = users[0].password_hash
    response = client.post('/api/auth/change-password', headers=auth_headers['admin'], json={'new_password': 'short'})
    assert response.status_code == 422
    assert users[0].password_hash == before
