# KeltiaWave Record

Frontend Angular autonome consacré à l'enregistrement vocal. Il fonctionne en
parallèle des interfaces historiques et ne les remplace pas encore.

## Lancement

Depuis la racine du dépôt :

```bash
./start_backend.sh
./start_record_frontend.sh
```

- frontend Record : `http://127.0.0.1:4400`
- backend partagé : `http://127.0.0.1:8100`
- documentation API : `http://127.0.0.1:8100/docs`

## Parcours

1. choisir breton ou gallois et le microphone ;
2. enregistrer et réécouter l'audio ;
3. en breton, corriger le brouillon Vosk produit en direct ;
4. lancer facultativement l'amélioration Whisper ;
5. télécharger le texte ou l'audio.

L'interface conserve côte à côte les versions Vosk et Whisper après
amélioration. L'utilisateur peut corriger puis sauvegarder Vosk, Whisper ou les
deux versions. Une progression estimée accompagne le traitement Whisper.

Le header autonome contient uniquement le sélecteur `FR / EN / BR / CY` et le
lien **Autres outils** vers `https://keltiawave.bzh`. Le footer commun affiche
l'adresse Hautiere prod, la signature **Brezhoneg gant Fañch** et l'adresse de
contact.

Whisper est présenté comme une amélioration après le brouillon breton. En
gallois, où le direct Vosk n'est pas proposé, il génère le premier texte après
l'enregistrement.

## Isolation

Le frontend utilise uniquement :

```text
GET       /api/record/capabilities
POST      /api/record/transcribe
POST      /api/record/improve
WEBSOCKET /api/record/live
```

Il ne dépend pas des routes de sous-titrage. Les médias restent dans le
navigateur après le traitement et ne sont pas ajoutés automatiquement au
corpus.

## Validation avant remplacement

Ne supprimer `public-frontend/record.*` et l'ancien composant Angular Record
qu'après validation des points suivants :

- capture Chrome, Firefox et Safari sous HTTPS ;
- sélection du microphone ;
- brouillon direct breton ;
- transcription Whisper bretonne et galloise ;
- nettoyage de la phrase parasite finale ;
- réécoute et téléchargements ;
- affichage mobile ;
- configuration de production et supervision des erreurs.
