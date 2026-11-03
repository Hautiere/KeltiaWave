import struct
from app.live import wav2vec2_stream as stream


def test_pcm_context_windows_keep_each_core_frame_once_and_flush_tail():
    buffer=stream.PcmWindows(10)
    first=buffer.feed(struct.pack('<50h',*range(50)))
    assert len(first)==1 and first[0][2:]==(0,40)
    assert struct.unpack('<50h',first[0][0])==tuple(range(50))
    assert buffer.feed(struct.pack('<20h',*range(50,70)))==[]
    last=buffer.feed(b'',final=True)
    assert len(last)==1 and last[0][2:]==(10,30)
    assert struct.unpack('<40h',last[0][0])==tuple(range(30,70))
    assert sum(window[3] for window in first+last)==70
    assert not buffer.pending


def test_ctc_word_crossing_windows_is_not_split_or_duplicated(monkeypatch):
    chunks=iter([[1,1,3,2],[2,2,3,1]])
    monkeypatch.setattr(stream,'live_window_ids',lambda *args:next(chunks))
    def decode(ids):
        unique=[value for index,value in enumerate(ids) if index==0 or value!=ids[index-1]]
        return ''.join({1:'bore',2:'da',3:' '}[value] for value in unique).strip()
    monkeypatch.setattr(stream,'decode_live_ids',decode)
    recognizer=stream.LiveCtcWords(3)
    assert recognizer.accept(())[0]=={'type':'final','text':'bore'}
    assert recognizer.accept(())[0]=={'type':'final','text':'da'}
    assert recognizer.finish()=={'type':'final','text':'bore'}


def test_live_backlog_is_bounded_and_explicitly_rejected(monkeypatch):
    import asyncio
    import threading
    from app.live import routes
    release=threading.Event()
    monkeypatch.setattr(routes,'prepare_live',lambda:3)
    class Recognizer:
        def __init__(self,*args):pass
        def accept(self,window):release.wait(2);return []
        def finish(self):return {'type':'final','text':''}
    monkeypatch.setattr(routes,'LiveCtcWords',Recognizer)
    class Socket:
        async def send_json(self,event):pass
        async def receive(self):
            await asyncio.sleep(0)
            return {'type':'websocket.receive','bytes':b'\0\0'*16000}
    async def run():
        try:
            import pytest
            with pytest.raises(ValueError,match='ne suit pas'):
                await asyncio.wait_for(routes._welsh_stream(Socket(),16000),2)
        finally:release.set()
    asyncio.run(run())
