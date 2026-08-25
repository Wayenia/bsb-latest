#!/bin/sh
# Restaure un fichier .dump (produit par db_dump.sh / pg_dump -F c) dans le
# conteneur suudu_db. Le conteneur suudu_db doit deja tourner :
#   docker compose up -d suudu_db
#
# Usage : ./db_restore.sh chemin/vers/suudu_db_XXXXXXXX.dump [--force]
#
#   --force  saute la demande de confirmation. Reserve aux scripts (CI,
#            provisionnement d'une machine neuve). ATTENTION : --clean detruit
#            les objets existants, ne l'utilisez jamais sur une base de
#            production sans avoir pris un dump juste avant.
#
# Ce script NE tourne PAS dans l'entrypoint du backend : il s'appuie sur
# `docker exec`, indisponible depuis l'interieur d'un conteneur. La restauration
# reste une operation deliberee, lancee depuis l'hote.
set -e

DUMP_FILE=""
FORCE=0
for arg in "$@"; do
    case "$arg" in
        --force) FORCE=1 ;;
        *)       [ -z "$DUMP_FILE" ] && DUMP_FILE="$arg" ;;
    esac
done

if [ -z "$DUMP_FILE" ] || [ ! -f "$DUMP_FILE" ]; then
    echo "Usage : ./db_restore.sh chemin/vers/fichier.dump [--force]"
    exit 1
fi

if [ ! -f .env ]; then
    echo "Erreur : .env introuvable. Lancez ce script depuis la racine du projet."
    exit 1
fi

# `.` et non `export $(... | xargs)` : xargs interprete guillemets et
# antislashs, ce qui corrompait silencieusement un mot de passe genere
# contenant ces caracteres.
POSTGRES_USER=$(sed -n 's/^POSTGRES_USER=//p' .env | head -1)
POSTGRES_DB=$(sed -n 's/^POSTGRES_DB=//p' .env | head -1)

if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_DB" ]; then
    echo "Erreur : POSTGRES_USER ou POSTGRES_DB absent de .env."
    exit 1
fi

if [ "$FORCE" -eq 0 ]; then
    echo "==> Restauration dans la base '${POSTGRES_DB}' (conteneur suudu_db)."
    echo "==> ATTENTION : --clean supprime les objets existants avant de les recreer"
    echo "    (aucune perte si la base est vide ou si c'est justement ce que vous voulez ecraser)."
    printf "Continuer ? [y/N] "
    read CONFIRM
    case "$CONFIRM" in
        y|Y) ;;
        *) echo "Annule."; exit 0 ;;
    esac
else
    echo "==> Restauration NON INTERACTIVE dans '${POSTGRES_DB}' (--force)."
fi

BASENAME=$(basename "$DUMP_FILE")
docker cp "$DUMP_FILE" "suudu_db:/tmp/${BASENAME}"
docker exec suudu_db pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists --no-owner "/tmp/${BASENAME}"
docker exec suudu_db rm -f "/tmp/${BASENAME}"

echo ""
echo "==> Restauration terminee."
echo "==> Si le backend tourne deja, redemarrez-le pour appliquer d'eventuelles migrations en attente :"
echo "    docker compose restart suudu_backend"
