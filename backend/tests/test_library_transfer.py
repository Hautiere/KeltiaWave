from argparse import Namespace
from datetime import datetime
import io
import json
from pathlib import Path
import stat
import zipfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from botocore.exceptions import ClientError

from app.db import Base
from app.models.audio import Audio, AudioStatus, AudioValidation
from app.models.phrase import Phrase
from app.library_storage import TransferStorage
from app.library_transfer import (AUDIO_FIELDS, PHRASE_FIELDS, VALIDATION_FIELDS, TransferError,
                                  export_library, import_library, values)


@pytest.fixture
def libraries(tmp_path):
    result = []
    for name in ('a', 'b'):
        engine = create_engine(f'sqlite:///{tmp_path / (name + ".sqlite")}')
        Base.metadata.create_all(engine)
        db = Session(engine)
        root = tmp_path / name
        root.mkdir()
        result.append((db, TransferStorage(root)))
    yield result
    for db, _ in result:
        engine = db.bind
        db.close()
        engine.dispose()


def seed(db, store):
    date = datetime(2026, 8, 30, 10, 30, 12, 123456)
    bare = Phrase(texte='Sans audio', traduction_fr=None, theme=None, niveau=None,
                  source=None, source_url=None, langue='br', auteur=None, url_audio=None, created_at=date)
    spoken = Phrase(texte='Demat !', traduction_fr='Bonjour !', theme='vie-quotidienne', niveau='A1',
                    source='internet', source_url='https://example.org/source', langue='br',
                    auteur='Auteur', url_audio=None, created_at=date)
    db.add_all([bare, spoken]); db.flush()
    for index in range(2):
        ref = store.reserve('.mp3')
        store.put(ref, b'ID3-test-audio-' + bytes([index]))
        audio = Audio(phrase_id=spoken.id, filename=ref, origin='dataset' if index == 0 else 'user',
                      status=AudioStatus.approved if index == 0 else AudioStatus.pending,
                      phrase_source='collection', domain='quotidien', speaker_region='Leon', speaker_city=None,
                      speaker_accent='leonard', speaker_level='B2', created_at=date,
                      validated_at=date if index == 0 else None, validated_by='Prof' if index == 0 else None,
                      validator_role='teacher' if index == 0 else None, validation_weight='0.75' if index == 0 else None,
                      validation_comment=None, contributor_name='Locuteur', contributor_email=None,
                      contributor_school='Skol', contributor_school_level=None)
        db.add(audio); db.flush()
        if index == 0:
            for decision in ['approved', 'commented', 'commented']:
                db.add(AudioValidation(audio_id=audio.id, decision=decision, validator='Prof', validator_role='teacher',
                                       validation_weight='0.75', pronunciation_level='B2', pronunciation_region='Leon',
                                       comment='Très bien' if decision == 'commented' else None, created_at=date))
    db.commit()


def snapshot(db, store):
    rows = []
    for phrase in db.query(Phrase).order_by(Phrase.texte):
        audios = []
        for audio in db.query(Audio).filter_by(phrase_id=phrase.id).order_by(Audio.id):
            history = [values(v, VALIDATION_FIELDS) for v in audio.validations]
            audios.append({'data': values(audio, AUDIO_FIELDS), 'bytes': store.read(audio.filename), 'history': history})
        rows.append({'phrase': values(phrase, PHRASE_FIELDS), 'audios': audios})
    return rows


@pytest.fixture
def archive(libraries, tmp_path):
    db, store = libraries[0]
    seed(db, store)
    path = tmp_path / 'library.zip'
    assert export_library(db, store, path) == {'phrases': 2, 'audios': 2, 'audio_validations': 3, 'files': 2}
    return path


def rewrite(source, target, edit=None, file_edit=None, extra=None):
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, 'w') as new:
        for name in old.namelist():
            data = old.read(name)
            if name == 'manifest.json' and edit:
                manifest = json.loads(data); edit(manifest); data = json.dumps(manifest).encode()
            elif name != 'manifest.json' and file_edit:
                data = file_edit(name, data)
                if data is None:
                    continue
            new.writestr(name, data)
        if extra:
            new.writestr(*extra)
    return target


def test_round_trip_two_bases_two_storages_and_second_import(libraries, archive):
    (a, sa), (b, sb) = libraries
    before = snapshot(a, sa)
    dry = import_library(b, sb, archive)
    assert dry['create'] == {'phrases': 2, 'audios': 2, 'audio_validations': 3}
    assert b.query(Phrase).count() == 0 and list(sb.root.iterdir()) == []
    report = import_library(b, sb, archive, apply=True)
    assert report['mode'] == 'applied'
    assert snapshot(b, sb) == before
    assert {a.filename for a in a.query(Audio)}.isdisjoint({a.filename for a in b.query(Audio)})
    original_files = sorted(sb.root.iterdir())
    second = import_library(b, sb, archive, apply=True)
    assert second['create'] == {'phrases': 0, 'audios': 0, 'audio_validations': 0}
    assert second['existing'] == {'phrases': 2, 'audios': 2, 'audio_validations': 3}
    assert snapshot(b, sb) == before and sorted(sb.root.iterdir()) == original_files


@pytest.mark.parametrize('kind', ['phrase', 'audio', 'validation'])
def test_corrections_are_conflicts_without_overwrite(libraries, archive, kind):
    b, sb = libraries[1]
    import_library(b, sb, archive, apply=True)
    if kind == 'phrase': b.query(Phrase).filter_by(texte='Demat !').one().traduction_fr = 'Correction'
    elif kind == 'audio': b.query(Audio).first().speaker_region = 'Kerne'
    else: b.query(AudioValidation).first().comment = 'Correction'
    b.commit()
    before, files = snapshot(b, sb), sorted(sb.root.iterdir())
    report = import_library(b, sb, archive, apply=True)
    assert report['conflicts'] and all('CONFLICT' in c for c in report['conflicts'])
    assert snapshot(b, sb) == before and sorted(sb.root.iterdir()) == files


@pytest.mark.parametrize('change', ['missing', 'corrupt', 'version', 'reference', 'null-required'])
def test_bad_package_no_writes(libraries, archive, tmp_path, change):
    b, sb = libraries[1]
    options = {}
    if change == 'missing': options['file_edit'] = lambda n, d: None
    if change == 'corrupt': options['file_edit'] = lambda n, d: d + b'corrupt'
    if change == 'version': options['edit'] = lambda m: m.update(manifest_version=2)
    if change == 'reference': options['edit'] = lambda m: m['audios'][0].update(phrase_id=999)
    if change == 'null-required': options['edit'] = lambda m: m['phrases'][0].update(created_at=None)
    bad = rewrite(archive, tmp_path/'bad.zip', **options)
    with pytest.raises(TransferError): import_library(b, sb, bad, apply=True)
    assert b.query(Phrase).count() == 0 and list(sb.root.iterdir()) == []


@pytest.mark.parametrize('path', ['../escape', '/tmp/escape', 'audios/../../escape', 'audios\\escape', 'https://example.org/a.mp3'])
def test_zip_path_traversal_rejected(libraries, archive, tmp_path, path):
    b, sb = libraries[1]
    bad = rewrite(archive, tmp_path/'bad.zip', extra=(path, b'bad'))
    with pytest.raises(TransferError): import_library(b, sb, bad, apply=True)
    assert b.query(Phrase).count() == 0 and list(sb.root.iterdir()) == []


def test_zip_symlink_rejected(libraries, archive, tmp_path):
    b, sb = libraries[1]
    link = zipfile.ZipInfo('audios/' + 'a'*64 + '.mp3')
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    bad = rewrite(archive, tmp_path/'bad.zip', extra=(link, b'/etc/passwd'))
    with pytest.raises(TransferError, match='links'): import_library(b, sb, bad)


def test_storage_confinement_and_collision(tmp_path):
    root = tmp_path/'storage'; root.mkdir()
    store = TransferStorage(root)
    outside = tmp_path/'outside.mp3'; outside.write_bytes(b'private')
    (root/'link.mp3').symlink_to(outside)
    for ref in [str(outside), '../outside.mp3', 'data/audios/link.mp3', 'https://example.org/audio.mp3']:
        with pytest.raises(ValueError): store.read(ref)
    ref = store.reserve('.mp3'); store.put(ref, b'original')
    with pytest.raises(FileExistsError): store.put(ref, b'new')
    assert store.read(ref) == b'original'


def test_flush_failure_rolls_back_and_cleans_created_files(libraries, archive, monkeypatch):
    b, sb = libraries[1]
    original = b.flush
    def fail_on_history(*args, **kwargs):
        if any(isinstance(x, AudioValidation) for x in b.new):
            raise RuntimeError('DB failure')
        return original(*args, **kwargs)
    monkeypatch.setattr(b, 'flush', fail_on_history)
    with pytest.raises(RuntimeError, match='DB failure'): import_library(b, sb, archive, apply=True)
    assert b.query(Phrase).count() == b.query(Audio).count() == 0
    assert list(sb.root.iterdir()) == []


def test_copy_failure_cleans_previous_files(libraries, archive, monkeypatch):
    b, sb = libraries[1]
    original, calls = sb.put, []
    def fail_second(ref, data):
        calls.append(ref)
        if len(calls) == 2: raise OSError('copy failure')
        original(ref, data)
    monkeypatch.setattr(sb, 'put', fail_second)
    with pytest.raises(OSError): import_library(b, sb, archive, apply=True)
    assert b.query(Phrase).count() == 0 and list(sb.root.iterdir()) == []


def test_cleanup_failure_is_explicit(libraries, archive, monkeypatch):
    b, sb = libraries[1]
    monkeypatch.setattr(b, 'commit', lambda: (_ for _ in ()).throw(RuntimeError('DB failure')))
    monkeypatch.setattr(sb, 'remove', lambda ref: (_ for _ in ()).throw(OSError('storage offline')))
    with pytest.raises(TransferError, match='cleanup incomplete'): import_library(b, sb, archive, apply=True)
    assert b.query(Phrase).count() == 0 and len(list(sb.root.iterdir())) == 2


def test_uncertain_commit_keeps_referenced_files(libraries, archive, monkeypatch):
    b, sb = libraries[1]
    original = b.commit
    def commit_then_disconnect():
        original(); raise OSError('lost acknowledgement')
    monkeypatch.setattr(b, 'commit', commit_then_disconnect)
    with pytest.raises(TransferError, match='preserved'): import_library(b, sb, archive, apply=True)
    assert b.query(Audio).count() == 2 and len(list(sb.root.iterdir())) == 2


def test_export_missing_file_removes_partial_archive(libraries, tmp_path):
    a, sa = libraries[0]; seed(a, sa)
    sa.remove(a.query(Audio).first().filename)
    target = tmp_path/'broken.zip'
    with pytest.raises(FileNotFoundError): export_library(a, sa, target)
    assert not target.exists()


def test_export_never_replaces_existing_archive(libraries, archive):
    a, sa = libraries[0]
    before = archive.read_bytes()
    with pytest.raises(FileExistsError): export_library(a, sa, archive)
    assert archive.read_bytes() == before


def test_phrase_audio_url_remapped_and_external_url_not_fetched(libraries, tmp_path):
    (a, sa), (b, sb) = libraries; seed(a, sa)
    audio = a.query(Audio).first()
    a.get(Phrase, audio.phrase_id).url_audio = audio.filename
    a.query(Phrase).filter_by(texte='Sans audio').one().url_audio = 'https://example.org/external.mp3'
    a.commit()
    path = tmp_path/'linked.zip'; export_library(a, sa, path)
    import_library(b, sb, path, apply=True)
    imported = b.query(Audio).first()
    assert b.get(Phrase, imported.phrase_id).url_audio == f'/api/audios/{imported.id}/file'
    assert b.query(Phrase).filter_by(texte='Sans audio').one().url_audio == 'https://example.org/external.mp3'
    assert not import_library(b, sb, path)['conflicts']


@pytest.mark.parametrize('format', ['csv', 'json'])
def test_legacy_formats_still_export_and_import(libraries, tmp_path, monkeypatch, format):
    from scripts import export_corpus_dataset as exporter, import_corpus_dataset as importer
    (a, sa), (b, sb) = libraries; seed(a, sa)
    monkeypatch.setattr(exporter, 'SessionLocal', lambda: a)
    def copy(ref, dest):
        dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(sa.read(ref)); return True
    monkeypatch.setattr(exporter, 'copy_storage_ref', copy)
    folder = tmp_path/'legacy'
    exporter.export_dataset(Namespace(output=str(folder), dataset=None, status=None, limit=None, format=format, skip_missing=False))
    monkeypatch.setattr(importer, 'SessionLocal', lambda: b)
    monkeypatch.setattr(importer, 'engine', b.bind)
    def save(path, name, mime):
        ref = sb.reserve(Path(name).suffix); sb.put(ref, path.read_bytes()); return ref
    monkeypatch.setattr(importer, 'save_audio_file_path', save)
    result = importer.import_dataset(Namespace(dataset=str(folder/f'metadata.{format}'), audio_root=str(folder), name='legacy', langue='br', source='import', author='test', status='pending'))
    assert result['created_phrases'] == 1 and result['created_audios'] == 2
    assert b.query(Phrase).one().texte == 'Demat !'


def test_s3_transfer_mock_uses_bucket_confinement_and_conditional_create():
    class Client:
        def __init__(self): self.objects = {}
        def put_object(self, *, Bucket, Key, Body, ContentType, IfNoneMatch):
            assert Bucket == 'test' and IfNoneMatch == '*'
            if Key in self.objects:
                raise ClientError({'Error': {'Code': 'PreconditionFailed'}}, 'PutObject')
            self.objects[Key] = Body
        def get_object(self, *, Bucket, Key): return {'Body': io.BytesIO(self.objects[Key])}
        def delete_object(self, *, Bucket, Key): self.objects.pop(Key)
    client = Client(); store = TransferStorage(client=client, bucket='test')
    ref = store.reserve('.mp3'); store.put(ref, b'ID3')
    with pytest.raises(FileExistsError): store.put(ref, b'new')
    assert store.read(ref) == b'ID3'
    with pytest.raises(ValueError): store.read('s3://other/audios/file.mp3')
    store.remove(ref); assert not client.objects


def test_cli_library_dispatch_and_default_simulation(libraries, tmp_path, monkeypatch):
    from scripts import export_corpus_dataset as exporter, import_corpus_dataset as importer
    (a, sa), (b, sb) = libraries; seed(a, sa)
    monkeypatch.setattr(exporter, 'SessionLocal', lambda: a)
    monkeypatch.setattr(TransferStorage, 'configured', lambda: sa)
    path = tmp_path/'cli.zip'
    monkeypatch.setattr('sys.argv', ['export', '--format', 'library', '--output', str(path)])
    exporter.export_dataset(exporter.parse_args())
    monkeypatch.setattr(importer, 'SessionLocal', lambda: b)
    monkeypatch.setattr(TransferStorage, 'configured', lambda: sb)
    for flags in [[], ['--dry-run']]:
        monkeypatch.setattr('sys.argv', ['import', str(path), *flags])
        assert importer.import_dataset(importer.parse_args())['mode'] == 'dry-run'
        assert b.query(Phrase).count() == 0 and list(sb.root.iterdir()) == []
    monkeypatch.setattr('sys.argv', ['import', str(path), '--apply'])
    assert importer.import_dataset(importer.parse_args())['mode'] == 'applied'
    assert snapshot(b, sb) == snapshot(a, sa)


def test_unknown_manifest_not_treated_as_legacy_json(tmp_path):
    from scripts.import_corpus_dataset import load_rows
    path = tmp_path/'manifest.json'
    path.write_text(json.dumps({'format': 'keltiawave-library', 'manifest_version': 9, 'phrases': []}))
    with pytest.raises(SystemExit, match='ZIP'): load_rows(path)


def test_duplicate_zip_members_rejected(libraries, archive, tmp_path):
    with pytest.warns(UserWarning):
        bad = rewrite(archive, tmp_path/'duplicate.zip', extra=('manifest.json', b'{}'))
    with pytest.raises(TransferError, match='Duplicate ZIP'): import_library(*libraries[1], bad)


def test_manifest_path_traversal_rejected(libraries, archive, tmp_path):
    def edit(m):
        m['files'][0]['path'] = '../escape.mp3'
        m['audios'][0]['file'] = '../escape.mp3'
    bad = rewrite(archive, tmp_path/'bad.zip', edit=edit)
    with pytest.raises(TransferError, match='file path'): import_library(*libraries[1], bad)


def test_size_mismatch_rejected(libraries, archive, tmp_path):
    bad = rewrite(archive, tmp_path/'bad.zip', edit=lambda m: m['files'][0].update(size=1))
    with pytest.raises(TransferError, match='integrity'): import_library(*libraries[1], bad)


def test_ambiguous_existing_phrase_is_conflict(libraries, archive):
    b, sb = libraries[1]
    import_library(b, sb, archive, apply=True)
    row = b.query(Phrase).filter_by(texte='Sans audio').one()
    b.add(Phrase(**{field: getattr(row, field) for field in PHRASE_FIELDS})); b.commit()
    assert import_library(b, sb, archive, apply=True)['conflicts']
    assert b.query(Phrase).count() == 3


def test_audio_status_does_not_synthesize_history(libraries, archive, tmp_path):
    bad = rewrite(archive, tmp_path/'no-events.zip', edit=lambda m: m.update(audio_validations=[]))
    b, sb = libraries[1]
    import_library(b, sb, bad, apply=True)
    assert b.query(Audio).filter_by(status=AudioStatus.approved).count() == 1
    assert b.query(AudioValidation).count() == 0


def test_identical_binary_can_belong_to_multiple_audios(libraries, tmp_path):
    (a, sa), (b, sb) = libraries; seed(a, sa)
    first, second = a.query(Audio).order_by(Audio.id).all()
    # Same bytes, distinct metadata/history: preserve both business objects.
    sa.remove(second.filename)
    second.filename = first.filename; a.commit()
    path = tmp_path/'shared.zip'; result = export_library(a, sa, path)
    assert result['files'] == 1 and result['audios'] == 2
    import_library(b, sb, path, apply=True)
    assert snapshot(b, sb) == snapshot(a, sa)
    assert not import_library(b, sb, path, apply=True)['conflicts']
    assert b.query(Audio).count() == 2


def test_s3_mock_roundtrip_and_compensation(libraries, archive, monkeypatch):
    class Client:
        def __init__(self): self.objects = {}
        def put_object(self, **kwargs):
            assert kwargs['IfNoneMatch'] == '*'
            self.objects[kwargs['Key']] = kwargs['Body']
        def get_object(self, **kwargs): return {'Body': io.BytesIO(self.objects[kwargs['Key']])}
        def delete_object(self, **kwargs): self.objects.pop(kwargs['Key'])
    b, _ = libraries[1]
    client = Client(); store = TransferStorage(client=client, bucket='isolated-test')
    original = b.commit
    monkeypatch.setattr(b, 'commit', lambda: (_ for _ in ()).throw(RuntimeError('DB failure')))
    with pytest.raises(RuntimeError): import_library(b, store, archive, apply=True)
    assert client.objects == {} and b.query(Phrase).count() == 0
    monkeypatch.setattr(b, 'commit', original)
    import_library(b, store, archive, apply=True)
    assert snapshot(b, store) == snapshot(*libraries[0])


def test_import_collision_does_not_remove_existing_file(libraries, archive, monkeypatch):
    b, sb = libraries[1]
    ref = sb.reserve('.mp3'); sb.put(ref, b'existing unrelated file')
    monkeypatch.setattr(sb, 'reserve', lambda extension: ref)
    with pytest.raises(FileExistsError): import_library(b, sb, archive, apply=True)
    assert sb.read(ref) == b'existing unrelated file'
    assert b.query(Phrase).count() == 0 and len(list(sb.root.iterdir())) == 1


def test_dry_run_does_not_create_storage_directory(libraries, archive, tmp_path):
    db, _ = libraries[1]
    store = TransferStorage(tmp_path / 'not-created')
    report = import_library(db, store, archive)
    assert report['create']['phrases'] == 2
    assert not store.root.exists()
    assert db.query(Phrase).count() == 0


def test_archive_ids_are_remapped_in_empty_target(libraries, tmp_path):
    (a, sa), (b, sb) = libraries
    seed(a, sa)
    # Give the archive identifiers deliberately unrelated to target sequences.
    path = tmp_path / 'original.zip'
    export_library(a, sa, path)
    def remap(manifest):
        for row in manifest['phrases']:
            row['id'] += 100
        for row in manifest['audios']:
            row['id'] += 200
            row['phrase_id'] += 100
        for row in manifest['audio_validations']:
            row['id'] += 300
            row['audio_id'] += 200
    changed = rewrite(path, tmp_path / 'remapped.zip', edit=remap)
    import_library(b, sb, changed, apply=True)
    assert snapshot(a, sa) == snapshot(b, sb)
    assert max(p.id for p in b.query(Phrase)) < 100
