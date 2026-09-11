import asyncio
import threading
import pytest
from app.transcribe import routes

@pytest.mark.parametrize('lang', ['br', 'cy'])
def test_whisper_keeps_event_loop_responsive(monkeypatch, lang):
    started, release = threading.Event(), threading.Event()
    async def upload(*args):
        return 'audio.wav', '/unused.wav', '.wav'
    def transcribe(*args, **kwargs):
        started.set()
        assert release.wait(2), 'Event loop blocked'
        return {'text': 'Test', 'segments': []}
    monkeypatch.setattr(routes, 'whisper_available', lambda _: True)
    monkeypatch.setattr(routes, 'save_and_validate_upload', upload)
    monkeypatch.setattr(routes, 'to_wav_if_needed', lambda *args: '/unused.wav')
    monkeypatch.setattr(routes, 'wav_duration_seconds', lambda _: 169)
    monkeypatch.setattr(routes, 'whisper_run', transcribe)
    monkeypatch.setattr(routes, 'record_observation', lambda *args: None)
    async def scenario():
        monkeypatch.setattr(routes, '_whisper_slot', asyncio.Semaphore(1))
        task = asyncio.create_task(routes._transcribe_whisper_metrics(None, lang=lang, tmp_prefix='test_whisper_'))
        try:
            for _ in range(100):
                if started.is_set(): break
                await asyncio.sleep(.01)
            assert started.is_set()
            assert not task.done()
        finally:
            release.set()
        result = await task
        assert result['text'] == 'Test'
        assert result['metrics']['lang'] == lang
    asyncio.run(scenario())
