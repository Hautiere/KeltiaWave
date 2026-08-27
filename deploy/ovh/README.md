# Déploiement OVH sans régression

Le déploiement est volontairement séparé en deux opérations :

1. `deploy-ovh.sh --apply` construit une pile **candidate isolée**, liée seulement
   à des ports `127.0.0.1`. Le site actuel et Caddy ne sont jamais modifiés ;
2. la promotion publique sera ajoutée après un audit en lecture seule du VPS,
   la copie vérifiée de PostgreSQL/MinIO et la validation des domaines DNS.

## Préparation unique sur le VPS

```bash
mkdir -p /home/ubuntu/apps/keltiawave/shared
cp deploy/ovh/.env.candidate.example \
  /home/ubuntu/apps/keltiawave/shared/.env.candidate
chmod 600 /home/ubuntu/apps/keltiawave/shared/.env.candidate
```

Remplacer tous les secrets et renseigner `MODELS_DIR`. Ce répertoire doit déjà
contenir les modèles Vosk et Whisper ; aucun modèle n'est téléchargé pendant le
déploiement.

## Simulation puis déploiement candidat

```bash
./scripts/deploy-ovh.sh
./scripts/deploy-ovh.sh --apply
```

Variables facultatives :

```bash
SSH_TARGET=ubuntu@vps-dc75d8a6.vps.ovh.net
REMOTE_ROOT=/home/ubuntu/apps/keltiawave
DEPLOY_SLOT=candidate
```

Le transfert exclut `.env`, les bases locales, les fichiers utilisateurs et les
modèles. Le script refuse de déclarer le candidat valide si les contrôles ne
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
