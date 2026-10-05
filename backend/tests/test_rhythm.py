import io
import math
import struct
import wave

from app.transcribe.rhythm_analysis import analyze_wav, compare_rhythm


def sample_wav(gain=1.0, extra_pause=False, frequency=180, second_stress=1.0):
    samples = []
    for segment, (on, duration) in enumerate([(True, 0.28), (False, 0.18 if extra_pause else 0.12), (True, 0.32)]):
        for i in range(round(duration * 16000)):
            stress = second_stress if segment == 2 else 1.0
            sample = gain * stress * 0.3 * math.sin(2 * math.pi * frequency * i / 16000) if on else 0
            samples.append(round(sample * 32767))
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return output.getvalue()


def test_rhythm_profile_and_gain_invariance(tmp_path):
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    higher_voice = tmp_path / "higher.wav"
    slower = tmp_path / "slower.wav"
    shifted_stress = tmp_path / "shifted_stress.wav"
    first.write_bytes(sample_wav())
    second.write_bytes(sample_wav(gain=0.45))
    higher_voice.write_bytes(sample_wav(frequency=250))
    slower.write_bytes(sample_wav(extra_pause=True))
    shifted_stress.write_bytes(sample_wav(second_stress=0.35))
    baseline = analyze_wav(str(first))
    quiet = analyze_wav(str(second))
    higher = analyze_wav(str(higher_voice))
    delayed = analyze_wav(str(slower))
    less_emphasis = analyze_wav(str(shifted_stress))
    assert len(baseline["pauses"]) == 1
    assert len(baseline["energy_contour"]) == 64
    assert compare_rhythm(baseline, quiet)["rhythm_score"] >= 95
    assert compare_rhythm(baseline, higher)["rhythm_score"] >= 95
    assert compare_rhythm(baseline, delayed)["rhythm_score"] < compare_rhythm(baseline, quiet)["rhythm_score"]
    assert compare_rhythm(baseline, less_emphasis)["emphasis_score"] < compare_rhythm(baseline, quiet)["emphasis_score"]
    assert compare_rhythm(baseline, quiet)["pitch_used"] is False


def test_rhythm_route_accepts_reference(client):
    sample = sample_wav()
    response = client.post(
        "/api/transcribe/rhythm",
        files={
            "audio_file": ("learner.wav", sample, "audio/wav"),
            "reference_file": ("reference.wav", sample, "audio/wav"),
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["comparison"]["rhythm_score"] >= 95


def test_rhythm_route_includes_hf_similarity(client, monkeypatch):
    from app.transcribe import rhythm_routes

    monkeypatch.setattr(rhythm_routes, "compare_hf_prosody", lambda _a, _b: {
        "model": "Orange/Speaker-wavLM-pro", "cosine_similarity": 0.8, "calibrated_score": False,
    })
    sample = sample_wav()
    response = client.post(
        "/api/transcribe/rhythm",
        files={"audio_file": ("learner.wav", sample, "audio/wav"), "reference_file": ("reference.wav", sample, "audio/wav")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["hf_prosody"]["cosine_similarity"] == 0.8


def test_rhythm_route_rejects_silence(client):
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 8000)
    response = client.post("/api/transcribe/rhythm", files={"audio_file": ("silent.wav", output.getvalue(), "audio/wav")})
    assert response.status_code == 422
