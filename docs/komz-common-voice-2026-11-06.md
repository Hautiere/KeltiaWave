# Komz : 650 audios Common Voice supplémentaires en local

Le 6 novembre 2026, 50 nouvelles phrases et leurs MP3 ont été ajoutés dans
chacun des 13 thèmes de la pile Docker locale. Source : le même jeu Common
Voice breton 27.0 dans `../datasets/br`, sans téléchargement supplémentaire.
Aucun changement de staging ou de production.

## Sélection

Le lot exclut tous les textes bretons présents avant l'opération, après
normalisation de la casse et des espaces périphériques. Chaque texte et chaque
MP3 sont uniques. Parmi les fichiers éligibles d'une phrase, le classement
privilégie les votes positifs Common Voice, avec zéro vote négatif, un fichier
présent et une durée source de 0,5 à 20 secondes. Le lot final contient 635
MP3 avec au moins quatre votes positifs et 15 avec deux votes positifs ; leurs
durées vont de 1,908 à 8,280 secondes.

L'ancien classement lexical comportait des faux positifs. Les choix de thèmes
ont été revus sur les textes et sont conservés séparément, sans prétendre à
une validation linguistique. Cette sélection par métadonnées et texte ne prouve
pas la qualité acoustique ou la correspondance exacte voix/texte : aucune écoute
individuelle n'a été effectuée. Aucun nom de locuteur n'est inventé.

Les traductions étaient vides lors de l’import audio. Les trois langues ont
ensuite été complétées comme propositions à relire (voir ci-dessous). Les niveaux
restent vides avec le statut `a_evaluer`. Les audios sont disponibles pour
Komz/Listen grâce au mécanisme existant d'approbation en lot, avec le commentaire
« Approbation en lot demandée par le propriétaire ; écoute et contrôle linguistique
non effectués. » Aucun événement de validation d'enseignant ni rôle de validateur
n'a été créé. Les champs source restent `source=common-voice`, `origin=dataset`
et `phrase_source=common-voice`.

## Fichiers et reproduction

Le dossier `../datasets/exports/common_voice_komz_additions_2026-11-06/` contient :

- `existing_texts.json` : instantané des textes avant import, pour l'exclusion ;
- `theme_choices.csv` : les 650 choix thématiques proposés ;
- `manifest.csv` : métadonnées, votes, durées, identifiants Common Voice et SHA-256 ;
- `audios/` et `common_voice_komz_additions_650.zip` : 650 MP3 et leur manifeste ;
- `import_result.json` : identifiants locaux des phrases et audios importés ;
- `audio_integrity.json` et `http_verification.json` : contrôles des fichiers.

Le dossier conserve aussi les manifestes préparatoires, remplacés avant mise à
disposition ; ils ne constituent pas des lots supplémentaires importés.

Depuis la racine web :

```sh
python3 scripts/corpus/prepare_komz_additions.py \
  --existing ../datasets/exports/common_voice_komz_additions_2026-11-06/existing_texts.json \
  --choices ../datasets/exports/common_voice_komz_additions_2026-11-06/theme_choices.csv \
  --output /tmp/komz-additions-reproduced.csv
```

Ce script prépare un manifeste sans écrire dans la base. Il échoue si un thème
ne dispose pas de 50 candidates éligibles. Les scripts d'import existants ont
été utilisés avec le nom de lot `common-voice-komz-additions-2026-11-06`,
`--allow-incomplete` pour les phrases et `--expected-count 650` pour les audios.
Ne pas importer directement le ZIP comme une archive Bibliothèque : son format
est celui du manifeste de sélection, pas le format générique d'échange.

## Vérifications

- 650 textes nouveaux, 650 MP3 distincts, exactement 50 ajouts par thème.
- 650 MP3 entièrement décodés sans erreur par FFmpeg.
- 650 fichiers stockés présents ; 650 réponses HTTP 200 à travers le front
  `localhost:4200`, avec les mêmes SHA-256 que les sources.
- Une nouvelle simulation d'import retrouve 650 associations et zéro ajout.
- La reproduction du manifeste est identique octet par octet.
- Komz `/lire` affiche 100 phrases pour chacun des 13 thèmes ; Maison en affiche
  103 par rapprochement des trois anciennes phrases `vie-quotidienne` conservées.
  Le total local est de 1 303 phrases disposant d'un audio approuvé.

Les fichiers audio et exports restent hors du dépôt web Git. Le corpus existant
avant cette opération est conservé ; aucun fichier de modèle ou secret n'est ajouté.

## Traductions ajoutées ensuite

À la demande du propriétaire, les 650 nouvelles phrases ont reçu chacune une
traduction française, anglaise et galloise : 1 950 valeurs ajoutées uniquement
sur la pile locale. La langue d’interface détermine celle affichée dans Komz.
Les textes bretons, les audios et les autres données du corpus sont conservés.

Les propositions initiales Google Traduction breton → français/anglais/gallois
sont conservées dans `translations/{fr,en,cy}_drafts.json`. Une relecture de la
version anglaise par l’assistant a produit 153 corrections proposées, notamment
sur les nombres, mois, noms propres, instruments et expressions. La version
anglaise de travail sert ensuite de pivot pour harmoniser le français et le
gallois ; sept valeurs cibles ont reçu six corrections supplémentaires par
phrase. Cette relecture n’est pas une validation par un spécialiste du breton
ou du gallois. Le statut reste `proposition_automatique_a_relire` ; aucun champ
ne reçoit artificiellement le statut `valide`.

Quelques recherches lexicales ciblées ont aidé la relecture : [ragachat dans
Meurgorf](https://niverel.brezhoneg.bzh/fr/meurgorf/25173), [kendentadur dans
le lexique TES](https://www.reseau-canope.fr/tes/aaa/dl/germat/GERMAT5.pdf),
et l’usage de [Skrabell par Ti ar Vro Kemper](https://abp.bzh/skrabell-e-brezhoneg-e-plozeved-14636).
Les pages directes Devri recherchées pour ces mots n’étaient pas accessibles ;
les sens dépendants du contexte restent à relire. Ces recherches ne constituent
pas une vérification exhaustive du lot.

Le même dossier d’exports contient désormais :

- `translations/translations.csv` : 650 textes exacts, identifiants locaux et trois traductions ;
- `translations/corrections.json`, `en_working.json`, `target_corrections.json` : propositions et corrections traçables ;
- `translations/{fr,cy}_from_en.json` : traductions harmonisées et leur pivot anglais ;
- `translations/import_snapshot.json` : valeurs avant et après l’import ;
- `translations/verification.json` : contrôle des 650 phrases et conservation des autres données ;
- `manifest_translated.csv` et `common_voice_komz_additions_650_translated.zip` : version enrichie du lot, avec les 650 MP3.

Le manifeste initial est conservé pour reproduire la sélection audio. Les scripts
`translate_selection.py`, `translate_pivot.py` et `finalize_translations.py` du
dossier d’exports décrivent la préparation ; la dernière étape réapplique les
corrections cibles après toute régénération. Ces archives restent au format de
sélection Common Voice, pas au format générique Bibliothèque.

Le script `backend/scripts/import_phrase_translation_selection.py` simule par
défaut, vérifie les identifiants et les textes bretons, préserve les traductions
existantes et exige `--snapshot` lors d’un `--apply`. Les cinq tests ciblés passent.
Après import, 650 valeurs non vides sont vérifiées pour chacune des trois
langues ; une seconde simulation annonce zéro modification. Une empreinte des
données protégées confirme la conservation des champs hors périmètre.
L’affichage français, anglais et gallois a été vérifié dans Komz pour la phrase
« E-pad triwec’h miz ho peus labouret en Iwerzhon. », dont les traductions
conservent bien dix-huit mois.
