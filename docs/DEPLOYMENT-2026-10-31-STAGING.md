# Livraison staging OVH — 31 octobre 2026

## Révisions et périmètre

- Code web/backend déployé : `c0ab733fe33af72041b50aa00352efbe02cea5cf`,
  branche GitHub `fix/capacitor-cors`.
- Source mobile : `0e998d9` ; documentation mobile à jour dans `c730de5`,
  branche GitHub `fix/android-vosk-live` du dépôt KeltiaWave-Mobile.
- La documentation de livraison est publiée après le déploiement ; elle ne
  modifie pas la révision applicative ci-dessus.
- Aucun déploiement production, import local ou clonage de données.
- Les modifications Learning non commises et les fichiers de consignes locaux
  n’ont pas été inclus. Aucun modèle, secret ou APK n’est poussé.

## Déploiement

Livraison par `scripts/deploy-staging-ovh.sh --apply` avec `DEPLOY_REF` fixé au SHA
web/backend. Le code staging précédent a été sauvegardé dans
`shared/backups/staging/code-before-20261031/` avant remplacement.

Le routage `live.staging.keltiawave.com` a été ajouté au Caddyfile actif, sous les
mêmes contrôles d’accès staging que les autres apps. Le fichier précédent est
sauvegardé dans `Caddyfile.before-live` dans le même dossier de sauvegarde.
La configuration a été validée puis rechargée ; les routes production existantes
ont été conservées.

## Contrôles réussis

- 174 tests backend ; 12 tests Live web ; 7 tests d’attribution/références corpus ;
  6 tests mobile ; builds ciblés et contrôle des scripts de déploiement.
- Tous les services staging démarrés et sains.
- Contrôles de fumée : pages backend/Portal/Corpus/Learning/Record/Transcribe/
  Subtitles/Live, 786 phrases Komz, 5 leçons et 5 vidéos Learning.
- Lecture vidéo partielle HTTP Range : 1 024 octets.
- Connexion staging authentifiée : portail et sept parcours applicatifs publics
  accessibles, nouveaux bundles et carte Live rose présents.
- API Live publique : Vosk et Whisper breton disponibles.
- WebSocket Live via le frontend Nginx : `ready`, PCM silencieux synthétique,
  finalisation et `done` ; aucun audio utilisateur utilisé pour ce contrôle.
- Live sans session staging : redirection 302 ; `/api/audios/mine` sans session
  applicative : refus 401.

## Conservation des données et de la production

Avant et après : **786 phrases, 697 audios, 15 comptes** en staging.
L’image backend production est restée
`sha256:da60453e43fb20c7be4a122a872618306b4aabc8c5a069df70688586626b9132`.

## Accès et limites

- Portail : <https://staging.keltiawave.com/>
- Live : <https://live.staging.keltiawave.com/>
- Komz : <https://komz.staging.keltiawave.com/lire>
- Listen : <https://library.staging.keltiawave.com/>
- Compte : <https://komz.staging.keltiawave.com/compte>

L’authentification staging reste requise, puis la connexion applicative pour
les contributions personnelles. Les tests synthétiques ne remplacent pas la
recette d’un podcast réel, le consentement navigateur ni la capture Android sur
un téléphone physique. L’APK mobile n’est pas distribué par cette livraison OVH.
