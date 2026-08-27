# Roadmap — KeltiaWave Learn

Mise à jour : 22 août 2026

## Cap produit

KeltiaWave Learn permet d’apprendre le breton à partir de vidéos ou de MP3
authentiques :

```text
admin → brouillon → publication → catalogue → exercice → résultat → progression
```

La réalisation d’une leçon reste publique. La connexion ajoute la
synchronisation de la progression. L’administration est strictement réservée au
rôle `admin`.

## Architecture retenue

- frontend Angular autonome dans `learning-frontend/` ;
- domaine FastAPI isolé dans `backend/app/learning/` ;
- comptes et tokens Bearer partagés avec le Corpus ;
- données métier et métadonnées en SQL ;
- médias en stockage local ou S3/MinIO ;
- SQLite en développement, PostgreSQL comme cible ;
- catalogue public limité aux leçons publiées.

## Livré

### Socle backend

- [x] modèles et schémas des leçons, médias, segments, trous et contenus ;
- [x] migrations Alembic réversibles ;
- [x] CRUD, publication et archivage ;
- [x] routes publiques et routes protégées par `require_admin` ;
- [x] tests API des droits, médias, jaquettes et progression ;
- [x] progression par utilisateur et leçon.

### Médias

- [x] MP4, WebM, MOV et MP3 ;
- [x] validation MIME, extension, signature et taille ;
- [x] stockage local ou S3/MinIO ;
- [x] métadonnées, durée déclarée et SHA-256 ;
- [x] HTTP `Range` pour se déplacer dans les médias locaux ;
- [x] jaquettes JPEG, PNG et WebP ;
- [x] jaquette 16:9 adaptative dans le catalogue ;
- [x] jaquette fixe pendant la lecture d’un MP3.

### Administration

- [x] connexion via le compte Corpus ;
- [x] affichage uniquement pour le rôle `admin` ;
- [x] profils locaux de test apprenant et administrateur ;
- [x] création et réouverture d’un brouillon ;
- [x] upload média et jaquette ;
- [x] parsing TXT, SRT et VTT ;
- [x] reconstruction SRT avec timestamps lors de la réouverture ;
- [x] durée détectée automatiquement et surcharge manuelle ;
- [x] URL de source originale et libellé de lien facultatif ;
- [x] aperçu média synchronisé avec les segments de transcription ;
- [x] sélection des mots masqués ;
- [x] variantes de réponse et mutations bretonnes configurables par trou ;
- [x] traductions, vocabulaire et grammaire ;
- [x] aperçu, sauvegarde et publication.

### Parcours apprenant

- [x] accès avec ou sans compte ;
- [x] catalogue en grille et filtres verticaux ;
- [x] lecteur vidéo ou audio ;
- [x] barre de seek audio précise ;
- [x] transcription continue synchronisée par segment ;
- [x] segment actif centré avec contexte autour ;
- [x] découpage adaptatif des segments trop longs selon la largeur disponible ;
- [x] retours forcés avec `[br]` ;
- [x] correction et meilleur score ;
- [x] comparaison tolérante à la casse, aux apostrophes et aux espaces ;
- [x] résultat, traduction, vocabulaire et grammaire ;
- [x] relecture avec sous-titres bretons ou traduction française ;
- [x] traduction synchronisée, surlignée et centrée pendant la lecture ;
- [x] accès direct à ces contenus depuis la progression ;
- [x] progression invitée locale et progression connectée côté serveur ;
- [x] interface principale FR, BR et EN.

## Prochain jalon — Fiabilisation

- [ ] ajouter des tests unitaires Angular pour parsing, score et pagination
  continue ;
- [ ] ajouter un test navigateur `profil → leçon → résultat → progression` ;
- [ ] extraire le parsing et la synchronisation du composant principal ;
- [ ] valider toutes les migrations sous PostgreSQL ;
- [ ] tester les gros médias et le seek avec MinIO ;
- [ ] ajouter la reprise des uploads interrompus ;
- [ ] supprimer automatiquement les objets de stockage orphelins ;
- [ ] valider la durée serveur avec FFprobe.

## Jalon suivant — Tentatives détaillées

- [ ] créer `LearningAttempt` et `LearningAnswer` ;
- [ ] conserver chaque réponse et le temps passé ;
- [ ] recalculer le score côté serveur ;
- [ ] afficher le détail d’une ancienne tentative ;
- [ ] ajouter suppression et politique de conservation ;
- [ ] produire un compte rendu téléchargeable.

## Améliorations pédagogiques

- [ ] synchronisation ou surlignage mot par mot ;
- [ ] assistance d’alignement automatique audio/transcription ;
- [ ] plusieurs points de grammaire par leçon ;
- [ ] nouveaux types de jeux : QCM, remise en ordre et répétition ;
- [ ] définir le parcours multi-activités à partir des
  [propositions UX](./docs/roadmap-proposals/README.md) ;
- [ ] parcours par niveau et recommandations ;
- [ ] statistiques par thème et compétences.

## Interface et accessibilité

- [ ] terminer la traduction FR/BR/EN de tous les écrans admin ;
- [ ] vérifier clavier, lecteur d’écran et contrastes ;
- [ ] valider sur appareils réels la mise en page adaptative du lecteur et des
  exercices ;
- [ ] conserver recherche et filtres dans l’URL ;
- [ ] ajouter états de chargement et reprise réseau détaillés.

## Déploiement

- [ ] ajouter l’entrée Learning au portail KeltiaWave ;
- [ ] définir URLs et variables par environnement ;
- [ ] documenter sauvegarde et restauration ;
- [ ] ajouter contrôles de disponibilité backend et stockage ;
- [ ] tester le parcours complet sans régression du Corpus.

## Critères de prochaine version

La prochaine version sera considérée stable lorsque :

1. PostgreSQL et MinIO auront été validés ;
2. le parcours complet disposera d’un test navigateur ;
3. une tentative conservera ses réponses détaillées ;
4. la totalité de l’interface sera traduite ;
5. le frontend Learning n’introduira aucune régression dans le Corpus.
