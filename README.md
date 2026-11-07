# KeltiaWave

Sept interfaces web autonomes, un backend FastAPI partagé. Android natif vit dans [le dépôt voisin](../keltiawave-mobile/README.md). Pour intervenir sur le code, commencer par [AGENTS.md](AGENTS.md) puis ouvrir uniquement la documentation du sujet.

## Applications et état actuel

| Application | Port local | Usage |
|---|---:|---|
| Portal | 4100 | Accueil et accès aux outils, statique |
| Corpus | 4200 | Komz/Listen, voix, comptes, validation |
| Learning | 4300 | Cours, vidéos, exercices |
| Record | 4400 | Enregistrement, Vosk/Whisper |
| Transcribe | 4500 | Fichiers audio/vidéo ; breton et gallois |
| Subtitles | 4600 | Création, calage, export de sous-titres |
| Live | 4800 | Son d’un onglet partagé, breton/Vosk ou gallois/W2V |

État documenté le **7 novembre 2026** :

- Transcribe gallois propose **W2V · Rapide** et **Whisper · Qualité**. W2V utilise les poids locaux du serveur, décodage CTC glouton, sans KenLM ni horodatages fins. [Détails W2V](backend/app/transcribe/README.md).
- Live web gallois est livré sur [le serveur de test](https://live.staging.keltiawave.com/) : blocs utiles de 4 s, contexte 1 s et délai de calcul. Whisper reste disponible après l’arrêt, dans la langue capturée. Une seule écoute galloise par processus ; arrêt explicite si le calcul ne suit plus. [Capture, API et limites](apps/live/README.md).
- Tous les moteurs web nécessitent le serveur et Internet. Le partage web dépend du navigateur et ne capture pas les autres apps d’un téléphone. Le Vosk breton hors ligne appartient à l’implémentation Android native.
- Le portail affiche Transcribe, Record, Subtitles et Live lorsque le gallois est sélectionné. Subtitles propose W2V ou Whisper ; le calage W2V est approximatif et à ajuster. Ces changements locaux ne confirment pas une livraison staging, production ou mobile.

## Komz et Listen : navigation par sous-domaines

Les deux parcours de `apps/corpus` partagent le nouvel explorateur : thèmes illustrés, sous-domaines, niveaux, recherche, traductions et pagination. Komz (`/lire`) propose l’enregistrement puis le score et la référence ; Listen (`/` ou `/home-bibliotheque`) permet d’écouter immédiatement, puis de répéter et comparer après l’écoute.

La vue classique reste accessible avec `?interface=classic`, avec une préférence distincte pour chaque parcours. [Fonctionnement et retour à la vue classique](docs/komz-interface.md).

## Architecture et stockage

Les fronts Angular communiquent avec le backend (`8100`) via `/api` sur leur propre origine (Nginx ou proxy Angular). Portal ne consomme pas d’API. Caddy termine HTTPS ; PostgreSQL et MinIO/S3 restent sur le réseau Docker privé. SQLite et stockage local suffisent en développement. Migrations Alembic appliquées au démarrage.

Les modèles restent hors Git : `backend/models/`, dont `wav2vec2-cy`. La calibration partagée de durée est dans `backend/data/transcription-calibration.json`, persistée par `backend_data` ; `TRANSCRIPTION_DEFAULT_RTF_*` initialise les profils. Les fichiers temporaires de transcription sont supprimés après traitement.

[Architecture Docker](docs/assets/architecture-docker-keltiawave.png) · [Backend](backend/README.md) · [Modèles](backend/models/README.md)

## Comptes, contributions et retours

Même compte web/mobile sur le serveur choisi ; rôles `learner`, `teacher`, `admin`, `contributor`. Staging et production ont des données/comptes distincts. Le nom de profil est modifiable ; mot de passe oublié = lien de réinitialisation par email.

Deux parcours à distinguer :

- **Corpus public** : les contributions gardent l’origine de la voix (nom du compte ou « Inconnu »), même pour un texte Common Voice. Komz/Listen utilisent la même référence approuvée la plus récente ; les autres audios restent conservés. Mon compte affiche les envois personnels et leur statut. Les envois anonymes ne sont pas rattachés automatiquement.
- **Travail pédagogique privé** : envoi depuis Komz mobile uniquement, suivi et retours dans Mon compte, correction web/mobile par professeur/admin. École → formation, « Non inscrit » par défaut ; sans professeur actif, administration. Une validation pédagogique ne publie pas dans le corpus. [Contrats et confidentialité](backend/README-practice.md).

[Corpus : imports, traductions et administration](docs/corpus-reference.md) · [Thèmes Komz](docs/komz-themes.md)

## Démarrage local

Prérequis : Python 3.11+, Node.js 20+, npm, FFmpeg ; dépendances W2V indiquées dans son README.

1. Copier `.env.example` vers `.env`, configurer les secrets ; ne jamais les versionner.
2. Installer/lier les modèles : [guide](backend/models/README.md), `./scripts/link-legacy-models.sh` si modèles anciens disponibles.
3. `./scripts/start-backend.sh`, puis `./scripts/start-<app>.sh` (`portal`, `corpus`, `learning`, `record`, `transcribe`, `subtitles`, `live`).
4. Ouvrir le port du front ; documentation API : <http://127.0.0.1:8100/docs>.

Ou, depuis **ce dépôt**, lancer toute la pile :

```sh
./start-docker.sh               # construit, démarre, contrôle, ouvre les pages
./start-docker.sh --no-build --no-browser
```

Les volumes `postgres_data`, `minio_data`, `backend_data` conservent les données. Éviter une ancienne copie du projet utilisant les mêmes ports. Le portail simplifié reste accessible sur <http://127.0.0.1:4100/portal-simple.html>.

## Vérification et livraison

Compiler uniquement le front modifié (`npm run build:<app>`) et exécuter les tests backend ciblés ; commandes dans [AGENTS.md](AGENTS.md). Terminer par `git diff --check`. Une modification documentaire ne nécessite pas de build.

Staging et production OVH sont deux piles indépendantes. Livraison à partir d’une révision Git commise/poussée, sauvegarde préalable, contrôles API/fronts/données/médias, retour arrière préparé. Révision serveur effective : `DEPLOYED_GIT_SHA`. Ne pas confondre code poussé, web déployé et APK installé.

```sh
SSH_TARGET=ubuntu@vps-dc75d8a6.vps.ovh.net DEPLOY_REF=TAG_EXPLICITE \
  ./scripts/deploy-staging-ovh.sh --apply
```

Lire [le guide OVH](deploy/ovh/README.md) avant de déployer, modifier Caddy ou copier des données. Le rafraîchissement du staging depuis la production remplace des données : il ne fait pas partie d’une livraison de code ordinaire. Historique : `docs/CHANGES-*`, à consulter uniquement si nécessaire.
