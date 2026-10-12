#!/usr/bin/env python3
"""Split the Common Voice review queue into 50-row theme batches."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT.parent / "datasets/exports/common_voice_1000_editorial_review.csv"
DEFAULT_OUTPUT = ROOT.parent / "datasets/exports/common_voice_theme_batches"


def split(source: Path, output: Path, count: int = 50, min_up_votes: int = 2) -> Counter[str]:
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        fields = reader.fieldnames or []
        required = {"phrase_br", "theme_propose", "best_audio_filename"}
        if missing := required - set(fields):
            raise ValueError(f"Colonnes absentes : {', '.join(sorted(missing))}")
        groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        seen_texts: set[str] = set()
        seen_audio: set[str] = set()
        for row in reader:
            text = row["phrase_br"].strip().casefold()
            audio = row["best_audio_filename"].strip()
            if not text or not audio or text in seen_texts or audio in seen_audio:
                raise ValueError("Phrase ou audio vide ou en doublon dans la sélection")
            seen_texts.add(text)
            seen_audio.add(audio)
            if int(row["up_votes"]) >= min_up_votes and int(row["down_votes"]) == 0:
                groups[row["theme_propose"].strip()].append(row)

    if count < 1:
        raise ValueError("La taille d'un lot doit être positive")
    output.mkdir(parents=True, exist_ok=True)
    for theme, rows in sorted(groups.items()):
        if not theme or "/" in theme or ".." in theme:
            raise ValueError(f"Thème invalide : {theme!r}")
        selected = sorted(rows, key=lambda row: (-int(row["up_votes"]), int(row["rang"])))[:count]
        path = output / f"common_voice_{theme}_{len(selected)}_review.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter=";", fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(selected)
    return Counter({theme: min(count, len(rows)) for theme, rows in groups.items()})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--min-up-votes", type=int, default=2)
    args = parser.parse_args()
    for theme, amount in sorted(split(args.input, args.output, args.count, args.min_up_votes).items()):
        print(f"{theme}: {amount}")
    print("Lots de relecture uniquement ; aucun import Komz effectué.")


if __name__ == "__main__":
    main()
