# Livraison OVH du 7 novembre 2026 : Komz et Listen

## Révision et périmètre

Révision applicative staging et production :
`1e533e233096af405a1013a63baba0bdaefc2f11`.
Tag : `web-2026-11-07-komz-listen-mobile-compact`.

Cette livraison inclut l’explorateur partagé Komz/Listen avec sous-domaines,
les parcours distincts de pratique et d’écoute, les ajustements mobiles
(onglets défilants, icônes compactes, libellés équilibrés de quatre mots maximum,
retours de prononciation compacts), le filtre gallois du portail, W2V dans
Subtitles et les traductions du jeu Play. Aucun import de données n’a été lancé.

## Sauvegarde et procédure

Sauvegardes sur le VPS :
`/home/ubuntu/apps/keltiawave/shared/backups/production/pre-mobile-20261107-1e533e2/`.

Les sous-répertoires `production/` et `staging/` contiennent PostgreSQL, les
médias MinIO, les données backend, les sources et les empreintes des lignes
existantes. Les fichiers `SHA256SUMS` ont été vérifiés. Le routage Caddy hôte et
conteneur a également été sauvegardé. Les images précédentes sont conservées
sous `keltiawave-rollback-1e533e2-<slot>-<service>`.

L’archive provient exclusivement du tag commis et poussé. Les images sont
construites dans un répertoire staging isolé puis validées sur staging avant
promotion des mêmes images en production. Les volumes, secrets et comptes
production sont conservés ; `production-preserve-users.yml` désactive les
initialisations de comptes. Live garde le port production `24800`.
Les sources précédentes restent dans `releases/production-pre-mobile-1e533e2`.
Un retour automatique aux images précédentes était prévu en cas d’échec des
contrôles ; il n’a pas été nécessaire. Caddy n’a pas été modifié ni rechargé.

## Résultats vérifiés

- Builds serveur des sept fronts et du backend réussis ; 16 tests Corpus et
  6 tests API Subtitles réussis localement.
- Backend et sept fronts sains sur staging puis production.
- 1 436 phrases, 5 leçons et 5 vidéos accessibles ; lecture vidéo Range de
  1 024 octets validée via le front.
- Audit des 16 tables : aucune ligne préexistante modifiée ou supprimée sur
  staging et production. Production : 16 comptes, 1 436 phrases, 1 353 audios.
- Huit domaines publics en HTTP 200 : portail, Komz, Voices, Learning, Record,
  Transcribe, Subtitles et Live.
- Les fichiers JavaScript publics des sept domaines applicatifs correspondent
  exactement aux conteneurs production ; leurs images sont identiques à celles
  validées sur staging.
- Une référence audio approuvée est lisible publiquement ; `/api/audios/mine`
  refuse une requête anonyme avec HTTP 401.
- Empreintes des fichiers Caddy hôte et conteneur inchangées.

La recette visuelle navigateur n’a pas pu être achevée : les outils navigateur
ont échoué à ouvrir la fenêtre de contrôle. Les contrôles HTTP, données et
fichiers ne prouvent pas le rendu sur chaque téléphone. Aucun enregistrement
microphone réel ni test de qualité de reconnaissance galloise n’a été effectué.

Le commit documentaire de compte rendu est postérieur au tag applicatif ; il
ne change pas la révision des images livrées.
