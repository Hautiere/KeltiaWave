"""Local rhythm extraction with an optional Hugging Face prosody model."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core import save_and_validate_upload
from app.transcribe.rhythm_analysis import RhythmError, analyze_wav, compare_rhythm
from app.transcribe.hf_prosody import compare_hf_prosody


router = APIRouter(prefix="/api/transcribe", tags=["transcribe"])


def _analyze_uploaded(path: str, output: str) -> dict:
    try:
        subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-t", "31", output],
            check=True, capture_output=True, timeout=35,
        )
        return analyze_wav(output)
    except subprocess.TimeoutExpired as exc:
        raise RhythmError("Audio decoding timed out") from exc
    except subprocess.CalledProcessError as exc:
        raise RhythmError("Audio could not be decoded") from exc


@router.post("/rhythm", summary="Measure timing, pauses and relative intensity of an audio clip")
async def analyze_rhythm(
    audio_file: UploadFile = File(...),
    reference_file: UploadFile | None = File(None),
) -> dict:
    """Optional reference adds timing comparison and a local HF similarity when available."""
    folder = Path(tempfile.mkdtemp(prefix="keltia_rhythm_"))
    try:
        learner_dir = folder / "learner"
        learner_dir.mkdir()
        _, learner_path, _ = await save_and_validate_upload(audio_file, str(learner_dir))
        learner = await run_in_threadpool(_analyze_uploaded, learner_path, str(folder / "learner.wav"))
        result = {"audio": learner, "method": "normalized-energy-activity-v1", "pitch_used": False}
        if reference_file is not None:
            reference_dir = folder / "reference"
            reference_dir.mkdir()
            _, reference_path, _ = await save_and_validate_upload(reference_file, str(reference_dir))
            reference = await run_in_threadpool(_analyze_uploaded, reference_path, str(folder / "reference.wav"))
            result["reference"] = reference
            result["comparison"] = compare_rhythm(reference, learner)
            try:
                result["hf_prosody"] = await run_in_threadpool(
                    compare_hf_prosody,
                    str(folder / "reference.wav"),
                    str(folder / "learner.wav"),
                )
            except (ImportError, OSError, RuntimeError, ValueError):
                result["hf_prosody"] = None
                result["hf_prosody_status"] = "unavailable"
        return result
    except RhythmError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        shutil.rmtree(folder, ignore_errors=True)
