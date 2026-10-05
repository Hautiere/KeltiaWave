"""Import an editorial CSV of Breton phrases, with a dry-run by default."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from app.db import SessionLocal
from app.models import Phrase
from app.phrase_provenance import apply_phrase_provenance


LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}
THEMES = {
    "rencontres", "maison-quotidien", "famille-relations", "alimentation-achats",
    "deplacements", "travail-etudes", "sante-bien-etre", "nature-meteo",
    "loisirs-sport", "culture-fetes", "histoire-patrimoine",
    "demarches-services", "numerique-technologies",
}


def key(text: str, language: str) -> tuple[str, str]:
    return text.strip().casefold(), language.strip().casefold()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--apply", action="store_true", help="Écrire les nouvelles phrases.")
    parser.add_argument("--require-reviewed", action="store_true", help="Exiger les trois validations éditoriales.")
    parser.add_argument("--allow-incomplete", action="store_true", help="Importer des candidates sans traduction ni niveau.")
    args = parser.parse_args()
    if args.require_reviewed and args.allow_incomplete:
        parser.error("--require-reviewed et --allow-incomplete sont incompatibles")

    with args.csv.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter=";")
        required = {"phrase_br", "theme_propose", "niveau", "traduction_fr"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            parser.error("Colonnes absentes : " + ", ".join(sorted(missing)))
        rows = list(reader)

    planned: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for line, row in enumerate(rows, 2):
        if args.require_reviewed and any(
            (row.get(column) or "").strip() != "valide"
            for column in ("theme_statut", "traduction_statut", "niveau_statut")
        ):
            parser.error(f"Ligne {line} : thème, traduction ou niveau non validé.")
        text = (row["phrase_br"] or "").strip()
        theme = (row["theme_propose"] or "").strip()
        level = (row["niveau"] or "").strip()
        translation = (row["traduction_fr"] or "").strip()
        if not text or theme not in THEMES or (not translation and not args.allow_incomplete) or (level not in LEVELS and (level or not args.allow_incomplete)):
            parser.error(f"Ligne {line} : phrase, traduction, thème ou niveau invalide.")
        phrase_key = key(text, "br")
        if phrase_key in seen:
            parser.error(f"Ligne {line} : doublon dans le CSV.")
        seen.add(phrase_key)
        planned.append({"texte": text, "traduction_fr": translation or None, "theme": theme, "niveau": level or None,
                        "source": "common-voice", "langue": "br", "auteur": None})

    with SessionLocal() as db:
        existing = {key(item.texte, item.langue or "") for item in db.query(Phrase.texte, Phrase.langue)}
        new = [row for row in planned if key(row["texte"], "br") not in existing]
        print(f"Lignes : {len(planned)} ; déjà présentes : {len(planned) - len(new)} ; à créer : {len(new)}")
        for theme, count in sorted(Counter(row["theme"] for row in new).items()):
            print(f"  {theme}: {count}")
        if not args.apply:
            print("Simulation uniquement : aucune écriture.")
            return
        for row in new:
            apply_phrase_provenance(row)
            db.add(Phrase(**row))
        db.commit()
        print(f"Phrases créées : {len(new)}")


if __name__ == "__main__":
    main()
