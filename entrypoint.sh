#!/bin/bash
set -e

echo "==> Migrations..."
python manage.py migrate --noinput

# Peuplement desactive : populate_data.py cree 52 comptes a mots de passe en
# dur. Lancement manuel sur base neuve uniquement (README 9).
# python manage.py shell < populate_data.py

echo "==> CollectStatic..."
python manage.py collectstatic --noinput --clear

echo "==> Démarrage serveur..."
# Pas de --reload : option de developpement, instable en production.
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --timeout 120 --workers 3
