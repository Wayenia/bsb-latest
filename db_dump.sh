#!/bin/sh
# Sauvegarde la base Postgres du conteneur suudu_db (format custom, pour pg_restore).
#
# Usage : ./db_dump.sh [--retention N]
#
#   --retention N   ne conserve que les N sauvegardes les plus recentes
#                   (defaut : 14). Mettre 0 pour ne rien supprimer.
#
# Lancement automatique quotidien : voir le service `suudu_backup` de
# docker-compose.yml, qui execute la meme commande pg_dump depuis le reseau
# interne, sans dependre du binaire docker.
set -e

RETENTION=14
while [ $# -gt 0 ]; do
    case "$1" in
        --retention) RETENTION="$2"; shift 2 ;;
        *) echo "Option inconnue : $1"; exit 1 ;;
    esac
done

if [ ! -f .env ]; then
    echo "Erreur : .env introuvable. Lancez ce script depuis la racine du projet."
    exit 1
fi

# `sed` et non `export $(... | xargs)` : xargs interprete guillemets et
# antislashs, ce qui corrompait silencieusement un mot de passe genere
# contenant ces caracteres.
POSTGRES_USER=$(sed -n 's/^POSTGRES_USER=//p' .env | head -1)
POSTGRES_DB=$(sed -n 's/^POSTGRES_DB=//p' .env | head -1)

if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_DB" ]; then
    echo "Erreur : POSTGRES_USER ou POSTGRES_DB absent de .env."
    exit 1
fi

BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="suudu_db_${TIMESTAMP}.dump"

echo "==> Sauvegarde de la base '${POSTGRES_DB}' (conteneur suudu_db)..."
docker exec suudu_db pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -F c -f "/tmp/${BACKUP_FILE}"
docker cp "suudu_db:/tmp/${BACKUP_FILE}" "${BACKUP_DIR}/${BACKUP_FILE}"
docker exec suudu_db rm -f "/tmp/${BACKUP_FILE}"

# Purge : on garde les N plus recentes. `ls -1t` trie du plus recent au plus
# ancien, `tail -n +N+1` isole donc tout ce qui depasse la retention.
if [ "$RETENTION" -gt 0 ]; then
    A_SUPPRIMER=$(ls -1t "${BACKUP_DIR}"/suudu_db_*.dump 2>/dev/null | tail -n +$((RETENTION + 1)))
    if [ -n "$A_SUPPRIMER" ]; then
        echo "$A_SUPPRIMER" | while read -r vieux; do
            echo "    purge : $(basename "$vieux")"
            rm -f "$vieux"
        done
    fi
fi

echo ""
echo "==> Sauvegarde terminee : ${BACKUP_DIR}/${BACKUP_FILE}"
echo "    Retention : ${RETENTION} fichier(s) conserve(s)."
echo "    Pour restaurer :  ./db_restore.sh ${BACKUP_DIR}/${BACKUP_FILE}"
