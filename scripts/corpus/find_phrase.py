from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


from common_voice import (
    DEFAULT_DATASET_DIR,
    load_common_voice,
    phrase_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Recherche une phrase exacte dans Common Voice "
            "et retourne l'audio le mieux validé."
        )
    )

    parser.add_argument(
        "phrase",
        help='Phrase bretonne, ex. "Petra eo da anv ?"',
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_DIR,
        help="Répertoire du corpus Common Voice breton",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Afficher tous les enregistrements",
    )

    args = parser.parse_args()

    index = load_common_voice(args.dataset)

    result = phrase_summary(
        index,
        args.phrase,
    )

    print()
    print(f"Phrase : {result['phrase']}")
    print(f"Nombre d'audios : {result['audio_count']}")

    best = result["best_reference_audio"]

    if best is None:
        print()
        print("❌ Aucun audio Common Voice exact trouvé.")
        raise SystemExit(1)

    print()
    print("★ MEILLEUR AUDIO")
    print("-----------------")

    print(f"Fichier     : {best['audio_filename']}")
    print(f"Chemin      : {best['reference_audio']}")
    print(f"Up votes    : {best['up_votes']}")
    print(f"Down votes  : {best['down_votes']}")
    print(f"Âge         : {best['age'] or '-'}")
    print(f"Genre       : {best['gender'] or '-'}")
    print(f"Accent      : {best['accents'] or '-'}")
    print(f"Variante    : {best['variant'] or '-'}")
    print(f"Sentence ID : {best['source_id']}")
    print(f"Audio existe: {best['audio_exists']}")

    if args.all:
        print()
        print("TOUS LES AUDIOS")
        print("----------------")

        for position, audio in enumerate(
            result["reference_audios"],
            start=1,
        ):
            print(
                f"{position:02d}. "
                f"{audio['audio_filename']} "
                f"👍 {audio['up_votes']} "
                f"👎 {audio['down_votes']} "
                f"accent={audio['accents'] or '-'} "
                f"age={audio['age'] or '-'}"
            )


if __name__ == "__main__":
    main()