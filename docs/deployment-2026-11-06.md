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
