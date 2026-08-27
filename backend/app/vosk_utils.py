import os
import wave
import json
import re
import subprocess
from vosk import Model, KaldiRecognizer

MODELS_ROOT = os.getenv("MODELS_ROOT", os.path.join(os.path.dirname(__file__), "models"))
MODEL_PATH = os.getenv("VOSK_MODEL_PATH", os.path.join(MODELS_ROOT, "vosk-model-br-25.02"))
_vosk_model = None


def get_vosk_model():
    global _vosk_model
    if _vosk_model is None:
        if not os.path.isdir(MODEL_PATH):
            raise FileNotFoundError(
                f"Vosk model not found: {MODEL_PATH}. "
                "Set VOSK_MODEL_PATH or MODELS_ROOT for deployed environments."
            )
        _vosk_model = Model(MODEL_PATH)
    return _vosk_model


def vosk_is_available() -> bool:
    return os.path.isdir(MODEL_PATH)

def _one_line(text: str) -> str:
    """Remove newlines + collapse spaces. Safe for UI/API text."""
    if not text:
        return ""
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return " ".join(text.split())

def convert_to_wav(input_path: str) -> str:
    """Convertit un fichier audio en WAV 16 kHz mono via ffmpeg CLI."""
    base, _ = os.path.splitext(input_path)
    wav_path = f"{base}_converted.wav"
    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        wav_path
    ], check=True)
    return wav_path

def transcrire_audio(wav_path: str) -> tuple[str, list]:
    """Lit le WAV et collecte le texte brut + liste de mots avec timestamps."""
    wf = wave.open(wav_path, "rb")
    rec = KaldiRecognizer(get_vosk_model(), wf.getframerate())
    rec.SetWords(True)

    results = []
    words = []

    while True:
        data = wf.readframes(4000)
        if not data:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            results.append(result.get("text", ""))
            words.extend(result.get("result", []))

    final = json.loads(rec.FinalResult())
    results.append(final.get("text", ""))
    words.extend(final.get("result", []))

    full_text = " ".join(r for r in results if r)
    return full_text, words


def create_streaming_recognizer(sample_rate: float = 16000) -> KaldiRecognizer:
    rec = KaldiRecognizer(get_vosk_model(), sample_rate)
    rec.SetWords(True)
    return rec


def stream_accept_audio(rec: KaldiRecognizer, pcm_bytes: bytes) -> dict:
    if rec.AcceptWaveform(pcm_bytes):
        result = json.loads(rec.Result() or "{}")
        return {
            "type": "final",
            "text": _one_line(result.get("text", "")),
        }

    result = json.loads(rec.PartialResult() or "{}")
    return {
        "type": "partial",
        "text": _one_line(result.get("partial", "")),
    }


def stream_finalize(rec: KaldiRecognizer) -> dict:
    result = json.loads(rec.FinalResult() or "{}")
    return {
        "type": "final",
        "text": _one_line(result.get("text", "")),
    }

def ponctuer_transcription_breton_v2(texte: str) -> str:
    """Ponctuation améliorée en breton : virgules pour liaison, points pour rupture."""
    mots_virgule = ["ha", "hag", "met", "pe"]
    mots_point = ["eme", "setu", "goude-se", "dre vras", "hervez", "e gwirionez", "en desped", "evit gwir"]

    texte = texte.strip()

    for mot in mots_virgule:
        texte = re.sub(rf"\b({mot})\b", r", \1", texte, flags=re.IGNORECASE)

    for mot in mots_point:
        texte = re.sub(rf"\b({mot})\b", r". \1", texte, flags=re.IGNORECASE)

    texte = re.sub(r'\s+', ' ', texte)
    texte = re.sub(r'\.\s*\.', '.', texte)
    texte = texte.strip()

    phrases = [phrase.strip().capitalize() for phrase in texte.split('.') if phrase.strip()]
    return '.\n'.join(phrases) + '.'

def nettoyer_transcription(words: list, pause_threshold=0.8, max_chars=90) -> tuple[str, list]:
    """
    Segmente la transcription par pauses, ponctue les segments,
    et découpe les longs textes en sous-segments lisibles (type .srt).
    """
    if not words:
        return "", []

    segments = []
    current_segment = []
    start_time = words[0]['start']

    for i, word in enumerate(words):
        current_segment.append(word['word'])
        end_time = word['end']
        next_word = words[i + 1] if i + 1 < len(words) else None
        gap = next_word['start'] - end_time if next_word else 0

        if not next_word or gap > pause_threshold:
            # Étape 1 : texte du segment
            segment_text = " ".join(current_segment).strip()
            punctuated = ponctuer_transcription_breton_v2(segment_text)

            # Étape 2 : découpage si trop long
            if len(punctuated) > max_chars:
                # On découpe par phrases ou lignes courtes
                lines = []
                buffer = ""
                for word in punctuated.split():
                    if len(buffer + " " + word) > max_chars:
                        lines.append(buffer.strip())
                        buffer = word
                    else:
                        buffer += " " + word
                if buffer.strip():
                    lines.append(buffer.strip())

                duration = end_time - start_time
                part_duration = duration / len(lines)

                for j, line in enumerate(lines):
                    part_start = round(start_time + j * part_duration, 3)
                    part_end = round(start_time + (j + 1) * part_duration, 3)
                    segments.append({
                        "start": part_start,
                        "end": part_end,
                        "text": line
                    })
            else:
                segments.append({
                    "start": round(start_time, 3),
                    "end": round(end_time, 3),
                    "text": punctuated
                })

            current_segment = []
            if next_word:
                start_time = next_word['start']

    # 1) Optional: ensure no \n inside segment texts (prevents UI weirdness)
    for seg in segments:
        seg["text"] = _one_line(seg.get("text", ""))

    # 2) Build full text as single-line
    full_text = " ".join(seg["text"] for seg in segments if seg.get("text"))
    full_text = _one_line(full_text)

    return full_text, segments


# Test rapide
if __name__ == "__main__":
    print("== Test de chargement Vosk ==")
    print("MODEL_PATH =", MODEL_PATH)
    try:
        _ = Model(MODEL_PATH)
        print("✔ Modèle chargé avec succès !")
    except Exception as e:
        print("❌ Erreur lors du chargement :", e)


def segments_to_srt(segments):
    def format_timestamp(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    srt_lines = []
    for i, segment in enumerate(segments, start=1):
        start = format_timestamp(segment["start"])
        end = format_timestamp(segment["end"])
        text = segment["text"]
        srt_lines.append(f"{i}\n{start} --> {end}\n{text}\n")

    return "\n".join(srt_lines)
