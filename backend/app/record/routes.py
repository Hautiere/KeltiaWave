from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect

from app.record.text_cleanup import clean_record_transcript, preserve_draft_prefix
from app.core import vosk_available, whisper_available
from app.transcribe.routes import _transcribe_whisper_metrics
from app.vosk_utils import create_streaming_recognizer, stream_accept_audio, stream_finalize

router = APIRouter(prefix="/api/record", tags=["record"])


@router.get("/capabilities")
def record_capabilities() -> dict[str, Any]:
    return {
        "languages": {
            "br": {"live": vosk_available("br"), "whisper": whisper_available("br")},
            "cy": {"live": False, "whisper": whisper_available("cy")},
        },
        "max_recording_seconds": 600,
    }


async def _whisper_recording(audio_file: UploadFile, language: Literal["br", "cy"], draft_text: str) -> dict[str, Any]:
    payload = await _transcribe_whisper_metrics(
        audio_file,
        lang=language,
        tmp_prefix=f"keltia_record_{language}_",
    )
    cleaned_text, removed = clean_record_transcript(str(payload.get("text") or ""))
    final_text, draft_prefix_preserved = preserve_draft_prefix(draft_text, cleaned_text)
    return {
        "filename": payload.get("filename"),
        "language": language,
        "engine": "whisper",
        "draft_text": draft_text.strip(),
        "text": final_text,
        "whisper_text": cleaned_text,
        "draft_prefix_preserved": draft_prefix_preserved,
        "removed_trailing_phrases": removed,
        "metrics": payload.get("metrics", {}),
    }


@router.post("/transcribe", summary="Generate a Record transcript with Whisper")
async def transcribe_recording(
    audio_file: UploadFile = File(...),
    language: Literal["br", "cy"] = Form("br"),
) -> dict[str, Any]:
    return await _whisper_recording(audio_file, language, "")


@router.post("/improve", summary="Improve an existing Record draft with Whisper")
async def improve_recording(
    audio_file: UploadFile = File(...),
    language: Literal["br", "cy"] = Form("br"),
    draft_text: str = Form(""),
) -> dict[str, Any]:
    if language == "br" and not draft_text.strip():
        raise HTTPException(status_code=422, detail="A draft transcript is required before Whisper improvement.")
    return await _whisper_recording(audio_file, language, draft_text)


@router.websocket("/live")
async def record_live_vosk(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        start = json.loads(await websocket.receive_text() or "{}")
        recognizer = create_streaming_recognizer(float(start.get("sample_rate", 16000)))
        await websocket.send_json({"type": "ready", "sample_rate": 16000})
        while True:
            message = await websocket.receive()
            if message.get("text") is not None:
                control = json.loads(message.get("text") or "{}")
                if control.get("type") == "stop":
                    final = stream_finalize(recognizer)
                    if final.get("text"):
                        await websocket.send_json(final)
                    await websocket.send_json({"type": "done"})
                    break
                continue
            chunk = message.get("bytes")
            if chunk:
                event = stream_accept_audio(recognizer, chunk)
                if event.get("text"):
                    await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    finally:
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close()
