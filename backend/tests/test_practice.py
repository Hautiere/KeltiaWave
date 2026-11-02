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


def test_choose_formation_from_school_directory_and_preserve_default(client, db_session, auth_headers):
    from app.models.practice import PracticeClass, PracticeMembership
    first, second = teacher(db_session, 'school-first'), teacher(db_session, 'school-second')
    assert client.get('/api/practice/classes/available').status_code == 401
    assert client.get('/api/practice/classes', headers=auth_headers['learner']).json()['joined'] is None
    first_class = client.post('/api/practice/classes', headers=first, json={'name':'Débutant','school':'École A'}).json()
    second_class = client.post('/api/practice/classes', headers=second, json={'name':'Débutant','school':'École B'}).json()
    directory = client.get('/api/practice/classes/available', headers=auth_headers['learner']).json()
    assert [(item['school'],item['name'],item['teacher']) for item in directory] == [('École A','Débutant','school-first'),('École B','Débutant','school-second')]
    assert all('code' not in item and 'email' not in item for item in directory)
    assert client.post('/api/practice/classes/join',headers=auth_headers['learner'],json={'class_id':second_class['id']}).status_code==200
    assert db_session.query(PracticeMembership).one().class_id == second_class['id']
    assert client.get('/api/practice/classes',headers=auth_headers['learner']).json()['joined']['school']=='École B'
    assert client.post('/api/practice/classes/join',headers=auth_headers['learner'],json={'class_id':first_class['id'],'code':first_class['code']}).status_code==400
    assert client.patch(f"/api/practice/classes/{first_class['id']}",headers=second,json={'name':'Forged','school':'Fake'}).status_code==404
    updated=client.patch(f"/api/practice/classes/{first_class['id']}",headers=first,json={'name':'Intermédiaire','school':'École C'})
    assert updated.status_code==200 and updated.json()['school']=='École C'
    owner=db_session.get(User,db_session.get(PracticeClass,second_class['id']).teacher_id)
    owner.active=False;db_session.commit()
    assert len(client.get('/api/practice/classes/available',headers=auth_headers['learner']).json())==1
    assert client.post('/api/practice/classes/join',headers=auth_headers['learner'],json={'class_id':second_class['id']}).status_code==409
    assert client.delete('/api/practice/classes/join',headers=auth_headers['learner']).status_code==204
    assert client.get('/api/practice/classes',headers=auth_headers['learner']).json()['joined'] is None


def test_unread_feedback_is_per_owner_persists_and_new_revision_is_not_hidden(client, db_session, auth_headers, monkeypatch, tmp_path):
    monkeypatch.setattr(storage, 'LOCAL_AUDIO_DIR', tmp_path / 'audios')
    row=send(client,auth_headers['learner']).json()
    path=f"/api/practice/submissions/{row['id']}"
    def count(role='learner'):
        return client.get('/api/practice/notifications',headers=auth_headers[role]).json()['unread_count']
    assert count()==0
    review=client.post(path+'/review',headers=auth_headers['admin'],json={'status':'changes_requested','feedback':'Premier retour'}).json()
    assert review['feedback_revision']==1 and count()==1 and count('admin')==0
    assert client.get('/api/practice/submissions',headers=auth_headers['learner']).json()[0]['unread_feedback'] is True
    assert count()==1  # Listing/playing does not acknowledge feedback.
    assert client.post(path+'/read',headers=auth_headers['admin'],json={'revision':1}).status_code==404
    assert client.post(path+'/read',headers=auth_headers['learner'],json={'revision':2}).status_code==409
    assert client.post(path+'/read',headers=auth_headers['learner'],json={'revision':1}).json()['unread_feedback'] is False
    assert count()==0
    client.post(path+'/review',headers=auth_headers['admin'],json={'status':'approved','feedback':'Deuxième retour'})
    assert count()==1
    stale=client.post(path+'/read',headers=auth_headers['learner'],json={'revision':1}).json()
    assert stale['unread_feedback'] is True and stale['feedback_revision']==2
    assert count()==1
    client.post(path+'/read',headers=auth_headers['learner'],json={'revision':2})
    db_session.expire_all()
    assert count()==0


def test_practice_schema_upgrade_keeps_old_data_and_is_idempotent():
    from sqlalchemy import create_engine, text
    from app.practice_schema import ensure_practice_columns
    engine=create_engine('sqlite://')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE practice_classes (id INTEGER PRIMARY KEY, name TEXT)'))
        conn.execute(text('CREATE TABLE practice_submissions (id INTEGER PRIMARY KEY, feedback TEXT)'))
        conn.execute(text("INSERT INTO practice_classes VALUES (1,'Formation existante')"))
        conn.execute(text("INSERT INTO practice_submissions VALUES (1,'Retour existant')"))
    ensure_practice_columns(engine)
    ensure_practice_columns(engine)
    with engine.begin() as conn:
        assert conn.execute(text('SELECT name, school FROM practice_classes')).one()==('Formation existante','')
        assert conn.execute(text('SELECT feedback, feedback_revision, feedback_seen_revision FROM practice_submissions')).one()==('Retour existant',1,0)
        conn.execute(text('UPDATE practice_submissions SET feedback_seen_revision=1'))
    ensure_practice_columns(engine)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT feedback_seen_revision FROM practice_submissions')).scalar()==1
    engine.dispose()
