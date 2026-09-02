#!/bin/sh
# Environnement de STAGING isole (agents en test), totalement separe de la prod.
# BD, conteneurs, reseau, media et port dedies. La prod n'est jamais touchee.
#
#   ./staging.sh up        build + demarre le stack staging (port 8081)
#   ./staging.sh seed      BD staging neuve : donnees de reference (populate_data)
#   ./staging.sh refresh   copie la BD de prod dans staging (donnees reelles, sans anonymisation)
#   ./staging.sh down      arrete staging (volumes conserves)
#   ./staging.sh           etat courant
set -e

RACINE="$(cd "$(dirname "$0")" && pwd)"
cd "$RACINE"
ENVF=".env.staging"
PROJ="suudu_staging"
DC="docker compose --env-file $ENVF -p $PROJ"

alea() { openssl rand -base64 "${1:-24}" | tr -d '\n=/+' 2>/dev/null || python3 -c "import secrets;print(secrets.token_urlsafe(${1:-24}))"; }

generer_env() {
    [ -f "$ENVF" ] && return 0
    echo "Generation de $ENVF (secrets aleatoires)..."
    IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    cat > "$ENVF" <<EOF
# --- STAGING : environnement de test isole (genere automatiquement) ---
ENV_FILE=$ENVF
COMPOSE_PROJECT_NAME=$PROJ
COMPOSE_SUFFIX=_staging
STAGING_NET=suudu_staging_network
WEB_PORT=8081
MEDIA_DIR=./media_staging
BACKUP_DIR=./backups_staging
ENV_LABEL=STAGING — Environnement de test

SECRET_KEY=$(alea 50)
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,${IP}
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8081,http://localhost:8081
CORS_ALLOWED_ORIGINS=http://127.0.0.1:8081,http://localhost:8081
CORS_ALLOW_CREDENTIALS=True
SITE_URL=http://localhost:8081

POSTGRES_DB=suudu_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$(alea 20)
POSTGRES_HOST=suudu_db
POSTGRES_PORT=5432

REDIS_LOCATION_URL=redis://suudu_redis:6379/1
PGADMIN_DEFAULT_EMAIL=staging@local.dev
PGADMIN_DEFAULT_PASSWORD=$(alea 12)

# E-mail en mode console (aucun OTP reel envoye a de vrais destinataires).
ADMIN_LOGIN_PATH=$(alea 8 | tr 'A-Z' 'a-z')
AI_MODULE=off
BACKUP_INTERVAL=86400
BACKUP_RETENTION=7
AUDIT_SCAN_INTERVAL=3600
EOF
}

case "${1:-}" in
    up)
        generer_env
        mkdir -p media_staging backups_staging
        echo "Demarrage du stack staging (port 8081)..."
        $DC up -d --build
        echo "Staging demarre : http://localhost:8081  (bandeau STAGING visible)."
        echo "Astuce : ./staging.sh seed (donnees neuves) ou ./staging.sh refresh (copie de la prod)."
        ;;
    seed)
        echo "Peuplement des donnees de reference dans staging..."
        $DC exec -T suudu_backend python manage.py migrate
        $DC exec -T suudu_backend python manage.py shell < populate_data.py
        echo "Seed termine."
        ;;
    refresh)
        echo "Copie de la BD de PROD vers STAGING (donnees reelles, sans anonymisation)..."
        printf "Confirmer l'ecrasement de la BD staging par la prod ? [oui/non] "
        read -r rep
        [ "$rep" = "oui" ] || { echo "Annule."; exit 0; }
        docker exec suudu_db pg_dump -U postgres -Fc suudu_db \
          | docker exec -i suudu_db_staging pg_restore --clean --if-exists --no-owner -U postgres -d suudu_db
        $DC exec -T suudu_backend python manage.py migrate
        echo "Refresh termine : staging reflete la prod."
        ;;
    down)
        $DC down
        echo "Staging arrete (volumes conserves ; la prod n'a pas ete touchee)."
        ;;
    "")
        echo "Staging : projet $PROJ"
        docker ps --filter "name=_staging" --format "  {{.Names}}  {{.Status}}" 2>/dev/null || true
        echo "Usage : ./staging.sh [up|seed|refresh|down]"
        ;;
    *)
        echo "Commande inconnue : $1 (attendu : up|seed|refresh|down)"; exit 1 ;;
esac
