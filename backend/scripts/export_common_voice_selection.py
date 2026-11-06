"""Export an exact, verified Common Voice selection as a Library archive."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from uuid import uuid4
import zipfile

from app.db import SessionLocal
from app.library_storage import TransferStorage
from app.library_transfer import FORMAT, VERSION, PHRASE_FIELDS, AUDIO_FIELDS, values, validate_manifest
from app.models import Phrase, Audio
from app.models.audio import AudioStatus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selection', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--expected-count', type=int, required=True)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text())
    if len(selection) != args.expected_count or len({r['phrase_id'] for r in selection}) != len(selection) or len({r['audio_id'] for r in selection}) != len(selection):
        raise ValueError('Selection count or uniqueness mismatch')
    store = TransferStorage.configured()
    manifest = dict(format=FORMAT, manifest_version=VERSION, export_id=str(uuid4()), exported_at=datetime.utcnow().isoformat(), phrases=[], audios=[], audio_validations=[], files=[])
    files = {}
    with SessionLocal() as db:
        for row in selection:
            phrase = db.get(Phrase, row['phrase_id'])
            audio = db.get(Audio, row['audio_id'])
            if phrase is None or audio is None or audio.phrase_id != phrase.id or audio.filename != row['filename'] or phrase.langue != 'br' or phrase.source != 'common-voice':
                raise ValueError('Selection no longer matches database')
            if audio.origin != 'dataset' or audio.phrase_source != 'common-voice' or audio.status != AudioStatus.approved or audio.validations or audio.contributor_email or audio.contributor_name:
                raise ValueError('Selection contains an unexpected recording')
            if phrase.url_audio or not all((getattr(phrase, f'traduction_{lang}') or '').strip() for lang in ('fr', 'en', 'cy')):
                raise ValueError('Unexpected phrase audio link or missing translation')
            data = store.read(audio.filename)
            sha = hashlib.sha256(data).hexdigest()
            if sha != row['audio_sha256']:
                raise ValueError('Audio checksum mismatch')
            name = f'audios/{sha}.mp3'
            files[name] = data
            manifest['phrases'].append(dict(id=phrase.id, **values(phrase, PHRASE_FIELDS), url_audio_audio_id=None))
            manifest['audios'].append(dict(id=audio.id, phrase_id=phrase.id, file=name, **values(audio, AUDIO_FIELDS)))
        manifest['files'] = [dict(path=name, size=len(data), sha256=hashlib.sha256(data).hexdigest()) for name, data in files.items()]
        validate_manifest(manifest)
        with args.output.open('xb') as handle:
            with zipfile.ZipFile(handle, 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, data in files.items():
                    archive.writestr(name, data)
                archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps({key: len(manifest[key]) for key in ('phrases', 'audios', 'files')}))


if __name__ == '__main__':
    main()
