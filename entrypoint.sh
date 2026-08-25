#!/bin/bash
set -e

echo "==> Migrations..."
python manage.py migrate --noinput

# Peuplement des donnees de reference : DESACTIVE.
# populate_data.py cree 52 comptes privilegies (1 superutilisateur + 51 agents)
# avec des mots de passe ecrits en dur dans un fichier suivi par Git, et les
# affiche dans les logs de deploiement. Il n'a sa place qu'en phase de test, et
# doit etre lance a la main, une seule fois, sur une base neuve :
#     docker compose exec suudu_backend python manage.py shell < populate_data.py
# Rappel : commenter cette ligne empeche la RE-creation de comptes supprimes,
# mais ne change rien aux comptes deja presents en base. Seule la rotation des
# mots de passe existants leve le risque.
# python manage.py shell < populate_data.py

echo "==> CollectStatic..."
python manage.py collectstatic --noinput --clear   # ← --clear force le rechargement

echo "==> Démarrage serveur..."
# Pas de --reload : c'est une option de developpement. Elle fait surveiller
# l'arborescence a gunicorn et redemarrer les workers a la moindre ecriture de
# fichier — instabilite en production, d'autant que le projet est monte en
# volume depuis l'hote.
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --timeout 120 --workers 3
