#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd -P)"
LEGACY_MODELS="${1:-$PROJECT_DIR/../breizh-transcriptor-whisper/backend/app/models}"
TARGET="$PROJECT_DIR/backend/models"

if [ ! -d "$LEGACY_MODELS" ]; then
  echo "Répertoire de modèles introuvable : $LEGACY_MODELS" >&2
  exit 1
fi

mkdir -p "$TARGET"
for model in vosk-model-br-25.02 whisper-breton-ct2 whisper-welsh-ct2; do
  if [ -d "$LEGACY_MODELS/$model" ] && [ ! -e "$TARGET/$model" ]; then
    ln -s "$LEGACY_MODELS/$model" "$TARGET/$model"
    echo "Modèle lié : $model"
  fi
done
