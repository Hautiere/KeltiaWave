"""Import the English and Welsh translation lots across databases with different IDs.

Matches each row by its exact Breton text, checks uniqueness and commits both
languages in one transaction. Dry-run by default; existing translations are
preserved. Use --allow-missing only after reviewing the reported missing rows.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from app.db import SessionLocal
from app.models import Phrase
from scripts.seed_english_translations import TRANSLATIONS as EN_CORRECTIONS
from scripts.seed_welsh_corrections import CORRECTIONS as CY_CORRECTIONS


def read_rows(path: Path, language: str) -> dict[int, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"id", "texte", f"traduction_{language}"}
        if not required.issubset(reader.fieldnames or []):
            raise SystemExit(f"{path}: missing columns {required}")
        rows = list(reader)
    by_id = {int(row["id"]): row for row in rows}
    if len(by_id) != len(rows):
        raise SystemExit(f"{path}: duplicate IDs")
    if any(not row["texte"].strip() or not row[f"traduction_{language}"].strip() for row in rows):
        raise SystemExit(f"{path}: empty source or translation")
    return by_id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("english_csv", type=Path)
    parser.add_argument("welsh_csv", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()

    english = read_rows(args.english_csv, "en")
    welsh = read_rows(args.welsh_csv, "cy")
    if set(english) & set(EN_CORRECTIONS) or set(english) | set(EN_CORRECTIONS) != set(welsh):
        raise SystemExit("English draft and corrections must partition the Welsh reference IDs")
    if not set(CY_CORRECTIONS) <= set(welsh):
        raise SystemExit("Welsh corrections contain IDs absent from the reference")
    for phrase_id, row in english.items():
        if row["texte"] != welsh[phrase_id]["texte"]:
            raise SystemExit(f"Breton text differs between CSVs for ID {phrase_id}")

    sources = [row["texte"] for row in welsh.values()]
    if len(sources) != len(set(sources)):
        raise SystemExit("Duplicate Breton texts in the source lot")

    with SessionLocal() as db:
        by_text: dict[str, list[Phrase]] = defaultdict(list)
        for phrase in db.query(Phrase).filter(Phrase.langue == "br").all():
            by_text[phrase.texte].append(phrase)
        missing = [(phrase_id, row["texte"]) for phrase_id, row in welsh.items() if row["texte"] not in by_text]
        ambiguous = [(phrase_id, row["texte"]) for phrase_id, row in welsh.items() if len(by_text[row["texte"]]) > 1]
        if ambiguous:
            raise SystemExit(f"Ambiguous target texts: {ambiguous}")
        if missing:
            print(f"Missing target phrases ({len(missing)}): {missing}")
            if not args.allow_missing:
                raise SystemExit("Import stopped; review missing phrases before using --allow-missing")

        changed_en = changed_cy = already_en = already_cy = 0
        for phrase_id, row in welsh.items():
            if not by_text[row["texte"]]:
                continue
            phrase = by_text[row["texte"]][0]
            en = EN_CORRECTIONS.get(phrase_id) or english[phrase_id]["traduction_en"].strip()
            cy = CY_CORRECTIONS.get(phrase_id) or row["traduction_cy"].strip()
            if phrase.traduction_en:
                already_en += 1
            else:
                phrase.traduction_en = en
                changed_en += 1
            if phrase.traduction_cy:
                already_cy += 1
            else:
                phrase.traduction_cy = cy
                changed_cy += 1
        print(
            f"Matched: {len(welsh) - len(missing)}; missing: {len(missing)}; "
            f"English new/existing: {changed_en}/{already_en}; "
            f"Welsh new/existing: {changed_cy}/{already_cy}; apply: {args.apply}"
        )
        if args.apply:
            db.commit()


if __name__ == "__main__":
    main()
