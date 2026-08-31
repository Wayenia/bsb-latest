#!/bin/sh
# Migration majeure de PostgreSQL, idempotente et non destructive.
# Appelee par redeploy.sh apres le git pull. Detaille : README section 7.5.
#
# Ne fait rien si :
#   - le cluster cible tourne deja (volume ..._18 initialise en version cible), ou
#   - aucune ancienne donnee n'existe (premiere installation).
# Sinon : sauvegarde de l'ancien cluster via un conteneur temporaire a l'ancienne
# version, puis restauration dans le cluster cible. L'ancien volume reste intact
# comme point de retour ; aucune commande ne supprime de donnees.
set -e

ANCIENNE_IMAGE="postgres:15.15-trixie"
CIBLE_IMAGE="postgres:18.6-trixie"
CIBLE_MAJEUR="18"
SUFFIXE_CIBLE="_18"

[ -f .env ] || { echo "pg_migrate: .env introuvable, lancez ce script depuis la racine."; exit 1; }
PGUSER=$(sed -n 's/^POSTGRES_USER=//p' .env | head -1)
PGDB=$(sed -n 's/^POSTGRES_DB=//p' .env | head -1)
PGPW=$(sed -n 's/^POSTGRES_PASSWORD=//p' .env | head -1)
[ -n "$PGUSER" ] && [ -n "$PGDB" ] || { echo "pg_migrate: POSTGRES_USER/DB absents du .env."; exit 1; }

# Lit le fichier PG_VERSION d'un volume avec la premiere image postgres disponible.
# Renvoie toujours 0 (chaine vide si le volume n'existe pas) : appelee sous set -e.
lire_pgver() {
    vol="$1"
    if ! docker volume inspect "$vol" >/dev/null 2>&1; then
        return 0
    fi
    img=""
    for candidat in "$CIBLE_IMAGE" "$ANCIENNE_IMAGE"; do
        if docker image inspect "$candidat" >/dev/null 2>&1; then
            img="$candidat"
            break
        fi
    done
    if [ -z "$img" ]; then
        docker pull "$CIBLE_IMAGE" >/dev/null 2>&1 || true
        img="$CIBLE_IMAGE"
    fi
    docker run --rm --entrypoint cat -v "$vol":/d "$img" /d/PG_VERSION 2>/dev/null | tr -d '[:space:]' || true
    return 0
}

# Nom du projet compose : les volumes en sont prefixes. Plusieurs deploiements
# peuvent coexister sur une meme machine, d'ou un ciblage strict du projet courant
# et non d'un motif global.
# if/then explicites : l'idiome « cond && { return; } » sous set -e avorte la
# fonction des que cond est fausse (conteneur absent, par exemple).
projet_compose() {
    if [ -n "$COMPOSE_PROJECT_NAME" ]; then
        printf '%s\n' "$COMPOSE_PROJECT_NAME"
        return 0
    fi
    etiquette=$(docker inspect suudu_db --format '{{ index .Config.Labels "com.docker.compose.project" }}' 2>/dev/null || true)
    if [ -n "$etiquette" ]; then
        printf '%s\n' "$etiquette"
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        nom=$(docker compose config --format json 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin).get('name',''))" 2>/dev/null || true)
        if [ -n "$nom" ]; then
            printf '%s\n' "$nom"
            return 0
        fi
    fi
    # Repli : algorithme par defaut de compose (minuscules, caracteres restreints).
    basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]//g'
}

PROJET=$(projet_compose)
ANCIEN_VOL="${PROJET}_suudu_postgres_data"
NOUVEAU_VOL="${PROJET}_suudu_postgres_data${SUFFIXE_CIBLE}"
if ! docker volume inspect "$ANCIEN_VOL" >/dev/null 2>&1; then
    echo "pg_migrate: aucun ancien volume PostgreSQL ($ANCIEN_VOL) -> premiere installation, rien a migrer."
    exit 0
fi

if [ "$(lire_pgver "$NOUVEAU_VOL")" = "$CIBLE_MAJEUR" ]; then
    echo "pg_migrate: cluster PostgreSQL $CIBLE_MAJEUR deja en place ($NOUVEAU_VOL). Rien a faire."
    exit 0
fi

ANCIEN_MAJEUR=$(lire_pgver "$ANCIEN_VOL")
if [ -z "$ANCIEN_MAJEUR" ]; then
    echo "pg_migrate: ancien volume vide -> rien a migrer."
    exit 0
fi

echo "pg_migrate: migration PostgreSQL $ANCIEN_MAJEUR -> $CIBLE_MAJEUR detectee."
echo "            source : $ANCIEN_VOL"
echo "            cible  : $NOUVEAU_VOL (l'ancien volume est conserve pour retour arriere)."

# En cas d'echec apres creation du volume cible, on le retire : sans cela un
# second passage le prendrait pour un cluster deja migre et demarrerait sur une
# base vide. L'ancien volume, lui, n'est jamais touche.
CIBLE_CREEE=0
nettoyer_si_echec() {
    code=$?
    [ "$code" -eq 0 ] && return 0
    if [ "$CIBLE_CREEE" -eq 1 ]; then
        echo "pg_migrate: ECHEC -> retrait du volume cible incomplet ($NOUVEAU_VOL)."
        echo "            L'ancien volume ($ANCIEN_VOL) reste intact ; relancez redeploy.sh."
        docker rm -f suudu_pg_migr >/dev/null 2>&1 || true
        docker compose rm -sf suudu_db >/dev/null 2>&1 || true
        docker volume rm "$NOUVEAU_VOL" >/dev/null 2>&1 || true
    fi
}
trap nettoyer_si_echec EXIT

# 1. Tout arreter proprement (jamais -v : aucun volume supprime).
docker compose down

# 2. Sauvegarde de l'ancien cluster via un serveur temporaire a l'ancienne version.
mkdir -p ./backups
HORO=$(date +%Y%m%d_%H%M%S)
DUMP="./backups/premigration_pg${ANCIEN_MAJEUR}_${HORO}.dump"
docker rm -f suudu_pg_migr >/dev/null 2>&1 || true
echo "pg_migrate: demarrage d'un serveur temporaire $ANCIENNE_IMAGE sur l'ancien volume..."
docker run -d --name suudu_pg_migr \
    -e POSTGRES_DB="$PGDB" -e POSTGRES_USER="$PGUSER" -e POSTGRES_PASSWORD="$PGPW" \
    -v "$ANCIEN_VOL":/var/lib/postgresql/data \
    "$ANCIENNE_IMAGE" >/dev/null
i=0
while [ "$i" -lt 60 ]; do
    docker exec suudu_pg_migr pg_isready -U "$PGUSER" -d "$PGDB" >/dev/null 2>&1 && break
    i=$((i + 1)); sleep 1
done
echo "pg_migrate: sauvegarde pre-migration -> $DUMP"
docker exec -e PGPASSWORD="$PGPW" suudu_pg_migr \
    pg_dump -U "$PGUSER" -d "$PGDB" -F c -f /tmp/premigr.dump
docker cp suudu_pg_migr:/tmp/premigr.dump "$DUMP"
docker rm -f suudu_pg_migr >/dev/null

# 3. Nouveau cluster (version cible) sur le volume neuf, initialise depuis .env.
echo "pg_migrate: initialisation du cluster PostgreSQL $CIBLE_MAJEUR..."
CIBLE_CREEE=1
docker compose up -d suudu_db
i=0
while [ "$i" -lt 90 ]; do
    docker exec suudu_db pg_isready -U "$PGUSER" -d "$PGDB" >/dev/null 2>&1 && break
    i=$((i + 1)); sleep 1
done

# 4. Restauration des donnees.
echo "pg_migrate: restauration des donnees dans le cluster $CIBLE_MAJEUR..."
./db_restore.sh "$DUMP" --force
CIBLE_CREEE=0

# 5. Rendre la main a redeploy.sh, qui reprend le cycle down/up/build normal.
docker compose stop suudu_db >/dev/null
echo "pg_migrate: migration terminee."
echo "            Sauvegarde pre-migration : $DUMP"
echo "            Ancien volume conserve   : $ANCIEN_VOL (a supprimer manuellement une fois la migration validee)."
