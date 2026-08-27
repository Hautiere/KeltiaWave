# KeltiaWave Transcribe frontend

Frontend Angular autonome pour la transcription de fichiers audio et vidéo.

```bash
./start_transcribe_frontend.sh
```

Interface : `http://127.0.0.1:4500`
API commune : `http://127.0.0.1:8100/api/transcribe`

L’ancienne page `public-frontend/transcribe.html` reste présente pendant la phase de validation.

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
