# Lot Common Voice de 1 000 phrases : préparation éditoriale

Le fichier `../datasets/exports/common_voice_1000_editorial_review.csv` est une
file de **1 000 nouvelles candidates** en plus des 50 phrases du premier lot.
Il a été généré depuis `../datasets/br` (Common Voice breton 27.0) et
`../datasets/keltiawave_commonvoice_phrases_classees.csv` :

```sh
python3 scripts/corpus/prepare_common_voice_1000.py
```

La sélection est reproductible et ne modifie pas Komz. Elle exclut les 50
phrases du manifeste `backend/data/common_voice_selected_50.csv`, prend une
phrase unique et un MP3 unique par ligne, et exige un fichier présent, une durée
de 0,5 à 20 secondes, au moins deux votes positifs et aucun vote négatif.
L'audio retenu est celui qui a le plus de votes positifs, puis le moins de votes
négatifs, selon `scripts/corpus/common_voice.py`. La sélection couvre 11 thèmes
issus des catégories directement rapprochables ; les catégories ambiguës
« Vie quotidienne » et « Culture & patrimoine » sont exclues de cette passe.
Les thèmes `rencontres` et `maison-quotidien` n'ont donc pas de candidates dans
ce lot. Le classement source contient malgré tout des erreurs : aucun thème
proposé n'est considéré comme validé.

## Lots de 50 par thème

`python3 scripts/corpus/split_common_voice_theme_batches.py` produit 11 fichiers
`../datasets/exports/common_voice_theme_batches/common_voice_<theme>_<nombre>_review.csv`.
La sélection privilégie les MP3 avec au moins quatre votes positifs, puis
complète avec ceux ayant deux votes positifs ; tous ont zéro vote négatif.
Les 11 thèmes disponibles ont chacun 50 candidates. Sur les 550 MP3, 504 ont
au moins quatre votes positifs et 46 en ont deux.
Chaque fichier conserve les colonnes de traçabilité et les statuts de relecture
du CSV source. Les 550 lignes ont des textes et MP3 distincts ; les 550 fichiers
existent et leurs SHA-256 correspondent au manifeste. Aucun de ces lots n'est
encore importable avec `--require-reviewed` : traductions, niveaux, thèmes et
audios restent à contrôler individuellement.

Le 1er octobre 2026, les 550 candidates des 11 lots ont été importées dans la
pile Docker **locale** avec `traduction_fr` et `niveau` à `NULL`, et leurs 550
MP3 ont été associés comme audios `pending`. Il s'agit de données de travail,
pas de fiches éditorialement validées. La simulation après import retrouve les
550 associations et ne propose aucun nouvel audio.

À la demande du propriétaire, les 550 audios ont ensuite été marqués
`approved` dans la base locale, avec un commentaire explicite indiquant qu'aucun
contrôle d'écoute ou linguistique n'a été fait. Aucun événement de validation
attribué à un enseignant ou administrateur n'a été fabriqué. Les 550 phrases ont
reçu un niveau **estimé automatiquement par longueur du texte** : A1 jusqu'à
5 mots, A2 de 6 à 8, B1 de 9 à 12, B2 au-delà. Ces niveaux ne constituent pas
une évaluation pédagogique et doivent être relus. Les 550 traductions ont été
ajoutées ensuite comme propositions automatiques dans la base locale. Le fichier
`../datasets/exports/common_voice_550_translation_comparison.csv` conserve
pour chaque phrase les résultats Apertium et Google Traduction, la proposition
retenue et son origine. Six propositions ont reçu une correction manuelle.
L'échantillon examiné montre encore des contresens possibles : aucune de ces
traductions ne doit être considérée comme validée éditorialement.

Dans la bibliothèque Corpus, ces 550 audios sont affichés avec la
mention « Approuvé en lot · non écouté ». Ils ne sont pas présentés comme des
validations d'enseignants. Le filtre « Se présenter et se rencontrer » ne montre
aucun de ces nouveaux lots : sélectionner « Tous les thèmes » ou l'un des 11
thèmes importés pour les retrouver.

Le 2 octobre 2026, une archive Bibliothèque ZIP ciblée contenant les 600
phrases et 600 audios Common Voice (premier lot et 550 nouveaux) a été importée
sur le staging puis sur la pile production OVH existante. La simulation avant
chaque import n'a signalé aucun conflit. Les contrôles ont retrouvé les 600
fichiers sur chaque pile ; le site public expose 600 phrases Common Voice et
les 550 audios approuvés en lot. La production a conservé ses volumes propres,
notamment ses cinq leçons et cinq vidéos Learning.

`rencontres` et `maison-quotidien` n'ont pas de lot dans cette sélection.
Leur recherche exige une relecture des catégories source ambiguës, notamment
« Vie quotidienne », sans attribuer automatiquement un thème aux phrases.

Le CSV comprend le texte, le thème source et proposé, le nom du MP3, le nombre
d'audios pour la phrase, les votes du MP3 choisi, sa durée et son SHA-256, ainsi
que l'identifiant de phrase Common Voice, la locale, l'accent et la variante
déclarés quand présents. Le `client_id` du locuteur n'est pas recopié. La source
déclare le jeu de données sous CC0 ; cette mention n'est ni une validation audio
Komz ni une preuve que la phrase est adaptée à l'application.

## Relecture et enrichissement

Traiter le CSV en lots de 50 lignes, en conservant `rang` et les colonnes de
traçabilité. Pour chaque ligne :

1. Écouter le MP3 et vérifier qu'il correspond au texte, qu'il est intelligible
   et adapté à l'usage de Komz. Les votes Common Voice ne remplacent pas ce
   contrôle.
2. Vérifier ou corriger `theme_propose`, puis écrire `valide` dans
   `theme_statut`.
3. Rédiger et relire `traduction_fr`, puis écrire `valide` dans
   `traduction_statut`.
4. Attribuer un niveau A1 à C2 selon la difficulté réelle, puis écrire `valide`
   dans `niveau_statut`.

Les valeurs initiales `proposition_a_relire`, `a_traduire` et `a_evaluer` sont des
blocages explicites. Ne pas remplacer ces valeurs en masse par `valide`.
Une ligne écartée doit être retirée du lot d'import, avec sa décision conservée
dans la copie de travail éditoriale.

## Import après relecture

Les scripts existants sont en simulation par défaut. Utiliser la **copie relue**
du CSV et une base cible explicitement configurée par `DATABASE_URL` :

```sh
PYTHONPATH=backend python3 backend/scripts/import_selected_phrases.py LOT_RELU.csv --require-reviewed
PYTHONPATH=backend python3 backend/scripts/import_selected_phrases.py LOT_RELU.csv --require-reviewed --apply
PYTHONPATH=backend python3 backend/scripts/import_selected_common_voice_audios.py LOT_RELU.csv \
  --audio-root ../datasets/br/clips --expected-count 1000 \
  --name common-voice-selected-1000 --require-reviewed
PYTHONPATH=backend python3 backend/scripts/import_selected_common_voice_audios.py LOT_RELU.csv \
  --audio-root ../datasets/br/clips --expected-count 1000 \
  --name common-voice-selected-1000 --require-reviewed --apply
```

Adapter `--expected-count` au nombre réellement retenu après relecture. Les
audios sont importés avec le statut `pending`, sans validation Komz implicite.
Vérifier ensuite par API le nombre de phrases, l'unicité des associations et
la lecture des fichiers. Parmi cette file, 550 candidates ont été importées
dans la base locale, puis transférées avec le premier lot vers le staging et
la production, comme indiqué plus haut.
