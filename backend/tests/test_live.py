import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.live import routes


@pytest.fixture
def live_client(monkeypatch):
    application = FastAPI()
    application.include_router(routes.router)
    monkeypatch.setattr(routes, "vosk_available", lambda language: True)
    monkeypatch.setattr(routes, "whisper_available", lambda language: True)
    monkeypatch.setattr(routes, "create_streaming_recognizer", lambda rate: {"rate": rate})
    monkeypatch.setattr(routes, "stream_accept_audio", lambda recognizer, chunk: {"type": "partial", "text": "demat"})
    monkeypatch.setattr(routes, "stream_finalize", lambda recognizer: {"type": "final", "text": "demat deoc’h"})
    with TestClient(application) as client:
        yield client


def test_live_capabilities_are_separate_and_honest(live_client):
    response = live_client.get("/api/live/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["languages"] == {"br": {"live": True, "whisper": True}}
    assert data["processing"] == "server"
    assert data["audio_format"] == "pcm_s16le_mono"


def test_live_pcm_and_stop_flush_last_words(live_client):
    with live_client.websocket_connect("/api/live/stream") as socket:
        socket.send_json({"type": "start", "sample_rate": 48000, "language": "br"})
        assert socket.receive_json() == {"type": "ready", "sample_rate": 48000}
        socket.send_bytes(b"\x00\x00" * 2048)
        assert socket.receive_json() == {"type": "partial", "text": "demat"}
        socket.send_json({"type": "ping"})
        assert socket.receive_json() == {"type": "pong"}
        socket.send_json({"type": "stop"})
        assert socket.receive_json() == {"type": "final", "text": "demat deoc’h"}
        assert socket.receive_json() == {"type": "done"}
    assert routes._active_sessions == 0


@pytest.mark.parametrize("start", [[], {}, {"type": "start", "sample_rate": -1},
    {"type": "start", "sample_rate": True}, {"type": "start", "sample_rate": 16000, "language": "cy"}])
def test_invalid_start_is_reported(live_client, start):
    with live_client.websocket_connect("/api/live/stream") as socket:
        socket.send_json(start)
        assert socket.receive_json()["type"] == "error"
    assert routes._active_sessions == 0


@pytest.mark.parametrize("chunk", [b"", b"\x01", b"\x00" * 65538])
def test_invalid_pcm_is_rejected(live_client, chunk):
    with live_client.websocket_connect("/api/live/stream") as socket:
        socket.send_json({"type": "start", "sample_rate": 16000})
        assert socket.receive_json()["type"] == "ready"
        socket.send_bytes(chunk)
        assert socket.receive_json()["type"] == "error"


def test_missing_model_is_explicit(live_client, monkeypatch):
    monkeypatch.setattr(routes, "vosk_available", lambda language: False)
    assert live_client.get("/api/live/capabilities").json()["languages"]["br"]["live"] is False
    with live_client.websocket_connect("/api/live/stream") as socket:
        socket.send_json({"type": "start", "sample_rate": 16000})
        assert "modèle" in socket.receive_json()["message"]


def test_empty_partial_clears_provisional_text(live_client, monkeypatch):
    monkeypatch.setattr(routes, "stream_accept_audio", lambda *args: {"type": "partial", "text": ""})
    with live_client.websocket_connect("/api/live/stream") as socket:
        socket.send_json({"type": "start", "sample_rate": 16000})
        socket.receive_json()
        socket.send_bytes(b"\x00\x00")
        assert socket.receive_json() == {"type": "partial", "text": ""}
        socket.send_json({"type": "stop"})
        socket.receive_json()
        socket.receive_json()


def test_busy_server_rejects_before_allocating_model(live_client, monkeypatch):
    monkeypatch.setattr(routes, "_active_sessions", routes.MAX_SESSIONS)
    with live_client.websocket_connect("/api/live/stream") as socket:
        assert "occupé" in socket.receive_json()["message"]


def test_foreign_browser_origin_is_rejected(live_client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with live_client.websocket_connect("/api/live/stream", headers={"origin": "https://untrusted.example"}):
            pass
    assert exc.value.code == 1008


def test_same_origin_with_forwarded_port_is_accepted(live_client):
    with live_client.websocket_connect('/api/live/stream', headers={
        'origin': 'http://testserver:4800', 'host': 'testserver:4800',
    }) as socket:
        socket.send_json({'type': 'start', 'sample_rate': 16000})
        assert socket.receive_json()['type'] == 'ready'
        socket.send_json({'type': 'stop'})
        assert socket.receive_json()['type'] == 'final'
        assert socket.receive_json()['type'] == 'done'


def test_whisper_improvement_uses_live_audio_and_shared_service(live_client, monkeypatch):
    async def transcribe(audio, *, lang, tmp_prefix):
        assert lang == 'br'
        assert tmp_prefix == 'keltia_live_br_'
        assert await audio.read() == b'audio-content'
        return {'text': 'Demat deoc’h.', 'metrics': {'engine': 'whisper'}}
    monkeypatch.setattr(routes, 'transcribe_whisper_metrics', transcribe)
    response = live_client.post('/api/live/improve', files={'audio_file': ('live.webm', b'audio-content', 'audio/webm')})
    assert response.status_code == 200
    assert response.json()['text'] == 'Demat deoc’h.'
    assert response.json()['engine'] == 'whisper'


def test_whisper_requires_audio_rather_than_text(live_client):
    assert live_client.post('/api/live/improve', data={'draft_text': 'demat'}).status_code == 422


def test_whisper_unavailable_is_not_a_false_success(live_client, monkeypatch):
    from fastapi import HTTPException
    async def unavailable(*args, **kwargs):
        raise HTTPException(status_code=503, detail='Whisper model unavailable')
    monkeypatch.setattr(routes, 'transcribe_whisper_metrics', unavailable)
    response = live_client.post('/api/live/improve', files={'audio_file': ('live.webm', b'audio', 'audio/webm')})
    assert response.status_code == 503
