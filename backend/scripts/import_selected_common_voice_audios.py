"""Associate the selected Common Voice clips with existing Komz phrases.

Dry run by default. Run with --apply only after reviewing the printed plan.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from app.db import SessionLocal
from app.models import Audio, Phrase
from app.models.audio import AudioStatus
from app.storage import save_audio_file_path, storage_ref_exists
from scripts.import_corpus_dataset import audio_storage_name


def key(text: str) -> str:
    return text.strip().casefold()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with args.csv.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter=";")
        required = {"phrase_br", "best_audio_filename", "theme_propose"}
        if required - set(reader.fieldnames or []):
            parser.error(f"Colonnes absentes : {', '.join(sorted(required - set(reader.fieldnames or [])))}")
        rows = list(reader)

    if len(rows) != 50:
        parser.error(f"Lot attendu : 50 phrases ; trouvé : {len(rows)}")

    audio_root = args.audio_root.resolve()
    planned = []
    seen_phrases = set()
    seen_files = set()
    with SessionLocal() as db:
        phrases = db.query(Phrase).filter(Phrase.source == "common-voice", Phrase.langue == "br").all()
        by_text: dict[str, list[Phrase]] = {}
        for phrase in phrases:
            by_text.setdefault(key(phrase.texte), []).append(phrase)

        for line, row in enumerate(rows, 2):
            text = (row["phrase_br"] or "").strip()
            name = (row["best_audio_filename"] or "").strip()
            matches = by_text.get(key(text), [])
            if len(matches) != 1:
                parser.error(f"Ligne {line} : {len(matches)} phrase(s) Common Voice pour {text!r}")
            if key(text) in seen_phrases or name in seen_files:
                parser.error(f"Ligne {line} : phrase ou fichier audio en doublon")
            seen_phrases.add(key(text))
            seen_files.add(name)
            if not name or Path(name).name != name or Path(name).suffix.lower() != ".mp3":
                parser.error(f"Ligne {line} : nom de fichier MP3 invalide")
            path = (audio_root / name).resolve()
            if not path.is_relative_to(audio_root) or not path.is_file() or path.stat().st_size == 0:
                parser.error(f"Ligne {line} : audio absent ou vide : {name}")
            phrase = matches[0]
            if phrase.theme != (row["theme_propose"] or "").strip():
                parser.error(f"Ligne {line} : thème différent dans la base pour la phrase #{phrase.id}")
            storage_name = audio_storage_name("common-voice-selected-50", text, path)
            existing = db.query(Audio).filter(Audio.filename.like(f"%/{storage_name}")).all()
            if len(existing) > 1 or (existing and existing[0].phrase_id != phrase.id):
                parser.error(f"Ligne {line} : conflit de stockage pour {name}")
            if existing and not storage_ref_exists(existing[0].filename):
                parser.error(f"Ligne {line} : fichier stocké introuvable pour {name}")
            planned.append((phrase, path, storage_name, existing[0] if existing else None))

        new = [item for item in planned if item[3] is None]
        print(f"Phrases vérifiées : {len(planned)} ; audios déjà associés : {len(planned) - len(new)} ; à créer : {len(new)}")
        for phrase, path, _, _ in new:
            print(f"  #{phrase.id} {phrase.texte} <- {path.name}")
        if not args.apply:
            print("Simulation uniquement : aucune écriture.")
            return

        uploaded: list[str] = []
        try:
            for phrase, path, storage_name, _ in new:
                storage_ref = save_audio_file_path(path, storage_name, "audio/mpeg")
                uploaded.append(storage_ref)
                db.add(Audio(
                    phrase_id=phrase.id,
                    filename=storage_ref,
                    origin="dataset",
                    status=AudioStatus.pending,
                    phrase_source="common-voice",
                    domain=phrase.theme,
                ))
            db.commit()
        except Exception:
            db.rollback()
            from app.storage import delete_audio_file
            for storage_ref in uploaded:
                try:
                    delete_audio_file(storage_ref)
                except Exception:
                    pass
            raise
        print(f"Audios créés : {len(new)} ; statut : pending")


if __name__ == "__main__":
    main()
