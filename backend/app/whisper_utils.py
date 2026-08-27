# backend/app/whisper_utils.py
from __future__ import annotations

import os
import time
import json
import math
import tempfile
import subprocess
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("whisper")

# Racine des modèles whisper offline (dans backend/app/models)

MODELS_ROOT = Path(os.getenv("MODELS_ROOT", str(Path(__file__).resolve().parent / "models")))
MODEL_DIRS: Dict[str, Path] = {
    "br": MODELS_ROOT / "whisper-breton-ct2",
    "cy": MODELS_ROOT / "whisper-welsh-ct2",
}

_MODEL_CACHE: Dict[str, "WhisperModel"] = {}
_MODEL_NAME: Dict[str, str] = {}  # pour metrics/log

_BRETON_TRAILING_HALLUCINATION_RE = re.compile(
    r"\s*Pelec['’]h\s+emañ\s+ar\s+c['’]huzul-se\s*\?"
    r"\s*Pelec['’]h\s+emañ\s+ar\s+c['’]hêri-se\s*\?\s*$",
    re.IGNORECASE,
)

_ALLOWED_NAMES = {
    "tiny.en","tiny","base.en","base","small.en","small","medium.en","medium",
    "large-v1","large-v2","large-v3","large",
    "distil-large-v2","distil-medium.en","distil-small.en",
    "distil-large-v3","distil-large-v3.5","large-v3-turbo","turbo",
}

def whisper_is_available(lang: str = "br") -> bool:
    model_dir = MODEL_DIRS.get(lang)
    return bool(model_dir and model_dir.exists())

def _get_model_dir(lang: str) -> Path:
    model_dir = MODEL_DIRS.get(lang)
    if not model_dir:
        raise ValueError(f"Langue whisper non supportée: {lang} (MODEL_DIRS)")
    if not model_dir.exists():
        raise FileNotFoundError(f"Modèle whisper local introuvable: {model_dir}")
    return model_dir

def _load_model(lang: str, device: str = "cpu", compute_type: str = "int8"):
    if lang in _MODEL_CACHE:
        return _MODEL_CACHE[lang]

    from faster_whisper import WhisperModel  # import tardif

    # 1) priorité à WHISPER_MODEL si fourni
    forced = os.getenv("WHISPER_MODEL", "").strip()

    model_ref: str
    if forced:
        if Path(forced).exists():
            model_ref = forced  # chemin local
        elif forced in _ALLOWED_NAMES:
            model_ref = forced  # nom officiel
        else:
            raise ValueError(
                f"WHISPER_MODEL='{forced}' invalide (ni dossier existant, ni nom officiel)."
            )
    else:
        model_ref = str(_get_model_dir(lang))  # fallback local par langue

    t0 = time.time()
    model = WhisperModel(model_ref, device=device, compute_type=compute_type)
    _MODEL_CACHE[lang] = model
    _MODEL_NAME[lang] = Path(model_ref).name if Path(model_ref).exists() else model_ref

    log.info("WHISPER loaded lang=%s model_ref=%s device=%s compute=%s in %.2fs",
             lang, model_ref, device, compute_type, time.time() - t0)
    return model

def _ffprobe_duration(path: str) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path]
    out = subprocess.check_output(cmd).decode("utf-8", errors="replace")
    return float(json.loads(out)["format"]["duration"])

def _extract_wav_segment(src_wav: str, start_s: float, dur_s: float, dst_wav: str) -> None:
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_s:.3f}", "-t", f"{dur_s:.3f}",
        "-i", src_wav,
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        dst_wav
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _strip_known_trailing_hallucination(
    segments: List[Dict[str, Any]],
    lang: str,
) -> List[Dict[str, Any]]:
    """Remove a known Breton model hallucination only when it is the final suffix."""
    if lang != "br" or not segments:
        return segments

    full_text = " ".join((segment.get("text", "") or "").strip() for segment in segments).strip()
    match = _BRETON_TRAILING_HALLUCINATION_RE.search(full_text)
    if not match:
        return segments

    keep_until = match.start()
    filtered: List[Dict[str, Any]] = []
    cursor = 0

    for segment in segments:
        text = (segment.get("text", "") or "").strip()
        segment_start = cursor
        segment_end = segment_start + len(text)

        if segment_start >= keep_until:
            break

        kept_text = text
        if segment_end > keep_until:
            kept_text = text[: max(0, keep_until - segment_start)].rstrip()

        if kept_text:
            kept_segment = dict(segment)
            kept_segment["text"] = kept_text
            if kept_segment.get("words"):
                kept_word_count = len(kept_text.split())
                kept_segment["words"] = kept_segment["words"][:kept_word_count]
            filtered.append(kept_segment)

        cursor = segment_end + 1

    for index, segment in enumerate(filtered):
        segment["id"] = index

    log.info("WHISPER removed known trailing Breton hallucination")
    return filtered

def whisper_transcribe(
    _wav_path: str,
    lang: str = "br",
    _lang: Optional[str] = None,   # compat main.py 
    *,
    device: str = "cpu",
    compute_type: str = "int8",
    vad_filter: Optional[bool] = None,
    beam_size: Optional[int] = None,
) -> Dict[str, Any]:
    # compat: main.py appelle parfois whisper_transcribe(wav, lang="br") ou _lang=
    if _lang:
        lang = _lang

    device = os.getenv("WHISPER_DEVICE", device)
    compute_type = os.getenv("WHISPER_COMPUTE", compute_type)

    if vad_filter is None:
        vad_filter = os.getenv("WHISPER_VAD", "1").strip() in ("1", "true", "yes", "on")
    if beam_size is None:
        beam_size = int(os.getenv("WHISPER_BEAM", "5"))
    word_timestamps = os.getenv("WHISPER_WORD_TIMESTAMPS", "1").strip() in ("1", "true", "yes", "on")
    hallucination_silence_threshold = float(os.getenv("WHISPER_HALLUCINATION_SILENCE_S", "2.0"))
    vad_min_silence_ms = int(os.getenv("WHISPER_VAD_MIN_SILENCE_MS", "500"))

    # chunking optionnel (pour corriger "début+fin")
    chunk_len = float(os.getenv("WHISPER_CHUNK_LEN_S", "0"))  # 0 => pas de chunking
    overlap = float(os.getenv("WHISPER_CHUNK_OVERLAP_S", "5"))

    # langue réellement passée à whisper
    # pour ton modèle breton CT2 : on garde "br" par défaut
    forced_lang = os.getenv("WHISPER_LANG", "").strip() or lang
    whisper_language = None if forced_lang == "auto" else forced_lang

    model = _load_model(lang, device=device, compute_type=compute_type)

    t0 = time.time()

    segments_out: List[Dict[str, Any]] = []
    seg_id = 0

    def run_one(wav_path: str, offset: float = 0.0):
        nonlocal seg_id
        transcribe_kwargs = {
            "language": whisper_language,
            "vad_filter": vad_filter,
            "vad_parameters": {"min_silence_duration_ms": vad_min_silence_ms},
            "beam_size": beam_size,
            "condition_on_previous_text": False,
            "without_timestamps": False,
            "temperature": 0.0,
            "hallucination_silence_threshold": hallucination_silence_threshold,
        }
        if word_timestamps:
            transcribe_kwargs["word_timestamps"] = True

        try:
            seg_iter, info = model.transcribe(wav_path, **transcribe_kwargs)
        except TypeError:
            transcribe_kwargs.pop("word_timestamps", None)
            transcribe_kwargs.pop("hallucination_silence_threshold", None)
            seg_iter, info = model.transcribe(wav_path, **transcribe_kwargs)

        for s in seg_iter:
            t = (s.text or "").strip()
            st = float(s.start) + offset
            en = float(s.end) + offset
            if t:
                words_out = []
                for word in (getattr(s, "words", None) or []):
                    w_text = (getattr(word, "word", "") or "").strip()
                    w_start = getattr(word, "start", None)
                    w_end = getattr(word, "end", None)
                    if w_text and w_start is not None and w_end is not None:
                        words_out.append({
                            "word": w_text,
                            "start": float(w_start) + offset,
                            "end": float(w_end) + offset,
                        })

                if words_out:
                    st = max(0.0, min(w["start"] for w in words_out))
                    en = max(w["end"] for w in words_out)

                segment = {"id": seg_id, "start": st, "end": en, "text": t}
                if words_out:
                    segment["words"] = words_out
                segments_out.append(segment)
                seg_id += 1
        return info

    info = None
    if chunk_len and chunk_len > 1.0:
        duration = _ffprobe_duration(_wav_path)
        step = max(5.0, chunk_len - overlap)
        n = int(math.ceil(duration / step))

        with tempfile.TemporaryDirectory() as td:
            for i in range(n):
                start_s = i * step
                if start_s >= duration:
                    break
                dur_s = min(chunk_len, duration - start_s)
                chunk_wav = os.path.join(td, f"chunk_{i:03d}.wav")
                _extract_wav_segment(_wav_path, start_s, dur_s, chunk_wav)
                info = run_one(chunk_wav, offset=start_s)
                log.info("WHISPER chunk=%s start=%.2fs dur=%.2fs", i, start_s, dur_s)
    else:
        info = run_one(_wav_path, offset=0.0)

    segments_out = _strip_known_trailing_hallucination(segments_out, lang)
    full_text = " ".join((segment.get("text", "") or "").strip() for segment in segments_out).strip()
    dt = time.time() - t0

    end_vals = [s["end"] for s in segments_out]
    metrics = {
        "engine": "whisper",
        "model": _MODEL_NAME.get(lang),
        "language": forced_lang,
        "vad_filter": vad_filter,
        "beam_size": beam_size,
        "word_timestamps": word_timestamps,
        "hallucination_silence_threshold": hallucination_silence_threshold,
        "vad_min_silence_ms": vad_min_silence_ms,
        "processing_time_s": round(dt, 2),
        "segments": len(segments_out),
        "text_len": len(full_text),
        "end_max": max(end_vals) if end_vals else None,
        "detected_language": getattr(info, "language", None) if info else None,
        "language_probability": getattr(info, "language_probability", None) if info else None,
        "duration": getattr(info, "duration", None) if info else None,
    }

    return {"text": full_text, "segments": segments_out, "metrics": metrics}
