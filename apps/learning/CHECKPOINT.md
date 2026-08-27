# Point de reprise — KeltiaWave Learn

Date : 23 août 2026

## État stable

Le frontend `learning-frontend/` communique avec le module FastAPI
`backend/app/learning/` et réutilise les comptes du Corpus.

Fonctions opérationnelles :

- migrations Alembic jusqu’à `20260822_06` ;
- CRUD, brouillons, publication et archivage côté API ;
- contrôle du rôle admin dans l’interface et l’API ;
- stockage local ou S3/MinIO des MP4, WebM, MOV et MP3 ;
- jaquettes JPEG, PNG ou WebP ;
- réponses HTTP partielles permettant le seek audio ;
- catalogue avec grille, durée, jaquette et filtres verticaux ;
- parsing TXT, SRT et VTT ;
- conservation et reconstruction des timestamps en administration ;
- retours forcés avec `[br]` ;
- variantes, casse, apostrophes, espaces et mutations configurables pour les
  réponses ;
- transcription continue, segment actif surligné et centré ;
- découpage adaptatif des segments longs dans l’exercice ;
- lecteur et exercice alignés dans une présentation à deux panneaux ;
- sous-titres bretons ou français pendant la relecture du résultat ;
- traduction synchronisée et centrée sur le passage en cours ;
- résultat, traduction, vocabulaire et grammaire ;
- progression locale sans compte et synchronisée avec compte ;
- connexion, rôle, déconnexion et profils de test ;
- interface FR, BR ou EN pour les principaux écrans.
- durée du média modifiable et lien vers la source originale ;

## Commandes de reprise

```bash
./start_learning.sh
```

```bash
backend/.venv/bin/python -m pytest -q backend/tests
learning-frontend/node_modules/.bin/tsc -p learning-frontend/tsconfig.app.json --noEmit
learning-frontend/node_modules/.bin/ngc -p learning-frontend/tsconfig.app.json --outDir /tmp/keltia-learning-ngc
git diff --check
```

État au checkpoint : 10 tests backend passent, ainsi que TypeScript et Angular.

## Progression actuelle

`LearningProgress` conserve par utilisateur et leçon l’état, le meilleur score,
le total de questions, le nombre de tentatives et les dates. Un invité conserve
le même résumé dans le navigateur. Le détail des réponses historiques n’est pas
encore persisté.

## Limites connues

- logique Angular encore concentrée dans le composant principal ;
- aucun test unitaire Angular ni scénario navigateur automatisé ;
- mise en page adaptative à valider sur plusieurs appareils réels ;
- traduction à généraliser aux libellés avancés de l’administration ;
- une seule fiche de grammaire éditable ;
- fichier SRT/VTT source non stocké séparément ;
- durée non validée côté serveur par FFprobe ;
- réponses historiques détaillées non enregistrées ;
- migrations à valider sous PostgreSQL ;
- alignement au niveau segment, pas encore mot par mot.

## Prochaines étapes recommandées

1. persister les réponses détaillées de chaque tentative ;
2. ajouter tests Angular et scénario navigateur ;
3. extraire parsing, synchronisation et progression du composant principal ;
4. valider PostgreSQL et MinIO ;
5. terminer la traduction de l’administration ;
6. permettre plusieurs fiches de grammaire ;
7. étudier l’alignement automatique mot par mot.

## Garde-fous

- conserver Learning indépendant du frontend Corpus ;
- ne jamais exposer l’administration sans rôle `admin` ;
- conserver l’accès public aux leçons publiées ;
- ne pas stocker les médias lourds dans Git ;
- appliquer les migrations avant le démarrage ;
- exécuter tests, compilation et `git diff --check` avant chaque commit.
