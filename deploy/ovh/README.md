# Déploiement OVH sans régression

Le déploiement est volontairement séparé en deux opérations :

1. `deploy-ovh.sh --apply` construit une pile **candidate isolée**, liée seulement
   à des ports `127.0.0.1`. Le site actuel et Caddy ne sont jamais modifiés ;
2. la promotion publique sera ajoutée après un audit en lecture seule du VPS,
   la copie vérifiée de PostgreSQL/MinIO et la validation des domaines DNS.

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

## Simulation puis déploiement candidat

```bash
SSH_TARGET=ubuntu@your-ovh-host.example ./scripts/deploy-staging-ovh.sh
SSH_TARGET=ubuntu@your-ovh-host.example ./scripts/deploy-staging-ovh.sh --apply --with-local-data
```

Variables facultatives :

```bash
SSH_TARGET=ubuntu@your-ovh-host.example
REMOTE_ROOT=/home/ubuntu/apps/keltiawave
DEPLOY_SLOT=staging
```

Le transfert principal exclut `.env`, les bases locales, les fichiers utilisateurs
et les modèles. L'option `--with-local-data` sauvegarde d'abord PostgreSQL et
MinIO dans `shared/backups/staging/`, transfère explicitement le SQLite et les
médias validés, puis exécute la migration contrôlée. Le script refuse l'import si
les comptes diffèrent ou si les tables métier du staging ne sont pas vides.

Le script refuse de déclarer le candidat valide si les contrôles ne
retrouvent pas au minimum 105 phrases Komz et 4 leçons Learning. Il est donc
normal que le premier passage s'arrête avant validation tant que les données
PostgreSQL et MinIO n'ont pas été migrées vers la pile candidate.

## Retour arrière

Avant la future promotion, l'ancienne pile reste en fonctionnement. Le retour
arrière consistera uniquement à remettre Caddy sur ses anciennes cibles puis à
recharger sa configuration. La pile candidate peut être arrêtée sans toucher à
la production :

```bash
cd /home/ubuntu/apps/keltiawave/releases/candidate
docker compose --env-file /home/ubuntu/apps/keltiawave/shared/.env.candidate \
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
