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
