from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4

import boto3
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse


LOCAL_AUDIO_DIR = Path(__file__).resolve().parents[1] / "data" / "audios"
LOCAL_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _s3_endpoint_url() -> str | None:
    return _env("MINIO_ENDPOINT_URL") or _env("S3_ENDPOINT_URL") or _env("AWS_ENDPOINT_URL")


def _s3_bucket() -> str | None:
    return _env("MINIO_BUCKET") or _env("S3_BUCKET_NAME")


def s3_enabled() -> bool:
    explicit = (_env("AUDIO_STORAGE") or "").lower() in {"s3", "minio"}
    configured = bool(_s3_bucket() and _s3_endpoint_url())
    return explicit or configured


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=_s3_endpoint_url(),
        region_name=_env("S3_REGION", "us-east-1"),
        aws_access_key_id=_env("MINIO_ACCESS_KEY") or _env("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=_env("MINIO_SECRET_KEY") or _env("AWS_SECRET_ACCESS_KEY"),
    )


def _safe_ext(filename: str | None) -> str:
    ext = Path(filename or "").suffix.lower()
    return ext if ext in {".webm", ".ogg", ".mp3", ".wav", ".m4a", ".mp4"} else ".webm"


def make_audio_key(phrase_id: int, filename: str | None) -> str:
    ext = _safe_ext(filename)
    return f"audios/raw/phrase-{phrase_id}-{uuid4().hex}{ext}"


def save_audio_file_path(source_path: Path, storage_name: str, content_type: str | None = None) -> str:
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {source_path}")

    ext = _safe_ext(storage_name)
    storage_name = f"{Path(storage_name).stem}{ext}"

    if s3_enabled():
        bucket = _s3_bucket()
        if not bucket:
            raise RuntimeError("S3 bucket is not configured")

        key = f"audios/imports/{storage_name}"
        _s3_client().upload_file(
            str(source_path),
            bucket,
            key,
            ExtraArgs={"ContentType": content_type or "audio/webm"},
        )
        return f"s3://{bucket}/{key}"

    dest = LOCAL_AUDIO_DIR / storage_name
    if source_path.resolve() != dest.resolve():
        shutil.copy2(source_path, dest)
    return str(Path("data") / "audios" / dest.name)


async def save_audio_upload(file: UploadFile, phrase_id: int) -> str:
    key = make_audio_key(phrase_id, file.filename)

    if s3_enabled():
        bucket = _s3_bucket()
        if not bucket:
            raise HTTPException(status_code=500, detail="S3 bucket is not configured")

        await file.seek(0)
        _s3_client().upload_fileobj(
            file.file,
            bucket,
            key,
            ExtraArgs={"ContentType": file.content_type or "audio/webm"},
        )
        return f"s3://{bucket}/{key}"

    dest = LOCAL_AUDIO_DIR / Path(key).name
    dest.write_bytes(await file.read())
    return str(Path("data") / "audios" / dest.name)


def audio_response(storage_ref: str) -> Response:
    if storage_ref.startswith("s3://"):
        _, rest = storage_ref.split("s3://", 1)
        bucket, key = rest.split("/", 1)
        obj = _s3_client().get_object(Bucket=bucket, Key=key)
        return StreamingResponse(
            obj["Body"].iter_chunks(),
            media_type=obj.get("ContentType") or "audio/webm",
            headers={"Content-Disposition": f'inline; filename="{Path(key).name}"'},
        )

    path = Path(storage_ref)
    if not path.is_absolute():
        if path.parts[:2] == ("data", "audios"):
            path = LOCAL_AUDIO_DIR / path.name
        else:
            path = LOCAL_AUDIO_DIR / path

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(path, media_type=audio_media_type(path))


def audio_media_type(path: Path) -> str:
    try:
        header = path.read_bytes()[:16]
    except OSError:
        return "application/octet-stream"

    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio/webm"
    if header.startswith(b"OggS"):
        return "audio/ogg"
    if header.startswith(b"ID3") or header[:2] == b"\xff\xfb":
        return "audio/mpeg"
    if header.startswith(b"RIFF"):
        return "audio/wav"
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return "audio/mp4"
    return "application/octet-stream"


def storage_backend_info() -> dict[str, str | bool | None]:
    return {
        "backend": "s3" if s3_enabled() else "local",
        "bucket": _s3_bucket() if s3_enabled() else None,
        "endpoint": _s3_endpoint_url() if s3_enabled() else None,
        "local_directory": None if s3_enabled() else str(LOCAL_AUDIO_DIR),
    }


def storage_ref_exists(storage_ref: str) -> bool:
    if storage_ref.startswith("s3://"):
        try:
            _, rest = storage_ref.split("s3://", 1)
            bucket, key = rest.split("/", 1)
            _s3_client().head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False

    path = Path(storage_ref)
    if not path.is_absolute():
        path = LOCAL_AUDIO_DIR / path.name
    return path.exists() and path.is_file()


def delete_audio_file(storage_ref: str) -> None:
    if storage_ref.startswith("s3://"):
        _, rest = storage_ref.split("s3://", 1)
        bucket, key = rest.split("/", 1)
        _s3_client().delete_object(Bucket=bucket, Key=key)
        return

    path = Path(storage_ref)
    if not path.is_absolute():
        path = LOCAL_AUDIO_DIR / path.name
    path.unlink(missing_ok=True)
