# KeltiaWave Komz — Frontend Angular

## Lancement local

1. Installer les dépendances :
   npm install
2. Lancer le serveur de dev :
   ng serve
3. Accéder à l'app :
   http://localhost:4200

## Structure du projet

- `src/app/pages` : une page par fonctionnalité principale
- `src/app/core` : services, constantes, gestion API
- `src/app/shared` : composants UI réutilisables

## Parcours par rôle

- Élève : `Voix validées`, `My progress`, `Practice`, `Compte`.
- Professeur : `My class`, correction/écoute, `Écrire`, `Compte`.
- Administrateur : gestion des audios, phrases et comptes.

La bibliothèque publique ne présente que les audios dont la dernière décision
professeur ou administrateur est positive. Sa matrice est triable par phrase,
thème, niveau de prononciation, région/pays et date. Les filtres couvrent aussi
le niveau de phrase et la source. Une source Internet est affichée sous forme de
lien externe ; un niveau de prononciation absent est affiché `NA`.

Lors de la création d'une phrase, le professeur peut choisir `Internet` et doit
alors renseigner l'URL HTTP(S) d'origine. L'administration permet de modifier la
source et son URL, le domaine, le niveau de phrase et les métadonnées du locuteur
(région/pays, ville, accent, niveau et nom). Les valeurs historiques qui ne font
pas partie des listes prédéfinies sont conservées via les choix `Autre`.

L'onglet Données de l'administration peut importer un jeu de données validées à
partir d'un fichier de métadonnées et d'une archive contenant les MP3 associés.

`My progress` présente les enregistrements de l'élève avec leur dernier statut
et le commentaire du professeur. `My class` regroupe les enregistrements par
classe pour le professeur. Les lecteurs utilisent tous le composant visuel
compact bouton bleu + sinusoïde.

L'élève ne valide pas les enregistrements et ne voit pas le menu Admin. La
création de phrases est réservée aux professeurs et administrateurs ; thème et
niveau sont obligatoires.

Komz et Library utilisent le même frontend et le même backend, mais sont
exposées par deux domaines distincts. L'enregistrement associe explicitement
chaque fichier à son `phrase_id` ; le stockage ajoute un UUID pour éviter les
collisions. Sur l'écran d'évaluation, les réponses asynchrones devenues
obsolètes sont ignorées afin que le texte reste toujours celui de l'audio
sélectionné.

Les liens du logo ciblent automatiquement le portail local sur `127.0.0.1:4100`,
le portail staging sur `staging.keltiawave.com`, ou le portail de production.

Déploiements publics :

- production : `https://komz.keltiawave.com` et `https://voices.keltiawave.com` ;
- staging : `https://komz.staging.keltiawave.com` et
  `https://library.staging.keltiawave.com`.

## Vérification

```bash
node_modules/.bin/tsc -p tsconfig.app.json --noEmit
node_modules/.bin/ngc -p tsconfig.app.json --outDir /tmp/keltia-komz-ngc
```
