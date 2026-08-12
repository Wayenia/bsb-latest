#!/bin/bash
set -e

echo "==> Migrations..."
python manage.py migrate --noinput

echo "==> CollectStatic..."
python manage.py collectstatic --noinput --clear

echo "==> Démarrage serveur..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --timeout 120 --workers 3

#echo "==> Démarrage serveur..."
#exec python manage.py runserver 0.0.0.0:8000