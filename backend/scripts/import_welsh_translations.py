"""Import draft Welsh translations with a dry run by default.

Run from backend with PYTHONPATH=. python scripts/import_welsh_translations.py FILE.
Existing Welsh translations are preserved unless --replace is passed.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from app.db import SessionLocal
from app.models import Phrase


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    with args.file.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if not {"id", "texte", "traduction_cy"}.issubset(reader.fieldnames or []):
            raise SystemExit("CSV must contain id, texte and traduction_cy")
        rows = list(reader)
    ids = [int(row["id"]) for row in rows]
    if len(ids) != len(set(ids)) or any(not row["traduction_cy"].strip() for row in rows):
        raise SystemExit("Duplicate IDs or empty Welsh translations")

    with SessionLocal() as db:
        phrases = {phrase.id: phrase for phrase in db.query(Phrase).filter(Phrase.id.in_(ids)).all()}
        for row in rows:
            phrase = phrases.get(int(row["id"]))
            if phrase is None or phrase.langue != "br" or phrase.texte != row["texte"]:
                raise SystemExit(f"Phrase {row['id']} is missing or its Breton text changed")
        changes = [row for row in rows if args.replace or not phrases[int(row["id"])].traduction_cy]
        print(f"Matched: {len(rows)}; to update: {len(changes)}; apply: {args.apply}")
        if args.apply:
            for row in changes:
                phrases[int(row["id"])].traduction_cy = row["traduction_cy"].strip()
            db.commit()


if __name__ == "__main__":
    main()
