# KeltiaWave Transcribe frontend

Frontend Angular autonome pour la transcription de fichiers audio et vidéo.

```bash
./scripts/start-backend.sh
./scripts/start-transcribe.sh
```

Interface : `http://127.0.0.1:4500`
API commune : `http://127.0.0.1:8100/api/transcribe`

Déploiements publics :

- production : `https://transcribe.keltiawave.com` ;
- staging : `https://transcribe.staging.keltiawave.com`.

Le domaine historique `transcription.keltiawave.com` reste compatible.

## Fonctionnement

- sélection d'interface `FR / EN / BR / CY` ;
- transcription bretonne rapide avec Vosk sélectionnée par défaut ;
- transcription de qualité avec Whisper pour le breton et le gallois ;
- progression distincte du chargement du fichier et estimation du traitement ;
- estimation partagée et persistante côté serveur, adaptée automatiquement à
  la machine locale ou OVH dès la première transcription de chaque navigateur ;
- indicateur animé pendant le travail ;
- résultat éditable et téléchargeable ;
- lien **Autres outils** vers `https://keltiawave.bzh`.

Sur ordinateur, la page occupe la fenêtre sans scrollbar globale. Le footer
commun KeltiaWave reste visible et reprend l'adresse Hautiere prod, la signature
**Brezhoneg gant Fañch** et l'adresse de contact.
