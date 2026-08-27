#!/usr/bin/env bash
set -euo pipefail

FRONT_URL="http://localhost:4200"
echo "=== 🔎 Test FRONTEND ($FRONT_URL) ==="

# 1) Vérifier que le front est lancé
echo "- Check front root"
curl -fs $FRONT_URL | head -n 10

# 2) Vérifier que le proxy marche pour les phrases
echo "- Proxy /api/phrases/"
curl -fs $FRONT_URL/api/phrases/ | jq .

# 3) Vérifier que la page Accueil contient le mot "Accueil"
echo "- Page Accueil"
curl -fs $FRONT_URL | grep -q "Accueil" && echo "✔ Accueil OK"

# 4) Vérifier que la page Enregistrement contient le mot "Enregistrement"
echo "- Page Enregistrement"
curl -fs $FRONT_URL/enregistrement | grep -q "Enregistrement" && echo "✔ Enregistrement OK"

echo "✅ Tests frontend terminés avec succès"
