# Se rencontrer — prototype autonome

Ce dossier est un espace d'essai dans le dépôt unifié KeltiaWave, séparé du backend.
Il ne lit ni la configuration ni la base de l'application. Python 3.9 ou plus
suffit : aucune dépendance à installer, aucun appel réseau.

## Dans VS Code

Ouvrir `meeting-people.code-workspace` avec **Fichier → Ouvrir l'espace de travail
à partir du fichier**. Le prototype devient la racine de cet espace de travail.
Puis **Terminal → Exécuter la tâche → Se rencontrer : démo**.
La tâche **Se rencontrer : tests** lance les vérifications.

Ou, dans un terminal :

```bash
cd /Users/gr4dl0nys29/projets/breizh_transcriptors/keltiawave/experiments/meeting-people-poc
python3 builder.py --demo
python3 -m unittest -v
```

Consulter `output/meeting_people_candidates.csv` dans un tableur, ou le JSON
voisin dans VS Code. Chaque exécution remplace ces deux exports dans le dossier
choisi ; utiliser `--output output/autre-essai` pour conserver plusieurs essais.

## Ce que contient l'essai

- `data/intentions.json` : 16 intentions, quatre par niveau proposé A1 à B2.
  Les formulations bretonnes, traductions et niveaux sont à relire et modifier.
- `data/demo/validated.tsv` : **8 lignes artificielles**, créées pour tester le
  programme. Elles ne proviennent pas de Common Voice et ne prouvent aucune
  attestation linguistique. Aucun MP3 n'est fourni : les audios sont manquants.
- `builder.py` : normalisation NFC et apostrophes, recherche lexicale avec
  `difflib.SequenceMatcher`, puis export. La phrase originale est conservée.
- `test_builder.py` : vérifications automatisées avec `unittest`.

On compare la formulation **bretonne candidate** à chaque phrase bretonne, pas
l'intention française. Le score mesure la ressemblance de caractères, pas le
sens, la correction linguistique ou le niveau CECRL. Les catégories sont EXACT
à partir de 0,98, VERY_CLOSE à 0,85, CLOSE à 0,70 et WEAK en dessous. EXACT est
une catégorie de score ; seule une égalité normalisée garantit un score de 1.
Les résultats faibles restent visibles pour examiner les limites du prototype.

Les traductions et niveaux concernent l'intention de départ : ils ne sont pas
automatiquement ceux des phrases trouvées. Plusieurs enregistrements d'une même
phrase peuvent apparaître. Le prototype ne déduplique pas les locuteurs.

## Plus tard : un vrai dossier Common Voice

Une fois un corpus breton téléchargé et extrait, fournir un dossier contenant
`validated.tsv` et `clips/` :

```bash
python3 builder.py --corpus /chemin/vers/common_voice_br --top 5 --output output/common-voice
```

Les chemins audio restent locaux. Le programme ne copie ni ne publie les MP3.
La licence et l'URL source restent non renseignées tant qu'elles ne sont pas
documentées ; les droits audio restent `TO_CHECK`, `publication_audio=false`.
Le statut de Common Voice ne remplace pas une validation pédagogique.

La lecture du TSV est progressive, mais la recherche exhaustive peut être lente
sur un grand corpus. Pas encore d'index, de matching sémantique, de traduction
automatique, d'interface admin ou d'import dans la base.

Prochaine étape : relire les 16 intentions ensemble, puis essayer un vrai corpus
et mesurer combien de propositions sont utiles avant d'envisager l'intégration.
