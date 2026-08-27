from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse

from .. import storage as corpus_storage


LOCAL_LEARNING_DIR = Path(__file__).resolve().parents[2] / "data" / "learning"
LOCAL_LEARNING_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
}
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
DEFAULT_MAX_VIDEO_BYTES = 500 * 1024 * 1024
MAX_THUMBNAIL_BYTES = 8 * 1024 * 1024


def max_video_bytes() -> int:
    try:
        return int(os.getenv("LEARNING_MAX_VIDEO_BYTES", str(DEFAULT_MAX_VIDEO_BYTES)))
    except ValueError:
        return DEFAULT_MAX_VIDEO_BYTES


def _learning_bucket() -> str | None:
    return os.getenv("LEARNING_MINIO_BUCKET") or corpus_storage._s3_bucket()


def _extension_for(file: UploadFile) -> str:
    content_type = (file.content_type or "").lower()
    expected_extension = ALLOWED_VIDEO_TYPES.get(content_type)
    if not expected_extension:
        raise HTTPException(status_code=415, detail="Unsupported video type")

    extension = Path(file.filename or "").suffix.lower()
    if extension != expected_extension:
        raise HTTPException(status_code=415, detail="Unsupported video extension")
    return extension


def _validate_signature(content_type: str, header: bytes) -> None:
    if content_type in {"audio/mpeg", "audio/mp3"} and not (
        header.startswith(b"ID3") or (len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0)
    ):
        raise HTTPException(status_code=415, detail="File content does not match its audio type")
    if content_type == "video/webm" and not header.startswith(b"\x1a\x45\xdf\xa3"):
        raise HTTPException(status_code=415, detail="File content does not match its video type")
    if content_type in {"video/mp4", "video/quicktime"} and (
        len(header) < 12 or header[4:8] != b"ftyp"
    ):
        raise HTTPException(status_code=415, detail="File content does not match its video type")


def _validate_image_signature(content_type: str, header: bytes) -> None:
    valid = (
        (content_type == "image/jpeg" and header.startswith(b"\xff\xd8\xff"))
        or (content_type == "image/png" and header.startswith(b"\x89PNG\r\n\x1a\n"))
        or (content_type == "image/webp" and header.startswith(b"RIFF") and header[8:12] == b"WEBP")
    )
    if not valid:
        raise HTTPException(status_code=415, detail="File content does not match its image type")


async def save_learning_video(file: UploadFile, lesson_id: int) -> dict[str, str | int]:
    extension = _extension_for(file)
    content_type = (file.content_type or "").lower()
    key = f"learning/lessons/{lesson_id}/videos/{uuid4().hex}/source{extension}"
    digest = hashlib.sha256()
    size = 0

    await file.seek(0)
    while chunk := await file.read(1024 * 1024):
        if size == 0:
            _validate_signature(content_type, chunk[:16])
        size += len(chunk)
        if size > max_video_bytes():
            await file.seek(0)
            raise HTTPException(status_code=413, detail="Video file is too large")
        digest.update(chunk)

    if size == 0:
        raise HTTPException(status_code=400, detail="Video file is empty")

    await file.seek(0)
    if corpus_storage.s3_enabled():
        bucket = _learning_bucket()
        if not bucket:
            raise HTTPException(status_code=500, detail="Learning storage bucket is not configured")
        corpus_storage._s3_client().upload_fileobj(
            file.file,
            bucket,
            key,
            ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
        )
        storage_key = f"s3://{bucket}/{key}"
    else:
        destination = LOCAL_LEARNING_DIR / key.removeprefix("learning/")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                output.write(chunk)
        storage_key = str(destination.relative_to(LOCAL_LEARNING_DIR))

    return {
        "storage_key": storage_key,
        "size_bytes": size,
        "checksum_sha256": digest.hexdigest(),
    }


async def save_learning_thumbnail(file: UploadFile, lesson_id: int) -> dict[str, str | int]:
    content_type = (file.content_type or "").lower()
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if not extension or Path(file.filename or "").suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=415, detail="Unsupported thumbnail type")

    key = f"learning/lessons/{lesson_id}/thumbnail/{uuid4().hex}{extension}"
    size = 0
    await file.seek(0)
    while chunk := await file.read(1024 * 1024):
        if size == 0:
            _validate_image_signature(content_type, chunk[:16])
        size += len(chunk)
        if size > MAX_THUMBNAIL_BYTES:
            await file.seek(0)
            raise HTTPException(status_code=413, detail="Thumbnail file is too large")
    if size == 0:
        raise HTTPException(status_code=400, detail="Thumbnail file is empty")

    await file.seek(0)
    if corpus_storage.s3_enabled():
        bucket = _learning_bucket()
        if not bucket:
            raise HTTPException(status_code=500, detail="Learning storage bucket is not configured")
        corpus_storage._s3_client().upload_fileobj(
            file.file,
            bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        storage_key = f"s3://{bucket}/{key}"
    else:
        destination = LOCAL_LEARNING_DIR / key.removeprefix("learning/")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                output.write(chunk)
        storage_key = str(destination.relative_to(LOCAL_LEARNING_DIR))
    return {"storage_key": storage_key, "size_bytes": size}


def learning_video_response(storage_key: str, content_type: str, request: Request | None = None) -> Response:
    if storage_key.startswith("s3://"):
        _, rest = storage_key.split("s3://", 1)
        bucket, key = rest.split("/", 1)
        url = corpus_storage._s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=3600,
        )
        return RedirectResponse(url=url, status_code=307)

    path = (LOCAL_LEARNING_DIR / storage_key).resolve()
    if LOCAL_LEARNING_DIR.resolve() not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Video file not found")
    range_header = request.headers.get("range") if request else None
    if not range_header:
        return FileResponse(path, media_type=content_type, filename=path.name, headers={"Accept-Ranges": "bytes"})

    size = path.stat().st_size
    try:
        unit, value = range_header.split("=", 1)
        if unit.strip().lower() != "bytes" or "," in value:
            raise ValueError
        start_raw, end_raw = value.split("-", 1)
        start = int(start_raw) if start_raw else max(0, size - int(end_raw))
        end = int(end_raw) if end_raw else size - 1
        if start < 0 or start >= size or end < start:
            raise ValueError
        end = min(end, size - 1)
    except (ValueError, TypeError):
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})

    length = end - start + 1
    def chunks():
        with path.open("rb") as source:
            source.seek(start)
            remaining = length
            while remaining:
                chunk = source.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(chunks(), status_code=206, media_type=content_type, headers={
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{size}",
        "Content-Length": str(length),
    })


def learning_thumbnail_response(storage_key: str, content_type: str) -> Response:
    return learning_video_response(storage_key, content_type)


def delete_learning_video(storage_key: str) -> None:
    if storage_key.startswith("s3://"):
        _, rest = storage_key.split("s3://", 1)
        bucket, key = rest.split("/", 1)
        corpus_storage._s3_client().delete_object(Bucket=bucket, Key=key)
        return

    path = (LOCAL_LEARNING_DIR / storage_key).resolve()
    if LOCAL_LEARNING_DIR.resolve() in path.parents:
        path.unlink(missing_ok=True)


def delete_learning_thumbnail(storage_key: str) -> None:
    delete_learning_video(storage_key)
