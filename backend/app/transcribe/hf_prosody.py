"""Experimental Orange/Speaker-wavLM-pro non-timbral embedding comparison.

Model architecture follows Orange's published spk_embeddings.py (CC-BY-SA-3.0):
https://huggingface.co/Orange/Speaker-wavLM-pro/blob/main/spk_embeddings.py
Weights must be downloaded locally; this module never calls paid inference APIs.
"""

from __future__ import annotations

import os
import threading
import wave
from array import array


MODEL_ID = "Orange/Speaker-wavLM-pro"
_model = None
_lock = threading.Lock()


def _load_model():
    global _model
    with _lock:
        if _model is not None:
            return _model
        import torch
        from huggingface_hub import snapshot_download
        from torch import nn
        from transformers.models.wavlm.modeling_wavlm import WavLMModel, WavLMPreTrainedModel

        class EmbeddingsModel(WavLMPreTrainedModel):
            def __init__(self, config):
                super().__init__(config)
                self.wavlm = WavLMModel(config)
                self.top_layers = nn.Module()
                self.top_layers.affine1 = nn.Conv1d(2048, config.top_interm_size, 1)
                self.top_layers.batchnorm1 = nn.BatchNorm1d(config.top_interm_size, affine=False, eps=1e-3)
                self.top_layers.affine2 = nn.Conv1d(config.top_interm_size, config.embd_size, 1)
                self.top_layers.batchnorm2 = nn.BatchNorm1d(config.embd_size, affine=False, eps=1e-3)

            def forward(self, input_values):
                values = (input_values - input_values.mean(dim=1, keepdim=True)) / input_values.std(dim=1, keepdim=True).clamp_min(1e-6)
                frames = self.wavlm(input_values=values).last_hidden_state
                stats = torch.cat((frames.mean(dim=1), frames.var(dim=1).clamp_min(1e-10).sqrt()), dim=1).unsqueeze(-1)
                top = self.top_layers
                hidden = top.batchnorm1(torch.relu(top.affine1(stats)))
                embedding = top.batchnorm2(torch.relu(top.affine2(hidden)))
                return nn.functional.normalize(embedding[:, :, 0], dim=1)

        local_path = os.getenv("HF_PROSODY_MODEL_DIR") or snapshot_download(MODEL_ID, local_files_only=True)
        _model = EmbeddingsModel.from_pretrained(local_path, local_files_only=True).eval()
        return _model


def _waveform(path: str):
    import torch

    with wave.open(path, "rb") as audio:
        if audio.getframerate() != 16000 or audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError("Expected 16 kHz mono PCM WAV")
        raw = audio.readframes(min(audio.getnframes(), 20 * 16000))
    samples = array("h")
    samples.frombytes(raw)
    if not samples:
        raise ValueError("Empty audio")
    return torch.tensor(samples, dtype=torch.float32).unsqueeze(0) / 32768


def compare_hf_prosody(reference_wav: str, learner_wav: str) -> dict:
    import torch

    model = _load_model()
    with _lock, torch.inference_mode():
        reference = model(_waveform(reference_wav))
        learner = model(_waveform(learner_wav))
        cosine = float((reference * learner).sum())
    return {"model": MODEL_ID, "cosine_similarity": round(cosine, 4), "calibrated_score": False}
