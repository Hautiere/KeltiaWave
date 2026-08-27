# KeltiaWave Learn

Application Angular autonome d’apprentissage du breton par vidéo ou MP3. Elle
réutilise le backend, les comptes et les rôles du Corpus sans modifier son
frontend.

## Lancement local

Depuis la racine du dépôt :

```bash
./start_learning.sh
```

Cette commande applique les migrations Alembic, démarre FastAPI sur
`http://127.0.0.1:8000` et Angular sur `http://localhost:4300`. Le proxy Angular
redirige `/api` vers FastAPI.

Pour ne lancer que le frontend :

```bash
FRONTEND_MODE=learning ./start_frontend.sh
```

Dans ce cas, le backend doit déjà être actif.

## Parcours disponibles

- catalogue public avec recherche et filtres verticaux ;
- leçons accessibles sans connexion ;
- connexion facultative depuis **Sign in** ;
- progression locale pour un invité et synchronisée pour un compte connecté ;
- administration visible uniquement avec le rôle `admin` ;
- profils de test pour les parcours apprenant et admin ;
- interface FR, BR et EN ;
- accès direct depuis la progression au résultat, à la traduction, au
  vocabulaire et à la grammaire.

L’interface du lecteur utilise une mise en page à deux panneaux : le média reste
visible à gauche tandis que l’exercice, la correction ou les contenus de
révision s’affichent à droite. Les longs segments sont découpés en pages selon
la largeur de l’écran afin de conserver une zone de réponse lisible.

## Médias et jaquettes

Formats acceptés :

- vidéo : MP4, WebM et MOV ;
- audio : MP3 (`audio/mpeg`) ;
- jaquette : JPEG, PNG et WebP, 8 Mio maximum ;
- transcription : TXT, SRT et VTT.

La jaquette est affichée dans l’imagette 16:9 avec un recadrage proportionnel
centré. Pour un MP3, elle reste visible pendant l’écoute. La lecture locale
prend en charge HTTP `Range`, ce qui permet de se déplacer librement dans le
fichier audio.

## Transcription et synchronisation

Les timestamps SRT/VTT sont persistés en millisecondes et reconstruits au
format SRT lorsqu’une leçon est rouverte dans l’administration.

Pendant l’exercice :

- tout le texte reste dans une zone continue ;
- le segment correspondant au son est surligné ;
- le segment actif est automatiquement centré avec du contexte autour ;
- les retours internes des blocs SRT/VTT sont conservés ;
- le marqueur `[br]` force un retour à la ligne.
- la validation ignore la casse, les différences d’apostrophes et les espaces ;
- chaque trou peut accepter des variantes saisies par l’administrateur et,
  facultativement, les mutations bretonnes courantes.

Après la correction, le média peut être relu avec les sous-titres bretons ou,
lorsqu’elles existent, les traductions françaises. Dans l’onglet Traduction,
le segment courant est également surligné et recentré pendant la lecture.

```text
Demat deoc'h holl.[br]Hiziv e vo kaoz eus an amzer.
```

## Authentification et rôles

- invité : progression conservée dans `localStorage` ;
- apprenant ou enseignant : progression synchronisée avec le backend ;
- administrateur : création, modification, publication, médias et jaquettes ;
- déconnexion disponible dans le menu du compte.

L’ouverture directe de `/admin` sans rôle `admin` n’affiche pas l’éditeur. Les
routes d’écriture sont également protégées côté backend.

Profils locaux de test, créés avec `BOOTSTRAP_CLASS_USERS=true` :

| Profil | Adresse | Mot de passe | Rôle |
|---|---|---|---|
| Annaig Le Roux | `emsav1@keltia.test` | `classe123` | apprenant |
| Admin Learning | `learning.admin@keltia.test` | `classe123` | administrateur |

## Administration

Un administrateur peut créer ou rouvrir une leçon, charger une vidéo ou un
MP3, charger une jaquette, importer une transcription TXT/SRT/VTT, sélectionner
les mots masqués, saisir les contenus pédagogiques, prévisualiser, enregistrer
un brouillon et publier. La durée détectée peut être corrigée manuellement et un
lien vers la source originale, avec un libellé facultatif, peut être associé au
média. Pour chaque mot masqué, l’administrateur peut ajouter des variantes
séparées par des virgules et activer la tolérance des mutations. L’aperçu
d’administration suit les timestamps de la transcription.

## Vérifications

```bash
backend/.venv/bin/python -m pytest -q backend/tests
learning-frontend/node_modules/.bin/tsc -p learning-frontend/tsconfig.app.json --noEmit
git diff --check
```

Voir aussi [`CHECKPOINT.md`](./CHECKPOINT.md) et
[`ROADMAP.md`](./ROADMAP.md), ainsi que le
[`GUIDE_PRATIQUE.md`](./GUIDE_PRATIQUE.md) illustré.
