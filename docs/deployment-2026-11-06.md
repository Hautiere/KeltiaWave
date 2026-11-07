# Livraison web et enrichissement Komz du 6 novembre 2026

## Périmètre préparé

- Record : gallois W2V en direct, amélioration Whisper facultative, attente de
  finalisation et langue de l’audio conservée ; appels via l’origine frontend.
- Live : présentation harmonisée avec Record, partage audio navigateur conservé.
- Vues téléphone Record/Transcribe/Live/Komz : navigation, icône vague, drapeau
  audio et langue d’interface séparés, cartes et actions adaptées jusqu’à 700 px.
- Backend : installation Torch CPU explicite pour les images d’inférence.
- Komz : archive ciblée de 650 phrases Common Voice bretonnes, leurs 650 MP3 et
  1 950 traductions proposées FR/EN/CY. Voir `komz-common-voice-2026-11-06.md`.

Les audios, exports, modèles et secrets restent hors Git. L’archive Bibliothèque
`../datasets/exports/common_voice_komz_additions_2026-11-06/library-additions-650.zip`
est produite par `backend/scripts/export_common_voice_selection.py` à partir des
seuls identifiants du nouveau lot. Le format Bibliothèque vérifie les conflits
avant toute écriture et ne met pas à jour les phrases préexistantes.

## Procédure conservant les données de production

La pile publique existante utilise le projet Compose `keltiawave-production`,
la source `releases/production` et les volumes propres de production. Ne pas
utiliser `deploy-production-candidate-ovh.sh` pour cette mise à jour : ce wrapper
clone le staging et remplacerait les données de destination.

1. Sauvegarder PostgreSQL, MinIO, les données backend, la source et le routage.
2. Capturer les empreintes des lignes existantes avec
   `backend/scripts/audit_existing_rows.py capture SNAPSHOT.json`.
3. Déployer une révision commise et poussée sur staging, sans copie de données
   locales ; tester le nouvel import ciblé et les services.
4. Mettre à jour le code production en réutilisant les mêmes volumes, sans
   clonage ni restauration d’une base locale/staging. Préserver les secrets et
   les paramètres propres à chaque slot.
5. Simuler l’import Bibliothèque ciblé ; n’appliquer qu’un plan sans conflit.
6. Vérifier les empreintes de toutes les lignes existantes, les nouveaux médias,
   les traductions, les leçons/vidéos, les modèles et les domaines publics.

Les changements de schéma de cette version sont additifs. L’audit projette les
colonnes présentes avant livraison pour contrôler leurs valeurs même quand de
nouvelles colonnes sont ajoutées. Il n’affiche aucune donnée de ligne. En cas de
ligne existante modifiée ou supprimée, arrêter et enquêter avant de poursuivre.

Un nouveau service Live production peut nécessiter l’ajout de son seul bloc de
routage public. Sauvegarder et valider le fichier réellement chargé par Caddy ;
préserver les autres routes et l’authentification staging. Ne pas remplacer le
Caddyfile actif par un template complet du dépôt.

## Vérifications avant livraison

Builds ciblés Record, Transcribe, Live et Corpus réussis. Corpus conserve ses
avertissements de budget initial et d’inlining de la feuille mobile chargée comme
asset. Les tests front Record/Live/Corpus passent (26 tests) ; les suites backend
import de traductions, Bibliothèque, Live, W2V et retours privés passent
(81 tests). Trois tests supplémentaires vérifient l’audit des lignes existantes.
Les parcours d’affichage locaux FR/EN/CY ont été contrôlés. Les traductions
restent des propositions à relire ; une écoute galloise réelle n’est pas déduite
de ces tests simulés.

La simulation en lecture seule sur la production existante a retrouvé 650
phrases et 650 audios à créer, zéro correspondance préexistante, zéro conflit
et zéro erreur. SHA-256 de l’archive ciblée :
`da7bdd40ce4f7f13611d7cc435313601b3023dbc0feec1db5c1fcfa03ad60ca8`.

Pour préserver également les profils et mots de passe des comptes existants,
la mise à jour production utilise les deux fichiers Compose :

```sh
docker compose --env-file /home/ubuntu/apps/keltiawave/shared/.env.production \
  -f deploy/ovh/docker-compose.candidate.yml \
  -f deploy/ovh/production-preserve-users.yml up -d
```

Le second fichier désactive les initialisations/réinitialisations de comptes au
démarrage ; il conserve la configuration d’authentification normale et les
comptes présents. Le port Live propre à la production est `24800`, lié à
`127.0.0.1`, pour conserver le port `14800` du staging.

## Compatibilité du stockage vérifiée sur staging

Le test d’import réel a détecté que le modèle de service du SDK boto3 épinglé
ne connaît pas encore l’argument `IfNoneMatch` de `PutObject`. La transaction
staging a été annulée. `TransferStorage` transmet désormais la même condition
HTTP `If-None-Match: *` via le [hook public avant appel de
boto3](https://docs.aws.amazon.com/boto3/latest/guide/events.html#before-call)
lorsque cet argument n’est pas pris en charge. Les clients récents conservent
l’argument natif. Il n’y a aucun repli vers une écriture sans condition.
Le client est propre au transfert ; les autres envois audio sont inchangés.
Un test avec le vrai sérialiseur et le signataire botocore vérifie que cet en-tête
est présent et signé, sans requête réseau. Les 41 tests Bibliothèque passent.

## Résultat de la livraison production

La version applicative `7969fdbf308d6dedca87ba7d81da324c1e215722` a été
validée sur staging puis livrée en production par promotion des mêmes images.
Les fichiers source du tag ont été vérifiés par SHA-256. La livraison conserve
les volumes production et applique la protection des comptes décrite ci-dessus.

L’import réel a ajouté exactement 650 phrases et 650 audios. La simulation
suivante retrouve les 650 associations et ne propose aucun ajout. Le contrôle
HTTP des 650 nouveaux médias à travers le frontend a renvoyé 650 réponses 200 et
650 SHA-256 conformes ; 650 traductions FR, EN et CY sont présentes.

L’audit des 12 tables présentes avant livraison retrouve toutes leurs anciennes
lignes, avec zéro modification et zéro suppression :

| Données | Avant | Après | Lignes anciennes modifiées/supprimées |
| --- | ---: | ---: | ---: |
| Comptes | 16 | 16 | 0 |
| Phrases | 786 | 1 436 | 0 |
| Audios | 703 | 1 353 | 0 |
| Leçons Learning | 5 | 5 | 0 |
| Vidéos Learning | 5 | 5 | 0 |
| Validations audio | 6 | 6 | 0 |

Les sauvegardes vérifiées sont conservées sur le VPS dans
`shared/backups/production/pre-web-20261106-e0614db/` : PostgreSQL, MinIO,
données backend, source, images, routage et rapports d’audit. Les anciens fichiers
source restent dans `releases/production-pre-web-20261106`. Aucun secret ni média
utilisateur n’a été transféré dans Git.

La route `live.keltiawave.com` a été ajoutée au fichier Caddy actif. Une comparaison
structurelle confirme la conservation de toutes les routes et journalisations
préexistantes. Les fichiers hôte et conteneur sont identiques après rechargement.
Les huit domaines publics répondent HTTP 200 : portail, Komz, Voices, Learning,
Record, Transcribe, Subtitles et Live. Les vidéos conservent la lecture Range de
1 024 octets. Record affiche W2V lorsqu’on choisit le gallois ; Record et Live à
393 px ne présentent ni débordement horizontal ni image cassée.

Les flux breton et gallois ont été vérifiés avec un silence synthétique à travers
le proxy frontend en production. Le navigateur public a également reçu
`ready`, `final`, puis `done` via `wss://live.keltiawave.com/api/live/stream` en
gallois. Ces contrôles vérifient le transport et le moteur ; ils ne constituent
pas un test de qualité sur une prise de parole galloise réelle.

Le commit final de documentation ne modifie pas les images applicatives : la
révision applicative ci-dessus reste celle des images promues.
