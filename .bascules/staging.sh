#!/bin/sh
# Environnement de STAGING isole (agents en test), totalement separe de la prod.
# BD, conteneurs, reseau, media et port dedies. La prod n'est jamais touchee.
#
#   DOMAIN=staging.exemple.bf ./.bascules/staging.sh up
#                                   build + demarre le stack staging (port 8081)
#                                   et inscrit le domaine dans .env.staging
#   ./.bascules/staging.sh up        idem sans (re)definir le domaine
#   ./.bascules/staging.sh seed      BD staging neuve : donnees de reference (populate_data)
#   ./.bascules/staging.sh refresh   copie la BD de prod dans staging (donnees reelles, sans anonymisation)
#   ./.bascules/staging.sh down      arrete staging (volumes conserves)
#   ./.bascules/staging.sh reset     supprime conteneurs + volumes + .env.staging (STAGING uniquement)
#   ./.bascules/staging.sh           etat courant
#
# Le domaine peut aussi etre (re)applique sur un stack deja genere :
#   DOMAIN=nouveau.exemple.bf ./.bascules/staging.sh up
set -e

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE"
ENVF=".env.staging"
PROJ="suudu_staging"
DC="docker compose --env-file $ENVF -p $PROJ"
IP=$(hostname -I 2>/dev/null | awk '{print $1}')

alea() { openssl rand -base64 "${1:-24}" | tr -d '\n=/+' 2>/dev/null || python3 -c "import secrets;print(secrets.token_urlsafe(${1:-24}))"; }

generer_env() {
    [ -f "$ENVF" ] && return 0
    echo "Generation de $ENVF (secrets aleatoires)..."
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

# ADMIN_LOGIN_PATH du staging : chemin fixe et memorable, distinct de la prod.
# Les agents yupaan ouvrent la page d'administration technique sur /staging-bsb.
# Surchargable au premier up : ADMIN_LOGIN_PATH=autre ./.bascules/staging.sh up
ADMIN_LOGIN_PATH=${ADMIN_LOGIN_PATH:-staging-bsb}
AI_MODULE=off
BACKUP_INTERVAL=86400
BACKUP_RETENTION=7
AUDIT_SCAN_INTERVAL=3600
EOF
    copier_cles_email "$ENVF"
}

# E-mail : le staging doit se comporter comme la prod (envoi reel des OTP, pas
# de mode console). On recopie tel quel le bloc e-mail du .env de prod dans
# .env.staging, sinon Django retombe sur le backend console.
# ATTENTION : apres un `refresh` (copie de la prod), la BD staging contient les
# adresses reelles des utilisateurs -> les OTP partent vraiment. Utiliser des
# comptes de test dont la boite mail est accessible aux agents.
copier_cles_email() {
    cible="$1"
    [ -f "$cible" ] || return 0
    if [ ! -f .env ]; then
        echo "Attention : .env (prod) absent, e-mail du staging laisse en mode console."
        return 0
    fi
    # Retire l'ancien bloc e-mail (du marqueur jusqu'a la fin) et le commentaire
    # obsolete de l'ancien generateur, puis resynchronise depuis .env de prod :
    # une cle e-mail modifiee en prod est ainsi reprise au prochain `up`.
    sed -i '/^# --- E-mail : recopie du \.env de prod/,$d' "$cible"
    sed -i '/^# E-mail en mode console/d' "$cible"
    # Supprime les lignes vides en fin de fichier (evite leur accumulation).
    awk 'NF{last=NR} {buf[NR]=$0} END{for(i=1;i<=last;i++) print buf[i]}' "$cible" > "$cible.tmp" \
        && mv "$cible.tmp" "$cible"
    {
        echo ""
        echo "# --- E-mail : recopie du .env de prod (envoi reel, identique a la prod) ---"
        grep -E '^(EMAIL_HOST|EMAIL_PORT|EMAIL_USE_TLS|EMAIL_HOST_USER|EMAIL_HOST_PASSWORD|EMAIL_TIMEOUT|DEFAULT_FROM_EMAIL|SERVER_EMAIL|BREVO_API_KEY)=' .env
    } >> "$cible" || true
    echo "E-mail staging : bloc resynchronise depuis .env de prod (envoi reel)."
}

# Inscrit (ou reecrit) le domaine public du staging dans .env.staging.
# Meme logique que `DOMAIN=... ./deploy.sh` pour la prod : le proxy d'infra
# termine le TLS, donc CSRF/CORS doivent contenir l'URL en https ET en http.
# Les origines localhost:8081 sont conservees pour les tests directs sur l'hote.
appliquer_domaine() {
    dom="$1"
    hosts="${dom},127.0.0.1,localhost"
    [ -n "$IP" ] && hosts="${hosts},${IP}"
    origines="https://${dom},http://${dom},http://127.0.0.1:8081,http://localhost:8081"
    sed -i \
      -e "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=${hosts}|" \
      -e "s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=${origines}|" \
      -e "s|^CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=${origines}|" \
      -e "s|^SITE_URL=.*|SITE_URL=https://${dom}|" \
      "$ENVF"
    echo "Domaine staging applique : ${dom}"
    echo "  ALLOWED_HOSTS       = ${hosts}"
    echo "  CSRF/CORS origines  = ${origines}"
    echo "  SITE_URL            = https://${dom}"
}

# (Re)ecrit le chemin de la page d'administration technique dans .env.staging.
# Meme logique que appliquer_domaine : utile pour changer /staging-bsb sur un
# stack deja genere (ADMIN_LOGIN_PATH=... ./.bascules/staging.sh up).
appliquer_admin_path() {
    chemin="$1"
    if grep -q '^ADMIN_LOGIN_PATH=' "$ENVF"; then
        sed -i -e "s|^ADMIN_LOGIN_PATH=.*|ADMIN_LOGIN_PATH=${chemin}|" "$ENVF"
    else
        echo "ADMIN_LOGIN_PATH=${chemin}" >> "$ENVF"
    fi
    echo "Chemin d'administration staging applique : /${chemin}"
}

case "${1:-}" in
    up)
        generer_env
        copier_cles_email "$ENVF"
        if [ -n "${DOMAIN:-}" ]; then
            appliquer_domaine "$DOMAIN"
        fi
        if [ -n "${ADMIN_LOGIN_PATH:-}" ]; then
            appliquer_admin_path "$ADMIN_LOGIN_PATH"
        fi
        mkdir -p media_staging backups_staging
        echo "Demarrage du stack staging (port 8081)..."
        $DC up -d --build
        # Recreation SYSTEMATIQUE des conteneurs applicatifs a chaque `up`.
        # Sans cela, `docker compose up -d` laisse tourner tels quels les
        # conteneurs deja lances (le code est monte en bind mount, donc l'image
        # ne change pas) : entrypoint.sh ne rejoue pas `collectstatic`, gunicorn
        # ne recharge pas, et Django garde ses templates en cache (loader de
        # cache actif des que DEBUG=False). Resultat : le staging continue de
        # servir d'ANCIENS templates / CSS / JS et ne reflete plus la prod.
        # La recreation force le rejeu d'entrypoint (statiques) + un gunicorn
        # neuf (code + templates a jour). --no-deps : db / redis intacts.
        $DC up -d --force-recreate --no-deps suudu_backend suudu_nginx suudu_audit
        chemin_admin=$(grep -E '^ADMIN_LOGIN_PATH=' "$ENVF" | cut -d= -f2-)
        if [ -n "${DOMAIN:-}" ]; then
            echo "Staging demarre : https://${DOMAIN}  (bandeau STAGING visible)."
            echo "Administration technique : https://${DOMAIN}/${chemin_admin}"
        else
            echo "Staging demarre : http://localhost:8081  (bandeau STAGING visible)."
            echo "Administration technique : http://localhost:8081/${chemin_admin}"
        fi
        echo "Astuce : ./.bascules/staging.sh seed (donnees neuves) ou ./.bascules/staging.sh refresh (copie de la prod)."
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
    reset)
        echo "Remise a zero du staging : conteneurs + volumes du projet $PROJ + $ENVF."
        echo "La prod (projet distinct) n'est pas concernee."
        printf "Confirmer ? [oui/non] "
        read -r rep
        [ "$rep" = "oui" ] || { echo "Annule."; exit 0; }
        # -v ne supprime que les volumes declares pour le projet staging.
        $DC down -v --remove-orphans 2>/dev/null || true
        rm -f "$ENVF"
        echo "Staging remis a zero. Relancez : DOMAIN=<domaine-test> ./.bascules/staging.sh up"
        ;;
    "")
        echo "Staging : projet $PROJ"
        docker ps --filter "name=_staging" --format "  {{.Names}}  {{.Status}}" 2>/dev/null || true
        echo "Usage : [DOMAIN=domaine-test] ./.bascules/staging.sh [up|seed|refresh|down|reset]"
        ;;
    *)
        echo "Commande inconnue : $1 (attendu : up|seed|refresh|down|reset)"; exit 1 ;;
esac
