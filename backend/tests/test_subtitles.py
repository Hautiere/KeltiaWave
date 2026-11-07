from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.subtitles import routes


@pytest.fixture
def subtitles_client():
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


@pytest.mark.parametrize('language,engine,target', [
    ('cy', 'wav2vec2', 'transcribe_w2v_wel_metrics'),
    ('cy', 'whisper', 'transcribe_whisper_metrics'),
    ('br', 'whisper', 'transcribe_whisper_metrics'),
    ('br', 'vosk', 'transcribe_vosk_bre_metrics_v2'),
])
def test_dispatches_selected_engine(subtitles_client, monkeypatch, language, engine, target):
    result = {'text': 'Test', 'segments': [{'start': 0, 'end': 4, 'text': 'Test'}]}
    handlers = {}
    for name in ['transcribe_w2v_wel_metrics', 'transcribe_whisper_metrics', 'transcribe_vosk_bre_metrics_v2']:
        handlers[name] = AsyncMock(return_value=result)
        monkeypatch.setattr(routes, name, handlers[name])
    response = subtitles_client.post(
        f'/api/subtitles/transcribe?language={language}&engine={engine}',
        files={'audio_file': ('test.wav', b'test', 'audio/wav')},
    )
    assert response.status_code == 200
    assert response.json() == result
    handlers[target].assert_awaited_once()
    for name, handler in handlers.items():
        if name != target:
            handler.assert_not_awaited()
    if engine == 'whisper':
        assert handlers[target].call_args.kwargs['lang'] == language


@pytest.mark.parametrize('language,engine', [('br', 'wav2vec2'), ('cy', 'vosk')])
def test_rejects_unsupported_language_engine_pair(subtitles_client, language, engine):
    response = subtitles_client.post(
        f'/api/subtitles/transcribe?language={language}&engine={engine}',
        files={'audio_file': ('test.wav', b'test', 'audio/wav')},
    )
    assert response.status_code == 400
