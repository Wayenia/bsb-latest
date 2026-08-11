#!/bin/sh
# Restaure un fichier .dump (produit par db_dump.sh / pg_dump -F c) dans le
# conteneur suudu_db. Le conteneur suudu_db doit déjà tourner :
#   docker compose up -d suudu_db
#
# Usage : ./db_restore.sh chemin/vers/suudu_db_XXXXXXXX.dump
set -e

DUMP_FILE="$1"
if [ -z "$DUMP_FILE" ] || [ ! -f "$DUMP_FILE" ]; then
    echo "Usage : ./db_restore.sh chemin/vers/fichier.dump"
    exit 1
fi

if [ ! -f .env ]; then
    echo "Erreur : .env introuvable. Lancez ce script depuis la racine du projet."
    exit 1
fi

export $(grep -v '^#' .env | grep -E '^POSTGRES_' | xargs)

echo "==> Restauration dans la base '${POSTGRES_DB}' (conteneur suudu_db)."
echo "==> ATTENTION : --clean supprime les objets existants avant de les recréer"
echo "    (aucune perte si la base est vide ou si c'est justement ce que vous voulez écraser)."
printf "Continuer ? [y/N] "
read CONFIRM
case "$CONFIRM" in
    y|Y) ;;
    *) echo "Annulé."; exit 0 ;;
esac

BASENAME=$(basename "$DUMP_FILE")
docker cp "$DUMP_FILE" "suudu_db:/tmp/${BASENAME}"
docker exec suudu_db pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists --no-owner "/tmp/${BASENAME}"
docker exec suudu_db rm -f "/tmp/${BASENAME}"

echo ""
echo "==> Restauration terminée."
echo "==> Si le backend tourne déjà, redémarrez-le pour appliquer d'éventuelles migrations en attente :"
echo "    docker compose restart suudu_backend"
