# KeltiaWave web/backend : contexte de travail

## Lire le minimum utile

- Commencer par ce fichier ; README seulement pour démarrer/livrer. `rg --files`, puis `rg -n` dans le plus petit répertoire ; lire les lignes voisines avant un fichier entier.
- Charger composant/service/template/styles pour le front, route/dépendances/tests ciblés pour l’API. Documentation externe : extraits ciblés, signaler les recherches infructueuses.
- Ne pas précharger les historiques `docs/CHANGES-*`, tous les fronts, lockfiles, dépendances, assets générés ou modèles. Consulter uniquement le document lié à la tâche.
- Vérifier `git status --short`, préserver les changements indépendants. Aucun `.env`, secret, audio utilisateur, modèle binaire ou APK dans Git/logs.

## Frontières et état fonctionnel (2026-11-07)

- Ce dépôt = sept fronts + backend FastAPI commun. Android natif = `../keltiawave-mobile` ; données de préparation = `../datasets`, dépôt distinct.
- Web : reconnaissance sur serveur, Internet requis. Android : Vosk breton local/offline dans Record/Transcribe/Live ; Whisper et W2V gallois en ligne.
- Transcribe gallois : **W2V · Rapide** ou **Whisper · Qualité**. W2V CTC glouton, KenLM non utilisé, pas d’horodatages fins ; « Rapide » ne garantit pas une vitesse supérieure à Whisper.
- Live web : breton/Vosk ou gallois/W2V ; blocs gallois utiles de 4 s + contexte 1 s, délai serveur, une écoute galloise/processus, file bornée. Whisper après arrêt conserve une autre version et la langue de l’audio.
- Live gallois livré sur staging web ; ne pas en déduire une livraison production ou une installation mobile. Le portail propose Transcribe, Record, Subtitles et Live pour le gallois.
- Compte partagé web/mobile sur le même serveur. Envoi pédagogique mobile depuis **Komz uniquement**, pas Record ; privé, distinct de la publication corpus. École → formation/professeur, « Non inscrit » par défaut, administration sans rattachement.
- Komz et Listen partagent un explorateur avec thèmes, sous-domaines, niveaux et pagination. Komz : enregistrer → analyse/score → référence ; Listen : référence immédiate → répéter et comparer après écoute. Retour classique via `?interface=classic` ; voir `docs/komz-interface.md`.
- Subtitles gallois : W2V ou Whisper ; W2V fournit un calage approximatif à ajuster, sans horodatages fins.
- Corpus public : origine de la voix = auteur/« Inconnu », indépendante du texte Common Voice. Komz/Listen partagent la référence approuvée la plus récente ; les autres voix restent conservées.

## Carte code → document ciblé

| Sujet | Points d’entrée |
|---|---|
| Portail / corpus / cours | `apps/portal/`, `apps/corpus/`, `apps/learning/` ; README de l’app |
| Outils audio | `apps/{record,transcribe,subtitles}/` et `backend/app/{record,transcribe,subtitles}/` |
| Live | `apps/live/src/live-app.component.*`, `live-audio.service.ts`, `apps/live/public/live-pcm-worklet.js` ; `apps/live/README.md` |
| Flux serveur | `backend/app/live/routes.py`, `wav2vec2_stream.py` ; Vosk partagé : `backend/app/vosk_utils.py` ; Whisper partagé : `backend/app/transcribe/service.py` |
| W2V / estimation | `backend/app/transcribe/wav2vec2.py`, `calibration.py`, README voisin ; registre : `backend/app/api/routes/transcription_models.py` |
| Compte / retours privés | `backend/app/api/endpoints/practice.py`, `backend/app/models/practice.py`, `practice_schema.py`, `web_formations.py` ; `backend/README-practice.md` ; front `apps/corpus/src/app/pages-v2/account/` |
| Auth / références corpus | `backend/app/api/endpoints/`, `apps/corpus/src/app/core/auth.service.ts`, `reference-audios.ts` ; `docs/corpus-reference.md`, `docs/komz-themes.md` |
| Infrastructure | `deploy/ovh/README.md`, `deploy/ovh/docker-compose.candidate.yml`, `scripts/` ; modèles : `backend/models/README.md` |

## Vérifier proportionnellement

- Front changé : `npm run build:<app>` à la racine ; pas de build global sans besoin d’intégration.
- Live : `npm --prefix apps/live test` ; `backend/.venv/bin/python -m pytest backend/tests/test_live.py backend/tests/test_live_wav2vec2.py -q`.
- W2V fichier : `backend/tests/test_wav2vec2.py`, calibration : `test_transcription_calibration.py` ; compte/retours : `test_practice.py` ; email : `test_transcript_email.py`.
- Browser HTTP/WebSocket via l’origine du front : Nginx (`Host $http_host`) ou proxy Angular, jamais port 8100 directement dans le navigateur.
- `git diff --check` et revue des lignes changées. Documentation seule : vérifier chemins/cohérence, sans rebuild.

## Livraison : repères stables

- Local : backend 8100 ; portal/corpus/learning/record/transcribe/subtitles/live : 4100/4200/4300/4400/4500/4600/4800. Mobile preview : 4700.
- OVH : staging et production séparés ; source `/home/ubuntu/apps/keltiawave/releases/staging`, compose candidat, secrets dans `shared/.env.staging` (ne pas afficher), révision effective dans `DEPLOYED_GIT_SHA`.
- Déployer une révision commise/poussée, sauvegarder, vérifier les services et médias ; ne pas copier les données production vers staging par défaut. Lire le guide OVH avant toute mutation.
- W2V hors Git : local `backend/models/wav2vec2-cy`, serveur `/home/ubuntu/apps/keltiawave-models/wav2vec2-cy`, monté en lecture seule ; `W2V_CY_MODEL_PATH`. Ne pas réembarquer les poids dans une image/APK.
- Une livraison web ne met pas à jour le téléphone : build/sync/APK et installation séparés. Vérifier la révision et l’appareil réellement installés avant de l’annoncer.
