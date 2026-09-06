# KeltiaWave Subtitles

Frontend Angular autonome pour générer, synchroniser, éditer et exporter des sous-titres.

```bash
./scripts/start-subtitles.sh
```

- Cette commande unique démarre le backend et l'interface, attend qu'ils soient
  disponibles, puis ouvre leurs deux URL dans le navigateur. `Ctrl+C` arrête les
  services lancés par le script.
- Interface : `http://127.0.0.1:4600`
- API dédiée : `POST http://127.0.0.1:8100/api/subtitles/transcribe`

Déploiements publics :

- production : `https://subtitles.keltiawave.com` ;
- staging : `https://subtitles.staging.keltiawave.com`.

L'ancien lien `transcription.keltiawave.com/studio.html` redirige vers la
nouvelle application.

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

Sur mobile, le parcours est réorganisé autour de l'action principale : choix du
média, aperçu 16:9, sélecteurs compacts de langue et de moteur, génération puis
édition. Les sous-titres superposés utilisent une taille adaptative et les
colonnes Début/Fin sont resserrées afin de privilégier le texte.
