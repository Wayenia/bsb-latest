#!/bin/sh
# Sauvegarde la base Postgres du conteneur suudu_db (format custom, pour pg_restore).
# À lancer depuis la machine où tourne actuellement suudu_db (ex: en dev, avant de
# transférer les données vers le serveur de production).
set -e

if [ ! -f .env ]; then
    echo "Erreur : .env introuvable. Lancez ce script depuis la racine du projet."
    exit 1
fi

export $(grep -v '^#' .env | grep -E '^POSTGRES_' | xargs)

BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="suudu_db_${TIMESTAMP}.dump"

echo "==> Sauvegarde de la base '${POSTGRES_DB}' (conteneur suudu_db)..."
docker exec suudu_db pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -F c -f "/tmp/${BACKUP_FILE}"
docker cp "suudu_db:/tmp/${BACKUP_FILE}" "${BACKUP_DIR}/${BACKUP_FILE}"
docker exec suudu_db rm -f "/tmp/${BACKUP_FILE}"

echo ""
echo "==> Sauvegarde terminée : ${BACKUP_DIR}/${BACKUP_FILE}"
echo "    Transférez ce fichier vers le serveur (scp), puis lancez :"
echo "    ./db_restore.sh ${BACKUP_FILE}"
