from __future__ import annotations

import re
import unicodedata


TRAILING_HALLUCINATIONS = (
    "pelec'h ar bloaz man",
    "pelec’h ar bloaz man",
    "pelec'h ar bloaz-mañ",
    "pelec’h ar bloaz-mañ",
    "pelec'h em eus ar c'her",
    "pelec’h em eus ar c’hêr",
)


def _canonical(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).replace("’", "'")
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9']+", " ", normalized.lower()).strip()


def clean_record_transcript(text: str) -> tuple[str, list[str]]:
    """Remove known model hallucinations only when they close the transcript.

    Whisper does not always reproduce the same words after ``Pelec'h``.  Once
    a real utterance precedes it, treat a short final ``Pelec'h …`` question as
    the same recurrent Record hallucination.
    """
    cleaned = (text or "").strip()
    removed: list[str] = []
    canonical_targets = {_canonical(item) for item in TRAILING_HALLUCINATIONS}

    while cleaned:
        match = re.search(r"([^.!?\n]+)[.!?]?\s*$", cleaned)
        if not match or _canonical(match.group(1)) not in canonical_targets:
            break
        removed.append(match.group(0).strip())
        cleaned = cleaned[: match.start()].rstrip(" \t\r\n,;:.!?")

    # The hallucinated question changes (city, year, place, etc.) and may be
    # glued to the genuine transcription without preceding punctuation.
    pelec_matches = list(re.finditer(r"(?i)(?<!\w)pelec\s*['’]\s*h\b", cleaned))
    if pelec_matches:
        start = pelec_matches[-1].start()
        trailing = cleaned[start:].strip()
        if start > 0 and len(_canonical(trailing).split()) <= 12:
            removed.append(trailing)
            cleaned = cleaned[:start].rstrip(" \t\r\n,;:.!?")

    return cleaned, removed


def preserve_draft_prefix(draft: str, whisper: str) -> tuple[str, bool]:
    """Keep a short Vosk prefix when Whisper only returns the draft suffix."""
    draft_clean = (draft or "").strip()
    whisper_clean = (whisper or "").strip()
    if not draft_clean or not whisper_clean:
        return whisper_clean or draft_clean, False

    draft_words = draft_clean.split()
    whisper_words = whisper_clean.split()
    canonical_draft = [_canonical(word) for word in draft_words]
    canonical_whisper = [_canonical(word) for word in whisper_words]

    max_missing_prefix = min(4, max(0, len(draft_words) - 1))
    for missing in range(1, max_missing_prefix + 1):
        suffix = canonical_draft[missing:]
        if len(suffix) >= 3 and suffix == canonical_whisper:
            return " ".join([*draft_words[:missing], *whisper_words]), True
    return whisper_clean, False
