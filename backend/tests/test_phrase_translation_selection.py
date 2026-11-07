import csv
import json
from contextlib import nullcontext

import pytest

from app.models import Phrase
from scripts import import_phrase_translation_selection as importer


def setup_lot(tmp_path, db_session, monkeypatch):
    phrases = [Phrase(texte='Demat.', langue='br', source='common-voice', traduction_fr='Bonjour.'),
               Phrase(texte='Kenavo.', langue='br', source='common-voice')]
    db_session.add_all(phrases)
    db_session.commit()
    rows = [dict(id=p.id, texte=p.texte, traduction_fr=fr, traduction_en=en, traduction_cy=cy)
            for p, fr, en, cy in zip(phrases, ['Salut.', 'Au revoir.'], ['Hello.', 'Goodbye.'], ['Helo.', 'Hwyl fawr.'])]
    path = tmp_path / 'translations.csv'
    def write():
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    write()
    monkeypatch.setattr(importer, 'SessionLocal', lambda: nullcontext(db_session))
    def run(*args):
        monkeypatch.setattr('sys.argv', ['import', str(path), '--expected-count', '2', *args])
        importer.main()
    return phrases, rows, write, run


def test_dry_run_then_apply_preserves_existing_and_is_idempotent(tmp_path, db_session, monkeypatch):
    phrases, rows, write, run = setup_lot(tmp_path, db_session, monkeypatch)
    run()
    assert phrases[0].traduction_en is None
    snapshot = tmp_path / 'before.json'
    run('--apply', '--snapshot', str(snapshot))
    assert phrases[0].traduction_fr == 'Bonjour.'
    assert phrases[0].traduction_en == 'Hello.'
    assert phrases[1].traduction_cy == 'Hwyl fawr.'
    saved = json.loads(snapshot.read_text())
    assert saved[0]['before']['traduction_fr'] == 'Bonjour.'
    assert saved[0]['before']['traduction_en'] is None
    second = tmp_path / 'second.json'
    run('--apply', '--snapshot', str(second))
    assert json.loads(second.read_text()) == []


def test_changed_source_text_stops_the_entire_import(tmp_path, db_session, monkeypatch):
    phrases, rows, write, run = setup_lot(tmp_path, db_session, monkeypatch)
    rows[1]['texte'] = 'Different source'
    write()
    with pytest.raises(ValueError, match='source/text changed'):
        run('--apply', '--snapshot', str(tmp_path / 'before.json'))
    assert phrases[0].traduction_en is None
    assert not (tmp_path / 'before.json').exists()


def test_duplicate_ids_are_rejected(tmp_path, db_session, monkeypatch):
    phrases, rows, write, run = setup_lot(tmp_path, db_session, monkeypatch)
    rows[1]['id'] = rows[0]['id']
    write()
    with pytest.raises(ValueError, match='Duplicate'):
        run()


def test_empty_language_stops_before_database_changes(tmp_path, db_session, monkeypatch):
    phrases, rows, write, run = setup_lot(tmp_path, db_session, monkeypatch)
    rows[1]['traduction_cy'] = ' '
    write()
    with pytest.raises(ValueError, match='Empty'):
        run()
    assert phrases[0].traduction_en is None


def test_existing_snapshot_is_never_overwritten(tmp_path, db_session, monkeypatch):
    phrases, rows, write, run = setup_lot(tmp_path, db_session, monkeypatch)
    snapshot = tmp_path / 'before.json'
    snapshot.write_text('original')
    with pytest.raises(FileExistsError):
        run('--apply', '--snapshot', str(snapshot))
    assert snapshot.read_text() == 'original'
    assert phrases[0].traduction_en is None
