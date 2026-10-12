#!/usr/bin/env python3
"""Preview the editorial theme migration without changing source data or Komz."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = ROOT / "datasets/keltiawave_commonvoice_phrases_classees.csv"
DEFAULT_OUTPUT = ROOT / "datasets/exports/preview_themes_komz.csv"

# These mappings preserve the meaning of a single old category. Broader or
# ambiguous categories deliberately remain pending editorial review.
DIRECT = {
    "👨‍👩‍👧 Famille": "famille-relations",
    "🍽️ Cuisine": "alimentation-achats",
    "🌿 Nature": "nature-meteo",
    "💼 Travail": "travail-etudes",
    "🚗 Transports": "deplacements",
    "⚽ Sports & loisirs": "loisirs-sport",
    "🎓 Éducation": "travail-etudes",
    "📜 Histoire": "histoire-patrimoine",
    "🏛️ Administration": "demarches-services",
    "🩺 Santé": "sante-bien-etre",
    "🎉 Traditions & fêtes": "culture-fetes",
    "💻 Technologies": "numerique-technologies",
}
REVIEW = {
    "☕ Vie quotidienne": ("maison-quotidien", "Peut aussi relever de rencontres, achats ou déplacements."),
    "🏰 Culture & patrimoine": ("histoire-patrimoine", "Distinguer patrimoine et culture/fêtes."),
    "📦 Non classé": ("", "Aucun thème éditorial validé."),
}


def preview(source: Path, output: Path) -> Counter:
    counts: Counter = Counter()
    with source.open(encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file, delimiter=";")
        required = {"phrase_id", "phrase_br", "theme_keltiawave", "audio_disponible"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Colonnes absentes : " + ", ".join(sorted(missing)))
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8-sig", newline="") as output_file:
            writer = csv.DictWriter(output_file, delimiter=";", fieldnames=[
                "phrase_id", "phrase_br", "ancien_theme", "theme_propose",
                "decision", "motif", "audio_disponible",
            ])
            writer.writeheader()
            for row in reader:
                old = row["theme_keltiawave"].strip()
                if old in DIRECT:
                    proposed, decision, reason = DIRECT[old], "correspondance_directe", ""
                elif old in REVIEW:
                    proposed, reason = REVIEW[old]
                    decision = "a_relire"
                else:
                    proposed, decision, reason = "", "a_relire", "Ancien thème inconnu."
                writer.writerow({
                    "phrase_id": row["phrase_id"], "phrase_br": row["phrase_br"],
                    "ancien_theme": old, "theme_propose": proposed,
                    "decision": decision, "motif": reason,
                    "audio_disponible": row["audio_disponible"],
                })
                counts[(old, proposed, decision)] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    counts = preview(args.input, args.output)
    print(f"Simulation : {sum(counts.values())} lignes -> {args.output}")
    for (old, proposed, decision), count in counts.most_common():
        print(f"{count:6}  {old} -> {proposed or '(aucun)'} [{decision}]")
    print("Aucune phrase Komz ni donnée source modifiée.")


if __name__ == "__main__":
    main()
