# app/core.py
import os
import json
from typing import Any, Dict

from fastapi import UploadFile, HTTPException
from pydantic import BaseModel

from app.vosk_utils import (
    convert_to_wav,
    transcrire_audio as vosk_transcribe_audio,
    nettoyer_transcription as vosk_clean_transcription,
)
from app.whisper_utils import whisper_transcribe, whisper_is_available

# Supprime cette ligne :
# from app.api.router import api_router
# from app.api.routes.subtitle_prep import router as subtitle_prep_router
# api_router.include_router(subtitle_prep_router, tags=["subtitles"])

# ----------------------------
# Config
# ----------------------------
CONFIG_PATH = os.getenv("APP_CONFIG_PATH", "app/config.json")
DEFAULT_CONFIG: Dict[str, Any] = {
    "max_file_size_mb": int(os.getenv("MAX_FILE_SIZE_MB", "75")),
    "admin_token": os.getenv("ADMIN_TOKEN", ""),
}


def get_config() -> Dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    except FileNotFoundError:
        pass

    if os.getenv("ADMIN_TOKEN") is not None:
        config["admin_token"] = os.getenv("ADMIN_TOKEN", "")
    if os.getenv("MAX_FILE_SIZE_MB") is not None:
        config["max_file_size_mb"] = int(os.getenv("MAX_FILE_SIZE_MB", "75"))

    return config


class ConfigUpdate(BaseModel):
    max_file_size_mb: int | None = None
    admin_token: str | None = None


# ----------------------------
# Shared constants
# ----------------------------
ALLOWED_EXT = {".wav", ".mp3", ".ogg", ".webm", ".flac", ".m4a", ".mp4"}


# ----------------------------
# Helpers (metrics / IO)
# ----------------------------
def human_duration(seconds: float) -> str:
    s = int(round(seconds))
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h} h {m} min {s} s"
    if m > 0:
        return f"{m} min {s} s"
    return f"{s} s"


def text_metrics(text: str, seconds: float, model: str) -> Dict[str, Any]:
    text = text or ""
    words = len(text.split())
    chars = len(text)
    speed_wps = (words / seconds) if seconds and seconds > 0 else None

    return {
        "processing_time": {"seconds": round(seconds, 2), "human": human_duration(seconds)},
        "words": words,
        "chars": chars,
        "speed_wps": round(speed_wps, 2) if speed_wps is not None else None,
        "model": model,
    }


def _upload_max_bytes() -> tuple[int, int]:
    config = get_config()
    max_mb = int(config["max_file_size_mb"])
    return max_mb, max_mb * 1024 * 1024


def _validate_upload_name(filename: str) -> tuple[str, str]:
    safe_filename = os.path.basename(filename or "audio")
    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=415, detail=f"Unsupported format '{ext}'")
    return safe_filename, ext


async def read_and_validate_upload(audio_file: UploadFile) -> tuple[str, bytes]:
    filename = audio_file.filename or "audio"
    filename, _ext = _validate_upload_name(filename)

    contents = await audio_file.read()

    max_mb, max_bytes = _upload_max_bytes()
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (> {max_mb} MB allowed)",
        )

    return filename, contents


async def save_and_validate_upload(audio_file: UploadFile, tmp_dir: str) -> tuple[str, str, str]:
    """
    Stream the upload to disk while enforcing MAX_FILE_SIZE_MB.
    This avoids loading oversized public uploads fully into memory.
    """
    filename = audio_file.filename or "audio"
    filename, ext = _validate_upload_name(filename)
    max_mb, max_bytes = _upload_max_bytes()

    in_path = os.path.join(tmp_dir, filename)
    total = 0
    chunk_size = 1024 * 1024

    try:
        with open(in_path, "wb") as f:
            while True:
                chunk = await audio_file.read(chunk_size)
                if not chunk:
                    break

                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large (> {max_mb} MB allowed)",
                    )

                f.write(chunk)
    except HTTPException:
        try:
            os.remove(in_path)
        except OSError:
            pass
        raise

    return filename, in_path, ext


def to_wav_if_needed(in_path: str, ext: str) -> str:
    return in_path if ext == ".wav" else convert_to_wav(in_path)


# ----------------------------
# Whisper compatibility wrappers (NO REGRESSION)
# ----------------------------
def whisper_available(lang: str = "br") -> bool:
    """
    Compatibility with:
    - whisper_is_available()
    - whisper_is_available(lang="br")
    """
    try:
        return bool(whisper_is_available(lang))  # type: ignore[arg-type]
    except TypeError:
        return bool(whisper_is_available())  # type: ignore[call-arg]


def whisper_run(wav_path: str, lang: str = "br") -> Dict[str, Any]:
    """
    Compatibility with:
    - whisper_transcribe(path, _lang="br")
    - whisper_transcribe(path, lang="br")
    """
    try:
        return whisper_transcribe(wav_path, lang=lang)  # type: ignore[call-arg]
    except TypeError:
        return whisper_transcribe(wav_path, _lang=lang)  # type: ignore[call-arg]


# ----------------------------
# Vosk compatibility wrappers (symmetric with Whisper)
# ----------------------------
def vosk_available(lang: str = "br") -> bool:
    """
    Check Vosk availability using the declarative models registry
    (single source of truth).
    """
    try:
        from app.api.routes.transcription_models import TRANSCRIPTION_MODELS_STATUS
    except Exception:
        return False

    return bool(
        TRANSCRIPTION_MODELS_STATUS.get("engines", {})
        .get("vosk", {})
        .get("languages", {})
        .get(lang, {})
        .get("available", False)
    )

def _normalize_vosk_segments(segments: Any) -> list[dict[str, Any]]:
    """Ensure consistent segment dicts: id/start/end/text."""
    out: list[dict[str, Any]] = []
    for i, s in enumerate(segments or []):
        if not isinstance(s, dict):
            continue
        start = float(s.get("start", 0.0) or 0.0)
        end = float(s.get("end", 0.0) or 0.0)
        text = (s.get("text", "") or "").strip()
        if not text or end <= start:
            continue
        out.append({"id": i, "start": start, "end": end, "text": text})
    return out


def _segments_from_words(words: Any, max_words: int = 12) -> list[dict[str, Any]]:
    """
    Build simple RAW segments from word-level timestamps.
    This avoids calling the 'clean' function while still providing subtitles-compatible segments.
    """
    if not words:
        return []

    segs: list[dict[str, Any]] = []
    buf: list[str] = []
    seg_start: float | None = None
    seg_end: float | None = None
    seg_id = 0

    for w in words:
        if not isinstance(w, dict):
            continue

        token = (w.get("word") or w.get("text") or "").strip()
        if not token:
            continue

        start = float(w.get("start", 0.0) or 0.0)
        end = float(w.get("end", 0.0) or 0.0)

        if seg_start is None:
            seg_start = start
        seg_end = max(seg_end or end, end)

        buf.append(token)

        # flush segment
        if len(buf) >= max_words:
            text = " ".join(buf).strip()
            if text and seg_start is not None and seg_end is not None and seg_end > seg_start:
                segs.append({"id": seg_id, "start": seg_start, "end": seg_end, "text": text})
                seg_id += 1
            buf = []
            seg_start = None
            seg_end = None

    # flush remainder
    if buf and seg_start is not None and seg_end is not None and seg_end > seg_start:
        text = " ".join(buf).strip()
        if text:
            segs.append({"id": seg_id, "start": seg_start, "end": seg_end, "text": text})

    return segs


def vosk_run(wav_path: str, lang: str = "br") -> Dict[str, Any]:
    """
    Backward-compatible behavior (NO REGRESSION):
    - returns CLEAN text by default (as before)
    - returns segments from the cleaner
    """
    if lang != "br":
        raise ValueError("Vosk is currently wired only for lang='br' (hardcoded model path in vosk_utils.py).")

    raw_text, words = vosk_transcribe_audio(wav_path)

    # Existing behavior: use cleaner by default
    clean_text, segments = vosk_clean_transcription(words)
    normalized_segments = _normalize_vosk_segments(segments)

    return {
        "raw_text": (raw_text or "").strip(),
        "text": ((clean_text or raw_text) or "").strip(),
        "segments": normalized_segments,
        "words": words or [],
    }

def vosk_run_v2(wav_path: str, lang: str = "br", clean: bool = False) -> Dict[str, Any]:
    """
    V2: raw by default (clean=False). If clean=True, apply nettoyer_transcription.
    Returns the same output contract as vosk_run for the frontend.
    """
    if lang != "br":
        raise ValueError("Vosk is currently wired only for lang='br' (hardcoded model path in vosk_utils.py).")

    raw_text, words = vosk_transcribe_audio(wav_path)

    # Default: RAW (no cleaning) — but still provide segments for subtitles/UX.
    if not clean:
        text = (raw_text or "").strip()
        # Build simple segments from word timestamps (no cleaner involved)
        segments = _segments_from_words(words, max_words=12)
        normalized_segments = _normalize_vosk_segments(segments)

        return {
            "raw_text": (raw_text or "").strip(),
            "text": text,
            "segments": normalized_segments,
            "words": words or [],
        }

    # Clean mode: use cleaner
    clean_text, segments = vosk_clean_transcription(words)
    normalized_segments = _normalize_vosk_segments(segments)

    return {
        "raw_text": (raw_text or "").strip(),
        "text": ((clean_text or raw_text) or "").strip(),
        "segments": normalized_segments,
        "words": words or [],
    }
