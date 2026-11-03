# Transcribe : W2V gallois

`wav2vec2.py` charge `backend/models/wav2vec2-cy` (ou `W2V_CY_MODEL_PATH`, sous `MODELS_ROOT` en Docker). Installer `requirements.txt` + `requirements-prosody.txt` pour les dépendances Torch/Transformers. Les poids et données du modèle restent exclus de Git.

POST `/api/transcribe/transcribe_w2v_wel_metrics`, multipart `audio_file`. Normalisation FFmpeg mono PCM16 16 kHz, modèle Safetensors en lecture locale uniquement, calcul CPU en tâche de fond sérialisée. Fenêtres utiles 16 s avec 2 s de contexte ; identifiants CTC assemblés avant décodage glouton. Le KenLM fourni n’est pas utilisé. Ce point d’entrée produit un segment global, sans horodatages fins. Live réutilise le modèle avec des blocs utiles de 4 s et 1 s de contexte, via `backend/app/live/wav2vec2_stream.py` ; les mots CTC sont assemblés entre blocs.

Réponse compatible Transcribe : `filename`, `text`, `segments`, `metrics` (`engine=wav2vec2`, `lang=cy`, `model_id=wav2vec2-cy`, `decoder=greedy-ctc`). `/estimate?lang=cy&mode=fast` utilise une calibration séparée `wav2vec2:cy`. Configuration initiale RTF : `TRANSCRIPTION_DEFAULT_RTF_W2V_CY`, ajustée après mesures.

Tests : `backend/.venv/bin/python -m pytest backend/tests/test_wav2vec2.py backend/tests/test_transcription_calibration.py -q`. Vérification réelle à compléter avec de la parole galloise : le test technique sur silence vérifie le chargement, pas l’exactitude de reconnaissance.
