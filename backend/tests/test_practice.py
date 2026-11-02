from app.auth import create_access_token
from app.models.user import User
from app.models.practice import PracticeSubmission
from app import storage


def teacher(db, name):
    user = User(email=f'{name}@example.test', display_name=name, password_hash='unused', role='teacher', active=True)
    db.add(user); db.commit(); db.refresh(user)
    return {'Authorization': f'Bearer {create_access_token(user)}'}


def send(client, headers, **data):
    return client.post('/api/practice/submissions', headers=headers, data={'title':'Ma lecture', **data},
                       files={'file':('test.wav', b'RIFF-synthetic', 'audio/wav')})


def test_private_submission_admin_fallback_and_ownership(client, db_session, auth_headers, monkeypatch, tmp_path):
    monkeypatch.setattr(storage, 'LOCAL_AUDIO_DIR', tmp_path / 'audios')
    assert send(client, {}).status_code == 401
    sent = send(client, auth_headers['learner'])
    assert sent.status_code == 201, sent.text
    row = sent.json()
    assert row['destination'] == 'Administration'
    assert client.get('/api/practice/submissions', headers=auth_headers['admin']).json() == []
    other = teacher(db_session, 'other')
    assert client.get('/api/practice/reviews', headers=other).json() == []
    assert client.get(f"/api/practice/submissions/{row['id']}/file", headers=other).status_code == 404
    assert client.post(f"/api/practice/submissions/{row['id']}/review", headers=auth_headers['learner'], json={'status':'approved','feedback':'forged'}).status_code == 404
    assert client.get('/api/practice/reviews', headers=auth_headers['admin']).json()[0]['id'] == row['id']
    review = client.post(f"/api/practice/submissions/{row['id']}/review", headers=auth_headers['admin'],json={'status':'changes_requested','feedback':'Reprenez lentement.'})
    assert review.status_code == 200
    mine = client.get('/api/practice/submissions',headers=auth_headers['learner']).json()[0]
    assert mine['feedback'] == 'Reprenez lentement.'
    assert mine['reviewer'] == 'Learning Admin'
    ref = db_session.query(PracticeSubmission).one().filename
    assert '/practice/' in ref
    assert client.get('/static/audios/' + ref.split('/')[-1]).status_code == 404
    assert client.get(f"/api/practice/submissions/{row['id']}/file",headers=auth_headers['learner']).content == b'RIFF-synthetic'
    assert client.get('/api/audios/?status=approved').json() == []


def test_class_routes_to_its_teacher_and_keeps_original_destination(client, db_session, auth_headers, monkeypatch, tmp_path):
    monkeypatch.setattr(storage, 'LOCAL_AUDIO_DIR', tmp_path / 'audios')
    first, second = teacher(db_session,'first'), teacher(db_session,'second')
    assert client.post('/api/practice/classes',headers=auth_headers['learner'],json={'name':'forged'}).status_code == 403
    cls = client.post('/api/practice/classes',headers=first,json={'name':'Breton A1'}).json()
    assert client.post('/api/practice/classes/join',headers=auth_headers['learner'],json={'code':'bad'}).status_code == 404
    assert client.post('/api/practice/classes/join',headers=auth_headers['learner'],json={'code':cls['code'].lower()}).status_code == 200
    sent=send(client,auth_headers['learner']).json()
    assert sent['destination'] == 'Breton A1'
    assert client.get('/api/practice/reviews',headers=second).json() == []
    assert client.get('/api/practice/reviews',headers=first).json()[0]['id']==sent['id']
    assert client.post(f"/api/practice/submissions/{sent['id']}/review",headers=second,json={'status':'approved','feedback':'No'}).status_code==404
    assert client.post(f"/api/practice/submissions/{sent['id']}/review",headers=first,json={'status':'approved','feedback':'Très bien'}).status_code==200
    assert client.delete('/api/practice/classes/join',headers=auth_headers['learner']).status_code==204
    mine=client.get('/api/practice/submissions',headers=auth_headers['learner']).json()
    assert mine[0]['destination']=='Breton A1'
    assert send(client,auth_headers['learner']).json()['destination']=='Administration'


def test_rejects_empty_and_non_audio_uploads(client, auth_headers):
    for data, files in [({'title':' '},{'file':('test.wav',b'RIFF','audio/wav')}),
                        ({'title':'test'},{'file':('test.txt',b'text','text/plain')}),
                        ({'title':'test'},{'file':('empty.wav',b'','audio/wav')})]:
        assert client.post('/api/practice/submissions',headers=auth_headers['learner'],data=data,files=files).status_code==400
