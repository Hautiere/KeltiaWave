#!/usr/bin/env python3
"""Build a reproducible 1,000-row Common Voice editorial review queue."""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

from common_voice import DEFAULT_DATASET_DIR, load_common_voice, rank_audios
from preview_theme_migration import DIRECT


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CLASSIFIED = PROJECT_ROOT.parent / "datasets/keltiawave_commonvoice_phrases_classees.csv"
DEFAULT_PILOT = PROJECT_ROOT / "backend/data/common_voice_selected_50.csv"
DEFAULT_OUTPUT = PROJECT_ROOT.parent / "datasets/exports/common_voice_1000_editorial_review.csv"
THEME_ORDER = list(dict.fromkeys(DIRECT.values()))
FIELDS = [
    "rang", "phrase_br", "theme_source", "theme_propose", "theme_statut",
    "traduction_fr", "traduction_statut", "niveau", "niveau_statut",
    "best_audio_filename", "audio_count", "up_votes", "down_votes",
    "duration_ms", "audio_sha256", "sentence_id", "locale", "accent_declare",
    "variante_declaree", "source", "licence_source", "validation_komz",
]


def read_pilot(path: Path) -> set[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["phrase_br"].strip().casefold() for row in csv.DictReader(handle, delimiter=";")}


def read_durations(path: Path) -> dict[str, int]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            row["clip"]: int(row["duration[ms]"])
            for row in csv.DictReader(handle, delimiter="\t")
            if row.get("duration[ms]", "").isdigit()
        }


def score(item: dict) -> tuple:
    confidence = {"élevée": 0, "moyenne": 1, "faible": 2}.get(item["confidence"], 3)
    return (confidence, -item["audio"]["up_votes"], item["audio"]["down_votes"],
            abs(len(item["text"].split()) - 7), item["text"].casefold())


def prepare(classified: Path, dataset: Path, pilot: Path, output: Path, count: int) -> Counter:
    if count < len(THEME_ORDER) * 10:
        raise ValueError("Le lot est trop petit pour couvrir les thèmes disponibles.")
    pilot_texts = read_pilot(pilot)
    audio_index = load_common_voice(dataset)
    durations = read_durations(dataset / "clip_durations.tsv")
    groups: dict[str, list[dict]] = defaultdict(list)
    seen_texts = set(pilot_texts)

    with classified.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            theme = DIRECT.get(row["theme_keltiawave"].strip())
            text = row["phrase_br"].strip()
            normalized = text.casefold()
            if not theme or normalized in seen_texts or not (12 <= len(text) <= 120):
                continue
            if len(text.split()) > 16:
                continue
            audios = [a for a in audio_index.get(text, [])
                      if a["audio_exists"] and a["up_votes"] >= 2 and a["down_votes"] == 0]
            if not audios:
                continue
            best = rank_audios(audios)[0]
            duration = durations.get(best["audio_filename"])
            if duration is None or not (500 <= duration <= 20000):
                continue
            seen_texts.add(normalized)
            groups[theme].append({
                "text": text, "source_theme": row["theme_keltiawave"],
                "theme": theme, "confidence": row["confiance_classement"],
                "audio": best, "audio_count": len(audio_index[text]),
                "duration": duration,
            })

    for group in groups.values():
        group.sort(key=score)

    # Give every source category a substantial review sample, then fill the
    # rest by cycling through categories. This keeps large categories from
    # crowding out smaller ones.
    selected: list[dict] = []
    positions = {theme: 0 for theme in THEME_ORDER}
    floor = min(50, count // len(THEME_ORDER))
    for theme in THEME_ORDER:
        take = min(floor, len(groups[theme]))
        selected.extend(groups[theme][:take])
        positions[theme] = take
    while len(selected) < count:
        progressed = False
        for theme in THEME_ORDER:
            position = positions[theme]
            if position < len(groups[theme]):
                selected.append(groups[theme][position])
                positions[theme] += 1
                progressed = True
                if len(selected) == count:
                    break
        if not progressed:
            raise ValueError(f"Seulement {len(selected)} candidats disponibles pour {count} lignes.")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter=";", fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for rank, item in enumerate(selected, 1):
            audio = item["audio"]
            path = dataset / "clips" / audio["audio_filename"]
            with path.open("rb") as clip:
                digest = hashlib.file_digest(clip, "sha256").hexdigest()
            writer.writerow({
                "rang": rank,
                "phrase_br": item["text"],
                "theme_source": item["source_theme"],
                "theme_propose": item["theme"],
                "theme_statut": "proposition_a_relire",
                "traduction_fr": "",
                "traduction_statut": "a_traduire",
                "niveau": "",
                "niveau_statut": "a_evaluer",
                "best_audio_filename": path.name,
                "audio_count": item["audio_count"],
                "up_votes": audio["up_votes"],
                "down_votes": audio["down_votes"],
                "duration_ms": item["duration"],
                "audio_sha256": digest,
                "sentence_id": audio["source_id"],
                "locale": audio["locale"],
                "accent_declare": audio["accents"],
                "variante_declaree": audio["variant"],
                "source": "common-voice",
                "licence_source": "CC0 (déclaration du jeu de données)",
                "validation_komz": "non_valide",
            })
    return Counter(item["theme"] for item in selected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classified", type=Path, default=DEFAULT_CLASSIFIED)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--count", type=int, default=1000)
    args = parser.parse_args()
    counts = prepare(args.classified, args.dataset, args.pilot, args.output, args.count)
    print(f"{sum(counts.values())} candidats à relire → {args.output}")
    for theme, count in sorted(counts.items()):
        print(f"  {theme}: {count}")
    print("Aucun import Komz effectué.")


if __name__ == "__main__":
    main()
