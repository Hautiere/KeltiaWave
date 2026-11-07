# Corpus : imports et fonctionnement éditorial

Référence extraite du README racine pour ne la charger que lors d’une tâche corpus. Les dates et volumes ci-dessous décrivent des opérations historiques, pas un inventaire actuel du serveur.

## Lot Common Voice dans Komz

Le manifeste `backend/data/common_voice_selected_50.csv` contient 50 phrases
bretonnes sélectionnées, leurs traductions françaises, niveaux A1/A2, thèmes
proposés et noms des meilleurs MP3 Common Voice. Les fichiers audio proviennent
du jeu de données Common Voice breton et ne sont pas versionnés ici. Les champs
`decision`, `traduction_statut` et `niveau_statut` signalent les propositions
éditoriales encore à relire.

Les scripts `backend/scripts/import_selected_phrases.py` et
`backend/scripts/import_selected_common_voice_audios.py` simulent par défaut.
Ils opèrent sur la base configurée par `DATABASE_URL` et exigent `--apply` pour
écrire. Le second script requiert `--audio-root`, un répertoire contenant les
MP3 nommés dans le manifeste. Il réutilise les phrases existantes et crée les
audios avec l'origine `common-voice` et le statut `pending` : les votes Common
Voice ne valent pas validation Komz.

Dans la pile Docker **locale**, les 50 phrases et leurs 50 audios ont été
importés et vérifiés le 1er octobre 2026. Un second lot de 550 phrases et
audios a ensuite été préparé sur 11 thèmes. Le 2 octobre 2026, les 600 phrases
et audios Common Voice ont été transférés sur le staging et la production OVH
via une archive Bibliothèque ZIP ciblée. Les 550 nouveaux audios ont été
approuvés en lot à la demande du propriétaire sans contrôle d'écoute ; les
traductions et niveaux automatiques restent à relire. Pour les thèmes et les
résultats de vérification, voir `docs/komz-themes.md` et
`docs/common-voice-1000.md`.

Le lot de 50 phrases « Maison et vie quotidienne » avec MP3, traductions et
sous-thèmes se trouve dans `../datasets/exports/common_voice_maison_50_2026-10-10.zip`.
Après un démarrage local, `docker cp` permet de placer l'archive dans le
conteneur backend ; `python -m scripts.import_common_voice_maison ARCHIVE`
simule l'import et `--apply` l'effectue. L'import est idempotent et refuse
les phrases déjà classées différemment. L'admin peut exporter un dataset en
ZIP avec ses audios et métadonnées, y compris les sous-thèmes. Son import
générique ne constitue pas encore une synchronisation sûre entre production
et local : il peut créer des audios en double pour des phrases déjà présentes.

Listen affiche les thèmes sous forme d'images, puis les phrases avec un audio
approuvé. Les niveaux sont regroupés sur une ligne, puis le sous-domaine et la
recherche occupent une zone compacte. Les compteurs et filtres reconnaissent
aussi les anciens imports qui enregistrent le libellé du sous-domaine plutôt
que son identifiant normalisé, dans Listen comme dans Komz. Niveau,
sous-domaine et recherche se combinent. L'utilisateur écoute
d'abord la voix de référence ; le lien vers la pratique dans Komz devient alors
disponible pour cette phrase. Dans Komz, il choisit un thème et une phrase,
enregistre sa voix et obtient son score avant de pouvoir écouter la voix de
référence. Cette dernière est présentée dans un encadré explicatif sous le
score. Les estimations des mots reconnus, du rythme et de la prosodie restent
expérimentales. Le détail des thèmes et sous-domaines figure dans
`docs/komz-themes.md` ; l'API d'analyse du rythme est décrite dans
`backend/README.md`.

La langue d'interface choisie détermine la traduction affichée sous la phrase
bretonne dans Listen et Komz : français, anglais ou gallois. En gallois, le
libellé des sous-domaines est également traduit et la traduction apparaît sans
préfixe. Les champs `traduction_en` et `traduction_cy` peuvent être corrigés
dans l'administration et sont conservés par les exports et imports du corpus.
Les archives Bibliothèque créées avant ces champs restent importables.

Les lots de traduction sont dans `backend/translations/`. Les scripts
`backend/scripts/import_english_translations.py` et
`backend/scripts/import_welsh_translations.py` vérifient l'identifiant et le
texte breton de chaque phrase, simulent l'import par défaut et préservent les
traductions déjà présentes. L'option `--apply` écrit les nouvelles valeurs ;
`--replace` permet une correction explicite. Exécuter ensuite
`seed_english_translations.py` et `seed_welsh_corrections.py` pour les phrases
courantes corrigées manuellement. Les autres traductions du CSV sont des
propositions automatiques qui demandent une relecture linguistique.
Pour livrer ces lots sur une base dont les identifiants diffèrent de la base
locale, `backend/scripts/import_phrase_translations_by_text.py` apparie le
texte breton exact, applique les corrections EN/CY et simule par défaut. Il
refuse les doublons et les phrases absentes ; `--allow-missing` permet de
laisser de côté les absences identifiées, puis `--apply` valide l'import en une
transaction. Les traductions déjà présentes sont préservées.

Dans **Admin > Phrases proposées**, la recherche et le filtre par thème se
combinent. Quand un thème est sélectionné, le tableau affiche le sous-thème à
la place du thème et permet de trier cette colonne. Le formulaire de création
ou de modification permet de choisir un domaine et, facultativement, un
sous-domaine. Les anciens domaines sont rapprochés des 13 domaines éditoriaux
pour l'affichage et le filtrage.

Dans **Admin > Audio recordings**, le filtre par thème s'applique aux
enregistrements avant la limite de résultats. Le tableau compact affiche le
sous-thème de la phrase associée dans une colonne triable ; les phrases sans
sous-thème portent la mention « Sans sous-thème ».
