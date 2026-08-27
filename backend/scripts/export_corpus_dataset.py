from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from app.db import SessionLocal
from app.models import Audio, Phrase
from app.models.audio import AudioStatus
from app.storage import LOCAL_AUDIO_DIR, _s3_client


EXPORT_FIELDS = [
    "texte",
    "traduction_fr",
    "audio_path",
    "origin",
    "status",
    "theme",
    "niveau",
    "source",
    "langue",
    "auteur",
    "phrase_source",
    "domain",
    "speaker_region",
    "speaker_city",
    "speaker_accent",
    "speaker_level",
    "contributor_name",
    "contributor_email",
    "contributor_school",
    "contributor_school_level",
    "validated_by",
    "validator_role",
    "validation_weight",
    "validation_comment",
    "created_at",
    "validated_at",
    "audio_id",
    "phrase_id",
    "storage_ref",
]


def status_value(status: AudioStatus | str) -> str:
    return status.value if hasattr(status, "value") else str(status)


def storage_ext(storage_ref: str) -> str:
    ext = Path(storage_ref.split("?", 1)[0]).suffix.lower()
    return ext if ext in {".webm", ".ogg", ".mp3", ".wav", ".m4a", ".mp4"} else ".webm"


def copy_storage_ref(storage_ref: str, destination: Path) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if storage_ref.startswith("s3://"):
        _, rest = storage_ref.split("s3://", 1)
        bucket, key = rest.split("/", 1)
        _s3_client().download_file(bucket, key, str(destination))
        return True

    source = Path(storage_ref)
    if not source.is_absolute():
        if source.parts[:2] == ("data", "audios"):
            source = LOCAL_AUDIO_DIR / source.name
        else:
            source = LOCAL_AUDIO_DIR / source

    if not source.exists() or not source.is_file():
        return False
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return True


def audio_row(audio: Audio, phrase: Phrase, audio_path: str) -> dict[str, Any]:
    return {
        "texte": phrase.texte,
        "traduction_fr": phrase.traduction_fr,
        "audio_path": audio_path,
        "origin": audio.origin,
        "status": status_value(audio.status),
        "theme": phrase.theme,
        "niveau": phrase.niveau,
        "source": phrase.source,
        "langue": phrase.langue,
        "auteur": phrase.auteur,
        "phrase_source": audio.phrase_source,
        "domain": audio.domain,
        "speaker_region": audio.speaker_region,
        "speaker_city": audio.speaker_city,
        "speaker_accent": audio.speaker_accent,
        "speaker_level": audio.speaker_level,
        "contributor_name": audio.contributor_name,
        "contributor_email": audio.contributor_email,
        "contributor_school": audio.contributor_school,
        "contributor_school_level": audio.contributor_school_level,
        "validated_by": audio.validated_by,
        "validator_role": audio.validator_role,
        "validation_weight": audio.validation_weight,
        "validation_comment": audio.validation_comment,
        "created_at": audio.created_at.isoformat() if audio.created_at else None,
        "validated_at": audio.validated_at.isoformat() if audio.validated_at else None,
        "audio_id": audio.id,
        "phrase_id": phrase.id,
        "storage_ref": audio.filename,
    }


def export_dataset(args: argparse.Namespace) -> None:
    output_dir = Path(args.output).expanduser().resolve()
    audio_dir = output_dir / "audios"
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    rows: list[dict[str, Any]] = []
    missing = 0
    try:
        query = (
            db.query(Audio, Phrase)
            .join(Phrase, Audio.phrase_id == Phrase.id)
            .order_by(Audio.created_at.desc(), Audio.id.desc())
        )
        if args.dataset:
            query = query.filter((Audio.phrase_source == args.dataset) | (Phrase.source == args.dataset))
        if args.status:
            query = query.filter(Audio.status == AudioStatus(args.status))
        if args.limit:
            query = query.limit(args.limit)

        for audio, phrase in query.all():
            exported_name = f"audio-{audio.id}{storage_ext(audio.filename)}"
            exported_path = audio_dir / exported_name
            if not copy_storage_ref(audio.filename, exported_path):
                missing += 1
                if not args.skip_missing:
                    raise SystemExit(f"Audio introuvable pour audio_id={audio.id}: {audio.filename}")
                print(f"Audio ignore, fichier introuvable: audio_id={audio.id}", file=sys.stderr)
                continue
            rows.append(audio_row(audio, phrase, str(Path("audios") / exported_name)))
    finally:
        db.close()

    if args.format == "json":
        metadata_path = output_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps({"items": rows}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        metadata_path = output_dir / "metadata.csv"
        with metadata_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=EXPORT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    print(f"Audios exportes: {len(rows)}")
    print(f"Audios manquants: {missing}")
    print(f"Metadonnees: {metadata_path}")
    print(f"Dossier audios: {audio_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporte un jeu de donnees audios + metadonnees depuis le corpus."
    )
    parser.add_argument("--output", required=True, help="Dossier de sortie.")
    parser.add_argument("--dataset", help="Filtrer par source/dataset.")
    parser.add_argument(
        "--status",
        choices=[status.value for status in AudioStatus],
        help="Filtrer par statut audio.",
    )
    parser.add_argument("--limit", type=int, help="Limiter le nombre d'audios exportes.")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Format des metadonnees.")
    parser.add_argument("--skip-missing", action="store_true", help="Ignorer les fichiers audio introuvables.")
    return parser.parse_args()


if __name__ == "__main__":
    export_dataset(parse_args())
