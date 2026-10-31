from __future__ import annotations

import shutil
import tempfile
import time
from typing import Any, Dict, List

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core import (
    save_and_validate_upload,
    to_wav_if_needed,
    vosk_available,
    vosk_run,
    vosk_run_v2,
    text_metrics,
)

from app.transcribe.calibration import get_estimate, record_observation, wav_duration_seconds
from app.transcribe.service import (
    transcribe_whisper_metrics, _fix_overlaps, _get_default_model_id,
)

router = APIRouter(prefix="/api/transcribe", tags=["transcribe"])



@router.get("/estimate", summary="Server-calibrated processing time estimate")
def transcription_estimate(
    lang: str = Query(..., pattern="^(br|cy)$"),
    mode: str = Query(..., pattern="^(fast|quality)$"),
    duration_seconds: float = Query(..., gt=0, le=86400),
) -> Dict[str, Any]:
    if lang == "cy" and mode == "fast":
        raise HTTPException(status_code=400, detail="Vosk is not available for Welsh")
    return get_estimate(lang, mode, duration_seconds)


# -------------------------------------------------------------------
# New route: metrics + segments (Whisper)
# -------------------------------------------------------------------
@router.post(
    "/transcribe_whisper_bre_metrics",
    summary="Whisper (Breton CT2) — text + segments + metrics",
)
async def transcribe_whisper_bre_metrics(audio_file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload -> Whisper transcription (Breton) + segments + metrics.

    Why this endpoint?
    - It returns segments (useful for subtitles and UX debugging)
    - It returns processing metrics (useful for comparisons)
    """

    payload = await transcribe_whisper_metrics(audio_file, lang="br", tmp_prefix="keltia_whisper_br_")
    return JSONResponse(payload)


@router.post(
    "/transcribe_whisper_wel_metrics",
    summary="Whisper (Welsh CT2) — text + segments + metrics",
)
async def transcribe_whisper_wel_metrics(audio_file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload -> Whisper transcription (Welsh) + segments + metrics.
    """

    payload = await transcribe_whisper_metrics(audio_file, lang="cy", tmp_prefix="keltia_whisper_cy_")
    return JSONResponse(payload)


@router.post(
    "/transcribe_vosk_bre_metrics_v2",
    summary="Vosk (Breton) — RAW by default, optional clean (?clean=true)",
)
async def transcribe_vosk_bre_metrics_v2(
    audio_file: UploadFile = File(...),
    clean: bool = Query(False),
    include_words: bool = Query(True),
) -> Dict[str, Any]:
    if not vosk_available("br"):
        raise HTTPException(
            status_code=503,
            detail="Vosk model not available for 'br'. Check /api/transcription/models/status.",
        )

    tmp_dir = tempfile.mkdtemp(prefix="keltia_vosk_br_v2_")
    try:
        filename, in_path, ext = await save_and_validate_upload(audio_file, tmp_dir)
        wav_path = to_wav_if_needed(in_path, ext)
        audio_duration = wav_duration_seconds(wav_path)

        # ⬇️ IMPORTANT: use a NEW core function that supports raw/clean
        t0 = time.perf_counter()
        v = vosk_run_v2(wav_path, lang="br", clean=clean)
        dt = time.perf_counter() - t0

        text = (v.get("text", "") or "").strip()
        segments = v.get("segments", []) or []
        segments = _fix_overlaps(segments)

        model_id = _get_default_model_id("vosk", "br")

        metrics = text_metrics(text, dt, model="vosk-breton")
        metrics["engine"] = "vosk"
        metrics["lang"] = "br"
        if model_id:
            metrics["model_id"] = model_id
        metrics["calibration"] = record_observation("br", "fast", dt, audio_duration)

        payload = {
            "filename": filename,
            "text": text,
            "segments": segments,
            "metrics": metrics,
            "clean": clean,  # optionnel mais pratique pour debug
        }

        if include_words:
            payload["words"] = v.get("words", []) or []

        return JSONResponse(payload)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# -------------------------------------------------------------------
# New route: metrics + segments (Vosk) — symmetric with Whisper
# -------------------------------------------------------------------
@router.post(
    "/transcribe_vosk_bre_metrics",
    summary="Vosk (Breton) — text + segments + metrics",
)

async def transcribe_vosk_bre_metrics(audio_file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload -> Vosk transcription (Breton) + segments + metrics.

    Symmetric contract with /transcribe_whisper_bre_metrics:
    - filename
    - text
    - segments
    - metrics
    """

    # 1) Check model availability (fast fail)
    if not vosk_available("br"):
        raise HTTPException(
            status_code=503,
            detail="Vosk model not available for 'br'. Check /api/transcription/models/status.",
        )

    tmp_dir = tempfile.mkdtemp(prefix="keltia_vosk_br_")
    try:
        # 2) Save uploaded file to disk with streaming size enforcement.
        filename, in_path, ext = await save_and_validate_upload(audio_file, tmp_dir)

        # 3) Convert to WAV if needed
        wav_path = to_wav_if_needed(in_path, ext)
        audio_duration = wav_duration_seconds(wav_path)

        # 4) Run Vosk + measure processing time
        t0 = time.perf_counter()
        v = vosk_run(wav_path, lang="br")
        dt = time.perf_counter() - t0

        text = (v.get("text", "") or "").strip()
        segments = v.get("segments", []) or []

        # ✅ Optional: avoid overlaps (recommended for subtitles)
        segments = _fix_overlaps(segments)

        # 5) Model id (source of truth = /api/transcription/models/status)
        model_id = _get_default_model_id("vosk", "br")

        metrics = text_metrics(text, dt, model="vosk-breton")
        metrics["engine"] = "vosk"
        metrics["lang"] = "br"
        if model_id:
            metrics["model_id"] = model_id
        metrics["calibration"] = record_observation("br", "fast", dt, audio_duration)

        return JSONResponse(
            {
                "filename": filename,
                "text": text,
                "segments": segments,
                "metrics": metrics,
            }
        )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
