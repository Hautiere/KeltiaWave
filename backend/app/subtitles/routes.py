from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.transcribe.routes import (
    _transcribe_whisper_metrics,
    transcribe_vosk_bre_metrics_v2,
)

router = APIRouter(prefix="/api/subtitles", tags=["subtitles"])


@router.post("/transcribe", summary="Transcribe media for the Subtitles application")
async def transcribe_for_subtitles(
    audio_file: UploadFile = File(...),
    language: Literal["br", "cy"] = "br",
    engine: Literal["vosk", "whisper"] = "whisper",
) -> Any:
    """Return timestamped segments through a stable, Subtitles-specific API."""
    if language == "cy" and engine == "vosk":
        raise HTTPException(status_code=400, detail="Vosk is not available for Welsh subtitles.")

    if engine == "whisper":
        return await _transcribe_whisper_metrics(
            audio_file,
            lang=language,
            tmp_prefix=f"keltia_subtitles_{language}_",
        )

    return await transcribe_vosk_bre_metrics_v2(
        audio_file=audio_file,
        clean=False,
        include_words=True,
    )
