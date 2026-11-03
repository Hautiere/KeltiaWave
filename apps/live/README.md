# KeltiaWave Live

Front Angular autonome pour suivre en direct un podcast breton (Vosk) ou gallois (W2V), avec le backend
commun. Démarrage : `./scripts/start-live.sh` depuis la racine,
puis ouvrir <http://127.0.0.1:4800>. Le backend doit écouter sur le port 8100 et
disposer du modèle Vosk breton. Les appels HTTP et WebSocket passent par le même hôte que le front : Nginx
en Docker, `proxy.conf.json` avec `npm start`. Aucun ajout CORS n’est nécessaire
pour Live. Le port 4700 reste réservé au mobile.

## Utilisation et limites

1. Ouvrir le podcast dans un autre onglet.
2. Cliquer sur « Démarrer Live », sélectionner cet onglet et activer le partage
   de son audio dans le sélecteur du navigateur.
3. Lancer le podcast et revenir lire la transcription dans Live.

Le partage utilise `getDisplayMedia` et nécessite HTTPS ou localhost. La prise
en charge audio varie selon le navigateur, le système et la source. Un partage
sans piste audio est refusé avec une explication. Il n’y a aucun repli vers le
microphone. Cette version ne capture pas les autres applications d’un téléphone.
Le navigateur exige aussi une piste vidéo : Live la garde ouverte pour maintenir
la session, mais ne la lit et ne la transmet jamais.

Contrairement au Vosk local du mobile, Vosk s’exécute ici **sur le serveur** :
une connexion Internet est nécessaire. Live ne conserve pas durablement le son ni la transcription sur le serveur.
Pour proposer Whisper après l’écoute, un enregistrement compressé est gardé en
mémoire dans la page, sans vidéo, en respectant les pauses. Il est supprimé à
la prochaine écoute ou au rechargement. Le bouton « Améliorer avec Whisper »
envoie cet audio au serveur ; le fichier temporaire est supprimé après traitement.
Le résultat est affiché dans une seconde version, sans écraser Vosk. Une erreur
Whisper conserve le texte et permet de réessayer. La taille audio est plafonnée
à 64 Mio ou à la limite serveur si elle est inférieure ; dépasser ce plafond
désactive Whisper pour cette session sans arrêter Vosk. Le texte reste dans la page jusqu’au rechargement ou au démarrage
réussi d’une nouvelle écoute. Télécharger et partager restent possibles
après une coupure. La première interface est en français ; la reconnaissance est
en breton ou en gallois. Les mots provisoires sont surlignés.

Sélectionner Gallois active W2V : résultats par blocs utiles de quatre secondes,
avec une seconde de contexte et un délai de calcul serveur. Le dernier bloc est
finalisé à l’arrêt. Une seule écoute galloise est admise par processus ; une file
bornée interrompt explicitement une écoute si le serveur ne suit plus. Le modèle
local `wav2vec2-cy` et ses dépendances sont ceux de Transcribe (voir
`backend/app/transcribe/README.md`). Whisper reçoit la langue de l’audio capturé.

Pause suspend l’envoi d’audio, sans mettre en pause le podcast. Arrêter coupe le
partage et attend les derniers mots du serveur. La session est limitée à une heure.

## API indépendante

- `GET /api/live/capabilities` : modèles Vosk/Whisper disponibles, format, traitement serveur et limites.
- `POST /api/live/improve` : fichier `audio_file` de la session, reconnaissance
  Whisper via le service partagé, champ `language` (`br` par défaut ou `cy`). Aucune réécriture à partir du texte seul.
- `WS /api/live/stream` : JSON `{ "type": "start", "sample_rate": 48000,
  "language": "br" }` (`cy` pour W2V), puis blocs binaires PCM16 mono little-endian à la fréquence
  réelle de l’AudioContext. Les blocs ne dépassent pas 64 Kio.
- Événements serveur : `ready`, `partial`, `final`, `error`, `done`.
- `{ "type": "stop" }` finalise la reconnaissance. `ping` / `pong` maintient
  la connexion pendant les pauses. Quatre sessions au maximum par processus serveur.

Le traitement Vosk réutilise `backend/app/vosk_utils.py`, sans importer les routes
de Record. Le service Whisper est partagé avec Record, Transcribe et Subtitles.

## Vérification et déploiement

`npm run build:live` à la racine ; `npm --prefix apps/live test` pour le traitement
PCM ; `backend/.venv/bin/python -m pytest backend/tests/test_live.py backend/tests/test_live_wav2vec2.py -q` pour l’API.
Le service Docker `live` expose 4800 en local et 14800 pour le slot OVH candidat.
Les configurations Caddy préparent `live.keltiawave.com` et
`live.staging.keltiawave.com` (avec l’authentification staging existante).
Il faut créer les entrées DNS avant une publication ; ces fichiers ne déploient rien.

À vérifier manuellement avec un podcast réel : autorisation et refus, partage sans
son, texte breton, pause/reprise, retour au direct après défilement, arrêt du partage
depuis le navigateur, coupure réseau, export et affichage mobile.

Références navigateur :
- https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia
- https://developer.chrome.com/docs/web-platform/screen-sharing-controls

La capture demande `systemAudio: "include"` et suggère le partage d’écran.
Le navigateur reste libre de proposer ou non le son système selon la plateforme.
Le sélecteur et l’autorisation à chaque session ne peuvent pas être supprimés
par le site. En l’absence de son système, partager l’audio de l’onglet du podcast.

## Interface et progression Whisper

L’en-tête reprend le portail et la mascotte de Transcribe. Sous le texte, trois
boutons bleus proposent Whisper, Enregistrer et Partager. Whisper reste facultatif :
il retranscrit l’audio pour proposer une seconde version ponctuée et plus lisible,
sans remplacer le texte Vosk. La progression distingue l’envoi réel du fichier
et le traitement estimé à partir de `/api/transcribe/estimate`. Si l’estimation
est dépassée ou indisponible, une barre animée et le temps écoulé restent visibles
jusqu’au résultat ; le pourcentage estimé ne confirme jamais la fin du traitement.

La carte Live du portail utilise un rose poudré distinct des autres applications.
