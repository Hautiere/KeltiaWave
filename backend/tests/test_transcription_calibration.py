import wave

from app.transcribe import calibration


def test_server_calibration_is_persisted_and_reused(tmp_path, monkeypatch):
    profile_path = tmp_path / "calibration.json"
    monkeypatch.setattr(calibration, "CALIBRATION_FILE", profile_path)

    initial = calibration.get_estimate("br", "fast", 100)
    assert initial["source"] == "server-default"
    assert initial["sample_count"] == 0

    observed = calibration.record_observation("br", "fast", 20, 100)
    assert observed is not None
    assert observed["source"] == "server-calibration"
    assert observed["real_time_factor"] == 0.2
    assert observed["sample_count"] == 1

    reused = calibration.get_estimate("br", "fast", 50)
    assert reused["estimated_seconds"] == 10
    assert reused["sample_count"] == 1


def test_wav_duration_is_measured_server_side(tmp_path):
    audio_path = tmp_path / "sample.wav"
    with wave.open(str(audio_path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 32000)

    assert calibration.wav_duration_seconds(str(audio_path)) == 2.0
