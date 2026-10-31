from app.api.endpoints import enregistrements
from app.models.audio import Audio
from app.models.phrase import Phrase


def test_audio_upload_preserves_region_and_level(client, db_session, monkeypatch):
    phrase = Phrase(texte="Demat deoc'h", theme="rencontres", niveau="A1", langue="br")
    db_session.add(phrase)
    db_session.commit()

    async def fake_save(_file, _phrase_id):
        return "data/audios/test.wav"

    monkeypatch.setattr(enregistrements, "save_audio_upload", fake_save)
    response = client.post(
        "/api/audios/",
        data={
            "phrase_id": str(phrase.id),
            "phrase_source": "suggested",
            "domain": "rencontres",
            "speaker_region": "bro-leon",
            "speaker_level": "intermediate",
        },
        files={"file": ("learner.wav", b"RIFF-test", "audio/wav")},
    )

    assert response.status_code == 201, response.text
    assert response.json()["speaker_region"] == "bro-leon"
    assert response.json()["speaker_level"] == "intermediate"
    audio = db_session.query(Audio).one()
    assert (audio.speaker_region, audio.speaker_level) == ("bro-leon", "intermediate")


def test_uploaded_audio_uses_account_name_not_phrase_source(client, db_session, monkeypatch, auth_headers):
    phrase = Phrase(texte="Demat", langue="br", source="common-voice")
    db_session.add(phrase)
    db_session.commit()

    async def fake_save(_file, _phrase_id):
        return "data/audios/contribution.wav"

    monkeypatch.setattr(enregistrements, "save_audio_upload", fake_save)
    for headers, expected_name in [(auth_headers['learner'], 'Learning Learner'), ({}, 'Inconnu')]:
        response = client.post(
            "/api/audios/", headers=headers,
            data={"phrase_id": str(phrase.id), "phrase_source": "suggested", "contributor_name": "Common Voice"},
            files={"file": ("contribution.wav", b"RIFF-test", "audio/wav")},
        )
        assert response.status_code == 201, response.text
        audio = response.json()
        assert audio['origin'] == 'user'
        assert audio['contributor_name'] == expected_name
        assert audio['phrase_source'] == 'suggested'
    db_session.refresh(phrase)
    assert phrase.source == 'common-voice'


def test_my_audios_requires_login_and_returns_only_own_contributions(client, db_session, auth_headers, users):
    from app.models.audio import AudioStatus
    admin, learner = users
    phrase = Phrase(texte="Demat deoc'h", langue="br", source="common-voice")
    db_session.add(phrase)
    db_session.flush()
    for status in [AudioStatus.pending, AudioStatus.approved, AudioStatus.rejected]:
        db_session.add(Audio(phrase_id=phrase.id, filename=f'{status.value}.wav', origin='user',
                             status=status, contributor_email=learner.email.upper(), contributor_name=learner.display_name))
    db_session.add_all([
        Audio(phrase_id=phrase.id, filename='other.wav', origin='user', contributor_email=admin.email),
        Audio(phrase_id=phrase.id, filename='anonymous.wav', origin='user', contributor_name='Inconnu'),
        Audio(phrase_id=phrase.id, filename='import.wav', origin='dataset', contributor_email=learner.email),
    ])
    db_session.commit()
    assert client.get('/api/audios/mine').status_code == 401
    response = client.get('/api/audios/mine', headers=auth_headers['learner'])
    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) == 3
    assert {row['status'] for row in rows} == {'pending', 'approved', 'rejected'}
    assert all(row['phrase_text'] == phrase.texte for row in rows)
    approved = next(row for row in rows if row['status'] == 'approved')
    assert approved['id'] in {row['id'] for row in client.get('/api/audios/?status=approved').json()}


def test_approval_updates_the_personal_list_and_public_approved_list(client, db_session, auth_headers, users):
    _, learner = users
    phrase = Phrase(texte='Demat', langue='br')
    db_session.add(phrase)
    db_session.flush()
    audio = Audio(phrase_id=phrase.id, filename='mine.wav', origin='user', contributor_email=learner.email)
    db_session.add(audio)
    db_session.commit()
    mine = client.get('/api/audios/mine', headers=auth_headers['learner']).json()
    assert mine[0]['status'] == 'pending'
    response = client.post(f'/api/audios/{audio.id}/validate', headers=auth_headers['admin'],
                           data={'approved': 'true', 'comment': 'Bonne lecture', 'pronunciation_level': 'B1', 'pronunciation_region': 'bro-leon'})
    assert response.status_code == 200, response.text
    mine = client.get('/api/audios/mine', headers=auth_headers['learner']).json()
    assert mine[0]['status'] == 'approved'
    assert mine[0]['validation_comment'] == 'Bonne lecture'
    approved = client.get('/api/audios/?status=approved').json()
    assert [row['id'] for row in approved] == [audio.id]
    assert approved[0]['validator_role'] == 'admin'
