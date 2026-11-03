"""Bounded Welsh PCM windows and continuous CTC words for Live."""
from array import array
from app.transcribe.wav2vec2 import live_window_ids, decode_live_ids

BLOCK_SECONDS = 4
CONTEXT_SECONDS = 1


class PcmWindows:
    def __init__(self, rate):
        self.rate = rate
        self.block = rate * 2 * BLOCK_SECONDS
        self.context = rate * 2 * CONTEXT_SECONDS
        self.pending = bytearray()
        self.left = b''

    def feed(self, pcm, final=False):
        self.pending.extend(pcm)
        windows = []
        while len(self.pending) >= self.block+self.context or (final and self.pending):
            size = min(self.block, len(self.pending))
            core = bytes(self.pending[:size])
            right = bytes(self.pending[size:size+self.context])
            windows.append((self.left+core+right, self.rate, len(self.left)//2, size//2))
            self.left = core[-self.context:]
            del self.pending[:size]
        return windows


class LiveCtcWords:
    def __init__(self, delimiter):
        self.delimiter = delimiter
        self.pending = array('i')

    def accept(self, window):
        self.pending.extend(live_window_ids(*window))
        split = next((index+1 for index in range(len(self.pending)-1, -1, -1)
                      if self.pending[index] == self.delimiter), 0)
        events = []
        if split:
            text = decode_live_ids(self.pending[:split])
            del self.pending[:split]
            if text:
                events.append({'type': 'final', 'text': text})
        events.append({'type': 'partial', 'text': decode_live_ids(self.pending) if self.pending else ''})
        return events

    def finish(self):
        text = decode_live_ids(self.pending) if self.pending else ''
        self.pending = array('i')
        return {'type': 'final', 'text': text}
