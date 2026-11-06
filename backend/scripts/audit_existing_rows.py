"""Fingerprint existing rows before an additive deployment; never print row data."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from sqlalchemy import inspect, text
from app.db import engine


def fingerprints(connection, table, columns):
    quote = connection.dialect.identifier_preparer.quote
    statement = text('SELECT ' + ', '.join(quote(c) for c in columns) + ' FROM ' + quote(table))
    return dict(Counter(hashlib.sha256(json.dumps(list(row), default=str, ensure_ascii=False).encode()).hexdigest()
                        for row in connection.execute(statement)))


def capture(db_engine):
    result = {}
    with db_engine.connect() as conn:
        inspector = inspect(conn)
        for table in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns(table)]
            result[table] = dict(columns=columns, rows=fingerprints(conn, table, columns))
    return result


def verify(db_engine, baseline):
    report = {}
    with db_engine.connect() as conn:
        inspector = inspect(conn)
        for table, original in baseline.items():
            if not inspector.has_table(table):
                raise ValueError(f'Existing table missing: {table}')
            current = fingerprints(conn, table, original['columns'])
            missing = sum(max(0, count - current.get(key, 0)) for key, count in original['rows'].items())
            report[table] = dict(before=sum(original['rows'].values()), after=sum(current.values()), missing_or_changed=missing)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['capture', 'verify'])
    parser.add_argument('snapshot', type=Path)
    args = parser.parse_args()
    if args.mode == 'capture':
        data = capture(engine)
        with args.snapshot.open('x', encoding='utf-8') as handle:
            json.dump(data, handle)
        print(json.dumps({table: sum(value['rows'].values()) for table, value in data.items()}))
    else:
        report = verify(engine, json.loads(args.snapshot.read_text()))
        print(json.dumps(report, indent=2))
        if any(value['missing_or_changed'] for value in report.values()):
            raise SystemExit('Existing rows were changed or removed; investigate before continuing')


if __name__ == '__main__':
    main()
