#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd -P)"
BACKEND_DIR="$PROJECT_DIR/backend"
ENV_FILE="$PROJECT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# Les chemins du fichier .env sont résolus depuis la racine du projet,
# indépendamment du répertoire courant utilisé ensuite par Uvicorn.
MODELS_ROOT="${MODELS_ROOT:-backend/models}"
if [[ "$MODELS_ROOT" != /* ]]; then
  MODELS_ROOT="$PROJECT_DIR/$MODELS_ROOT"
fi
export MODELS_ROOT
DATABASE_URL="${DATABASE_URL:-sqlite:///$BACKEND_DIR/keltiawave.db}"
if [[ "$DATABASE_URL" == sqlite:///* ]]; then
  SQLITE_PATH="${DATABASE_URL#sqlite:///}"
  if [[ "$SQLITE_PATH" != /* ]]; then
    if [[ "$SQLITE_PATH" == ./* ]]; then
      SQLITE_PATH="$BACKEND_DIR/${SQLITE_PATH#./}"
    else
      SQLITE_PATH="$PROJECT_DIR/$SQLITE_PATH"
    fi
    DATABASE_URL="sqlite:///$SQLITE_PATH"
  fi
fi
export DATABASE_URL

cd "$BACKEND_DIR"
VENV_DIR="${VENV_DIR:-.venv}"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

PYTHON="$VENV_DIR/bin/python"
if [ "${INSTALL_DEPS:-1}" = "1" ]; then
  "$PYTHON" -m pip install -r requirements.txt
fi

"$PYTHON" -m app.bootstrap_db
"$PYTHON" -m alembic upgrade head

UVICORN_ARGS=(app.main:app --host "${HOST:-127.0.0.1}" --port "${BACKEND_PORT:-8100}")
if [ "${RELOAD:-1}" = "1" ]; then
  UVICORN_ARGS+=(--reload)
fi
exec "$PYTHON" -m uvicorn "${UVICORN_ARGS[@]}"
