#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export DEPLOY_SLOT=production
exec "$SCRIPT_DIR/deploy-ovh.sh" --clone-from-slot staging "$@"
