#!/bin/bash
set -e

echo "==> Migrations..."
python manage.py migrate --noinput

echo "==> Population des données de référence..."
python manage.py shell < populate_data.py

echo "==> CollectStatic..."
python manage.py collectstatic --noinput --clear   # ← --clear force le rechargement

echo "==> Démarrage serveur..." en production 
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --reload --timeout 120 --workers 3 # ← --reload pour gunicorn

#echo "==> Démarrage serveur..."
#exec python manage.py runserver 0.0.0.0:8000