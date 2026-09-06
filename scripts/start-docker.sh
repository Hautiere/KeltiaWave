#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ENV_FILE="${ENV_FILE:-$PROJECT_DIR/.env}"
COMPOSE_FILE="$PROJECT_DIR/deploy/docker-compose.yml"
BACKEND_HEALTH_URL="http://127.0.0.1:8100/"
BACKEND_URL="http://127.0.0.1:8100/docs"
PORTAL_URL="http://127.0.0.1:4100/"

usage() {
  cat <<'EOF'
Usage: ./scripts/start-docker.sh [--no-build] [--no-browser]

Construit et lance toute la pile Docker locale : infrastructure et backend,
puis les six applications frontend. Le script attend les services, exécute les
contrôles HTTP, puis ouvre le backend et le portail donnant accès aux apps.

Options:
  --no-build    Réutiliser les images Docker existantes.
  --no-browser  Ne pas ouvrir automatiquement le backend et le portail.

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

resolve_model_dir() {
  local variable_name="$1" relative_path="$2" required_file="$3"
  local model_path="$PROJECT_DIR/$relative_path" resolved_path

  if [[ ! -f "$model_path/$required_file" ]]; then
    echo "Modèle local absent : $model_path/$required_file" >&2
    echo "Exécutez ./scripts/link-legacy-models.sh avant de relancer Docker." >&2
    exit 1
  fi
  resolved_path="$(cd "$model_path" && pwd -P)"
  printf -v "$variable_name" '%s' "$resolved_path"
  export "$variable_name"
}

# Les modèles locaux peuvent être des liens symboliques vers l'ancien projet.
# Docker reçoit ici leurs chemins physiques afin qu'ils soient lisibles dans le
# conteneur, sans recopier plusieurs gigaoctets de données.
resolve_model_dir VOSK_MODEL_HOST_DIR "backend/models/vosk-model-br-25.02" "final.mdl"
resolve_model_dir WHISPER_BRETON_MODEL_HOST_DIR "backend/models/whisper-breton-ct2" "model.bin"
resolve_model_dir WHISPER_WELSH_MODEL_HOST_DIR "backend/models/whisper-welsh-ct2" "model.bin"

compose=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

echo "[1/5] Validation de la configuration Docker Compose"
"${compose[@]}" config --quiet

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

open_url() {
  if command -v open >/dev/null 2>&1; then
    open "$1" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$1" >/dev/null 2>&1 || true
  fi
}

backend_up_args=(up -d --remove-orphans)
$BUILD && backend_up_args+=(--build)
backend_up_args+=(postgres minio minio-init backend)

echo "[2/5] Construction et démarrage de l'infrastructure et du backend"
"${compose[@]}" "${backend_up_args[@]}"

echo "[3/5] Attente du backend"
if ! wait_for_url "Backend" "$BACKEND_HEALTH_URL"; then
  "${compose[@]}" ps -a >&2
  "${compose[@]}" logs --tail=120 backend postgres minio >&2
  exit 1
fi

frontend_up_args=(up -d)
$BUILD && frontend_up_args+=(--build)
frontend_up_args+=(portal corpus learning record transcribe subtitles)

echo "[4/5] Construction et démarrage des six applications frontend"
"${compose[@]}" "${frontend_up_args[@]}"

echo "[5/5] Vérification des conteneurs et contrôles HTTP"
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

failed=0
wait_for_url "Backend" "$BACKEND_HEALTH_URL" || failed=1
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
  open_url "$BACKEND_URL"
  sleep 2
  open_url "$PORTAL_URL"
fi

cat <<EOF

Backend : $BACKEND_URL
Portail et accès aux six applications : $PORTAL_URL

Pour arrêter la pile sans supprimer les données :
  docker compose --env-file '$ENV_FILE' -f '$COMPOSE_FILE' down
EOF
