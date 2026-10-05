# Backend KeltiaWave

API FastAPI unique partagée par les cinq applications :

- Corpus, authentification et administration : `/api/auth`, `/api/phrases`,
  `/api/audios`, `/api/admin-data` ;
- Learning : `/api/learning` ;
- Record : `/api/record` ;
- Transcribe : `/api/transcribe` ;
- Subtitles : `/api/subtitles` ;
- disponibilité des moteurs : `/api/transcription/models/status`.

Corpus et Learning partagent SQLAlchemy, les utilisateurs, les rôles et les
jetons d'accès. Les tables Learning sont versionnées par Alembic. La commande
`python -m app.bootstrap_db` initialise d'abord les tables communes nécessaires
aux clés étrangères Learning sur une installation neuve.

Le stockage est local par défaut. En production, `AUDIO_STORAGE=s3` active le
stockage MinIO/S3 pour les audios Corpus et les médias Learning. Consultez
`.env.example` à la racine pour la configuration complète.

Les fichiers audio utilisateur reçoivent une clé unique contenant l'identifiant
de phrase et un UUID. Les médias Learning sont servis avec prise en charge des
requêtes HTTP Range, indispensable à la navigation dans les vidéos.

`BOOTSTRAP_CLASS_USERS=true` crée et maintient actifs les profils publics de
démonstration élève et professeur. L'ancien compte
`learning.admin@keltia.test` reste désactivé : `BOOTSTRAP_ADMIN_*` crée ou
resynchronise le compte administrateur privé (mot de passe et nom affiché), puis
réactive le véritable administrateur de l'installation. Une installation qui
ne doit exposer aucun compte de test peut utiliser `DISABLE_TEST_ACCOUNTS=true`.

Le traitement vocal nécessite FFmpeg et les modèles décrits dans
`models/README.md`. La santé du service est disponible sur `/healthz` et Swagger
sur `/docs`.

# Analyse locale du rythme

`POST /api/transcribe/rhythm` accepte un fichier `audio_file` (WAV, MP3 ou autre format audio pris en charge par le backend). Le champ facultatif `reference_file` ajoute une comparaison avec une voix de référence :

```sh
curl -F audio_file=@learner.wav -F reference_file=@reference.mp3 http://127.0.0.1:8100/api/transcribe/rhythm
```

La réponse contient la durée parlée, les pauses, un contour d'intensité normalisé et des pics de relief acoustique pour chaque audio. Avec une référence, elle ajoute `rhythm_score`, `pace_score`, `pause_score` et `emphasis_score` (0 à 100). L'algorithme aligne les contours avec une déformation temporelle limitée. Si les poids sont présents dans le cache local, `hf_prosody.cosine_similarity` donne aussi la similarité globale du modèle libre [Orange/Speaker-wavLM-pro](https://huggingface.co/Orange/Speaker-wavLM-pro) (licence CC-BY-SA-3.0). La route ne fait appel à aucun service distant payant ; si le modèle manque, `hf_prosody` vaut `null`. Ces nombres sont expérimentaux, pas une note validée de prononciation ou de placement de l'accent tonique. Les clips sont limités à 30 secondes.

Pour installer une fois les poids dans le volume local :

```sh
docker compose --env-file .env -f deploy/docker-compose.yml -p deploy exec -T backend python -c "from huggingface_hub import snapshot_download; snapshot_download('Orange/Speaker-wavLM-pro', allow_patterns=['config.json', 'model.safetensors'])"
```

Le service utilise `HF_HOME=/app/data/hf-cache` dans Docker Compose. Le modèle ajoute environ 1,27 Go de poids et les dépendances PyTorch alourdissent fortement l'image backend.
