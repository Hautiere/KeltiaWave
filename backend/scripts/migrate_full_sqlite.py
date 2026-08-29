from __future__ import annotations

import argparse
import json
import mimetypes
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import Boolean, DateTime, JSON, MetaData, Table, func, select, text

from app import storage
from app.db import engine
from app.learning import models as learning_models  # noqa: F401
from app.models import Audio, Phrase, User  # noqa: F401
from app.models.audio import AudioValidation  # noqa: F401


TABLES = (
    "phrases",
    "audios",
    "audio_validations",
    "learning_lessons",
    "learning_videos",
    "learning_segments",
    "learning_blanks",
    "learning_vocabulary_items",
    "learning_grammar_items",
    "learning_progress",
)


def rows(connection: sqlite3.Connection, table: str) -> list[dict]:
    return [dict(row) for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY id')]


def convert_value(column, value):
    if value is None:
        return None
    if isinstance(column.type, Boolean):
        return bool(value)
    if isinstance(column.type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value)
    if isinstance(column.type, JSON) and isinstance(value, str):
        return json.loads(value)
    return value


def upload_file(client, bucket: str, source: Path, key: str, content_type: str | None) -> str:
    try:
        client.head_object(Bucket=bucket, Key=key)
    except Exception:
        args = {"ContentType": content_type} if content_type else None
        client.upload_file(str(source), bucket, key, ExtraArgs=args)
    return f"s3://{bucket}/{key}"


def migrate_media(source_rows: dict[str, list[dict]], media_root: Path) -> None:
    if not storage.s3_enabled():
        raise RuntimeError("The target must use S3/MinIO storage")
    bucket = storage._s3_bucket()
    if not bucket:
        raise RuntimeError("Missing target MinIO bucket")
    client = storage._s3_client()

    for row in source_rows["audios"]:
        source = media_root / "audios" / Path(row["filename"]).name
        if not source.is_file():
            raise FileNotFoundError(source)
        key = f"audios/imports/sqlite-{row['id']}-{source.name}"
        content_type = mimetypes.guess_type(source.name)[0] or "audio/webm"
        row["filename"] = upload_file(client, bucket, source, key, content_type)

    lesson_content_types = {
        row["id"]: row.get("thumbnail_content_type") for row in source_rows["learning_lessons"]
    }
    for row in source_rows["learning_videos"]:
        old_key = row["storage_key"]
        source = media_root / "learning" / old_key
        if not source.is_file():
            raise FileNotFoundError(source)
        row["storage_key"] = upload_file(
            client, bucket, source, f"learning/{old_key}", row.get("content_type")
        )

    for row in source_rows["learning_lessons"]:
        old_key = row.get("thumbnail_storage_key")
        if not old_key:
            continue
        source = media_root / "learning" / old_key
        if not source.is_file():
            raise FileNotFoundError(source)
        row["thumbnail_storage_key"] = upload_file(
            client,
            bucket,
            source,
            f"learning/{old_key}",
            lesson_content_types[row["id"]],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the complete local SQLite dataset into PostgreSQL/MinIO.")
    parser.add_argument("sqlite_db", type=Path)
    parser.add_argument("media_root", type=Path)
    args = parser.parse_args()

    source = sqlite3.connect(args.sqlite_db)
    source.row_factory = sqlite3.Row
    source_rows = {table: rows(source, table) for table in TABLES}
    source_users = rows(source, "users")
    source.close()

    metadata = MetaData()
    target_tables = {name: Table(name, metadata, autoload_with=engine) for name in ("users", *TABLES)}

    with engine.begin() as target:
        target_users = target.execute(select(target_tables["users"])).mappings().all()
        source_identity = {(row["id"], row["email"]) for row in source_users}
        target_identity = {(row["id"], row["email"]) for row in target_users}
        if source_identity != target_identity:
            raise RuntimeError("Source and target users differ; refusing an unsafe relation remap")
        occupied = {
            name: target.scalar(select(func.count()).select_from(target_tables[name]))
            for name in TABLES
        }
        non_empty = {name: count for name, count in occupied.items() if count}
        if non_empty:
            raise RuntimeError(f"Target content tables are not empty: {non_empty}")

    migrate_media(source_rows, args.media_root)

    with engine.begin() as target:
        for name in TABLES:
            table = target_tables[name]
            prepared = [
                {column.name: convert_value(column, row[column.name]) for column in table.columns if column.name in row}
                for row in source_rows[name]
            ]
            if prepared:
                target.execute(table.insert(), prepared)
            if engine.dialect.name == "postgresql" and "id" in table.c:
                target.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {name}), 1), "
                    f"(SELECT COUNT(*) > 0 FROM {name}))"
                ))

    for name in TABLES:
        print(f"{name}: {len(source_rows[name])}")


if __name__ == "__main__":
    main()
