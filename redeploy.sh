#!/bin/bash
# ============================================================
# redeploy.sh — Met a jour le code sur le serveur SANS toucher
# aux donnees existantes (pas de -v, jamais).
#
# A lancer sur le SERVEUR, depuis le dossier bsb-latest-version deja clone :
#   git pull doit avoir ete fait au prealable OU est fait ici.
#   ./redeploy.sh
# ============================================================
set -e

echo "=== 1. Recuperation du code ==="
git pull

echo ""
echo "=== 2. Arret propre (AUCUN volume supprime) ==="
docker compose down

echo ""
echo "=== 3. Reconstruction + redemarrage ==="
docker compose up -d --build

echo ""
echo "=== 4. Attente du demarrage (10s) ==="
sleep 10
docker compose ps

echo ""
echo "=== 5. Migrations (inclut 0036 + 0037_merge - fusionne deux branches de migration divergentes, AJOUTE un champ + une permission, ne supprime aucune donnee) ==="
docker compose exec -T suudu_backend python manage.py migrate

echo ""
echo "=== 6. Verifications ==="
echo -n "Page d'accueil (attendu 200/302) : "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/

echo -n "Blocage .map (attendu 404) : "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/static/vendor/adminlte/js/adminlte.min.js.map

echo -n "CSP present : "
curl -s -I http://localhost/ | grep -i "content-security-policy" || echo "ABSENT - a verifier"

echo -n "Referrer-Policy sur /static/ : "
curl -s -I http://localhost/static/css/output.css | grep -i "referrer-policy" || echo "ABSENT - a verifier"

echo -n "jQuery local vendorise (attendu 200) : "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/static/vendor/jquery/jquery.min.js

echo -n "Ancien Bootstrap5 vendorise bien absent (attendu 404) : "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/static/vendor/bootstrap5/css/bootstrap.min.css

echo ""
echo "=== 7. Verification manuelle des donnees existantes ==="
echo "Connectez-vous sur le site et confirmez que les comptes/centres/inscriptions"
echo "crees avant cette mise a jour sont toujours presents."
echo "Testez aussi le flux d'encaissement complet (modale de paiement) sur"
echo "une page 'Detail dette' - c'est la partie reecrite avec le plus de risque."

echo ""
echo "=== Logs backend (Ctrl+C pour quitter) ==="
docker compose logs -f suudu_backend
