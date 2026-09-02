# Déploiement OVH sans régression

Le déploiement est séparé en trois opérations :

1. `deploy-staging-ovh.sh --apply` met à jour le staging persistant ;
2. `deploy-production-candidate-ovh.sh --apply` construit une pile production
   isolée et clone les données validées du staging ;
3. `promote-production-ovh.sh --apply` sauvegarde l'existant, bascule Caddy et
   contrôle tous les domaines avec rollback automatique.

Sans `--apply`, les scripts de déploiement et de promotion restent en simulation.

## Préparation unique sur le VPS

```bash
mkdir -p /home/ubuntu/apps/keltiawave/shared
cp deploy/ovh/.env.staging.example \
  /home/ubuntu/apps/keltiawave/shared/.env.staging
chmod 600 /home/ubuntu/apps/keltiawave/shared/.env.staging
```

Remplacer tous les secrets et renseigner `MODELS_DIR`. Ce répertoire doit déjà
contenir les modèles Vosk et Whisper ; aucun modèle n'est téléchargé pendant le
déploiement.

## Simulation puis déploiement staging

```bash
SSH_TARGET=ubuntu@your-ovh-host.example ./scripts/deploy-staging-ovh.sh
SSH_TARGET=ubuntu@your-ovh-host.example ./scripts/deploy-staging-ovh.sh --apply
```

Variables facultatives :

```bash
SSH_TARGET=ubuntu@your-ovh-host.example
REMOTE_ROOT=/home/ubuntu/apps/keltiawave
DEPLOY_SLOT=staging
```

Le transfert principal exclut `.env`, les bases locales, les fichiers utilisateurs
et les modèles. Il est produit avec `git archive origin/main` : seuls les fichiers
commités et poussés sont déployés, même si le répertoire local contient d'autres
modifications. `DEPLOY_REF` permet de cibler explicitement un tag ou un commit.

L'option initiale `--with-local-data` sauvegarde d'abord PostgreSQL et
MinIO dans `shared/backups/staging/`, transfère explicitement le SQLite et les
médias validés, puis exécute la migration contrôlée. Le script refuse l'import si
les comptes diffèrent ou si les tables métier du staging ne sont pas vides.

Le script refuse de déclarer le staging valide si les contrôles ne retrouvent
pas au minimum 105 phrases Komz, 4 leçons et 4 vidéos Learning. Une requête HTTP
Range de 1024 octets vérifie également la lecture progressive des vidéos.

Le staging public est protégé par une page de connexion unique. Le cookie de
session est partagé par `*.staging.keltiawave.com`, ce qui évite une nouvelle
saisie du mot de passe dans chaque application.

## Retour arrière

La promotion conserve l'ancienne pile en fonctionnement. En cas d'échec d'un
contrôle public, le script recharge immédiatement le Caddyfile sauvegardé. La
pile staging peut être arrêtée sans toucher à la production :

```bash
cd /home/ubuntu/apps/keltiawave/releases/staging
docker compose --env-file /home/ubuntu/apps/keltiawave/shared/.env.staging \
  -f deploy/ovh/docker-compose.candidate.yml down
```

Ne pas ajouter `--volumes` : les volumes candidats doivent rester récupérables.

## Références locales et portabilité

Les références `127.0.0.1` conservées dans les fichiers OVH servent uniquement
à lier les ports de la pile de staging à l'interface loopback et à exécuter les
healthchecks depuis le VPS. Les noms `backend`, `postgres` et `minio` sont des
noms DNS internes au réseau Compose. Ils ne sont jamais envoyés au navigateur.

Les fronts utilisent `/api`, résolu par Nginx vers le backend Docker. Aucun front
déployé ne dépend donc d'un backend installé sur la machine de développement.
Les scripts `start-*`, les proxies Angular et les branches locales du portail
conservent volontairement leurs URLs localhost pour le développement uniquement.

## Préparer la production depuis le staging validé

La production est une pile distincte : elle ne réutilise ni les conteneurs ni
les volumes du staging. Préparer d'abord le fichier secret sur le VPS :

```bash
cp deploy/ovh/.env.production.example \
  /home/ubuntu/apps/keltiawave/shared/.env.production
chmod 600 /home/ubuntu/apps/keltiawave/shared/.env.production
```

Générer de nouveaux secrets PostgreSQL, MinIO et applicatifs, puis construire
la candidate production en clonant les données du staging :

```bash
SSH_TARGET=ubuntu@your-ovh-host.example \
  ./scripts/deploy-production-candidate-ovh.sh

SSH_TARGET=ubuntu@your-ovh-host.example \
  ./scripts/deploy-production-candidate-ovh.sh --apply
```

Le clonage sauvegarde d'abord les volumes de destination, exporte PostgreSQL et
MinIO depuis le staging, restaure ces exports dans les volumes `production`, puis
redémarre les proxys frontend pour renouveler la résolution Docker du backend et
relance les tests fonctionnels. Le staging et l'ancienne production restent actifs.

## Rafraîchir les données staging depuis la production

Cette opération ne redéploie pas le code. Elle sauvegarde les données staging,
copie PostgreSQL et MinIO depuis la production, puis contrôle les deux piles :

```bash
SSH_TARGET=ubuntu@your-ovh-host.example \
  ./scripts/refresh-staging-data-from-production.sh

SSH_TARGET=ubuntu@your-ovh-host.example \
  ./scripts/refresh-staging-data-from-production.sh --apply
```

Sans `--apply`, la commande reste en simulation. La restauration remplace les
données staging mais conserve son code, ses domaines et ses secrets propres.

La zone DNS OVH peut utiliser un wildcard A vers l'IPv4 du VPS :

```text
*.keltiawave.com -> 51.178.38.152
```

Il couvre les domaines Learning, Komz, Voices, Transcribe, Record et Subtitles.
Le wildcard distinct `*.staging.keltiawave.com` reste plus spécifique et ne
conflite pas avec la production. Les domaines racines sont déclarés séparément.

La promotion est également un dry-run par défaut. Elle vérifie la révision Git,
les contenus et tous les DNS avant d'autoriser la bascule :

```bash
SSH_TARGET=ubuntu@your-ovh-host.example PUBLIC_IPV4=51.178.38.152 \
  ./scripts/promote-production-ovh.sh

SSH_TARGET=ubuntu@your-ovh-host.example PUBLIC_IPV4=51.178.38.152 \
  ./scripts/promote-production-ovh.sh --apply
```

Avec `--apply`, le script sauvegarde le Caddyfile et les données de l'ancienne
production, valide la nouvelle configuration, recharge Caddy sans arrêter les
anciens conteneurs, attend l'émission des certificats TLS, teste tous les domaines
publics et restaure automatiquement l'ancien routage si un contrôle échoue.

Les sauvegardes de promotion se trouvent dans
`/home/ubuntu/apps/keltiawave/shared/backups/pre-promotion-*`. Elles contiennent
le Caddyfile, PostgreSQL, MinIO, les données de l'application historique et les
empreintes SHA-256.
