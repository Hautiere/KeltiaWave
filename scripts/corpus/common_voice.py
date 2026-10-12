from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


# scripts/corpus/common_voice.py
# parents[0] = corpus
# parents[1] = scripts
# parents[2] = racine keltiawave
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent

DEFAULT_DATASET_DIR = WORKSPACE_ROOT / "datasets" / "br"

def _to_int(value: str | None) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def load_common_voice(
    dataset_dir: Path = DEFAULT_DATASET_DIR,
) -> dict[str, list[dict[str, Any]]]:
    """
    Charge datasets/br/validated.tsv.

    Retour :
        {
            "Petra eo da anv ?": [
                {...audio 1...},
                {...audio 2...},
                ...
            ]
        }

    Une phrase Common Voice peut avoir plusieurs enregistrements.
    """

    dataset_dir = Path(dataset_dir)
    validated_path = dataset_dir / "validated.tsv"
    clips_dir = dataset_dir / "clips"

    if not validated_path.exists():
        raise FileNotFoundError(
            f"Fichier Common Voice introuvable : {validated_path}"
        )

    if not clips_dir.exists():
        raise FileNotFoundError(
            f"Répertoire audio Common Voice introuvable : {clips_dir}"
        )

    index: dict[str, list[dict[str, Any]]] = {}

    with validated_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.DictReader(f, delimiter="\t")

        required_columns = {
            "client_id",
            "path",
            "sentence_id",
            "sentence",
            "up_votes",
            "down_votes",
        }

        missing = required_columns - set(reader.fieldnames or [])

        if missing:
            raise ValueError(
                "Colonnes absentes de validated.tsv : "
                + ", ".join(sorted(missing))
            )

        for row in reader:
            sentence = (row.get("sentence") or "").strip()
            filename = (row.get("path") or "").strip()

            if not sentence or not filename:
                continue

            audio_path = clips_dir / filename

            audio = {
                "source": "common_voice",
                "source_id": (row.get("sentence_id") or "").strip(),
                "sentence": sentence,
                "audio_filename": filename,
                "reference_audio": str(audio_path),
                "audio_exists": audio_path.exists(),
                "speaker": (row.get("client_id") or "").strip(),
                "age": (row.get("age") or "").strip(),
                "gender": (row.get("gender") or "").strip(),
                "accents": (row.get("accents") or "").strip(),
                "variant": (row.get("variant") or "").strip(),
                "locale": (row.get("locale") or "").strip(),
                "sentence_domain": (
                    row.get("sentence_domain") or ""
                ).strip(),
                "up_votes": _to_int(row.get("up_votes")),
                "down_votes": _to_int(row.get("down_votes")),

                # On reste prudent sur les droits tant qu'ils
                # n'ont pas été explicitement vérifiés.
                "license": None,
                "audio_rights": "TO_CHECK",
                "publication_audio": False,
            }

            index.setdefault(sentence, []).append(audio)

    return index


def rank_audios(
    audios: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Classe les audios :
      1. plus de up_votes
      2. moins de down_votes
      3. nom de fichier pour rendre les égalités déterministes
    """

    return sorted(
        audios,
        key=lambda audio: (
            -audio["up_votes"],
            audio["down_votes"],
            audio["audio_filename"],
        ),
    )


def best_audio(
    audios: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Retourne l'audio le mieux validé.
    """

    if not audios:
        return None

    return rank_audios(audios)[0]


def find_exact_phrase(
    index: dict[str, list[dict[str, Any]]],
    phrase: str,
) -> list[dict[str, Any]]:
    """
    Recherche exacte d'une phrase.
    """

    return index.get(phrase.strip(), [])


def find_best_audio(
    index: dict[str, list[dict[str, Any]]],
    phrase: str,
) -> dict[str, Any] | None:
    """
    Recherche une phrase exacte et retourne son meilleur audio.
    """

    return best_audio(find_exact_phrase(index, phrase))


def phrase_summary(
    index: dict[str, list[dict[str, Any]]],
    phrase: str,
) -> dict[str, Any]:
    """
    Retourne un résumé directement exploitable
    par KeltiaWave.
    """

    audios = find_exact_phrase(index, phrase)
    ranked = rank_audios(audios)

    return {
        "phrase": phrase,
        "audio_count": len(ranked),
        "best_reference_audio": ranked[0] if ranked else None,
        "reference_audios": ranked,
    }