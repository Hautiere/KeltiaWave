#!/usr/bin/env bash
set -Eeuo pipefail

# Point d'entrée depuis la racine du dépôt. Le script existant construit et
# démarre le backend et les sept fronts, vérifie leurs URL, puis ouvre la
# documentation de l'API et le portail dans le navigateur.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
exec "$PROJECT_DIR/scripts/start-docker.sh" "$@"
