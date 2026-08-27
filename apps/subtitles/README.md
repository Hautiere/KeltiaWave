# KeltiaWave Subtitles

Frontend Angular autonome pour générer, synchroniser, éditer et exporter des sous-titres.

```bash
./start_backend.sh
./start_subtitles_frontend.sh
```

- Interface : `http://127.0.0.1:4600`
- API dédiée : `POST http://127.0.0.1:8100/api/subtitles/transcribe`

L’ancienne page `public-frontend/studio.html` reste disponible pendant la validation.

## Atelier

- import d'un média ou d'un fichier SRT ;
- choix du breton ou du gallois ;
- cartes moteur harmonisées avec Transcribe : Vosk rapide et Whisper précis ;
- génération par l'API spécialisée avec progression de chargement et estimation
  du traitement ;
- prévisualisation des sous-titres sur la vidéo ;
- modification des timecodes et du texte dans une matrice ;
- surlignage bleu de la ligne active ;
- réglage du nombre de caractères, de lignes et de la durée maximale ;
- export SRT.

La vue ordinateur reste contenue dans la hauteur de la fenêtre. Le panneau de
réglages et la matrice possèdent leurs propres ascenseurs, tandis que le footer
commun KeltiaWave reste visible. Le header propose uniquement la langue de
l'interface et **Autres outils** vers `https://keltiawave.bzh`.
