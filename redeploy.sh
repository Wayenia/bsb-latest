#!/bin/bash
# Mise a jour d'un deploiement existant : git pull, rebuild, migrations, controles.
set -e

echo "=== 1. Recuperation du code ==="
git pull

echo ""
echo "=== 2. Arret propre (AUCUN volume supprime) ==="
docker compose down

echo ""
echo "=== 2 bis. Normalisation des droits de ./media et ./backups ==="
./fix_perms.sh

echo ""
echo "=== 3. Reconstruction + redemarrage ==="
docker compose up -d --build

echo ""
echo "=== 4. Attente du demarrage (healthcheck backend gere l'ordre, marge de securite) ==="
sleep 5
docker compose ps

echo ""
echo "=== 5. Migrations ==="
docker compose exec -T suudu_backend python manage.py migrate

echo ""
echo "=== 6. Verifications ==="
echo -n "Page d'accueil (attendu 200/302) : "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/

echo -n "Blocage .map (attendu 404) : "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/static/vendor/adminlte/js/adminlte.min.js.map

echo -n "CSP present, sans CDN inutilise : "
curl -s -I http://localhost/ | grep -i "content-security-policy" || echo "ABSENT - a verifier"

echo -n "Chaque en-tete de securite une seule fois (attendu 1) : "
curl -s -I http://localhost/ | grep -ci "^x-frame-options:"

echo -n "Referrer-Policy sur /static/ : "
curl -s -I http://localhost/static/css/output.css | grep -i "referrer-policy" || echo "ABSENT - a verifier"

echo -n "jQuery/DataTables bien retires (attendu 404) : "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/static/vendor/jquery/jquery.min.js

echo -n "Script maison data-table.js present (attendu 200) : "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/static/js/data-table.js

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
