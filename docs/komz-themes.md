# Thèmes Komz

## Parcours Komz et Listen

- **Komz** : choisir un thème et une phrase, enregistrer sa voix, puis demander le score expérimental. La voix de référence devient accessible sous le score, avec un titre et un texte expliquant comment comparer la prononciation, le rythme et les pauses.
- **Listen** : choisir l'image d'un domaine, consulter ses phrases validées et écouter la voix de référence. Le lien « Répéter et comparer » apparaît pour la phrase après cette écoute et ouvre directement Komz.

Les deux parcours utilisent le même corpus de phrases et d'audios approuvés. Les phrases sans audio approuvé peuvent être affichées dans Komz sur demande, mais ne figurent pas dans la liste des voix de Listen.

### Filtres Listen

La page d'un domaine propose les niveaux Toutes, A1, A2, B1 et B2, un sous-domaine et une recherche textuelle combinables. Les compteurs portent sur les phrases distinctes ayant un audio approuvé. La taxonomie des sous-domaines est définie dans `apps/corpus/src/app/core/subdomains.ts` ; le champ `Phrase.subdomain` est facultatif et peut être renseigné par l'API de création ou de mise à jour.

La liste Komz reprend les mêmes sous-domaines, leurs compteurs et le choix « Non classées ». Ses compteurs tiennent compte du réglage « Inclure les phrases sans audio ». Le niveau et le sous-domaine se combinent pour filtrer les phrases à pratiquer.

Un préclassement lexical prudent a été appliqué à la base **locale** : 258 des 555 phrases distinctes avec audio approuvé ont un sous-domaine proposé. Les 297 autres restent accessibles via « Non classées » ; 52 ont plusieurs correspondances possibles et 245 n'ont pas de correspondance suffisante. Le fichier `../datasets/exports/library_subdomains_proposed.csv` garde les propositions et leur statut pour relecture. Le script `backend/scripts/apply_subdomain_proposals.py` n'écrase jamais un sous-domaine existant et vérifie l'identifiant, le texte et le thème avant la mise à jour. Un sous-domaine encore vide apparaît avec le compteur 0 et un message explicite quand on le choisit. Aucun tag transversal n'a été appliqué.

Les 13 thèmes éditoriaux affichés par Corpus/Komz sont définis dans
`apps/corpus/src/app/core/domains.ts`. Les nouvelles phrases utilisent ces valeurs :

| Valeur | Libellé français |
| --- | --- |
| `rencontres` | Se présenter et se rencontrer |
| `maison-quotidien` | Maison et vie quotidienne |
| `famille-relations` | Famille et relations |
| `alimentation-achats` | Manger, cuisiner et acheter |
| `deplacements` | Se déplacer |
| `travail-etudes` | Travail et études |
| `sante-bien-etre` | Santé et bien-être |
| `nature-meteo` | Nature et météo |
| `loisirs-sport` | Loisirs et sport |
| `culture-fetes` | Culture et fêtes |
| `histoire-patrimoine` | Histoire et patrimoine |
| `demarches-services` | Démarches et services |
| `numerique-technologies` | Numérique et technologies |

Les anciennes valeurs restent stockées et sont rapprochées de ces thèmes dans
les libellés et filtres de l'interface. Par exemple, `cuisine` apparaît sous
« Manger, cuisiner et acheter » et `education` sous « Travail et études ».
`vie-quotidienne` reste dans « Maison et vie quotidienne » ; les présentations
ne peuvent être séparées de cet ancien groupe sans relecture phrase par phrase.
De même, `culture-patrimoine` est provisoirement associé à « Histoire et
patrimoine ». Les données ne sont pas modifiées par ce changement d'interface.

« Non classé » reste une catégorie de travail dans les fichiers source, mais
pas un choix de thème pour les nouvelles phrases. Le classement Common Voice
et les votes audio ne valident pas le thème éditorial d'une phrase.

## Simulation du reclassement Common Voice

Depuis la racine du projet :

```sh
python3 scripts/corpus/preview_theme_migration.py
```

Le résultat `../datasets/exports/preview_themes_komz.csv` ne modifie ni le
CSV source ni Komz. `correspondance_directe` indique une ancienne catégorie
qui se rattache clairement à un nouveau thème ; `a_relire` signale un choix
éditorial encore nécessaire. Les lignes « Vie quotidienne » reçoivent une
proposition `maison-quotidien`, mais certaines relèvent de `rencontres`, des
achats ou des déplacements. « Culture & patrimoine » et « Non classé » sont
également à relire.

Le lot de 50 phrases sélectionnées est annoté séparément dans
`../datasets/exports/selection_50_vie_quotidienne_komz_themes_proposes.csv`.
Ses thèmes sont des propositions éditoriales, pas des catégories validées.

## Premier lot local de 50 phrases

Le fichier `../datasets/exports/selection_50_vie_quotidienne_komz_themes_proposes.csv`
contient une traduction française, un niveau A1 ou A2 et un thème proposé
pour chaque phrase. Les colonnes `traduction_statut`, `niveau_statut` et
`decision` indiquent que ces choix restent à relire par un responsable
éditorial. Le backend ne stocke pas ces trois statuts : ils restent dans le CSV.

Le script `backend/scripts/import_selected_phrases.py` simule par défaut,
vérifie les 13 thèmes et les niveaux A1 à C2, et crée uniquement les phrases
absentes. Il ne modifie pas les phrases déjà présentes et n'importe pas les
audios. Le premier lot de 50 phrases a été ajouté à la base Docker **locale**
le 30 septembre 2026, puis vérifié via l'API (50 phrases et métadonnées
conformes au CSV). Aucune importation en staging ou production n'a été faite.

## Audios Common Voice du premier lot

Le champ `best_audio_filename` du CSV désigne un MP3 sélectionné pour chacune
des 50 phrases. Le script `backend/scripts/import_selected_common_voice_audios.py`
vérifie les correspondances avec les phrases existantes et les fichiers MP3,
puis simule l'import par défaut. Son option `--apply` associe les fichiers aux
phrases, avec `origin=dataset`, `phrase_source=common-voice` et `status=pending`.
Il n'ajoute aucune validation KeltiaWave : les votes Common Voice ne sont pas
une validation interne.

Les 50 audios ont été importés dans la base et le stockage Docker **locaux** le
1er octobre 2026. Vérification : 50 audios pour 50 phrases distinctes, 50 fichiers
présents, 50 statuts `pending`, lecture MP3 via l'API réussie. Une seconde
simulation indique zéro nouvel audio à créer. Aucun import en staging ou
production n'a été fait.
