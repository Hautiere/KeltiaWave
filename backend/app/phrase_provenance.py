"""Phrase provenance rules shared by HTTP write endpoints only."""
import re
from pydantic import AnyHttpUrl, TypeAdapter, ValidationError

from fastapi import HTTPException

_HTTP_URL = TypeAdapter(AnyHttpUrl)


def normalize_phrase_source_url(source: str | None, source_url: str | None) -> str | None:
    if source != "internet":
        return None
    value = (source_url or "").strip()
    if not value:
        raise HTTPException(400, "Source URL is required for an Internet phrase")
    if len(value) > 2048:
        raise HTTPException(400, "Source URL must not exceed 2048 characters")
    if not re.match(r"^https?://[^/?#]", value, re.IGNORECASE) or re.search(r"[\\\s]", value):
        raise HTTPException(400, "Source URL must be a valid HTTP(S) URL")
    try:
        _HTTP_URL.validate_python(value)
    except ValidationError:
        raise HTTPException(400, "Source URL must be a valid HTTP(S) URL") from None
    return value


def apply_phrase_provenance(patch: dict, source: str | None = None, source_url: str | None = None) -> None:
    # Leave unrelated edits of historical records untouched.
    if "source" in patch or "source_url" in patch:
        patch["source_url"] = normalize_phrase_source_url(
            patch.get("source", source), patch.get("source_url", source_url),
        )
