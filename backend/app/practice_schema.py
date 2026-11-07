"""Idempotent additive upgrades for existing Corpus-managed practice tables."""
from sqlalchemy import inspect, text


def ensure_practice_columns(engine):
    wanted = {
        'practice_classes': {'school': "TEXT DEFAULT '' NOT NULL"},
        'practice_submissions': {
            'feedback_revision': 'INTEGER DEFAULT 0 NOT NULL',
            'feedback_seen_revision': 'INTEGER DEFAULT 0 NOT NULL',
        },
    }
    with engine.begin() as conn:
        for table, columns in wanted.items():
            existing = {column['name'] for column in inspect(conn).get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    optional = 'IF NOT EXISTS ' if engine.dialect.name == 'postgresql' else ''
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {optional}{name} {ddl}'))
        conn.execute(text("UPDATE practice_submissions SET feedback_revision = 1 "
                          "WHERE feedback IS NOT NULL AND feedback <> '' AND feedback_revision = 0"))
