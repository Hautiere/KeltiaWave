"""Apply reviewed subdomain proposals to a local corpus database.

Dry run by default. Never overwrites an existing subdomain or other phrase data.
"""

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

from app.db import SessionLocal
from app.models.phrase import Phrase


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    rows = list(csv.DictReader(args.csv_file.open(encoding="utf-8-sig", newline="")))
    proposals = [row for row in rows if row.get("proposal_status") == "lexical" and row.get("subdomain_propose")]
    if len({row["phrase_id"] for row in proposals}) != len(proposals):
        raise SystemExit("Duplicate phrase IDs in proposals")

    counts: Counter[str] = Counter()
    with SessionLocal() as db:
        for row in proposals:
            value = row["subdomain_propose"]
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
                raise SystemExit(f"Invalid subdomain value for phrase {row['phrase_id']}")
            phrase = db.get(Phrase, int(row["phrase_id"]))
            if not phrase or phrase.texte != row["texte_breton"] or phrase.theme != row["theme"]:
                raise SystemExit(f"Phrase {row['phrase_id']} changed since export; no changes committed")
            if phrase.subdomain:
                counts["already_classified"] += 1
                continue
            phrase.subdomain = value
            counts["proposed"] += 1
        if args.apply:
            db.commit()
        else:
            db.rollback()
    print(f"mode={'apply' if args.apply else 'dry-run'} {dict(counts)}")


if __name__ == "__main__":
    main()
