"""Short-utterance timing and intensity analysis, independent of voice pitch."""

from __future__ import annotations

import math
import struct
import wave


FRAME_SECONDS = 0.02
SAMPLE_RATE = 16000
MAX_SECONDS = 30


class RhythmError(ValueError):
    pass


def _resample(values: list[float], count: int) -> list[float]:
    result = []
    for index in range(count):
        start = index * len(values) / count
        end = (index + 1) * len(values) / count
        weighted = 0.0
        for position in range(int(start), math.ceil(end)):
            overlap = max(0.0, min(end, position + 1) - max(start, position))
            weighted += values[min(position, len(values) - 1)] * overlap
        result.append(weighted / (end - start))
    return result


def analyze_wav(path: str) -> dict:
    with wave.open(path, "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getframerate() != SAMPLE_RATE:
            raise RhythmError("Expected 16 kHz mono PCM WAV")
        frames = audio.getnframes()
        if frames / SAMPLE_RATE > MAX_SECONDS:
            raise RhythmError("Audio must be 30 seconds or shorter")
        raw = audio.readframes(frames)
    frame_size = int(SAMPLE_RATE * FRAME_SECONDS)
    samples = struct.iter_unpack("<h", raw)
    rms = []
    power = 0
    size = 0
    for (sample,) in samples:
        power += sample * sample
        size += 1
        if size == frame_size:
            rms.append(math.sqrt(power / size) / 32768)
            power = size = 0
    if size:
        rms.append(math.sqrt(power / size) / 32768)
    peak = max(rms, default=0.0)
    if peak < 0.005:
        raise RhythmError("No audible speech detected")
    threshold = max(0.005, peak * 0.12)
    active = [value > threshold for value in rms]
    first = next((i for i, is_active in enumerate(active) if is_active), None)
    if first is None:
        raise RhythmError("No audible speech detected")
    last = len(active) - 1 - next(i for i, is_active in enumerate(reversed(active)) if is_active)
    if last - first < 9:
        raise RhythmError("Speech is too short to assess rhythm")

    speech = rms[first:last + 1]
    activity = active[first:last + 1]
    envelope = [math.log1p(20 * value / peak) / math.log1p(20) for value in speech]
    contour = _resample(envelope, 64)
    activity_contour = _resample([float(value) for value in activity], 32)
    pauses = []
    pause_start = None
    for index, is_active in enumerate(activity + [True]):
        if not is_active and pause_start is None:
            pause_start = index
        elif is_active and pause_start is not None:
            if index - pause_start >= 6:
                pauses.append({
                    "start_s": round((first + pause_start) * FRAME_SECONDS, 2),
                    "end_s": round((first + index) * FRAME_SECONDS, 2),
                    "duration_s": round((index - pause_start) * FRAME_SECONDS, 2),
                })
            pause_start = None
    # Local energy maxima are prominence cues, not identified stressed syllables.
    prominence = []
    smoothed = [sum(envelope[max(0, i - 2):i + 3]) / len(envelope[max(0, i - 2):i + 3]) for i in range(len(envelope))]
    for index in range(3, len(smoothed) - 3):
        if smoothed[index] >= 0.45 and smoothed[index] > smoothed[index - 3] + 0.08 and smoothed[index] >= smoothed[index + 3] + 0.08:
            if not prominence or index - prominence[-1][0] >= 7:
                prominence.append((index, smoothed[index]))
    duration = len(speech) * FRAME_SECONDS
    return {
        "duration_s": round(frames / SAMPLE_RATE, 2),
        "speech_start_s": round(first * FRAME_SECONDS, 2),
        "speech_end_s": round((last + 1) * FRAME_SECONDS, 2),
        "speech_duration_s": round(duration, 2),
        "speech_ratio": round(sum(activity) / len(activity), 3),
        "pauses": pauses,
        "energy_contour": [round(value, 3) for value in contour],
        "activity_contour": [round(value, 3) for value in activity_contour],
        "prominence_peaks": [
            {"time_s": round((first + index) * FRAME_SECONDS, 2), "relative_energy": round(value, 3)}
            for index, value in prominence
        ],
    }


def _dtw_similarity(left: list[float], right: list[float]) -> float:
    length = len(left)
    previous = [math.inf] * (length + 1)
    previous[0] = 0
    for i in range(1, length + 1):
        current = [math.inf] * (length + 1)
        for j in range(max(1, i - 8), min(length, i + 8) + 1):
            current[j] = abs(left[i - 1] - right[j - 1]) + min(previous[j - 1], previous[j], current[j - 1])
        previous = current
    return max(0.0, min(1.0, 1 - previous[length] / (length * 0.45)))


def compare_rhythm(reference: dict, learner: dict) -> dict:
    pace = math.exp(-abs(math.log(reference["speech_duration_s"] / learner["speech_duration_s"])) / 0.8)
    envelope = _dtw_similarity(reference["energy_contour"], learner["energy_contour"])
    activity = 1 - sum(abs(a - b) for a, b in zip(reference["activity_contour"], learner["activity_contour"])) / 32
    # Both contours have already been normalized by their own audio peak.
    emphasis = 1 - sum(abs(a - b) for a, b in zip(reference["energy_contour"], learner["energy_contour"])) / 64
    score = 0.45 * envelope + 0.30 * max(0, activity) + 0.25 * pace
    return {
        "rhythm_score": round(100 * max(0, min(1, score))),
        "pace_score": round(100 * pace),
        "pause_score": round(100 * max(0, activity)),
        "emphasis_score": round(100 * max(0, emphasis)),
        "method": "normalized-energy-activity-dtw-v1",
        "pitch_used": False,
        "calibrated_pronunciation_grade": False,
    }
