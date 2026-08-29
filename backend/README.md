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

`BOOTSTRAP_CLASS_USERS=true` crée les profils de démonstration du staging. En
production, `DISABLE_TEST_ACCOUNTS=true` désactive les comptes `@keltia.test`
après le clonage, sans supprimer leurs contributions. `BOOTSTRAP_ADMIN_*` crée
ou réactive le véritable administrateur de l'installation.

Le traitement vocal nécessite FFmpeg et les modèles décrits dans
`models/README.md`. La santé du service est disponible sur `/healthz` et Swagger
sur `/docs`.
