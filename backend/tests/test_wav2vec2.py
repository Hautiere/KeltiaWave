import asyncio
from io import BytesIO
from pathlib import Path
import threading
from fastapi import UploadFile
from app.transcribe import wav2vec2, calibration


def test_w2v_endpoint_contract_and_cleanup(client, monkeypatch, tmp_path):
    monkeypatch.setattr(wav2vec2, 'available', lambda: True)
    monkeypatch.setattr(calibration, 'CALIBRATION_FILE', tmp_path/'calibration.json')
    directories=[]
    def process(path, directory):
        assert Path(path).exists()
        directories.append(directory)
        return {'text':'bore da','segments':[{'id':0,'start':0,'end':2,'text':'bore da'}],'duration':2}
    monkeypatch.setattr(wav2vec2,'_process',process)
    response=client.post('/api/transcribe/transcribe_w2v_wel_metrics',files={'audio_file':('welsh.wav',b'RIFF-fixture','audio/wav')})
    assert response.status_code==200,response.text
    payload=response.json()
    assert payload['text']=='bore da'
    assert payload['metrics']['engine']=='wav2vec2'
    assert payload['metrics']['lang']=='cy'
    assert payload['metrics']['decoder']=='greedy-ctc'
    assert not Path(directories[0]).exists()
    estimate=client.get('/api/transcribe/estimate?lang=cy&mode=fast&duration_seconds=10')
    assert estimate.status_code==200 and estimate.json()['engine']=='wav2vec2'


def test_missing_welsh_model_reports_clear_error(client, monkeypatch, tmp_path):
    monkeypatch.setattr(wav2vec2,'model_path',lambda:tmp_path/'missing')
    response=client.post('/api/transcribe/transcribe_w2v_wel_metrics',files={'audio_file':('test.wav',b'RIFF','audio/wav')})
    assert response.status_code==503
    assert 'W2V gallois' in response.json()['detail']


def test_w2v_keeps_the_event_loop_responsive(monkeypatch, tmp_path):
    started,release=threading.Event(),threading.Event()
    monkeypatch.setattr(wav2vec2,'available',lambda:True)
    monkeypatch.setattr(calibration,'CALIBRATION_FILE',tmp_path/'calibration.json')
    def process(*args):
        started.set();assert release.wait(3)
        return {'text':'','segments':[],'duration':0.1}
    monkeypatch.setattr(wav2vec2,'_process',process)
    async def run():
        task=asyncio.create_task(wav2vec2.transcribe(UploadFile(filename='test.wav',file=BytesIO(b'RIFF-fixture'))))
        try:
            async def wait_started():
                while not started.is_set():await asyncio.sleep(.005)
            await asyncio.wait_for(wait_started(),1)
            await asyncio.sleep(.02)
            assert not task.done()
        finally:release.set()
        await task
    asyncio.run(run())


def test_w2v_crops_overlapping_context_without_splitting_decode():
    ids=list(range(100))
    assert wav2vec2.crop_ids(ids,20,60,100)==list(range(20,80))
    assert wav2vec2.crop_ids(ids,0,80,100)==list(range(80))
    assert wav2vec2.crop_ids(ids,20,80,100)==list(range(20,100))
