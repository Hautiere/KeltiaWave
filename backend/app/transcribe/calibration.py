"""Persistent, server-specific transcription speed calibration."""

from __future__ import annotations

import json
import os
import threading
import wave
from pathlib import Path
from typing import Any


CALIBRATION_FILE = Path(
    os.getenv(
        "TRANSCRIPTION_CALIBRATION_FILE",
        str(Path(__file__).resolve().parents[2] / "data" / "transcription-calibration.json"),
    )
)
_LOCK = threading.Lock()


def _profile_key(language: str, mode: str) -> str:
    engine = "vosk" if mode == "fast" else "whisper"
    return f"{engine}:{language}"


def _default_rtf(language: str, mode: str) -> float:
    engine = "VOSK" if mode == "fast" else "WHISPER"
    name = f"TRANSCRIPTION_DEFAULT_RTF_{engine}_{language.upper()}"
    fallback = 0.45 if mode == "fast" else 1.25
    try:
        return max(0.05, min(10.0, float(os.getenv(name, str(fallback)))))
    except ValueError:
        return fallback


def _read_profiles() -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
        profiles = payload.get("profiles", {})
        return profiles if isinstance(profiles, dict) else {}
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return {}


def _write_profiles(profiles: dict[str, dict[str, Any]]) -> None:
    CALIBRATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CALIBRATION_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps({"version": 1, "profiles": profiles}, indent=2), encoding="utf-8")
    temporary.replace(CALIBRATION_FILE)


def get_estimate(language: str, mode: str, duration_seconds: float) -> dict[str, Any]:
    key = _profile_key(language, mode)
    with _LOCK:
        profile = _read_profiles().get(key)
    calibrated = bool(profile and float(profile.get("rtf", 0) or 0) > 0)
    rtf = float(profile["rtf"]) if calibrated else _default_rtf(language, mode)
    estimate = max(2.0, duration_seconds * rtf)
    return {
        "language": language,
        "mode": mode,
        "engine": "vosk" if mode == "fast" else "whisper",
        "duration_seconds": round(duration_seconds, 2),
        "estimated_seconds": round(estimate, 2),
        "real_time_factor": round(rtf, 4),
        "sample_count": int(profile.get("sample_count", 0)) if profile else 0,
        "source": "server-calibration" if calibrated else "server-default",
    }


def record_observation(language: str, mode: str, processing_seconds: float, duration_seconds: float) -> dict[str, Any] | None:
    if duration_seconds < 1 or processing_seconds <= 0:
        return None
    observed = max(0.05, min(10.0, processing_seconds / duration_seconds))
    key = _profile_key(language, mode)
    with _LOCK:
        profiles = _read_profiles()
        previous = profiles.get(key, {})
        count = int(previous.get("sample_count", 0) or 0)
        previous_rtf = float(previous.get("rtf", 0) or 0)
        # The first real measurement replaces the generic default. Later jobs
        # adapt progressively to server load without making the ETA unstable.
        rtf = observed if count == 0 or previous_rtf <= 0 else previous_rtf * 0.7 + observed * 0.3
        profiles[key] = {
            "rtf": round(rtf, 6),
            "sample_count": count + 1,
            "last_observed_rtf": round(observed, 6),
        }
        _write_profiles(profiles)
    return get_estimate(language, mode, duration_seconds)


def wav_duration_seconds(path: str) -> float:
    try:
        with wave.open(path, "rb") as audio:
            rate = audio.getframerate()
            return audio.getnframes() / rate if rate else 0.0
    except (OSError, EOFError, wave.Error):
        return 0.0
