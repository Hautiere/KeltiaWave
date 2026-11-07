"""Import French, English and Welsh translations for an exact phrase selection.

Dry-run by default. Existing translations are preserved. An apply requires a
new snapshot file, written before the database transaction is committed.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from app.db import SessionLocal
from app.models import Phrase

FIELDS = ('traduction_fr', 'traduction_en', 'traduction_cy')


def read_rows(path: Path, expected_count: int) -> list[dict[str, str]]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not {'id', 'texte', *FIELDS}.issubset(reader.fieldnames or []):
            raise ValueError('CSV must contain id, texte and the three translations')
        rows = list(reader)
    if len(rows) != expected_count or expected_count < 1:
        raise ValueError(f'Expected {expected_count} rows, found {len(rows)}')
    ids = [int(row['id']) for row in rows]
    if len(set(ids)) != len(ids) or len({row['texte'] for row in rows}) != len(rows):
        raise ValueError('Duplicate phrase IDs or texts')
    if any(not row[field].strip() for row in rows for field in ('texte', *FIELDS)):
        raise ValueError('Empty text or translation')
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--expected-count', type=int, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--snapshot', type=Path)
    args = parser.parse_args()
    if args.apply and not args.snapshot:
        parser.error('--snapshot is required with --apply')
    rows = read_rows(args.csv, args.expected_count)
    with SessionLocal() as db:
        ids = [int(row['id']) for row in rows]
        phrases = {p.id: p for p in db.query(Phrase).filter(Phrase.id.in_(ids)).all()}
        changes = []
        counts = dict.fromkeys(FIELDS, 0)
        for row in rows:
            phrase = phrases.get(int(row['id']))
            if phrase is None or phrase.langue != 'br' or phrase.source != 'common-voice' or phrase.texte != row['texte']:
                raise ValueError(f"Phrase {row['id']}: missing or source/text changed")
            before = {field: getattr(phrase, field) for field in FIELDS}
            after = dict(before)
            for field in FIELDS:
                if not (before[field] or '').strip():
                    after[field] = row[field].strip()
                    counts[field] += 1
            if before != after:
                changes.append(dict(id=phrase.id, texte=phrase.texte, before=before, after=after))
        print(f'Matched: {len(rows)}; new translations: {counts}; apply: {args.apply}')
        if args.apply:
            with args.snapshot.open('x', encoding='utf-8') as handle:
                json.dump(changes, handle, ensure_ascii=False, indent=2)
            for change in changes:
                for field, value in change['after'].items():
                    setattr(phrases[change['id']], field, value)
            db.commit()


if __name__ == '__main__':
    main()
