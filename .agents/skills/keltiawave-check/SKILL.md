---
name: keltiawave-check
description: Choisir et exécuter les vérifications ciblées d'une modification dans le dépôt web/backend KeltiaWave. Utiliser pour valider un changement ou préparer sa revue ; les dépôts mobile et datasets suivent leurs propres instructions.
---

# Vérifier KeltiaWave

Travailler depuis la racine du dépôt web/backend. Lire son `AGENTS.md` actuel : il fait autorité si les commandes ci-dessous évoluent. Vérifier `git status --short` et distinguer les changements de la tâche des modifications préexistantes, y compris les fichiers non suivis concernés. Ne pas modifier des travaux indépendants pour faire passer une vérification.

## Choisir le périmètre

Examiner le diff de la tâche et ses dépendances directes. Choisir les vérifications selon le comportement modifié, pas uniquement le nom des fichiers. Une modification d'un service partagé peut nécessiter plusieurs suites ciblées.

| Changement | Vérification depuis la racine |
|---|---|
| Front | `npm run build:<app>` pour chaque app concernée : portal, corpus, learning, record, transcribe, subtitles, live |
| Live front | `npm --prefix apps/live test`, en plus du build |
| Live backend | `backend/.venv/bin/python -m pytest backend/tests/test_live.py backend/tests/test_live_wav2vec2.py -q` |
| W2V fichier | `backend/.venv/bin/python -m pytest backend/tests/test_wav2vec2.py -q` |
| Calibration | `backend/.venv/bin/python -m pytest backend/tests/test_transcription_calibration.py -q` |
| Compte et retours pédagogiques | `backend/.venv/bin/python -m pytest backend/tests/test_practice.py -q` |
| Email de transcription | `backend/.venv/bin/python -m pytest backend/tests/test_transcript_email.py -q` |
| Attribution ou référence audio corpus | `node --test apps/corpus/tests/*.test.mjs`, en plus du build si le front change |
| Autre comportement backend | Rechercher dans `backend/tests` les tests de la route ou du service modifié et exécuter les suites pertinentes avec le même interpréteur |
| Script shell | `bash -n <script>` ; aucun déploiement réel pour vérifier sa syntaxe |
| Documentation seule | Vérifier les liens, chemins et la cohérence ; aucun build |

Vérifier l'existence des commandes et tests avant exécution. Si le virtualenv manque, chercher l'environnement documenté ; ne pas utiliser arbitrairement le Python système et ne pas télécharger des modèles pour débloquer une suite. Signaler précisément une dépendance absente, un échec ou un test ignoré. Un test ignoré ne prouve pas que le comportement est validé.

## Validation et compte rendu

- Pour un parcours navigateur pertinent, utiliser l'origine du front et son proxy HTTP/WebSocket ; ne pas appeler directement le backend sur 8100 depuis le navigateur. Les scénarios nécessitant un micro ou un modèle réel doivent être signalés comme non vérifiés s'ils ne sont pas exécutables.
- Exécuter `git diff --check`, relire les lignes modifiées de la tâche et inspecter les nouveaux fichiers concernés. Un problème préexistant doit être distingué d'un problème introduit par la tâche.
- Élargir les vérifications si une dépendance partagée, un échec ou le périmètre d'intégration le justifie ; éviter le build global par défaut.
- Rapporter les commandes exécutées, leurs résultats et les limites restantes. Ne pas annoncer une livraison, une installation mobile ou une validation fonctionnelle complète sur la seule base d'un build.

Ce skill ne déclenche aucun commit, push, déploiement, changement de données ou installation sur un téléphone. Ces actions dépendent de la demande de l'utilisateur et des instructions applicables.
