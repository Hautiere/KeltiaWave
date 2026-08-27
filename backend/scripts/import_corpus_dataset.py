from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any

from app.db import Base, SessionLocal, engine
from app.models import Audio, Phrase
from app.models.audio import AudioStatus
from app.storage import save_audio_file_path


TEXT_FIELDS = ("texte", "text", "phrase")
AUDIO_FIELDS = ("audio_path", "audio", "file", "filename")


def load_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("items") or data.get("phrases") or data.get("rows")
        if not isinstance(data, list):
            raise SystemExit("JSON attendu: liste d'objets, ou objet avec items/phrases/rows.")
        return [dict(row) for row in data]

    raise SystemExit("Format non supporte. Utiliser un fichier .csv ou .json.")


def first_value(row: dict[str, Any], names: tuple[str, ...]) -> str | None:
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def optional(row: dict[str, Any], name: str) -> str | None:
    value = row.get(name)
    return str(value).strip() if value is not None and str(value).strip() else None


def set_if_changed(obj: Any, field: str, value: str | None) -> bool:
    if value is None or getattr(obj, field) == value:
        return False
    setattr(obj, field, value)
    return True


def audio_storage_name(dataset: str, phrase_text: str, audio_path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(dataset.encode("utf-8"))
    digest.update(b"\0")
    digest.update(phrase_text.encode("utf-8"))
    digest.update(b"\0")
    digest.update(audio_path.read_bytes())
    ext = audio_path.suffix.lower() if audio_path.suffix.lower() in {
        ".webm",
        ".ogg",
        ".mp3",
        ".wav",
        ".m4a",
        ".mp4",
    } else ".webm"
    safe_dataset = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-"
        for char in dataset.strip().lower()
    ).strip("-") or "dataset"
    return f"import-{safe_dataset}-{digest.hexdigest()[:16]}{ext}"


def resolve_audio_path(dataset_file: Path, audio_root: Path | None, raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate
    if audio_root:
        return (audio_root / candidate).resolve()
    return (dataset_file.parent / candidate).resolve()


def import_dataset(args: argparse.Namespace) -> dict[str, int]:
    dataset_file = Path(args.dataset).expanduser().resolve()
    audio_root = Path(args.audio_root).expanduser().resolve() if args.audio_root else None
    rows = load_rows(dataset_file)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    created_phrases = 0
    reused_phrases = 0
    updated_phrases = 0
    created_audios = 0
    reused_audios = 0
    updated_audios = 0
    skipped_without_audio = 0

    try:
        for index, row in enumerate(rows, start=1):
            phrase_text = first_value(row, TEXT_FIELDS)
            if not phrase_text:
                raise SystemExit(f"Ligne {index}: champ phrase manquant ({', '.join(TEXT_FIELDS)}).")

            langue = optional(row, "langue") or optional(row, "content_language") or args.langue
            phrase = (
                db.query(Phrase)
                .filter(Phrase.texte == phrase_text, Phrase.langue == langue)
                .first()
            )
            if phrase:
                reused_phrases += 1
                changed = False
                changed |= set_if_changed(phrase, "traduction_fr", optional(row, "traduction_fr") or optional(row, "translation_fr"))
                changed |= set_if_changed(phrase, "theme", optional(row, "theme") or optional(row, "domain"))
                changed |= set_if_changed(phrase, "niveau", optional(row, "niveau") or optional(row, "level"))
                changed |= set_if_changed(phrase, "source", optional(row, "source"))
                changed |= set_if_changed(phrase, "auteur", optional(row, "auteur") or optional(row, "author"))
                if changed:
                    updated_phrases += 1
            else:
                phrase = Phrase(
                    texte=phrase_text,
                    traduction_fr=optional(row, "traduction_fr") or optional(row, "translation_fr"),
                    theme=optional(row, "theme") or optional(row, "domain"),
                    niveau=optional(row, "niveau") or optional(row, "level"),
                    source=optional(row, "source") or args.source,
                    langue=langue,
                    auteur=optional(row, "auteur") or optional(row, "author") or args.author,
                )
                db.add(phrase)
                db.flush()
                created_phrases += 1

            raw_audio_path = first_value(row, AUDIO_FIELDS)
            if not raw_audio_path:
                skipped_without_audio += 1
                continue

            audio_path = resolve_audio_path(dataset_file, audio_root, raw_audio_path)
            if not audio_path.exists() or not audio_path.is_file():
                raise SystemExit(f"Ligne {index}: fichier audio introuvable: {audio_path}")

            row_status = optional(row, "status") or args.status
            if row_status not in {status.value for status in AudioStatus}:
                raise SystemExit(f"Ligne {index}: statut audio invalide: {row_status}")
            row_origin = optional(row, "origin") or "dataset"
            if row_origin not in {"dataset", "user"}:
                raise SystemExit(f"Ligne {index}: origin invalide: {row_origin}")

            storage_name = audio_storage_name(args.name, phrase_text, audio_path)
            content_type = mimetypes.guess_type(audio_path.name)[0] or "audio/webm"
            storage_ref = save_audio_file_path(audio_path, storage_name, content_type)

            audio = db.query(Audio).filter(Audio.filename == storage_ref).first()
            if audio:
                reused_audios += 1
                changed = False
                changed |= set_if_changed(audio, "phrase_source", optional(row, "phrase_source") or optional(row, "source"))
                changed |= set_if_changed(audio, "domain", optional(row, "domain") or optional(row, "theme"))
                changed |= set_if_changed(audio, "speaker_region", optional(row, "speaker_region"))
                changed |= set_if_changed(audio, "speaker_city", optional(row, "speaker_city"))
                changed |= set_if_changed(audio, "speaker_accent", optional(row, "speaker_accent"))
                changed |= set_if_changed(audio, "speaker_level", optional(row, "speaker_level"))
                changed |= set_if_changed(audio, "contributor_name", optional(row, "contributor_name"))
                changed |= set_if_changed(audio, "contributor_email", optional(row, "contributor_email"))
                changed |= set_if_changed(audio, "contributor_school", optional(row, "contributor_school"))
                changed |= set_if_changed(audio, "contributor_school_level", optional(row, "contributor_school_level"))
                if audio.status.value != row_status:
                    audio.status = AudioStatus(row_status)
                    changed = True
                if audio.origin != row_origin:
                    audio.origin = row_origin
                    changed = True
                if changed:
                    updated_audios += 1
                continue

            db.add(
                Audio(
                    phrase_id=phrase.id,
                    filename=storage_ref,
                    origin=row_origin,
                    status=AudioStatus(row_status),
                    phrase_source=optional(row, "phrase_source") or optional(row, "source") or args.source,
                    domain=optional(row, "domain") or optional(row, "theme"),
                    speaker_region=optional(row, "speaker_region"),
                    speaker_city=optional(row, "speaker_city"),
                    speaker_accent=optional(row, "speaker_accent"),
                    speaker_level=optional(row, "speaker_level"),
                    contributor_name=optional(row, "contributor_name"),
                    contributor_email=optional(row, "contributor_email"),
                    contributor_school=optional(row, "contributor_school"),
                    contributor_school_level=optional(row, "contributor_school_level"),
                )
            )
            created_audios += 1

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    stats = {
        "rows_read": len(rows),
        "created_phrases": created_phrases,
        "reused_phrases": reused_phrases,
        "updated_phrases": updated_phrases,
        "created_audios": created_audios,
        "reused_audios": reused_audios,
        "updated_audios": updated_audios,
        "skipped_without_audio": skipped_without_audio,
    }
    print(f"Lignes lues: {stats['rows_read']}")
    print(f"Phrases ajoutees: {stats['created_phrases']}")
    print(f"Phrases deja presentes: {stats['reused_phrases']}")
    print(f"Phrases mises a jour: {stats['updated_phrases']}")
    print(f"Audios ajoutes: {stats['created_audios']}")
    print(f"Audios deja presents: {stats['reused_audios']}")
    print(f"Audios mis a jour: {stats['updated_audios']}")
    print(f"Lignes sans audio: {stats['skipped_without_audio']}")
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importe un jeu de donnees phrases + audios dans le corpus."
    )
    parser.add_argument("dataset", help="Fichier CSV ou JSON a importer.")
    parser.add_argument("--name", default="dataset", help="Nom court du jeu de donnees.")
    parser.add_argument("--audio-root", help="Dossier racine des fichiers audio si les chemins sont relatifs.")
    parser.add_argument("--langue", default="br", help="Langue par defaut des phrases.")
    parser.add_argument("--author", default="import-corpus", help="Auteur par defaut des phrases.")
    parser.add_argument("--source", default="import", help="Source par defaut des phrases et audios.")
    parser.add_argument(
        "--status",
        choices=[status.value for status in AudioStatus],
        default=AudioStatus.pending.value,
        help="Statut initial des audios importes.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    import_dataset(parse_args())
