from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


from common_voice import (
    DEFAULT_DATASET_DIR,
    find_exact_phrase,
    load_common_voice,
    rank_audios,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent

DEFAULT_INPUT = (
    WORKSPACE_ROOT
    / "datasets"
    / "keltiawave_commonvoice_phrases_classees.csv"
)

DEFAULT_OUTPUT_DIR = (
    WORKSPACE_ROOT
    / "datasets"
    / "exports"
)

def safe_filename(value: str) -> str:
    """
    Produit un nom de fichier simple à partir du thème.
    """

    value = value.lower().strip()

    value = re.sub(
        r"[^a-z0-9àâäéèêëîïôöùûüç]+",
        "_",
        value,
    )

    return value.strip("_")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extrait les phrases d'un thème KeltiaWave "
            "et sélectionne le meilleur audio Common Voice."
        )
    )

    parser.add_argument(
        "--theme",
        required=True,
        help='Exemple : "👨‍👩‍👧 Famille"',
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="CSV contenant les phrases classées",
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_DIR,
        help="Corpus Common Voice breton",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV de sortie",
    )

    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            f"CSV d'entrée introuvable : {args.input}"
        )

    cv_index = load_common_voice(args.dataset)

    output = args.output

    if output is None:
        output = (
            DEFAULT_OUTPUT_DIR
            / f"{safe_filename(args.theme)}.csv"
        )

    results = []

    with args.input.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        reader = csv.DictReader(
            f,
            delimiter=";",
        )

        required = {
            "phrase_id",
            "phrase_br",
            "theme_keltiawave",
        }

        missing = required - set(reader.fieldnames or [])

        if missing:
            raise ValueError(
                "Colonnes absentes du CSV : "
                + ", ".join(sorted(missing))
            )

        for row in reader:

            if row["theme_keltiawave"].strip() != args.theme:
                continue

            phrase = row["phrase_br"].strip()

            audios = find_exact_phrase(
                cv_index,
                phrase,
            )

            ranked = rank_audios(audios)

            best = ranked[0] if ranked else None

            result = {
                "phrase_id": row["phrase_id"],
                "phrase_br": phrase,
                "theme": args.theme,

                "audio_count": len(ranked),
                "audio_available": bool(ranked),

                "best_audio_filename": "",
                "best_reference_audio": "",

                "up_votes": "",
                "down_votes": "",

                "sentence_id": "",
                "speaker": "",

                "age": "",
                "gender": "",
                "accent": "",
                "variant": "",
                "locale": "",

                "audio_rights": "",
                "publication_audio": False,
            }

            if best:
                result.update(
                    {
                        "best_audio_filename":
                            best["audio_filename"],

                        "best_reference_audio":
                            best["reference_audio"],

                        "up_votes":
                            best["up_votes"],

                        "down_votes":
                            best["down_votes"],

                        "sentence_id":
                            best["source_id"],

                        "speaker":
                            best["speaker"],

                        "age":
                            best["age"],

                        "gender":
                            best["gender"],

                        "accent":
                            best["accents"],

                        "variant":
                            best["variant"],

                        "locale":
                            best["locale"],

                        "audio_rights":
                            best["audio_rights"],

                        "publication_audio":
                            best["publication_audio"],
                    }
                )

            results.append(result)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "phrase_id",
        "phrase_br",
        "theme",

        "audio_count",
        "audio_available",

        "best_audio_filename",
        "best_reference_audio",

        "up_votes",
        "down_votes",

        "sentence_id",
        "speaker",

        "age",
        "gender",
        "accent",
        "variant",
        "locale",

        "audio_rights",
        "publication_audio",
    ]

    with output.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter=";",
        )

        writer.writeheader()
        writer.writerows(results)

    with_audio = sum(
        1
        for row in results
        if row["audio_available"]
    )

    print()
    print("EXTRACTION KELTIAWAVE")
    print("---------------------")
    print(f"Thème       : {args.theme}")
    print(f"Phrases     : {len(results)}")
    print(f"Avec audio  : {with_audio}")
    print(f"Sans audio  : {len(results) - with_audio}")
    print(f"Sortie      : {output}")


if __name__ == "__main__":
    main()