"""Versioned library archives. No schema creation, editorial rewriting or API changes."""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import stat
from uuid import uuid4
import zipfile

from .models.audio import Audio, AudioStatus, AudioValidation
from .models.phrase import Phrase
from .library_storage import MAX_AUDIO_BYTES

FORMAT = 'keltiawave-library'
VERSION = 1
PHRASE_FIELDS = ('texte', 'traduction_fr', 'theme', 'niveau', 'source', 'source_url', 'langue', 'auteur', 'url_audio', 'created_at')
AUDIO_FIELDS = ('origin', 'status', 'phrase_source', 'domain', 'speaker_region', 'speaker_city', 'speaker_accent', 'speaker_level', 'created_at', 'validated_at', 'validated_by', 'validator_role', 'validation_weight', 'validation_comment', 'contributor_name', 'contributor_email', 'contributor_school', 'contributor_school_level')
VALIDATION_FIELDS = ('decision', 'validator', 'validator_role', 'validation_weight', 'pronunciation_level', 'pronunciation_region', 'comment', 'created_at')
FILE_PATTERN = re.compile(r'audios/([0-9a-f]{64})\.[a-z0-9]{1,10}\Z')
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024
MAX_MANIFEST_BYTES = 16 * 1024 * 1024


class TransferError(ValueError):
    pass


def values(obj, fields):
    result = {}
    for field in fields:
        value = getattr(obj, field)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, AudioStatus):
            value = value.value
        result[field] = value
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def event_key(event):
    return json.dumps({key: event[key] for key in VALIDATION_FIELDS}, sort_keys=True, ensure_ascii=False)


def clean_session(db):
    if db.new or db.dirty or db.deleted:
        raise TransferError('Transfer requires a session with no pending changes')


def export_library(db, store, output):
    """Export all three collections; fail rather than omit an unavailable file."""
    clean_session(db)
    output = Path(output)
    phrases = db.query(Phrase).order_by(Phrase.id).all()
    audios = db.query(Audio).order_by(Audio.id).all()
    events = db.query(AudioValidation).order_by(AudioValidation.id).all()
    manifest = {'format': FORMAT, 'manifest_version': VERSION, 'export_id': str(uuid4()),
                'exported_at': datetime.utcnow().isoformat(), 'phrases': [], 'audios': [],
                'audio_validations': [], 'files': []}
    phrase_ids = {p.id for p in phrases}
    audio_ids = {a.id for a in audios}
    refs = defaultdict(list)
    for audio in audios:
        if audio.phrase_id not in phrase_ids:
            raise TransferError(f'Orphan audio {audio.id}')
        refs[audio.filename].append(audio.id)
        refs[f'/api/audios/{audio.id}/file'].append(audio.id)
    for phrase in phrases:
        row = {'id': phrase.id, **values(phrase, PHRASE_FIELDS), 'url_audio_audio_id': None}
        ref = phrase.url_audio
        if ref:
            matches = refs.get(ref, [])
            if len(matches) == 1:
                row['url_audio_audio_id'] = matches[0]
            elif matches or not re.match(r'^https?://', ref, re.I):
                raise TransferError(f'Phrase {phrase.id}: unresolved or ambiguous url_audio')
        manifest['phrases'].append(row)
    manifest['audio_validations'] = [{'id': e.id, 'audio_id': e.audio_id, **values(e, VALIDATION_FIELDS)} for e in events]
    if any(e.audio_id not in audio_ids for e in events):
        raise TransferError('Orphan audio validation')
    # Exclusive output: an existing archive is never replaced. Remove partial exports.
    created = False
    try:
        with output.open('xb') as stream:
            created = True
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                files = set()
                total = 0
                for audio in audios:
                    data = store.read(audio.filename)
                    sha = digest(data)
                    extension = Path(audio.filename).suffix.lower()
                    if not re.fullmatch(r'\.[a-z0-9]{1,10}', extension):
                        extension = '.bin'
                    path = f'audios/{sha}{extension}'
                    if path not in files:
                        total += len(data)
                        if total > MAX_ARCHIVE_BYTES or len(files) >= 10000:
                            raise TransferError('Library exceeds archive limits')
                        archive.writestr(path, data)
                        manifest['files'].append({'path': path, 'size': len(data), 'sha256': sha})
                        files.add(path)
                    manifest['audios'].append({'id': audio.id, 'phrase_id': audio.phrase_id,
                                              'file': path, **values(audio, AUDIO_FIELDS)})
                validate_manifest(manifest)
                raw = json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8')
                if len(raw) > MAX_MANIFEST_BYTES:
                    raise TransferError('Manifest exceeds size limit')
                archive.writestr('manifest.json', raw)
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise
    return {name: len(manifest[name]) for name in ('phrases', 'audios', 'audio_validations', 'files')}


def require(condition, message):
    if not condition:
        raise TransferError(message)


def validate_manifest(manifest):
    require(isinstance(manifest, dict), 'Manifest must be an object')
    require(manifest.get('format') == FORMAT, 'Unknown library format')
    require(type(manifest.get('manifest_version')) is int and manifest['manifest_version'] == VERSION, 'Unknown manifest version')
    require(set(manifest) == {'format', 'manifest_version', 'export_id', 'exported_at', 'phrases', 'audios', 'audio_validations', 'files'}, 'Invalid manifest fields')
    require(isinstance(manifest['export_id'], str) and bool(manifest['export_id']), 'Invalid export id')
    require(isinstance(manifest['exported_at'], str), 'Invalid export date')
    try:
        datetime.fromisoformat(manifest['exported_at'])
    except ValueError:
        raise TransferError('Invalid export date') from None
    ids = {}
    for name, fields, extra in [('phrases', PHRASE_FIELDS, {'url_audio_audio_id'}),
                                ('audios', AUDIO_FIELDS, {'phrase_id', 'file'}),
                                ('audio_validations', VALIDATION_FIELDS, {'audio_id'})]:
        rows = manifest[name]
        require(isinstance(rows, list), f'{name} must be an array')
        ids[name] = set()
        for row in rows:
            require(isinstance(row, dict) and set(row) == set(fields) | extra | {'id'}, f'Invalid {name} fields')
            require(type(row['id']) is int and row['id'] > 0 and row['id'] not in ids[name], f'Duplicate/invalid {name} id')
            ids[name].add(row['id'])
            for field in fields:
                value = row[field]
                require(value is None or isinstance(value, str), f'{name}.{field} must be string or null')
                if field.endswith('_at') and value is not None:
                    try:
                        date = datetime.fromisoformat(value)
                        require(date.tzinfo is None, 'V1 database timestamps must be timezone-naive UTC')
                    except ValueError as exc:
                        raise TransferError(f'Invalid timestamp {name}.{field}: {exc}') from None
            required = ('texte', 'created_at') if name == 'phrases' else ('origin', 'status', 'created_at') if name == 'audios' else ('decision', 'created_at')
            require(all(row[f] is not None for f in required), f'Null required field in {name}')
            if name == 'audios':
                require(row['status'] in {s.value for s in AudioStatus}, 'Invalid audio status')
    require(isinstance(manifest['files'], list), 'files must be an array')
    paths = set()
    for row in manifest['files']:
        require(isinstance(row, dict) and set(row) == {'path', 'size', 'sha256'}, 'Invalid file fields')
        require(isinstance(row['path'], str), 'Invalid file path')
        match = FILE_PATTERN.fullmatch(row['path'])
        require(match is not None and row['path'] not in paths, 'Invalid/duplicate file path')
        require(row['sha256'] == match[1], 'Invalid file SHA-256')
        require(type(row['size']) is int and 0 <= row['size'] <= MAX_AUDIO_BYTES, 'Invalid file size')
        paths.add(row['path'])
    for audio in manifest['audios']:
        require(type(audio['phrase_id']) is int and audio['phrase_id'] in ids['phrases'], 'Invalid audio phrase reference')
        require(isinstance(audio['file'], str) and audio['file'] in paths, 'Missing audio file reference')
    require(paths == {a['file'] for a in manifest['audios']}, 'Unreferenced file in manifest')
    for event in manifest['audio_validations']:
        require(type(event['audio_id']) is int and event['audio_id'] in ids['audios'], 'Invalid validation audio reference')
    for phrase in manifest['phrases']:
        ref = phrase['url_audio_audio_id']
        require(ref is None or type(ref) is int and ref in ids['audios'], 'Invalid phrase audio reference')
        if ref is None and phrase['url_audio']:
            require(bool(re.match(r'^https?://', phrase['url_audio'], re.I)), 'Unmapped local phrase audio URL')


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'Duplicate JSON key: {key}')
        result[key] = value
    return result


class Package:
    def __init__(self, archive):
        self.archive = archive
        infos = archive.infolist()
        require(len(infos) <= 10001, 'Too many ZIP members')
        require(sum(i.file_size for i in infos) <= MAX_ARCHIVE_BYTES + MAX_MANIFEST_BYTES, 'ZIP exceeds size limit')
        names = set()
        for info in infos:
            require(info.filename not in names, 'Duplicate ZIP entry')
            names.add(info.filename)
            require(info.filename == 'manifest.json' or FILE_PATTERN.fullmatch(info.filename), 'Unsafe ZIP path')
            kind = stat.S_IFMT(info.external_attr >> 16)
            require(kind in (0, stat.S_IFREG), 'ZIP links and special files are forbidden')
            require(not info.flag_bits & 1, 'Encrypted ZIP not supported')
            limit = MAX_MANIFEST_BYTES if info.filename == 'manifest.json' else MAX_AUDIO_BYTES
            require(info.file_size <= limit, 'ZIP member exceeds size limit')
        require('manifest.json' in names, 'Missing manifest.json')
        try:
            self.manifest = json.loads(archive.read('manifest.json'), object_pairs_hook=unique_json)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise TransferError(f'Invalid manifest JSON: {exc}') from None
        validate_manifest(self.manifest)
        self.files = {row['path']: row for row in self.manifest['files']}
        require(names == {'manifest.json'} | set(self.files), 'Missing or undeclared ZIP file')
        for path in self.files:
            self.read(path)

    def read(self, path):
        data = self.archive.read(path)
        row = self.files[path]
        require(len(data) == row['size'] and digest(data) == row['sha256'], f'File integrity failure: {path}')
        return data


def decoded(row, fields):
    result = {field: row[field] for field in fields}
    for field in fields:
        if field.endswith('_at') and result[field] is not None:
            result[field] = datetime.fromisoformat(result[field])
    return result


def plan_import(db, store, package):
    manifest = package.manifest
    report = {'mode': 'dry-run', 'create': {k: 0 for k in ('phrases', 'audios', 'audio_validations')},
              'existing': {k: 0 for k in ('phrases', 'audios', 'audio_validations')}, 'conflicts': [], 'errors': []}
    phrase_map, audio_map = {}, {}
    by_key = defaultdict(list)
    for obj in db.query(Phrase).all():
        by_key[(obj.texte, obj.langue)].append(obj)
    used = set()
    for row in manifest['phrases']:
        candidates = by_key[(row['texte'], row['langue'])]
        fields = tuple(f for f in PHRASE_FIELDS if f != 'url_audio' or row['url_audio_audio_id'] is None)
        expected = values(Phrase(**decoded(row, PHRASE_FIELDS)), fields)
        exact = [p for p in candidates if values(p, fields) == expected and p.id not in used]
        if candidates and len(exact) != 1:
            report['conflicts'].append(f"CONFLICT phrase {row['id']}: differing metadata or ambiguous match")
            continue
        obj = exact[0] if exact else None
        phrase_map[row['id']] = obj
        report['existing' if obj else 'create']['phrases'] += 1
        if obj:
            used.add(obj.id)
    events = defaultdict(list)
    for row in manifest['audio_validations']:
        events[row['audio_id']].append(row)
    audios_by_phrase = defaultdict(list)
    for audio in db.query(Audio).all():
        audios_by_phrase[audio.phrase_id].append(audio)
    hashes, used = {}, set()
    for row in manifest['audios']:
        if row['phrase_id'] not in phrase_map:
            continue
        phrase = phrase_map[row['phrase_id']]
        candidates = []
        if phrase:
            for obj in audios_by_phrase[phrase.id]:
                if obj.filename not in hashes:
                    try:
                        hashes[obj.filename] = digest(store.read(obj.filename))
                    except Exception as exc:
                        hashes[obj.filename] = None
                        report['errors'].append(f'Cannot verify existing audio {obj.id}: {exc}')
                if hashes[obj.filename] == package.files[row['file']]['sha256']:
                    candidates.append(obj)
        expected = values(Audio(**decoded(row, AUDIO_FIELDS)), AUDIO_FIELDS)
        history = Counter(event_key(event) for event in events[row['id']])
        exact = [a for a in candidates if a.id not in used and values(a, AUDIO_FIELDS) == expected
                 and Counter(event_key(values(v, VALIDATION_FIELDS)) for v in a.validations) == history]
        if candidates and len(exact) != 1:
            report['conflicts'].append(f"CONFLICT audio {row['id']}: differing metadata/history or ambiguous match")
            continue
        obj = exact[0] if exact else None
        audio_map[row['id']] = obj
        group = 'existing' if obj else 'create'
        report[group]['audios'] += 1
        report[group]['audio_validations'] += len(events[row['id']])
        if obj:
            used.add(obj.id)
    for row in manifest['phrases']:
        if row['url_audio_audio_id'] is None or row['id'] not in phrase_map:
            continue
        phrase = phrase_map[row['id']]
        audio = audio_map.get(row['url_audio_audio_id'])
        if phrase and (not audio or phrase.url_audio not in (audio.filename, f'/api/audios/{audio.id}/file')):
            report['conflicts'].append(f"CONFLICT phrase {row['id']}: audio URL differs")
    return report, phrase_map, audio_map


def import_library(db, store, source, *, apply=False):
    """Owns commit/rollback on a clean session. A dry-run performs only reads."""
    clean_session(db)
    with zipfile.ZipFile(source) as archive:
        package = Package(archive)
        with db.no_autoflush:
            report, phrase_map, audio_map = plan_import(db, store, package)
        if not apply or report['conflicts'] or report['errors']:
            return report
        created_files = []
        commit_attempted = False
        try:
            manifest = package.manifest
            for row in manifest['phrases']:
                if phrase_map[row['id']] is None:
                    data = decoded(row, PHRASE_FIELDS)
                    if row['url_audio_audio_id'] is not None:
                        data['url_audio'] = None
                    obj = Phrase(**data)
                    db.add(obj)
                    phrase_map[row['id']] = obj
            db.flush()
            new_audio_ids = set()
            for row in manifest['audios']:
                if audio_map[row['id']] is None:
                    data = package.read(row['file'])
                    ref = store.reserve(Path(row['file']).suffix)
                    store.put(ref, data)
                    created_files.append(ref)
                    obj = Audio(phrase_id=phrase_map[row['phrase_id']].id, filename=ref, **decoded(row, AUDIO_FIELDS))
                    db.add(obj)
                    audio_map[row['id']] = obj
                    new_audio_ids.add(row['id'])
            db.flush()
            for row in manifest['phrases']:
                # Never update a pre-existing phrase, including its URL spelling.
                if row['url_audio_audio_id'] is not None:
                    obj = phrase_map[row['id']]
                    if obj.url_audio is None:
                        obj.url_audio = f"/api/audios/{audio_map[row['url_audio_audio_id']].id}/file"
            for row in manifest['audio_validations']:
                if row['audio_id'] in new_audio_ids:
                    db.add(AudioValidation(audio_id=audio_map[row['audio_id']].id, **decoded(row, VALIDATION_FIELDS)))
            commit_attempted = True
            db.commit()
        except BaseException as exc:
            try:
                db.rollback()
                if commit_attempted and created_files:
                    # A lost commit acknowledgement must not cause deletion of committed media.
                    if db.query(Audio).filter(Audio.filename.in_(created_files)).first():
                        raise TransferError(f"Commit outcome requires inspection; referenced files preserved: {created_files}") from exc
            except BaseException as recovery:
                raise TransferError(f"Cannot confirm rollback; files preserved for inspection: {created_files}; {recovery}") from exc
            cleanup_errors = []
            for ref in reversed(created_files):
                try:
                    store.remove(ref)
                except Exception as cleanup:
                    cleanup_errors.append(f'{ref}: {cleanup}')
            if cleanup_errors:
                raise TransferError(f'Import failed ({exc}); storage cleanup incomplete: {cleanup_errors}') from exc
            raise
        report['mode'] = 'applied'
        return report
