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
le niveau de phrase et la source.

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

Déploiements publics :

- production : `https://komz.keltiawave.com` et `https://voices.keltiawave.com` ;
- staging : `https://komz.staging.keltiawave.com` et
  `https://library.staging.keltiawave.com`.

## Vérification

```bash
node_modules/.bin/tsc -p tsconfig.app.json --noEmit
node_modules/.bin/ngc -p tsconfig.app.json --outDir /tmp/keltia-komz-ngc
```
