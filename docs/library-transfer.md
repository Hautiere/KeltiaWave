# Transfert de Bibliothèque — format ZIP v1

Le moteur `backend/app/library_transfer.py` transfère les collections Phrase,
Audio et AudioValidation, avec leurs fichiers, entre deux bases au schéma actuel.
Il ne crée pas de tables et ne nécessite aucune migration. Il n'ajoute aucune API.
Les comptes et les autres collections ne font pas partie de cet export.
`scripts/corpus/push_phrases.py` reste un client éditorial indépendant.

## Commandes

Depuis `backend`, avec la configuration habituelle de la base et du stockage :

```sh
.venv/bin/python -m scripts.export_corpus_dataset --format library --output /chemin/bibliotheque-v1.zip
.venv/bin/python -m scripts.import_corpus_dataset /chemin/bibliotheque-v1.zip --dry-run
.venv/bin/python -m scripts.import_corpus_dataset /chemin/bibliotheque-v1.zip --apply
```

Configurer la base et le stockage source pour l'export, puis ceux de destination
pour la simulation et l'import. Le schéma de destination doit déjà exister.
L'import ZIP est une simulation par défaut ; seul `--apply` écrit.
La simulation lit les fichiers nécessaires aux correspondances mais ne crée ni
lignes, ni fichiers, ni répertoire de stockage.

L'export v1 porte sur toute la Bibliothèque : les filtres `--dataset`, `--status`,
`--limit` et `--skip-missing` ne sont pas acceptés. Un fichier manquant fait échouer
l'export plutôt que produire une sauvegarde incomplète. Un ZIP existant n'est
jamais remplacé ; un export partiel est supprimé en cas d'échec.

Les anciens exports CSV/JSON et imports CSV/JSON conservent leur comportement.
Attention : leur import historique écrit directement, contrairement à l'import
ZIP. `--dry-run` est donc explicitement refusé pour ces anciens formats.
Un manifest versionné seul n'est pas traité comme un ancien JSON : fournir le ZIP.

## Manifest

Le ZIP contient `manifest.json` (UTF-8), et uniquement les fichiers référencés :

```json
{
  "format": "keltiawave-library",
  "manifest_version": 1,
  "export_id": "UUID",
  "exported_at": "2026-09-21T10:00:00",
  "phrases": [],
  "audios": [],
  "audio_validations": [],
  "files": []
}
```

- `phrases` : `id`, `texte`, `traduction_fr`, `theme`, `niveau`, `source`,
  `source_url`, `langue`, `auteur`, `url_audio`, `created_at`,
  `url_audio_audio_id`. Les phrases sans audio sont incluses.
- `audios` : `id`, `phrase_id`, `file`, `origin`, `status`, `phrase_source`,
  `domain`, `speaker_region`, `speaker_city`, `speaker_accent`, `speaker_level`,
  `created_at`, `validated_at`, `validated_by`, `validator_role`,
  `validation_weight`, `validation_comment`, `contributor_name`,
  `contributor_email`, `contributor_school`, `contributor_school_level`.
- `audio_validations` : `id`, `audio_id`, `decision`, `validator`,
  `validator_role`, `validation_weight`, `pronunciation_level`,
  `pronunciation_region`, `comment`, `created_at`.
- `files` : `path`, `sha256`, `size`. `path` et `audios[].file` utilisent
  `audios/<sha256>.<extension>` ; une extension inutilisable devient `bin`.

Les identifiants servent aux relations internes du manifest ; la destination
attribue ses propres identifiants. Le chemin physique `Audio.filename` est
reconstruit dans le stockage cible. Les références locales `Phrase.url_audio`
reconnues sont remappées grâce à `url_audio_audio_id`. Une référence locale
introuvable ou ambiguë bloque l'export. Les URL HTTP(S) sont conservées sans
être téléchargées.

Les valeurs `null`, chaînes et dates ISO avec microsecondes sont conservées ;
les dates suivent la convention actuelle du backend (UTC sans fuseau stocké).
Ce transfert conserve les données historiques : il ne réapplique pas les règles
éditoriales pour normaliser les textes ou leur provenance.
L'état d'un Audio et son historique sont distincts : aucun événement de validation
n'est fabriqué à partir du statut ou de l'origine. Les événements répétés sont
conservés avec leur multiplicité.

## Correspondances et conflits

La simulation retourne `create`, `existing` (compteurs pour chaque collection),
`conflicts` et `errors`. Une erreur structurelle ou d'intégrité interrompt la
lecture avec une erreur explicite. Un conflit ou une erreur bloque tout l'import,
y compris avec `--apply` ; aucun sous-ensemble n'est appliqué.

- Phrase : texte exact + langue, puis égalité des métadonnées exportées.
- Audio : phrase correspondante + SHA-256, puis égalité des métadonnées et de
  l'historique complet.
- AudioValidation : contenu de l'événement, dates comprises, avec multiplicité.

Une divergence ou une correspondance ambiguë produit `CONFLICT`. Aucune correction
existante n'est écrasée. Les dates font partie de la comparaison. Deux objets
entièrement identiques pouvant correspondre au même élément sont volontairement
considérés comme ambigus. Un second import d'un corpus non ambigu ne duplique rien.
Les compteurs décrivent les éléments résolus ; lorsqu'une phrase est en conflit,
les éléments qui en dépendent ne sont pas nécessairement comptés.

## Fichiers, transactions et limites

Aucune extraction libre du ZIP : chemins relatifs stricts, noms fondés sur le
SHA-256, refus des doublons de membres, des liens symboliques, des chemins sortants
et des membres inattendus. Taille et SHA-256 sont vérifiés avant toute écriture
et de nouveau à la copie. Limites : 128 Mio par audio, 1 Gio pour le contenu
non compressé contrôlé, 16 Mio pour le manifest, 10 000 fichiers audio.
Le stockage local est limité à sa racine configurée. Les anciennes références
absolues ne sont lisibles que sous cette racine. S3 est limité au bucket configuré
et au préfixe `audios/` ; aucune URL distante arbitraire n'est téléchargée.

Les fichiers importés reçoivent des noms uniques. La création est exclusive
(`xb` en local, `IfNoneMatch: *` en S3), sans remplacement silencieux.
Les écritures S3 conditionnelles doivent être supportées par le service utilisé.

Les fichiers créés sont suivis en mémoire et supprimés si la transaction DB
échoue avant validation. Un échec de nettoyage est signalé explicitement avec
les références concernées. Si un commit a pu réussir malgré une erreur de
connexion, les fichiers référencés sont conservés ; une vérification impossible
est également signalée et impose une inspection.

Il n'existe pas de transaction atomique entre DB et stockage, ni de journal
persistant de récupération. Un arrêt brutal peut laisser des fichiers orphelins.
Une réponse S3 perdue peut laisser une création incertaine : la référence est
signalée, sans supprimer un objet dont la propriété ne peut être confirmée.
Effectuer les transferts pendant une période sans modifications concurrentes et
avec un seul importeur : ce mécanisme n'ajoute pas de verrou distribué ni de
contrainte d'unicité métier en base.

## Vérification

`backend/tests/test_library_transfer.py` exerce deux bases SQLite et deux
stockages temporaires isolés, les CLI, les anciens formats et un stockage S3
simulé. Aucun test ne nécessite un import dans une Bibliothèque réelle.
Les tests S3 simulés ne remplacent pas une qualification du fournisseur réel.
