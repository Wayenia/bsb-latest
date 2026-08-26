#!/bin/sh
# Restaure un .dump dans suudu_db, qui doit deja tourner.
# Usage : ./db_restore.sh chemin/vers/fichier.dump [--force]
# --force saute la confirmation ; --clean detruit les objets existants (README 7).
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

# sed et non xargs, qui interprete guillemets et antislashs et corrompt un mot
# de passe en contenant.
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
