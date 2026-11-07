import pytest

from app.models.audio import Audio
from app.models.phrase import Phrase


BASE = {"texte": "Demat deoc'h", "theme": "faire-connaissance", "niveau": "A1", "langue": "br"}
VALID_URL = "https://example.org/source?lang=br#phrase"
LIMIT_URL = "https://example.org/" + "a" * (2048 - len("https://example.org/"))


@pytest.fixture(params=["phrase", "segment"])
def target(request, db_session):
    phrase = Phrase(**BASE, source="internet", source_url=VALID_URL)
    db_session.add(phrase)
    db_session.flush()
    audio = Audio(phrase_id=phrase.id, filename="unused-test.mp3")
    db_session.add(audio)
    db_session.commit()
    route = f"/api/phrases/{phrase.id}" if request.param == "phrase" else f"/api/admin-data/segments/{audio.id}"
    return phrase, route


@pytest.mark.parametrize("url", [None, "", "   ", "ftp://example.org", "javascript:alert(1)", "https://", "https:///path", "https://exa mple.org", "https://example.org:bad", "https://example.org\\path", LIMIT_URL + "a"])
def test_create_rejects_invalid_internet_provenance(client, auth_headers, db_session, url):
    response = client.post('/api/phrases/', headers=auth_headers['admin'], json={**BASE, 'source': 'internet', 'source_url': url})
    assert response.status_code == 400
    assert db_session.query(Phrase).count() == 0


@pytest.mark.parametrize("url", [VALID_URL, 'HTTP://example.org/path', LIMIT_URL, '  ' + VALID_URL + '  '])
def test_create_accepts_http_and_trims(client, auth_headers, url):
    response = client.post('/api/phrases/', headers=auth_headers['admin'], json={**BASE, 'source': 'internet', 'source_url': url})
    assert response.status_code == 201
    assert response.json()['source_url'] == url.strip()


@pytest.mark.parametrize("source", [None, 'livre', 'common-voice-pilote'])
def test_create_discards_url_for_other_sources(client, auth_headers, source):
    response = client.post('/api/phrases/', headers=auth_headers['admin'], json={**BASE, 'source': source, 'source_url': 'unused'})
    assert response.status_code == 201
    assert response.json()['source_url'] is None


@pytest.mark.parametrize("url", [None, '', 'https://', 'file:///tmp/source', LIMIT_URL + 'x'])
def test_partial_url_edit_checks_existing_source_atomically(client, auth_headers, target, db_session, url):
    phrase, route = target
    response = client.patch(route, headers=auth_headers['admin'], json={'texte': 'Changed text', 'source_url': url})
    assert response.status_code == 400
    db_session.refresh(phrase)
    assert phrase.texte == BASE['texte']
    assert phrase.source_url == VALID_URL


def test_url_only_patch_keeps_source(client, auth_headers, target, db_session):
    phrase, route = target
    response = client.patch(route, headers=auth_headers['admin'], json={'source_url': '  http://example.org/new  '})
    assert response.status_code == 200
    db_session.refresh(phrase)
    assert phrase.source == 'internet'
    assert phrase.source_url == 'http://example.org/new'


@pytest.mark.parametrize('source', [None, 'livre'])
def test_source_only_patch_clears_old_url(client, auth_headers, target, db_session, source):
    phrase, route = target
    assert client.patch(route, headers=auth_headers['admin'], json={'source': source}).status_code == 200
    db_session.refresh(phrase)
    assert phrase.source == source
    assert phrase.source_url is None


def test_switch_to_internet_requires_final_url(client, auth_headers, target, db_session):
    phrase, route = target
    phrase.source, phrase.source_url = 'livre', None
    db_session.commit()
    assert client.patch(route, headers=auth_headers['admin'], json={'source': 'internet'}).status_code == 400
    assert client.patch(route, headers=auth_headers['admin'], json={'source': 'internet', 'source_url': VALID_URL}).status_code == 200
    db_session.refresh(phrase)
    assert (phrase.source, phrase.source_url) == ('internet', VALID_URL)


def test_source_only_uses_existing_url(client, auth_headers, target, db_session):
    phrase, route = target
    phrase.source = 'livre'
    db_session.commit()
    assert client.patch(route, headers=auth_headers['admin'], json={'source': 'internet'}).status_code == 200
    db_session.refresh(phrase)
    assert phrase.source_url == VALID_URL


def test_legacy_reads_and_unrelated_patch_unchanged(client, auth_headers, target, db_session):
    phrase, route = target
    legacy = 'javascript:' + 'x' * 2050
    phrase.source_url = legacy
    db_session.commit()
    detail = client.get(f'/api/phrases/{phrase.id}')
    assert detail.status_code == 200 and detail.json()['source_url'] == legacy
    listing = client.get('/api/phrases/')
    assert listing.status_code == 200 and listing.json()[0]['source_url'] == legacy
    assert client.patch(route, headers=auth_headers['admin'], json={'traduction_fr': 'Bonjour'}).status_code == 200
    db_session.refresh(phrase)
    assert phrase.source_url == legacy
    assert phrase.traduction_fr == 'Bonjour'


def test_non_internet_url_edit_is_discarded(client, auth_headers, target, db_session):
    phrase, route = target
    phrase.source, phrase.source_url = 'livre', None
    db_session.commit()
    assert client.patch(route, headers=auth_headers['admin'], json={'source_url': VALID_URL}).status_code == 200
    db_session.refresh(phrase)
    assert phrase.source_url is None


def test_final_non_internet_state_clears_even_supplied_url(client, auth_headers, target, db_session):
    phrase, route = target
    assert client.patch(route, headers=auth_headers['admin'], json={'source': 'livre', 'source_url': 'not-a-url'}).status_code == 200
    db_session.refresh(phrase)
    assert (phrase.source, phrase.source_url) == ('livre', None)
