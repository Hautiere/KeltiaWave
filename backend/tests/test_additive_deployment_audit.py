from sqlalchemy import create_engine, text
from scripts.audit_existing_rows import capture, verify


def test_additions_and_new_columns_preserve_old_rows():
    engine = create_engine('sqlite://')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE items (id INTEGER PRIMARY KEY, value TEXT)'))
        conn.execute(text("INSERT INTO items VALUES (1, 'original')"))
    original = capture(engine)
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE items ADD COLUMN extra TEXT'))
        conn.execute(text("INSERT INTO items VALUES (2, 'new', NULL)"))
    assert verify(engine, original)['items'] == dict(before=1, after=2, missing_or_changed=0)


def test_changed_existing_value_is_detected():
    engine = create_engine('sqlite://')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE items (id INTEGER PRIMARY KEY, value TEXT)'))
        conn.execute(text("INSERT INTO items VALUES (1, 'original')"))
    original = capture(engine)
    with engine.begin() as conn:
        conn.execute(text("UPDATE items SET value = 'changed' WHERE id = 1"))
    assert verify(engine, original)['items']['missing_or_changed'] == 1


def test_deleted_duplicate_row_is_detected():
    engine = create_engine('sqlite://')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE items (value TEXT)'))
        conn.execute(text("INSERT INTO items VALUES ('same'), ('same')"))
    original = capture(engine)
    with engine.begin() as conn:
        conn.execute(text('DELETE FROM items WHERE rowid = 1'))
    assert verify(engine, original)['items']['missing_or_changed'] == 1
