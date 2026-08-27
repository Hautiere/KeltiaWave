from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from app.db import Base, SessionLocal, engine
from app.models import Audio, Phrase
from app.models.audio import AudioStatus
from app.storage import save_audio_file_path


def sqlite_rows(db_path: Path, table: str) -> list[sqlite3.Row]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
    finally:
        connection.close()


def audio_path(audio_root: Path, storage_ref: str) -> Path:
    path = Path(storage_ref)
    if path.is_absolute():
        return path
    return audio_root / path.name


def optional(row: sqlite3.Row, name: str):
    return row[name] if name in row.keys() else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Migre un SQLite local vers la base et le stockage courants.")
    parser.add_argument("sqlite_db", type=Path)
    parser.add_argument("audio_root", type=Path)
    args = parser.parse_args()

    phrases = sqlite_rows(args.sqlite_db, "phrases")
    audios = sqlite_rows(args.sqlite_db, "audios")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    phrase_ids: dict[int, int] = {}
    created_phrases = 0
    reused_phrases = 0
    created_audios = 0
    reused_audios = 0
    missing_audio_files = 0
    orphan_audios = 0
    try:
        for row in phrases:
            language = optional(row, "langue")
            phrase = (
                db.query(Phrase)
                .filter(Phrase.texte == row["texte"], Phrase.langue == language)
                .first()
            )
            if phrase:
                reused_phrases += 1
            else:
                phrase = Phrase(
                    texte=row["texte"],
                    theme=optional(row, "theme"),
                    niveau=optional(row, "niveau"),
                    source=optional(row, "source") or "sqlite-local",
                    langue=language,
                    auteur=optional(row, "auteur"),
                    url_audio=optional(row, "url_audio"),
                )
                db.add(phrase)
                db.flush()
                created_phrases += 1
            phrase_ids[row["id"]] = phrase.id

        for row in audios:
            phrase_id = phrase_ids.get(row["phrase_id"])
            if not phrase_id:
                orphan_audios += 1
                continue
            source_path = audio_path(args.audio_root, row["filename"])
            if not source_path.is_file():
                missing_audio_files += 1
                continue
            storage_name = f"sqlite-{row['id']}-{source_path.name}"
            storage_ref = save_audio_file_path(source_path, storage_name)
            if db.query(Audio).filter(Audio.filename == storage_ref).first():
                reused_audios += 1
                continue

            status_value = optional(row, "status") or AudioStatus.pending.value
            db.add(Audio(
                phrase_id=phrase_id,
                filename=storage_ref,
                status=AudioStatus(status_value),
                phrase_source=optional(row, "phrase_source"),
                domain=optional(row, "domain"),
                speaker_region=optional(row, "speaker_region"),
                speaker_city=optional(row, "speaker_city"),
                speaker_accent=optional(row, "speaker_accent"),
                speaker_level=optional(row, "speaker_level"),
                validated_at=optional(row, "validated_at"),
                validated_by=optional(row, "validated_by"),
                validator_role=optional(row, "validator_role"),
                validation_weight=optional(row, "validation_weight"),
                validation_comment=optional(row, "validation_comment"),
                contributor_name=optional(row, "contributor_name"),
                contributor_email=optional(row, "contributor_email"),
                contributor_school=optional(row, "contributor_school"),
                contributor_school_level=optional(row, "contributor_school_level"),
            ))
            created_audios += 1

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"Phrases SQLite lues: {len(phrases)}")
    print(f"Phrases ajoutees: {created_phrases}")
    print(f"Phrases deja presentes: {reused_phrases}")
    print(f"Audios SQLite lus: {len(audios)}")
    print(f"Audios ajoutes dans MinIO: {created_audios}")
    print(f"Audios deja presents: {reused_audios}")
    print(f"Fichiers audio absents: {missing_audio_files}")
    print(f"Audios orphelins ignores: {orphan_audios}")


if __name__ == "__main__":
    main()
