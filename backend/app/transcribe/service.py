from __future__ import annotations

import asyncio
import shutil
import tempfile
import time
from typing import Any, Dict, List

from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core import save_and_validate_upload, to_wav_if_needed, whisper_available, whisper_run, text_metrics
from app.api.routes.transcription_models import TRANSCRIPTION_MODELS_STATUS
from app.transcribe.calibration import record_observation, wav_duration_seconds

# Shared by Record, Transcribe and Subtitles within this server process.
_whisper_slot = asyncio.Semaphore(1)

def _normalize_whisper_segments(raw_segments: Any) -> List[Dict[str, Any]]:
    """
    Normalize Whisper segments so the frontend/subtitles can rely on:
    - id: int
    - start/end: float
    - text: non-empty string
    - end > start
    """
    out: List[Dict[str, Any]] = []

    for i, s in enumerate(raw_segments or []):
        if isinstance(s, dict):
            start = float(s.get("start", 0.0) or 0.0)
            end = float(s.get("end", 0.0) or 0.0)
            text = (s.get("text", "") or "").strip()
        else:
            # some libraries return objects instead of dicts
            start = float(getattr(s, "start", 0.0) or 0.0)
            end = float(getattr(s, "end", 0.0) or 0.0)
            text = (getattr(s, "text", "") or "").strip()

        if not text:
            continue
        if end <= start:
            # ignore broken timestamps
            continue

        out.append({"id": i, "start": start, "end": end, "text": text})

    return out


def _fix_overlaps(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Optional: ensure a monotonic timeline (no overlaps, no going backwards).
    This is helpful for SRT/VTT generation and simpler frontend rendering.
    """
    if not segments:
        return segments

    fixed: List[Dict[str, Any]] = []
    prev_end = 0.0

    for s in segments:
        start = max(float(s["start"]), prev_end)
        end = float(s["end"])

        if end <= start:
            continue

        s2 = dict(s)
        s2["start"] = start
        s2["end"] = end

        fixed.append(s2)
        prev_end = end

    return fixed


def _get_default_model_id(engine: str, lang: str) -> str | None:
    """
    Read model id from the 'models/status' structure (single source of truth).
    """
    return (
        TRANSCRIPTION_MODELS_STATUS.get("engines", {})
        .get(engine, {})
        .get("languages", {})
        .get(lang, {})
        .get("default_model_id")
    )


async def transcribe_whisper_metrics(audio_file: UploadFile, *, lang: str, tmp_prefix: str) -> Dict[str, Any]:
    if not whisper_available(lang):
        raise HTTPException(
            status_code=503,
            detail=f"Whisper model not available for '{lang}'. Install the local model or disable this language in the frontend.",
        )

    tmp_dir = tempfile.mkdtemp(prefix=tmp_prefix)
    try:
        filename, in_path, ext = await save_and_validate_upload(audio_file, tmp_dir)
        async with _whisper_slot:
            wav_path = await run_in_threadpool(to_wav_if_needed, in_path, ext)
            audio_duration = await run_in_threadpool(wav_duration_seconds, wav_path)

            t0 = time.perf_counter()
            w = await run_in_threadpool(whisper_run, wav_path, lang=lang)
            dt = time.perf_counter() - t0

        text = (w.get("text", "") or "").strip()
        segments = _normalize_whisper_segments(w.get("segments", []) or [])
        segments = _fix_overlaps(segments)

        model_id = _get_default_model_id("whisper", lang)

        metrics = text_metrics(text, dt, model=f"whisper-{lang}-ct2")
        metrics["engine"] = "whisper"
        metrics["lang"] = lang
        if model_id:
            metrics["model_id"] = model_id
        metrics["calibration"] = record_observation(lang, "quality", dt, audio_duration)

        return {
            "filename": filename,
            "text": text,
            "segments": segments,
            "metrics": metrics,
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
