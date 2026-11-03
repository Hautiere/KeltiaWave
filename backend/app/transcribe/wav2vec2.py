"""Local Welsh Wav2Vec2 CTC inference, bounded windows and no Hub downloads."""
from array import array
import asyncio
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import wave

from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

_slot = asyncio.Semaphore(1)
_lock = threading.Lock()
_runtime = None
_runtime_path = None
MODEL_ID = 'wav2vec2-cy'


def model_path():
    root = Path(os.getenv('MODELS_ROOT') or str(Path(__file__).resolve().parents[2] / 'models'))
    return Path(os.getenv('W2V_CY_MODEL_PATH', str(root / MODEL_ID)))


def available():
    return all((model_path() / name).is_file() for name in
               ['config.json', 'model.safetensors', 'preprocessor_config.json', 'vocab.json'])


def _load():
    global _runtime, _runtime_path
    path = model_path().resolve()
    if _runtime is not None and path == _runtime_path:
        return _runtime
    if not available():
        raise HTTPException(503, 'Le modèle W2V gallois wav2vec2-cy est absent du serveur.')
    try:
        import torch
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
        processor = Wav2Vec2Processor.from_pretrained(str(path), local_files_only=True)
        model = Wav2Vec2ForCTC.from_pretrained(str(path), local_files_only=True, use_safetensors=True).eval()
    except ImportError as error:
        raise HTTPException(503, 'Les dépendances W2V ne sont pas installées sur ce serveur.') from error
    except (OSError, ValueError, RuntimeError) as error:
        raise HTTPException(503, 'Impossible de charger le modèle W2V gallois local.') from error
    _runtime, _runtime_path = (torch, processor, model), path
    return _runtime


def crop_ids(ids, left_samples, core_samples, input_samples):
    """Keep the center of each overlapping window; decode CTC only after joining."""
    start = round(len(ids) * left_samples / input_samples)
    end = round(len(ids) * (left_samples + core_samples) / input_samples)
    return ids[start:end]


def infer_wav(path):
    import numpy as np
    with _lock, wave.open(str(path), 'rb') as audio:
        if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (16000, 1, 2):
            raise HTTPException(400, 'W2V attend un audio PCM mono 16 kHz.')
        total = audio.getnframes()
        if total < 400:
            return {'text': '', 'segments': [], 'duration': total / 16000}
        torch, processor, model = _load()
        ids = array('i')
        core, context = 16 * 16000, 2 * 16000
        for offset in range(0, total, core):
            start, end = max(0, offset-context), min(total, offset+core+context)
            audio.setpos(start)
            samples = np.frombuffer(audio.readframes(end-start), dtype='<i2').astype(np.float32) / 32768.0
            inputs = processor(samples, sampling_rate=16000, return_tensors='pt')
            with torch.inference_mode():
                predicted = model(**inputs).logits.argmax(dim=-1)[0].cpu().tolist()
            ids.extend(crop_ids(predicted, offset-start, min(core, total-offset), len(samples)))
        text = processor.batch_decode([list(ids)])[0].strip()
        duration = total / 16000
        segments = [{'id': 0, 'start': 0.0, 'end': duration, 'text': text}] if text else []
        return {'text': text, 'segments': segments, 'duration': duration}


def _process(input_path, directory):
    output = str(Path(directory) / 'w2v-input.wav')
    try:
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', input_path,
                        '-vn', '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', output],
                       check=True, capture_output=True)
    except subprocess.CalledProcessError as error:
        raise HTTPException(400, 'Impossible de lire ce fichier audio ou vidéo.') from error
    return infer_wav(output)


async def transcribe(audio_file: UploadFile):
    from app.core import save_and_validate_upload, text_metrics
    from app.transcribe.calibration import record_observation
    if not available():
        raise HTTPException(503, 'Le modèle W2V gallois wav2vec2-cy est absent du serveur.')
    directory = tempfile.mkdtemp(prefix='keltia_w2v_cy_')
    try:
        filename, path, _ = await save_and_validate_upload(audio_file, directory)
        async with _slot:
            started = time.perf_counter()
            result = await run_in_threadpool(_process, path, directory)
            elapsed = time.perf_counter() - started
        metrics = text_metrics(result['text'], elapsed, model=MODEL_ID)
        metrics.update(engine='wav2vec2', lang='cy', model_id=MODEL_ID, decoder='greedy-ctc',
                       calibration=record_observation('cy', 'fast', elapsed, result['duration']))
        return dict(filename=filename, text=result['text'], segments=result['segments'], metrics=metrics)
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def prepare_live():
    if not _lock.acquire(blocking=False):
        raise HTTPException(503, 'W2V est occupé par une transcription. Réessayez dans un instant.')
    try:
        _, processor, _ = _load()
        return processor.tokenizer.convert_tokens_to_ids(processor.tokenizer.word_delimiter_token)
    finally:
        _lock.release()


def live_window_ids(pcm, sample_rate, left_frames, core_frames):
    """Decode a bounded PCM window; keep context out of the committed CTC frames."""
    import numpy as np
    converted = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 's16le',
        '-ar', str(sample_rate), '-ac', '1', '-i', 'pipe:0', '-f', 'f32le',
        '-ar', '16000', '-ac', '1', 'pipe:1'], input=pcm, capture_output=True, check=True)
    samples = np.frombuffer(converted.stdout, dtype='<f4')
    if len(samples) < 400:
        samples = np.pad(samples, (0, 400-len(samples)))
    with _lock:
        torch, processor, model = _load()
        inputs = processor(samples, sampling_rate=16000, return_tensors='pt')
        with torch.inference_mode():
            predicted = model(**inputs).logits.argmax(dim=-1)[0].cpu().tolist()
        return crop_ids(predicted, left_frames, core_frames, len(pcm)//2)


def decode_live_ids(ids):
    with _lock:
        _, processor, _ = _load()
        return processor.batch_decode([list(ids)])[0].strip()
