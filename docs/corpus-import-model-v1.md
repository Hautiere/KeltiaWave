# KeltiaWave Corpus Import Model v1

Statut : proposition de contrat conceptuel v1, à valider avant le Lot 3.
Ce document seul est livré : aucun lecteur, adaptateur, modèle SQLAlchemy,
endpoint, mécanisme de publication ou migration n'est implémenté ici.

Référence de comparaison : commits `a55a611` (provenance Phrase), `8be5da9`
(client REST éditorial) et `52a16a5` (transfert de Bibliothèque).

## 1. Portée et architecture

```text
Corpus externe ou collection éditoriale
    → Adaptateur spécifique
    → KeltiaWave Corpus Import Model v1
    → Validation structurelle / preview / décision d'import
    → Bibliothèque KeltiaWave
```

Le contrat est indépendant du fournisseur, du format d'origine et de la langue.
Common Voice, un corpus universitaire breton, gallois ou cornique et une
collection éditoriale KeltiaWave sont des sources possibles. Chacun fournit un
adaptateur vers les mêmes concepts. Aucun vocabulaire propre à un fournisseur
n'est exigé dans les champs génériques.

La validation structurelle vérifie un paquet. La validation KeltiaWave évalue un
audio. L'autorisation de publication traite ses droits. Ces trois décisions sont
indépendantes ; réussir la première n'implique aucune des deux autres.

Le modèle couvre des phrases, zéro ou plusieurs audios par phrase, et zéro ou
plusieurs événements de validation par audio. Une phrase sans audio est valide
et ne doit pas être écartée.

## 2. Enveloppe et conventions

Représentation JSON proposée :

```json
{
  "format": "keltiawave-corpus-import",
  "model_version": 1,
  "phrases": {},
  "audios": {},
  "validations": []
}
```

Ces cinq propriétés sont obligatoires. `phrases` et `audios` sont des objets
indexés par des références locales non vides, uniques dans leur collection,
par exemple `phrase-1` et `audio-1`. Ces clés techniques permettent les relations
sans imposer d'identifiant SQL ni d'identifiant fournisseur dans les objets.
`phrase_ref` désigne une clé de `phrases` ; `audio_ref` une clé de `audios` du même
paquet. `audios: {}` et `validations: []` sont autorisés.

Les références locales ne servent pas de clé de déduplication entre imports.
Un `external_id`, lorsqu'il existe, est une chaîne opaque identifiée dans le
contexte de sa `source`, et non un identifiant global ou SQL.

Conventions proposées :

- Les champs obligatoires sont présents, non `null`, et les chaînes obligatoires
  ne sont pas vides. Les champs optionnels peuvent être absents ou `null` pour
  indiquer une valeur inconnue ; aucun fait métier n'est inventé pour les remplir.
- `text` préserve le texte original, ses signes et sa casse. Toute correction
  éditoriale doit être explicite dans la preview, pas appliquée silencieusement.
- `language` est une étiquette de langue, par exemple `br`, `cy`, `kw` ou une
  étiquette plus précise de type BCP 47. La liste acceptée par KeltiaWave et sa
  normalisation devront être fixées avant implémentation ; aucune langue par
  défaut ne doit être déduite du nom du fournisseur.
- `source` est une chaîne identifiant l'origine documentaire, de manière stable
  au sein de l'adaptateur : par exemple `corpus-exemple-2026` ou
  `keltiawave-editorial`. Elle n'est ni un statut, ni une preuve de licence.
  Phrase et Audio peuvent avoir des sources différentes.
- Les dates fournies sont des chaînes ISO 8601 avec fuseau explicite, de préférence
  UTC avec `Z`. `created_at` décrit la création de l'objet ou de l'événement dans
  sa source, pas la date du téléchargement ou de l'import. Une date inconnue
  reste inconnue ; les autres dates fournisseur peuvent aller dans les extensions.
- `source_url` et les URL de preuve sont des références documentaires HTTP(S),
  jamais des instructions de téléchargement ou d'exécution.
- Une version inconnue est refusée explicitement. Les champs génériques inconnus
  sont signalés ; les extensions propres à un fournisseur utilisent uniquement
  `source_metadata`.

## 3. Phrase

| Champ | Présence | Type et sens |
| --- | --- | --- |
| `text` | Obligatoire | Chaîne : texte exact de la phrase. |
| `language` | Obligatoire | Chaîne : langue de la phrase. |
| `source` | Obligatoire | Chaîne : origine documentaire de la phrase. |
| `translation` | Optionnel | Objet `{ "language": "fr", "text": "Bonjour !" }`. Si présent, ses deux champs sont obligatoires ; une seule traduction dans cette v1. |
| `theme` | Optionnel | Chaîne : thème éditorial ; la correspondance avec les thèmes du site est contrôlée en preview. |
| `level` | Optionnel | Chaîne : niveau pédagogique, par exemple `A1` ; ne pas déduire ce niveau d'un score fournisseur. |
| `author` | Optionnel | Chaîne : auteur du texte, distinct du locuteur et de l'importateur. |
| `source_url` | Optionnel | URL documentaire ; requise conditionnellement si un futur mapping utilise la source actuelle `internet`. |
| `external_id` | Optionnel | Chaîne : identifiant de phrase dans la source. |
| `created_at` | Optionnel | Date de création connue de la phrase à la source. |
| `source_metadata` | Optionnel | Objet JSON d'extensions informatives, voir section 7. |

Le contrat n'ajoute pas `url_audio` à Phrase : les relations Audio → Phrase
expriment la présence de zéro, un ou plusieurs enregistrements sans lien privilégié
implicite. Un éventuel choix d'audio principal reste une décision de Bibliothèque.

## 4. Audio

| Champ | Présence | Type et sens |
| --- | --- | --- |
| `phrase_ref` | Obligatoire | Chaîne : référence locale à une Phrase du paquet. |
| `file` | Obligatoire | Chaîne : chemin relatif du fichier fourni avec le paquet. |
| `source` | Obligatoire | Chaîne : origine de cet enregistrement, indépendamment de celle du texte. |
| `rights` | Obligatoire | Objet explicite de droits, défini en section 6. |
| `external_id` | Optionnel | Chaîne : identifiant audio dans la source. |
| `source_url` | Optionnel | URL de la fiche documentaire de l'audio. |
| `speaker` | Optionnel | Chaîne : référence pseudonyme du locuteur dans le contexte de la source ; ne pas assimiler au contributeur/importateur. |
| `region` | Optionnel | Chaîne : région déclarée associée à la parole ou au locuteur. |
| `accent` | Optionnel | Chaîne : accent déclaré. |
| `variant` | Optionnel | Chaîne : variété linguistique, distincte de la région et de l'accent. |
| `age` | Optionnel | Chaîne descriptive telle que `30–39 ans`, âge ou tranche déclaré lors de l'enregistrement ; pas de date de naissance exigée. |
| `gender` | Optionnel | Chaîne déclarative provenant de la source ; ne pas inférer à partir de la voix. |
| `license` | Optionnel | Chaîne : identifiant ou intitulé de licence déclaré, par exemple un identifiant SPDX lorsqu'il existe ; ne vaut pas vérification. |
| `created_at` | Optionnel | Date connue de création de l'enregistrement. |
| `source_metadata` | Optionnel | Objet JSON d'extensions informatives. |

`file` ne désigne ni une URL distante, ni un chemin absolu de la machine source,
ni un chemin S3 interne à recopier tel quel. Le futur validateur devra contrôler
le confinement dans la racine du paquet, refuser `..` et les liens symboliques
sortants, vérifier la présence et l'intégrité avant application. Aucun
téléchargement distant implicite ne fait partie du contrat. Le conditionnement
physique du paquet, ses limites et son inventaire taille/SHA-256 restent à fixer
avant la mise en œuvre ; le format ZIP du Lot 2 n'est pas implicitement réutilisé.

Le modèle ne permet pas à un adaptateur externe d'imposer `status: approved`.
Sans événement KeltiaWave authentifié, la cible devra traiter l'audio comme
non validé par KeltiaWave. Ce principe est une exigence future, pas une modification
du comportement des imports existants.

## 5. Validation KeltiaWave

Une validation est facultative. Si un événement est fourni :

| Champ | Présence | Type et sens |
| --- | --- | --- |
| `audio_ref` | Obligatoire | Chaîne : référence locale à l'Audio concerné. |
| `decision` | Obligatoire | Chaîne : `approved`, `rejected` ou `commented` dans le contrat proposé ; un commentaire seul n'est pas une approbation. |
| `validator` | Obligatoire | Chaîne : référence d'un validateur KeltiaWave reconnu. Une simple déclaration du fournisseur ne prouve pas cette identité. |
| `validator_role` | Optionnel | Chaîne : rôle effectif du validateur, à vérifier côté KeltiaWave. |
| `validation_weight` | Optionnel | Nombre JSON fini : poids de la validation ; domaine et attribution à définir côté KeltiaWave, jamais issus automatiquement d'un score externe. |
| `pronunciation_level` | Optionnel | Chaîne : niveau de prononciation évalué. |
| `region` | Optionnel | Chaîne : région de prononciation évaluée ; distincte de la région déclarée dans Audio. |
| `comment` | Optionnel | Chaîne : commentaire du validateur. |
| `created_at` | Optionnel | Date de l'événement KeltiaWave ; ne pas fabriquer une date historique manquante. |
| `source_metadata` | Optionnel | Objet d'informations supplémentaires ; ne constitue pas une preuve d'autorité. |

**PROVENANCE EXTERNE != VALIDATION KELTIAWAVE.**

Votes Common Voice, score d'un autre corpus, nombre d'écoutes, classement
automatique et métadonnées du fournisseur restent des informations de source.
Ils ne créent jamais automatiquement un événement AudioValidation, un validateur,
un poids KeltiaWave ou une approbation KeltiaWave.

Même un objet ayant tous les champs ci-dessus ne constitue pas une validation
fiable sans vérification de son origine et de l'autorité du validateur. Un
adaptateur externe ordinaire émet `validations: []`. Les événements KeltiaWave
ne pourront être acceptés que par un chemin de confiance explicitement défini ;
les déclarations non vérifiables devront être bloquées pour revue, jamais promues.
Aucune évolution de l'authentification n'est entreprise dans ce document.

Un historique contient des événements, pas uniquement le dernier statut. La
règle de calcul de l'état courant à partir de cet historique devra être explicite
avant implémentation, notamment pour des décisions successives contradictoires.

## 6. Droits et publication

Objet `rights` proposé, obligatoire même lorsque tout est encore inconnu :

| Champ | Présence | Valeurs ou sens |
| --- | --- | --- |
| `verification` | Obligatoire | `unverified`, `verified`, `disputed`. État de la vérification des droits. |
| `publication` | Obligatoire | `undetermined`, `allowed`, `denied`. Décision de publication par KeltiaWave. |
| `holder` | Optionnel | Chaîne : titulaire de droits connu ou déclaré. |
| `evidence_url` | Optionnel | URL documentaire de preuve ou d'autorisation. |
| `note` | Optionnel | Chaîne : portée de l'autorisation, restrictions ou éléments restant à vérifier. |
| `verified_by` | Optionnel | Référence du responsable de la vérification KeltiaWave. |
| `verified_at` | Optionnel | Date de cette vérification. |

Quatre informations restent distinctes : `source` décrit l'origine ; `license`
la licence connue ou déclarée ; `rights.verification` la vérification ;
`rights.publication` l'autorisation de publication KeltiaWave.

Un adaptateur peut indiquer une licence tout en fournissant
`{"verification":"unverified","publication":"undetermined"}`.
L'absence de licence n'est ni une licence libre, ni une autorisation tacite.
Une autorisation spécifique peut également exister sans licence standard.

`allowed` n'est acceptable qu'avec `verified` et une décision KeltiaWave traçable,
contrôlée hors de la simple déclaration de l'adaptateur. Sans cette preuve,
la preview bloque l'autorisation au lieu de l'accorder silencieusement.
`unverified`, `disputed`, `undetermined` et `denied` n'autorisent pas de publication.
L'approbation linguistique d'un audio ne change jamais ses droits, et des droits
vérifiés ne constituent pas une approbation linguistique.

La possibilité de conserver en espace privé un audio aux droits non vérifiés,
les accès à sa preview et la politique de publication finale sont à décider avant
le Lot 3. Aucun automatisme actuel de publication n'est supposé conforme à ce
contrat. Les éventuels droits propres au texte restent un sujet à préciser :
les droits audio ne les couvrent pas implicitement.

## 7. Extensions propres aux sources

`source_metadata` est un objet JSON facultatif, organisé par espace de noms :

```json
{
  "corpus-exemple": {
    "release": "2026-01",
    "review_score": 0.92,
    "listening_count": 17,
    "original_category": "greetings"
  }
}
```

Les clés internes appartiennent à l'adaptateur. Elles préservent les données utiles
sans ajouter des colonnes conceptuelles génériques propres à un fournisseur.
Le contenu reste informatif : il ne remplace aucun champ obligatoire et ne modifie
ni les droits, ni une validation KeltiaWave, ni le statut de publication.
Les champs normalisés et les valeurs fournisseur ne doivent pas se contredire
silencieusement : les divergences sont affichées dans la preview.

L'adaptateur doit sélectionner les métadonnées utiles, éviter les secrets et
les données personnelles inutiles. Les limites de taille, les règles de
conservation et le stockage de ces objets restent à définir. Si la cible ne peut
pas conserver une information, la preview le signale et bloque l'application
jusqu'à une décision explicite ; aucune perte silencieuse n'est acceptable.

## 8. Exemples génériques

### Audio externe, aucune validation KeltiaWave

Le corpus et les identifiants suivants sont fictifs. Le score du fournisseur
n'est pas une validation KeltiaWave ; la licence déclarée n'est pas encore vérifiée.

```json
{
  "format": "keltiawave-corpus-import",
  "model_version": 1,
  "phrases": {
    "p1": {
      "text": "Demat !",
      "language": "br",
      "source": "corpus-exemple-2026",
      "translation": {"language": "fr", "text": "Bonjour !"},
      "theme": "faire-connaissance",
      "source_url": "https://example.org/corpus/phrases/42",
      "external_id": "phrase-42"
    }
  },
  "audios": {
    "a1": {
      "phrase_ref": "p1",
      "file": "audios/exemple-42.wav",
      "source": "corpus-exemple-2026",
      "rights": {"verification": "unverified", "publication": "undetermined"},
      "license": "CC-BY-4.0",
      "external_id": "recording-84",
      "source_url": "https://example.org/corpus/recordings/84",
      "speaker": "speaker-7",
      "region": "Leon",
      "source_metadata": {
        "corpus-exemple": {"release": "2026-01", "review_score": 0.92, "listening_count": 17}
      }
    }
  },
  "validations": []
}
```

### Même audio après validation KeltiaWave

Cet exemple suppose que l'événement a réellement été produit et vérifié dans
KeltiaWave. Il ne peut pas être fabriqué par l'adaptateur à partir du score externe.
Les droits restent inchangés : l'approbation ne suffit donc pas à publier l'audio.

```json
{
  "format": "keltiawave-corpus-import",
  "model_version": 1,
  "phrases": {
    "p1": {
      "text": "Demat !",
      "language": "br",
      "source": "corpus-exemple-2026",
      "translation": {"language": "fr", "text": "Bonjour !"},
      "theme": "faire-connaissance",
      "source_url": "https://example.org/corpus/phrases/42",
      "external_id": "phrase-42"
    }
  },
  "audios": {
    "a1": {
      "phrase_ref": "p1",
      "file": "audios/exemple-42.wav",
      "source": "corpus-exemple-2026",
      "rights": {"verification": "unverified", "publication": "undetermined"},
      "license": "CC-BY-4.0",
      "external_id": "recording-84",
      "source_url": "https://example.org/corpus/recordings/84",
      "speaker": "speaker-7",
      "region": "Leon",
      "source_metadata": {
        "corpus-exemple": {"release": "2026-01", "review_score": 0.92, "listening_count": 17}
      }
    }
  },
  "validations": [
    {
      "audio_ref": "a1",
      "decision": "approved",
      "validator": "keltiawave:validator-12",
      "validator_role": "teacher",
      "pronunciation_level": "B2",
      "region": "Leon",
      "comment": "Prononciation vérifiée dans KeltiaWave.",
      "created_at": "2026-09-21T10:00:00Z"
    }
  ]
}
```

## 9. Compatibilité avec l'existant

Comparaison avec [Phrase](../backend/app/models/phrase.py),
[Audio et AudioValidation](../backend/app/models/audio.py), la
[règle du Lot 1](../backend/app/phrase_provenance.py) et le
[transfert du Lot 2](library-transfer.md). Les correspondances ci-dessous ne
constituent pas une implémentation ni une promesse de persistance immédiate.

| Concept proposé | Capacité actuelle / écart |
| --- | --- |
| Phrase `text`, `language` | `texte`, `langue`. Seul `texte` est non nullable en SQL ; le contrat exige aussi une langue et une source. |
| Phrase `translation` | Seulement `traduction_fr` aujourd'hui : mapping direct uniquement pour `language: fr`. Une autre langue de traduction ne peut pas être conservée dans ce champ. |
| Phrase `theme`, `level`, `author`, `source` | `theme`, `niveau`, `auteur`, `source` existent. Le vocabulaire de source générique et les valeurs éditoriales actuelles restent à rapprocher explicitement. |
| Phrase `source_url` | Colonne existante. Le Lot 1 exige une URL HTTP(S) pour `source == internet` et remet l'URL à `None` pour les autres sources lors des écritures concernées. Une URL de corpus générique ne peut donc pas passer sans perte par ces chemins tels quels. Le snapshot Lot 2 conserve les valeurs existantes. |
| Phrase `external_id`, `source_metadata` | Aucune colonne dédiée. Ne pas détourner `auteur`, `source_url` ou `texte` pour les stocker. |
| Phrase → audios | `Audio.phrase_id` représente déjà plusieurs audios. `Phrase.url_audio` est un lien facultatif supplémentaire, absent du contrat externe. |
| Audio `file` | `filename` référence le stockage actuel ; une copie contrôlée et un remapping sont nécessaires. |
| Audio `source`, `source_url`, `external_id` | `origin` existe (défaut `user`), mais ne décrit pas à lui seul une provenance complète. Pas de colonnes audio dédiées `source_url` ou `external_id`. `phrase_source` ne doit pas être détourné pour simuler ces champs. |
| Audio `region`, `accent` | Correspondances possibles vers `speaker_region`, `speaker_accent`, après confirmation de la sémantique. |
| Audio `speaker`, `variant`, `age`, `gender` | Pas de champs dédiés. `contributor_name` et `contributor_email` décrivent un contributeur, pas automatiquement le locuteur. |
| Audio `license`, `rights`, `source_metadata` | Pas de stockage structuré équivalent dans Audio. Le statut audio n'est pas une autorisation de publication. |
| Métadonnées audio actuelles supplémentaires | `domain`, `speaker_city`, `speaker_level`, `contributor_*` ne sont pas des champs génériques de cette proposition. Ne pas les perdre lors d'un éventuel adaptateur interne : extension documentée ou évolution explicite du contrat. |
| Validation `audio_ref`, `decision`, `validator` | `audio_id`, `decision`, `validator` existent ; `validator` est nullable en SQL et `decision` une chaîne libre. Le contrat exige un validateur reconnu et propose un vocabulaire borné. |
| Validation `region`, autres métadonnées | `pronunciation_region`, `validator_role`, `pronunciation_level`, `comment` existent. `validation_weight` est actuellement une chaîne, contre un nombre proposé ici : conversion contrôlée à définir. Pas de `source_metadata`. |
| État courant et historique | `Audio.status` (`pending`, `approved`, `rejected`) et `validated_*`, `validator_role`, `validation_weight`, `validation_comment` coexistent avec les événements AudioValidation. Il faut décider explicitement comment ils sont synchronisés ; ne pas inférer un historique depuis un statut. |
| `created_at` | Présent et non nullable sur les trois modèles, avec défaut à l'heure courante. Dates actuellement sans fuseau. Le contrat permet une date source inconnue : ne pas confondre un défaut d'insertion avec une date source attestée. |

### Distinction avec le Lot 2

Le Lot 2 est un snapshot portable de Bibliothèque existante, identifié par
`format: keltiawave-library`, `manifest_version: 1`. Il préserve les champs actuels,
les `null`, les dates, les statuts et l'historique entre bases compatibles. Il
utilise des listes avec identifiants internes remappables, `audio_validations`,
un inventaire `files` et des fichiers `audios/<sha256>.<extension>`.

Le présent contrat est une entrée générique normalisée, identifiée autrement,
avec des références locales, `validations`, une séparation explicite des droits
et des extensions de source. Il ne remplace pas le Lot 2 et n'est pas accepté
par ses CLI. Le manifest strict du Lot 2 n'accepte pas ces nouveaux champs.

Une conversion directe vers le snapshot actuel serait incomplète : droits,
identifiants externes, métadonnées de source et plusieurs attributs audio n'y ont
pas de place. Elle ne doit pas les supprimer silencieusement. Une évolution de
persistance et une décision de version du transfert seront nécessaires si ces
informations entrent ultérieurement dans la Bibliothèque.

Le client `scripts/corpus/push_phrases.py` reste indépendant, limité au peuplement
éditorial REST. Il n'est ni un lecteur de ce contrat ni un outil de restauration.

## 10. Preview et décisions préalables au Lot 3

Le futur validateur devra présenter erreurs structurelles, références invalides,
fichiers absents, créations envisagées, correspondances, conflits, informations
non persistables, droits non vérifiés et validations non fiables avant écriture.
Un adaptateur ne doit jamais transformer une donnée externe en approbation pour
faire disparaître un avertissement. Aucun import ni publication n'est déclenché
par ce document.

Décisions à valider avant implémentation du Lot 3 :

1. Fixer les vocabulaires de source et leur mapping, notamment le rapport entre
   source du texte, origine technique audio et fournisseur ; résoudre le cas des
   URL de corpus hors `internet` sans contourner le Lot 1.
2. Choisir où persister provenance audio, licence, droits, identifiants externes
   et `source_metadata` ; identifier les migrations réellement nécessaires et
   l'évolution éventuelle du manifest Lot 2. Rien n'est modifié ici.
3. Définir l'autorité qui vérifie les droits, la preuve attendue, l'accès privé
   aux fichiers non vérifiés, les conditions de publication et le traitement des
   droits du texte. Fixer les règles de conservation des données de locuteur.
4. Définir le chemin de confiance des véritables validations KeltiaWave, les
   références de validateur, les décisions acceptées, le domaine des poids et
   le calcul de l'état courant depuis l'historique.
5. Choisir le traitement des dates source inconnues, des traductions non
   françaises, des langues/variétés, des thèmes et niveaux non reconnus.
6. Définir les clés de rapprochement et la politique de conflit pour les imports
   externes, y compris plusieurs provenances pour un même texte ou fichier. Les
   clés du Lot 2 (texte + langue, phrase + SHA-256) sont un point de comparaison,
   pas une justification de fusion silencieuse de provenances distinctes.
7. Fixer le conditionnement du paquet, les limites, les contrôles d'intégrité,
   la stabilité des références et la manière de rendre visibles les données
   non persistables. Prévoir des tests de conservation et d'absence de promotion
   automatique des scores externes en validation ou en droits de publication.

Ces décisions préparent le Lot 3 sans le commencer. Aucun adaptateur Common Voice,
autre adaptateur de corpus ou travail du Lot 4 n'est engagé.
