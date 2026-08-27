#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ENV_FILE="${ENV_FILE:-$PROJECT_DIR/.env}"
COMPOSE_FILE="$PROJECT_DIR/deploy/docker-compose.yml"
PORTAL_URL="http://127.0.0.1:4100/"

usage() {
  cat <<'EOF'
Usage: ./scripts/start-docker.sh [--no-build] [--no-browser]

Construit et lance toute la pile Docker locale, attend que les services soient
disponibles, exécute des contrôles HTTP, puis ouvre le portail.

Options:
  --no-build    Réutiliser les images Docker existantes.
  --no-browser  Ne pas ouvrir automatiquement le portail.

Variables:
  ENV_FILE      Fichier d'environnement (par défaut : .env à la racine).
EOF
}

BUILD=true
OPEN_BROWSER=true
while (($#)); do
  case "$1" in
    --no-build) BUILD=false ;;
    --no-browser) OPEN_BROWSER=false ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
  shift
done

command -v docker >/dev/null 2>&1 || {
  echo "Docker est introuvable. Installez et démarrez Docker Desktop." >&2
  exit 1
}
command -v curl >/dev/null 2>&1 || {
  echo "curl est requis pour les contrôles de santé." >&2
  exit 1
}
docker info >/dev/null 2>&1 || {
  echo "Docker ne répond pas. Démarrez Docker Desktop puis réessayez." >&2
  exit 1
}
docker compose version >/dev/null 2>&1 || {
  echo "Le plugin Docker Compose est requis." >&2
  exit 1
}
[[ -f "$ENV_FILE" ]] || {
  echo "Fichier manquant : $ENV_FILE" >&2
  echo "Copiez .env.example vers .env et remplacez les secrets de démonstration." >&2
  exit 1
}

env_value() {
  local name="$1" value="${!1:-}"
  if [[ -z "$value" ]]; then
    value="$(sed -n "s/^${name}=//p" "$ENV_FILE" | tail -n 1)"
  fi
  printf '%s' "$value"
}

existing_service_value() {
  local name="$1" service="$2" container_id
  container_id="$(docker ps -aq \
    --filter "label=com.docker.compose.project.config_files=$COMPOSE_FILE" \
    --filter "label=com.docker.compose.service=$service" | head -n 1)"
  [[ -n "$container_id" ]] || return 0
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$container_id" \
    | sed -n "s/^${name}=//p" | tail -n 1
}

append_if_missing() {
  local name="$1" value="$2" service="$3" existing
  if [[ -z "$(env_value "$name")" ]]; then
    existing="$(existing_service_value "$name" "$service")"
    [[ -z "$existing" ]] || value="$existing"
    printf '\n%s=%s\n' "$name" "$value" >>"$ENV_FILE"
    echo "  Initialisation locale : $name"
  fi
}

append_secret_if_missing() {
  local name="$1" bytes="$2" service="$3"
  if [[ -z "$(env_value "$name")" ]]; then
    append_if_missing "$name" "$(openssl rand -hex "$bytes")" "$service"
  fi
}

if [[ -z "$(env_value SECRET_KEY)" || -z "$(env_value POSTGRES_PASSWORD)" || -z "$(env_value MINIO_ROOT_PASSWORD)" ]]; then
  command -v openssl >/dev/null 2>&1 || {
    echo "openssl est requis pour générer les secrets Docker locaux." >&2
    exit 1
  }
  echo "Préparation des paramètres Docker absents dans $ENV_FILE"
fi

append_secret_if_missing SECRET_KEY 64 backend
append_if_missing POSTGRES_USER "keltiawave" postgres
append_secret_if_missing POSTGRES_PASSWORD 32 postgres
append_if_missing MINIO_ROOT_USER "keltiawave" minio
append_secret_if_missing MINIO_ROOT_PASSWORD 32 minio
append_if_missing BOOTSTRAP_CLASS_USERS "true" backend
append_if_missing BOOTSTRAP_CLASS_PASSWORD "classe123" backend
chmod 600 "$ENV_FILE"

compose=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

echo "[1/4] Validation de la configuration Docker Compose"
"${compose[@]}" config --quiet

echo "[2/4] Construction et démarrage de la pile"
up_args=(up -d --remove-orphans)
$BUILD && up_args+=(--build)
"${compose[@]}" "${up_args[@]}"

echo "[3/4] Vérification de l'état des conteneurs"
expected_services=(backend portal corpus learning record transcribe subtitles postgres minio)
running_services="$("${compose[@]}" ps --services --status running)"
containers_failed=0
for service in "${expected_services[@]}"; do
  if grep -qx "$service" <<<"$running_services"; then
    printf '  OK  %s\n' "$service"
  else
    printf '  ÉCHEC  %s n’est pas actif\n' "$service" >&2
    containers_failed=1
  fi
done
if ((containers_failed)); then
  "${compose[@]}" ps -a >&2
  echo "Consultez les journaux avec :" >&2
  echo "  docker compose --env-file '$ENV_FILE' -f '$COMPOSE_FILE' logs --tail=200" >&2
  exit 1
fi

wait_for_url() {
  local label="$1" url="$2" attempt
  for attempt in $(seq 1 60); do
    if curl --fail --silent --show-error --max-time 5 "$url" >/dev/null 2>&1; then
      printf '  OK  %-12s %s\n' "$label" "$url"
      return 0
    fi
    sleep 2
  done
  printf '  ÉCHEC  %-9s %s\n' "$label" "$url" >&2
  return 1
}

echo "[4/4] Attente et contrôles HTTP"
failed=0
wait_for_url "Backend" "http://127.0.0.1:8100/" || failed=1
wait_for_url "Portal" "$PORTAL_URL" || failed=1
wait_for_url "À propos" "http://127.0.0.1:4100/about.html" || failed=1
wait_for_url "Feedback" "http://127.0.0.1:4100/feedback.html" || failed=1
wait_for_url "Corpus" "http://127.0.0.1:4200/" || failed=1
wait_for_url "Learning" "http://127.0.0.1:4300/" || failed=1
wait_for_url "Record" "http://127.0.0.1:4400/" || failed=1
wait_for_url "Transcribe" "http://127.0.0.1:4500/" || failed=1
wait_for_url "Subtitles" "http://127.0.0.1:4600/" || failed=1

# Vérifie le contenu du vrai conteneur Portal, même si un ancien serveur local
# occupe déjà le port 4100 du Mac.
"${compose[@]}" exec -T portal wget -q --spider http://127.0.0.1/about.html || failed=1
"${compose[@]}" exec -T portal wget -q --spider http://127.0.0.1/feedback.html || failed=1

if ((failed)); then
  echo >&2
  echo "Au moins un service ne répond pas. État des conteneurs :" >&2
  "${compose[@]}" ps >&2
  echo "Consultez les journaux avec :" >&2
  echo "  docker compose --env-file '$ENV_FILE' -f '$COMPOSE_FILE' logs --tail=200" >&2
  exit 1
fi

echo "Tous les services et les pages du portail répondent."
"${compose[@]}" ps

if $OPEN_BROWSER; then
  if command -v open >/dev/null 2>&1; then
    open "$PORTAL_URL" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$PORTAL_URL" >/dev/null 2>&1 || true
  fi
fi

cat <<EOF

KeltiaWave est disponible sur $PORTAL_URL

Pour arrêter la pile sans supprimer les données :
  docker compose --env-file '$ENV_FILE' -f '$COMPOSE_FILE' down
EOF
