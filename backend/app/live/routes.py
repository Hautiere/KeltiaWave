import asyncio
import json
import logging
import os
import time
from urllib.parse import urlsplit
from typing import Literal

from fastapi import APIRouter, File, UploadFile, WebSocket, WebSocketDisconnect, Form, HTTPException
from starlette.concurrency import run_in_threadpool
from starlette.websockets import WebSocketState

from app.core import get_config, vosk_available, whisper_available
from app.transcribe.service import transcribe_whisper_metrics
from app.cors import DEFAULT_ORIGINS
from app.transcribe.wav2vec2 import available as w2v_available, prepare_live
from app.live.wav2vec2_stream import PcmWindows, LiveCtcWords, BLOCK_SECONDS
from app.vosk_utils import create_streaming_recognizer, stream_accept_audio, stream_finalize

router = APIRouter(prefix="/api/live", tags=["live"])
logger = logging.getLogger(__name__)
MAX_SECONDS = 3600
MAX_CHUNK_BYTES = 65536
MAX_SESSIONS = 4
_active_sessions = 0
_active_welsh_sessions = 0


@router.get("/capabilities")
def live_capabilities():
    return {
        "languages": {"br": {"live": vosk_available("br"), "whisper": whisper_available("br")},
                      "cy": {"live": w2v_available(), "whisper": whisper_available("cy"),
                             "engine": "wav2vec2", "block_seconds": BLOCK_SECONDS}},
        "engine": "vosk",
        "processing": "server",
        "audio_format": "pcm_s16le_mono",
        "max_session_seconds": MAX_SECONDS,
        "max_audio_upload_bytes": int(get_config()["max_file_size_mb"]) * 1024 * 1024,
    }


@router.post("/improve", summary="Transcribe the captured Live audio with Whisper")
async def improve_live(audio_file: UploadFile = File(...), language: Literal["br", "cy"] = Form("br")):
    """Whisper needs the original audio, rather than a text-only Vosk draft."""
    payload = await transcribe_whisper_metrics(audio_file, lang=language, tmp_prefix=f"keltia_live_{language}_")
    return {"text": payload["text"], "engine": "whisper", "language": language, "metrics": payload.get("metrics", {})}


async def _welsh_stream(websocket, rate):
    delimiter = await run_in_threadpool(prepare_live)
    recognizer, windows = LiveCtcWords(delimiter), PcmWindows(rate)
    await websocket.send_json({'type':'ready','sample_rate':rate,'engine':'wav2vec2','language':'cy','block_seconds':BLOCK_SECONDS})
    queue = asyncio.Queue(maxsize=2)
    send_lock = asyncio.Lock()
    deadline = time.monotonic()+MAX_SECONDS

    async def send(event):
        async with send_lock:
            await websocket.send_json(event)

    async def receive():
        audio_bytes = 0
        while True:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise ValueError('La session a atteint une heure. Démarrez une nouvelle écoute.')
            message = await asyncio.wait_for(websocket.receive(),timeout=min(90,remaining))
            if message['type']=='websocket.disconnect':
                raise WebSocketDisconnect()
            if message.get('text') is not None:
                control = json.loads(message['text'])
                if isinstance(control,dict) and control.get('type')=='ping':
                    await send({'type':'pong'}); continue
                if not isinstance(control,dict) or control.get('type')!='stop':
                    raise ValueError('Commande Live inconnue.')
                for window in windows.feed(b'',final=True):
                    await queue.put(window)
                await queue.put(None)
                return
            pcm = message.get('bytes',b'')
            if not pcm or len(pcm)%2 or len(pcm)>MAX_CHUNK_BYTES:
                raise ValueError('Bloc audio PCM16 invalide ou trop volumineux.')
            audio_bytes += len(pcm)
            if audio_bytes>MAX_SECONDS*rate*2:
                raise ValueError('La limite audio de la session est atteinte.')
            for window in windows.feed(pcm):
                try: queue.put_nowait(window)
                except asyncio.QueueFull:
                    raise ValueError('Le serveur W2V ne suit pas l’écoute. Votre texte reste conservé ; réessayez dans un instant.')

    async def decode():
        while True:
            window = await queue.get()
            if window is None:
                await send(await run_in_threadpool(recognizer.finish))
                await send({'type':'done'})
                return
            for event in await run_in_threadpool(recognizer.accept, window):
                await send(event)

    producer,consumer = asyncio.create_task(receive()),asyncio.create_task(decode())
    try:
        done,_ = await asyncio.wait({producer,consumer},return_when=asyncio.FIRST_COMPLETED)
        for task in done: task.result()
        if producer in done: await consumer
    finally:
        for task in (producer,consumer):
            if not task.done(): task.cancel()
        await asyncio.gather(producer,consumer,return_exceptions=True)


@router.websocket("/stream")
async def live_stream(websocket: WebSocket):
    """Start JSON (sample_rate), then mono PCM16 bytes; stop JSON flushes final text."""
    global _active_sessions, _active_welsh_sessions
    welsh_claimed = False
    origin = websocket.headers.get("origin")
    configured = os.getenv("CORS_ALLOW_ORIGINS", "")
    allowed = [value.strip() for value in configured.split(",") if value.strip()] or DEFAULT_ORIGINS
    same_origin = origin and urlsplit(origin).scheme in ("http", "https") and urlsplit(origin).netloc == websocket.headers.get("host")
    if origin and origin not in allowed and not same_origin:
        await websocket.close(code=1008)
        return
    protocols = websocket.scope.get("subprotocols", [])
    await websocket.accept(subprotocol="keltiawave-live" if "keltiawave-live" in protocols else None)
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
        language = start.get('language','br')
        if language not in ('br','cy'):
            raise ValueError('Choisissez le breton ou le gallois.')
        if language=='cy':
            if not w2v_available():
                raise ValueError('Le modèle W2V gallois n’est pas disponible sur le serveur.')
            if _active_welsh_sessions>=1:
                raise ValueError('Une écoute galloise est déjà en cours. Réessayez dans un instant.')
            _active_welsh_sessions += 1
            welsh_claimed = True
            await _welsh_stream(websocket,rate)
            return
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
    except HTTPException as exc:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type":"error","message":str(exc.detail)})
    except (ValueError, asyncio.TimeoutError) as exc:
        await websocket.send_json({"type": "error", "message": str(exc) or "Session inactive ou délai dépassé."})
    except Exception:
        logger.exception("Live stream failed")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type": "error", "message": "La transcription Live est indisponible. Votre texte reste affiché."})
    finally:
        _active_sessions -= 1
        if welsh_claimed: _active_welsh_sessions -= 1
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
