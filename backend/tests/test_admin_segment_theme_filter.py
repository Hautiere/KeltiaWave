from app.models.audio import Audio
from app.models.phrase import Phrase


def test_segment_theme_filter_applies_before_limit_and_matches_legacy_domains(client, auth_headers, db_session):
    matching_phrase = Phrase(texte="Phrase du quotidien", theme="vie-quotidienne", subdomain="maison", langue="br")
    other_phrase = Phrase(texte="Phrase de nature", theme="nature-meteo", langue="br")
    db_session.add_all([matching_phrase, other_phrase])
    db_session.flush()
    db_session.add(Audio(phrase_id=matching_phrase.id, filename="daily.wav"))
    db_session.add_all(Audio(phrase_id=other_phrase.id, filename=f"nature-{index}.wav") for index in range(3))
    db_session.commit()

    response = client.get(
        "/api/admin-data/segments",
        headers=auth_headers["admin"],
        params={"theme": "maison-quotidien", "limit": 1},
    )

    assert response.status_code == 200
    assert [item["texte"] for item in response.json()] == ["Phrase du quotidien"]
    assert response.json()[0]["subdomain"] == "maison"


def test_segment_theme_filter_can_find_unclassified_domains(client, auth_headers, db_session):
    phrase = Phrase(texte="Phrase sans domaine", theme="non-classe", langue="br")
    db_session.add(phrase)
    db_session.flush()
    db_session.add(Audio(phrase_id=phrase.id, filename="unclassified.wav"))
    db_session.commit()

    response = client.get(
        "/api/admin-data/segments",
        headers=auth_headers["admin"],
        params={"theme": "__unclassified__"},
    )

    assert response.status_code == 200
    assert [item["texte"] for item in response.json()] == ["Phrase sans domaine"]
