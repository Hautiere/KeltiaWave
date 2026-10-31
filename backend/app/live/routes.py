import asyncio
import json
import logging
import os
import time
from urllib.parse import urlsplit

from fastapi import APIRouter, File, UploadFile, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool
from starlette.websockets import WebSocketState

from app.core import get_config, vosk_available, whisper_available
from app.transcribe.service import transcribe_whisper_metrics
from app.cors import DEFAULT_ORIGINS
from app.vosk_utils import create_streaming_recognizer, stream_accept_audio, stream_finalize

router = APIRouter(prefix="/api/live", tags=["live"])
logger = logging.getLogger(__name__)
MAX_SECONDS = 3600
MAX_CHUNK_BYTES = 65536
MAX_SESSIONS = 4
_active_sessions = 0


@router.get("/capabilities")
def live_capabilities():
    return {
        "languages": {"br": {"live": vosk_available("br"), "whisper": whisper_available("br")}},
        "engine": "vosk",
        "processing": "server",
        "audio_format": "pcm_s16le_mono",
        "max_session_seconds": MAX_SECONDS,
        "max_audio_upload_bytes": int(get_config()["max_file_size_mb"]) * 1024 * 1024,
    }


@router.post("/improve", summary="Transcribe the captured Live audio with Whisper")
async def improve_live(audio_file: UploadFile = File(...)):
    """Whisper needs the original audio, rather than a text-only Vosk draft."""
    payload = await transcribe_whisper_metrics(audio_file, lang="br", tmp_prefix="keltia_live_br_")
    return {"text": payload["text"], "engine": "whisper", "language": "br", "metrics": payload.get("metrics", {})}


@router.websocket("/stream")
async def live_stream(websocket: WebSocket):
    """Start JSON (sample_rate), then mono PCM16 bytes; stop JSON flushes final text."""
    global _active_sessions
    origin = websocket.headers.get("origin")
    configured = os.getenv("CORS_ALLOW_ORIGINS", "")
    allowed = [value.strip() for value in configured.split(",") if value.strip()] or DEFAULT_ORIGINS
    same_origin = origin and urlsplit(origin).scheme in ("http", "https") and urlsplit(origin).netloc == websocket.headers.get("host")
    if origin and origin not in allowed and not same_origin:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    if _active_sessions >= MAX_SESSIONS:
        await websocket.send_json({"type": "error", "message": "Live est occupé. Réessayez dans un instant."})
        await websocket.close(code=1013)
        return
    _active_sessions += 1
    try:
        start = json.loads(await asyncio.wait_for(websocket.receive_text(), timeout=15))
        rate = start.get("sample_rate") if isinstance(start, dict) else None
        if not isinstance(start, dict) or start.get("type") != "start" or type(rate) is not int or not 8000 <= rate <= 96000:
            raise ValueError("Format audio invalide : PCM16 mono, entre 8 et 96 kHz requis.")
        if start.get("language", "br") != "br":
            raise ValueError("Live prend actuellement en charge le breton uniquement.")
        if not vosk_available("br"):
            raise ValueError("Le modèle Vosk breton n’est pas disponible sur le serveur.")
        recognizer = await run_in_threadpool(create_streaming_recognizer, rate)
        await websocket.send_json({"type": "ready", "sample_rate": rate})
        deadline = time.monotonic() + MAX_SECONDS
        audio_bytes = 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError("La session a atteint une heure. Démarrez une nouvelle écoute.")
            message = await asyncio.wait_for(websocket.receive(), timeout=min(90, remaining))
            if message["type"] == "websocket.disconnect":
                return
            if message.get("text") is not None:
                control = json.loads(message["text"])
                if isinstance(control, dict) and control.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue
                if not isinstance(control, dict) or control.get("type") != "stop":
                    raise ValueError("Commande Live inconnue.")
                final = await run_in_threadpool(stream_finalize, recognizer)
                await websocket.send_json(final)
                await websocket.send_json({"type": "done"})
                return
            chunk = message.get("bytes", b"")
            if not chunk or len(chunk) % 2 or len(chunk) > MAX_CHUNK_BYTES:
                raise ValueError("Bloc audio PCM16 invalide ou trop volumineux.")
            audio_bytes += len(chunk)
            if audio_bytes > MAX_SECONDS * rate * 2:
                raise ValueError("La limite audio de la session est atteinte.")
            event = await run_in_threadpool(stream_accept_audio, recognizer, chunk)
            # Empty partials must reach the client to clear obsolete provisional text.
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    except (ValueError, asyncio.TimeoutError) as exc:
        await websocket.send_json({"type": "error", "message": str(exc) or "Session inactive ou délai dépassé."})
    except Exception:
        logger.exception("Live stream failed")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type": "error", "message": "La transcription Live est indisponible. Votre texte reste affiché."})
    finally:
        _active_sessions -= 1
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
