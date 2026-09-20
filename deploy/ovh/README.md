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

## Capacitor mobile CORS

The explicit allowlist includes `http://localhost`, `https://localhost` and
`capacitor://localhost`. Capacitor 8 defaults to HTTPS on Android and the
capacitor scheme on iOS; verify the actual WebView Origin when diagnosing errors.
`CORS_ALLOW_ORIGINS`, when nonempty, replaces the defaults completely.

For existing installations, append these three comma-separated origins to the
existing CORS_ALLOW_ORIGINS value in the private environment file. Preserve all
existing origins. Do not print or commit the environment file. Changing the
versioned defaults does not override an existing environment value.

Apply first to shared/.env.staging as part of the normal staging workflow.
After validation, the equivalent change belongs in
`/home/ubuntu/apps/keltiawave/shared/.env.production`. Recreate the backend with
the updated environment through the deployment workflow; a process restart alone
does not update the container environment. Never use a wildcard origin.

Validation order: tests, commit/push, staging deployment, preflight, then a short
Android Whisper transcription. The staging authentication proxy must also permit
the authorized test request to reach FastAPI; do not disable staging protection.

```sh
curl -i -X OPTIONS https://record.staging.keltiawave.com/api/record/transcribe \
  -H 'Origin: http://localhost' \
  -H 'Access-Control-Request-Method: POST'
```

Expect HTTP 200 and `Access-Control-Allow-Origin: http://localhost` when the
request reaches FastAPI. Repeat for HTTPS localhost and capacitor localhost.
The web root domain is not the Record API endpoint. Only validate the production
Record domain after the approved production deployment. A successful preflight
alone does not prove Whisper or audio upload works.

## Temporary Android Record staging access

Only `record.staging.keltiawave.com` has the temporary API routes. OPTIONS
preflights requesting POST on exactly `/api/record/transcribe` or
`/api/record/improve` reach FastAPI's explicit CORS policy without a session.
POST goes through `/verify-record`; a valid browser session or temporary Bearer
credential is required. Other hosts, paths and methods keep `/verify` and the
normal staging login. Unauthorized API requests return 401, with CORS headers
only for the three approved Capacitor origins. The Bearer header is removed
before forwarding audio to Record/backend.

The auth container must have `DEPLOY_SLOT=staging`. Temporary access is disabled
unless both `STAGING_RECORD_TOKEN_SHA256` (SHA-256 hex digest of a random token)
and `STAGING_RECORD_TOKEN_EXPIRES_AT` (Unix timestamp) are configured in the
private staging environment. Use a 32-byte random token with a two-hour lifetime.
Keep its plaintext out of environment files, Git, URLs, command arguments and
logs. Deliver it privately to the tester. Only the digest belongs in the staging
environment; recreate **staging-auth only** to apply it. Never configure it in
production. An expired token fails closed and does not affect browser sessions.

Build the mobile app with `ng build --configuration development`, then
`npx cap sync android`. In the backend settings use
`https://record.staging.keltiawave.com` and enter the token in the masked field.
It stays in memory, is sent only to the two exact URLs, and disappears when the
app process restarts or the tester clears it. Production builds never send it.

Validate Caddy before reloading the shared proxy. Patch only the Record staging
host block in the active file; preserve and compare every other byte. Keep a
backup for immediate rollback. Do not run the production promotion script.
Check public preflight, unauthorized 401, authorized short synthetic audio POST,
and that other staging applications still redirect to login. Then test Android
recording, playback, and Whisper with real speech.

After the test, clear both token environment entries and recreate staging-auth.
Restore the original Record staging block (normal staging security, staging auth,
and Record reverse_proxy), validate and reload Caddy. This removes the preflight
exception too. Delete the tester's private token file and clear the app field.
Run `python3 -m unittest discover -s deploy/ovh/staging-auth -p 'test_*.py'`
for the authentication regression suite.

Deployment note: a single-file Docker bind mount can still refer to an old inode
if its host file was previously replaced. Compare the host and container file
hashes before reloading. Copy the validated candidate into the container and
reload that exact path; do not assume `/etc/caddy/Caddyfile` matches the host.
Keep the host file updated for future container recreation. Until the stale mount
is repaired in a separate maintenance operation, a reload/restart from that old
mounted file can restore obsolete routing. Do not restart the shared proxy just
for this staging test. For rollback, copy the saved original into the container,
validate it and reload that explicit path as well.


## Remembered Android development access

A debug emulator may be provisioned once with a random 256-bit device credential.
`STAGING_RECORD_DEVICE_SHA256` stores only its SHA-256 digest in the private
staging environment. This credential has no periodic expiry and remains valid
until explicitly revoked; it is strictly limited to the existing two Record
Whisper POST endpoints and the staging slot. It never authorizes email, another
application, or production. Clear this environment variable and recreate only
staging-auth to revoke it. Existing browser login remains unchanged.

The Android debug plugin imports a private `files/staging-device.seed` once,
encrypts it with an Android Keystore AES-GCM key in no-backup storage, and deletes
the seed. The seed must be streamed through adb run-as, never passed on the
command line or included in the APK. Release builds do not return a credential.
App updates retain access; uninstalling or wiping emulator data requires new
provisioning. This is development-only device enrollment, not production user
authentication. A debug device remains accessible to its authorized adb operator.

### Lien de récupération du compte

Configurer `PASSWORD_RESET_URL=https://komz.staging.keltiawave.com/reinitialiser-mot-de-passe` dans `shared/.env.staging`. Le backend envoie désormais un lien à usage unique et la page demande de choisir le nouveau mot de passe. Le déploiement ajoute `auth_version` aux comptes pour invalider les sessions après réinitialisation. Voir [le parcours de récupération](../../docs/password-recovery.md).
