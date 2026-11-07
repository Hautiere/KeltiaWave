# Envoyer des phrases éditoriales sans audio

`push_phrases.py` est un client REST autonome en Python standard (pas de dépendance backend, base de données ou stockage audio).

## Contrat existant

- `GET /api/phrases/` : liste complète, utilisée pour vérifier les doublons.
- `POST /api/phrases/` : création ; `Authorization: Bearer …`, compte enseignant ou administrateur actif, sans changement de mot de passe en attente.
- `PhraseCreate` exige `texte` (au moins un caractère). L'endpoint impose aussi `theme` non vide et `niveau` parmi A1/A2/B1/B2/C1/C2.
- Champs optionnels : `traduction_fr`, `source`, `source_url`, `langue`, `auteur`, `url_audio`. Leur valeur par défaut est `null`.
- `source` n'est pas une énumération. Pour `internet`, `source_url` doit être une URL HTTP(S) valide, au maximum 2048 caractères après nettoyage. Pour les autres sources, elle est remise à `null`.
- Aucun contrôle d'unicité texte/langue n'est défini par le POST ou le modèle Phrase.

## CSV

UTF-8 avec ou sans BOM ; séparateurs virgule, point-virgule ou tabulation détectés automatiquement. En-têtes requis : `phrase_br`, `theme`, `niveau`. Les colonnes optionnelles sont `traduction_fr`, `source`, `source_url`, `langue`, `auteur`.

Le script mappe uniquement `phrase_br` vers `texte` et les sept métadonnées précitées. Il conserve le texte original envoyé, espaces compris. Il nettoie les métadonnées ; les valeurs optionnelles vides deviennent `null`. Il refuse un texte composé uniquement d'espaces.

Toutes les autres colonnes sont ignorées, notamment `url_audio`, `best_reference_audio`, les votes et les champs Common Voice. Aucun fichier audio n'est ouvert. Les CSV produits par `extract_theme.py` doivent être enrichis d'un `niveau` avant utilisation ; renseigner aussi `langue` (par exemple `br`) pour assurer une comparaison fiable des doublons.

L'exemple `examples/vie_quotidienne.exemple.csv` contient trois propositions de démonstration, **non validées linguistiquement**, avec un niveau proposé. Il n'est pas un dataset approuvé à publier.

## Simulation et limite

Depuis la racine du dépôt :

```sh
python3 scripts/corpus/push_phrases.py scripts/corpus/examples/vie_quotidienne.exemple.csv --dry-run --offline
python3 scripts/corpus/push_phrases.py ../datasets/exports/vie_quotidienne.csv --dry-run --limit 5
```

Le mode par défaut est également une simulation. `--offline` supprime tout accès réseau et ne vérifie que les doublons internes au CSV. Sans `--offline`, le script effectue un GET ; si celui-ci échoue, la simulation continue avec un avertissement indiquant que les doublons serveur ne sont pas vérifiés. `--limit N` limite les lignes de données examinées, pas le nombre de créations réussies.

`KELTIAWAVE_API_URL` désigne l'origine sans `/api` (par défaut `http://127.0.0.1:8100`). HTTPS est exigé hors localhost. Les redirections sont refusées ; la protection d'accès propre au staging doit donc déjà permettre d'atteindre l'API. Le script ne contourne pas cette protection.

## Envoi explicite, après validation du dataset

Définir `KELTIAWAVE_API_TOKEN` avec un token existant via un moyen privé. Aucun login, mot de passe ou token n'est inscrit dans les fichiers. Le script n'effectue pas de connexion automatique.

Seul `--apply` autorise des POST. Ce mode nécessite le token et un GET préalable réussi. Il ne peut pas être combiné avec `--dry-run` ni `--offline`. Ne l'utiliser qu'après validation explicite du dataset et de la cible.

La clé de comparaison est `(texte.strip().casefold(), langue.strip().casefold())` ; langue absente et vide sont équivalentes. Les phrases existantes sont signalées `[EXISTS]`, sans mise à jour. Les doublons internes non envoyés sont signalés `[SKIP]`. Deux langues différentes restent distinctes. Le script ne peut pas garantir l'absence de doublons si un autre import écrit simultanément : exécuter un seul import à la fois.

Les erreurs de ligne sont comptées et les lignes suivantes continuent. Un échec de POST ne fait l'objet d'aucune nouvelle tentative automatique ; un doublon de cette ligne n'est pas réessayé dans le même lot. Après une réponse réseau incertaine, vérifier l'état serveur via une nouvelle simulation avant de relancer. Une erreur GET bloque tout import réel.

Le résumé distingue créations réelles et créations prévues. Le code de sortie est 1 en présence d'erreurs, sinon 0 ; les erreurs d'arguments retournent 2.

## Tests sans réseau réel

```sh
python3 -B -m unittest discover -s scripts/corpus/tests -p 'test_push_phrases.py' -v
```

Les API sont simulées. Aucun test n'utilise une base locale, staging ou production.
