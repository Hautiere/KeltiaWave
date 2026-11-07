# KeltiaWave Record

Frontend Angular autonome consacré à l'enregistrement vocal. Il est déployé en
production sur `https://record.keltiawave.com` et en staging sur
`https://record.staging.keltiawave.com`.

## Lancement

Depuis la racine du dépôt :

```bash
./scripts/start-backend.sh
./scripts/start-record.sh
```

- frontend Record : `http://127.0.0.1:4400`
- backend partagé : `http://127.0.0.1:8100`
- documentation API : `http://127.0.0.1:8100/docs`

## Parcours

1. choisir breton ou gallois et le microphone ;
2. enregistrer et réécouter l'audio ;
3. corriger le brouillon produit en direct : Vosk en breton, W2V en gallois ;
4. lancer facultativement l'amélioration Whisper ;
5. télécharger le texte ou l'audio.

L'interface conserve côte à côte les versions directes et Whisper après
amélioration. L'utilisateur peut corriger puis sauvegarder Vosk/W2V, Whisper ou les
deux versions. Une progression estimée accompagne le traitement Whisper.

Le header autonome contient uniquement le sélecteur `FR / EN / BR / CY` et le
lien **Autres outils** vers `https://keltiawave.bzh`. Le footer commun affiche
l'adresse Hautiere prod, la signature **Brezhoneg gant Fañch** et l'adresse de
contact.

Le direct web nécessite Internet pour les deux langues. En gallois, W2V traite
les blocs utiles de quatre secondes avec un délai serveur. L’arrêt attend le
dernier résultat ; Whisper reste facultatif et utilise la langue de l’audio
capturé, même si le choix de langue est ensuite modifié.

## Isolation

Le frontend utilise uniquement :

```text
GET       /api/record/capabilities
POST      /api/record/transcribe
POST      /api/record/improve
WEBSOCKET /api/record/live  (breton)
WEBSOCKET /api/live/stream  (gallois)
```

Les appels passent par la même origine que le front : Nginx en Docker,
`proxy.conf.json` avec `npm start`.

Il ne dépend pas des routes de sous-titrage. Les médias restent dans le
navigateur après le traitement et ne sont pas ajoutés automatiquement au
corpus.

## Validation et déclinaison mobile

Les contrôles fonctionnels prioritaires sont :

- capture Chrome, Firefox et Safari sous HTTPS ;
- sélection du microphone ;
- brouillon direct breton et gallois ;
- transcription Whisper bretonne et galloise ;
- nettoyage de la phrase parasite finale ;
- réécoute et téléchargements ;
- affichage mobile ;
- configuration de production et supervision des erreurs.

Record est la première application retenue pour une PWA mobile. L'objectif est
de conserver cette interface responsive et ce backend, puis d'ajouter une
installation plein écran avec icône, manifest et service worker. Cette étape est
planifiée mais pas encore implémentée.

Tests simulés de session : `npm --prefix apps/record test`. Build : `npm run build:record`.
