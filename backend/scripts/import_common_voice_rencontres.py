"""Import the reviewed selection envelope for 50 Common Voice meeting phrases.

The command plans by default. ``--apply`` creates missing phrases and audios,
then marks the selected dataset audios as batch approved without claiming an
individual listening or linguistic review.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import io
from pathlib import Path
import re
import tempfile
from uuid import uuid4
import zipfile

from app.db import SessionLocal
from app.library_storage import TransferStorage
from app.models import Audio, Phrase
from app.models.audio import AudioStatus
from app.storage import delete_audio_file, save_audio_file_path


BATCH_COMMENT = (
    "Approbation en lot demandée par le propriétaire ; "
    "écoute et contrôle linguistique non effectués."
)
SUBDOMAINS = {
    "saluer-et-prendre-conge", "se-presenter", "origine-et-lieu-de-vie",
    "parler-de-soi", "gouts-et-preferences", "poser-des-questions",
}
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_CLIP_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class Entry:
    text: str
    subdomain: str
    source_lot: str
    translation: str | None
    level: str | None
    filename: str
    data: bytes
    sha256: str


def load_package(path: Path) -> list[Entry]:
    if not path.is_file() or path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive absente ou trop volumineuse")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or "manifest.csv" not in names:
            raise ValueError("Manifeste absent ou noms dupliqués")
        if len(infos) != 51 or sum(info.file_size for info in infos) > MAX_ARCHIVE_BYTES:
            raise ValueError("Le lot doit contenir exactement 50 audios")
        if any(info.file_size > MAX_CLIP_BYTES for info in infos if info.filename != "manifest.csv"):
            raise ValueError("Audio trop volumineux")
        raw = archive.read("manifest.csv")
        if len(raw) > 256 * 1024:
            raise ValueError("Manifeste trop volumineux")
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter=";")
        required = {
            "phrase_br", "theme_propose", "sous_theme_propose", "source_lot",
            "traduction_fr_proposee", "niveau_propose", "best_audio_filename",
            "up_votes", "down_votes", "audio_sha256",
        }
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Colonnes manquantes dans le manifeste")
        rows = list(reader)
        if len(rows) != 50:
            raise ValueError(f"50 phrases attendues ; {len(rows)} trouvées")
        entries = []
        seen_text = set()
        seen_files = set()
        for row in rows:
            text = (row["phrase_br"] or "").strip()
            filename = (row["best_audio_filename"] or "").strip()
            subdomain = (row["sous_theme_propose"] or "").strip()
            lot = (row["source_lot"] or "").strip()
            level = (row["niveau_propose"] or "").strip() or None
            sha = (row["audio_sha256"] or "").strip().lower()
            if (
                not text or text.casefold() in seen_text
                or not re.fullmatch(r"common_voice_br_[0-9]+\.mp3", filename)
                or filename in seen_files or row["theme_propose"] != "rencontres"
                or subdomain not in SUBDOMAINS
                or lot not in {"premier_lot_existant", "nouvelle_candidate"}
                or (level is not None and level not in {"A1", "A2", "B1", "B2", "C1", "C2"})
                or int(row["up_votes"]) < 2 or int(row["down_votes"]) != 0
                or not re.fullmatch(r"[0-9a-f]{64}", sha)
            ):
                raise ValueError(f"Métadonnées invalides pour {text or filename}")
            seen_text.add(text.casefold())
            seen_files.add(filename)
            member = f"audios/{filename}"
            if member not in names:
                raise ValueError(f"Audio absent : {filename}")
            data = archive.read(member)
            if not data or len(data) > MAX_CLIP_BYTES or hashlib.sha256(data).hexdigest() != sha:
                raise ValueError(f"Empreinte ou taille invalide : {filename}")
            entries.append(Entry(text, subdomain, lot,
                                 (row["traduction_fr_proposee"] or "").strip() or None,
                                 level, filename, data, sha))
        if set(names) != {"manifest.csv"} | {f"audios/{entry.filename}" for entry in entries}:
            raise ValueError("Fichier inattendu dans l'archive")
        if sum(entry.source_lot == "premier_lot_existant" for entry in entries) != 19:
            raise ValueError("19 phrases du premier lot attendues")
        return entries


def plan(db, store: TransferStorage, entries: list[Entry]):
    phrases = db.query(Phrase).filter(Phrase.langue == "br").all()
    by_text: dict[str, list[Phrase]] = {}
    for phrase in phrases:
        by_text.setdefault(phrase.texte.strip().casefold(), []).append(phrase)
    result = []
    for entry in entries:
        matches = by_text.get(entry.text.casefold(), [])
        if len(matches) > 1:
            raise ValueError(f"Phrase ambiguë : {entry.text}")
        phrase = matches[0] if matches else None
        if entry.source_lot == "premier_lot_existant" and phrase is None:
            raise ValueError(f"Phrase historique absente : {entry.text}")
        if phrase and (phrase.theme != "rencontres" or phrase.source != "common-voice"):
            raise ValueError(f"Classement ou source inattendu pour #{phrase.id} {entry.text}")
        if phrase and phrase.subdomain and phrase.subdomain != entry.subdomain:
            raise ValueError(f"Sous-thème déjà différent pour #{phrase.id} {entry.text}")
        audio = None
        if phrase:
            audios = db.query(Audio).filter(Audio.phrase_id == phrase.id).all()
            candidates = [item for item in audios if item.origin == "dataset" and item.phrase_source == "common-voice"]
            if len(candidates) > 1 or (entry.source_lot == "premier_lot_existant" and len(candidates) != 1):
                raise ValueError(f"Nombre d'audios Common Voice inattendu pour #{phrase.id}")
            if candidates:
                audio = candidates[0]
                if audio.status == AudioStatus.rejected or audio.domain != "rencontres":
                    raise ValueError(f"Audio rejeté ou mal classé pour #{phrase.id}")
                if hashlib.sha256(store.read(audio.filename)).hexdigest() != entry.sha256:
                    raise ValueError(f"Audio déjà stocké différent du MP3 sélectionné pour #{phrase.id}")
        result.append((entry, phrase, audio))
    return result


def run(path: Path, *, apply: bool) -> dict[str, int]:
    entries = load_package(path)
    store = TransferStorage.configured()
    with SessionLocal() as db:
        planned = plan(db, store, entries)
        report = {
            "phrases_existantes": sum(phrase is not None for _, phrase, _ in planned),
            "phrases_a_creer": sum(phrase is None for _, phrase, _ in planned),
            "audios_existants": sum(audio is not None for _, _, audio in planned),
            "audios_a_creer": sum(audio is None for _, _, audio in planned),
            "audios_a_approuver": sum(audio is None or audio.status == AudioStatus.pending for _, _, audio in planned),
            "sous_themes_a_renseigner": sum(phrase is None or not phrase.subdomain for _, phrase, _ in planned),
        }
        if not apply:
            return report
        uploaded = []
        try:
            with tempfile.TemporaryDirectory(prefix="rencontres-import-") as temp_dir:
                for entry, phrase, audio in planned:
                    if phrase is None:
                        phrase = Phrase(texte=entry.text, traduction_fr=entry.translation,
                                        theme="rencontres", subdomain=entry.subdomain,
                                        niveau=entry.level, source="common-voice", langue="br")
                        db.add(phrase)
                        db.flush()
                    elif not phrase.subdomain:
                        phrase.subdomain = entry.subdomain
                    if audio is None:
                        clip = Path(temp_dir) / entry.filename
                        clip.write_bytes(entry.data)
                        storage_name = f"common-voice-rencontres-{uuid4().hex}.mp3"
                        ref = save_audio_file_path(clip, storage_name, "audio/mpeg")
                        uploaded.append(ref)
                        audio = Audio(phrase_id=phrase.id, filename=ref, origin="dataset",
                                      status=AudioStatus.approved, phrase_source="common-voice",
                                      domain="rencontres", validation_comment=BATCH_COMMENT)
                        db.add(audio)
                    elif audio.status == AudioStatus.pending:
                        audio.status = AudioStatus.approved
                        audio.validation_comment = BATCH_COMMENT
            db.commit()
        except BaseException:
            db.rollback()
            for ref in uploaded:
                try:
                    delete_audio_file(ref)
                except Exception:
                    pass
            raise
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    report = run(args.archive, apply=args.apply)
    for label, count in report.items():
        print(f"{label}: {count}")
    print("Import effectué." if args.apply else "Simulation uniquement : aucune écriture.")


if __name__ == "__main__":
    main()
