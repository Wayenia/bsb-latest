#!/bin/sh
clear

echo "******* Déploiement en cours ... *********"

# Generation automatique du .env s'il est absent.
# Avec un domaine reel :  DOMAIN=mon-domaine.example ./deploy.sh
if [ ! -f .env ]; then
    echo " .env manquant - génération automatique..."

    SECRET_KEY=$(openssl rand -base64 50 | tr -d '\n=' 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    DB_PASS=$(openssl rand -base64 20 | tr -d '\n=' 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(20))")
    PGADMIN_PASS=$(openssl rand -base64 15 | tr -d '\n=' 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(15))")
    ADMIN_PATH=$(openssl rand -hex 8 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(8))")
    EMAIL="admin_$(date +%s)@local.dev"
    SERVER_IP=$(hostname -I | awk '{print $1}' | head -1)

    if [ -n "$DOMAIN" ]; then
        ALLOWED_HOSTS_VAL="${DOMAIN},${SERVER_IP},127.0.0.1,localhost"
        CORS_VAL="https://${DOMAIN},http://${DOMAIN},http://127.0.0.1,http://localhost,http://${SERVER_IP}"
        CSRF_VAL="https://${DOMAIN},http://${DOMAIN},http://127.0.0.1,http://localhost,http://${SERVER_IP}"
        SITE_URL_VAL="https://${DOMAIN}"
        echo " Domaine détecté : ${DOMAIN}"
    else
        ALLOWED_HOSTS_VAL="${SERVER_IP},127.0.0.1,localhost"
        CORS_VAL="http://127.0.0.1,http://localhost,http://${SERVER_IP}"
        CSRF_VAL="http://127.0.0.1,http://localhost,http://${SERVER_IP}"
        SITE_URL_VAL=""
        echo " Aucun DOMAIN fourni - génération avec IP/localhost uniquement (relancez avec DOMAIN=... si besoin)"
    fi

    cat > .env << EOF
# Configuration Django
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${ALLOWED_HOSTS_VAL}

# --- Frontend CORS Origins ---
CORS_ALLOWED_ORIGINS=${CORS_VAL}
CORS_ALLOW_CREDENTIALS=True

# --- CSRF ---
CSRF_TRUSTED_ORIGINS=${CSRF_VAL}

# --- Database ---
POSTGRES_DB=suudu_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=${DB_PASS}
POSTGRES_HOST=suudu_db
POSTGRES_PORT=5432

# --- pgAdmin ---
PGADMIN_DEFAULT_EMAIL=${EMAIL}
PGADMIN_DEFAULT_PASSWORD=${PGADMIN_PASS}
PGADMIN_PORT=8080

# --- Redis ---
REDIS_LOCATION_URL=redis://suudu_redis:6379/1
CELERY_BROKER_URL=redis://suudu_redis:6379/0
CELERY_RESULT_BACKEND=redis://suudu_redis:6379/0

# --- URL publique (liens absolus des e-mails hors requete HTTP) ---
SITE_URL=${SITE_URL_VAL}

# --- Audit et surveillance ---
# Destinataires du rapport d'inspection des connexions (separes par des virgules).
# Vide : la commande envoyer_rapport_audit refuse de s'executer sans --a.
AUDIT_DESTINATAIRES=
AUDIT_PERIODE_JOURS=7
AUDIT_SCAN_INTERVAL=3600

# --- Espace d'administration technique ---
# Chemin secret de la page de connexion des comptes a privileges (jamais lie
# depuis le site). Genere aleatoirement ici ; notez-le et communiquez-le aux
# seuls administrateurs. Peut etre renouvele a tout moment.
ADMIN_LOGIN_PATH=${ADMIN_PATH}
# Plages d'adresses autorisees (CIDR, separees par des virgules). Vide : aucun
# filtrage. Ex : ADMIN_LOGIN_IPS=196.28.0.0/16,10.0.0.0/8
ADMIN_LOGIN_IPS=

# --- E-mail (SMTP) ---
# Requis pour l'envoi du code de verification a 4 chiffres a la connexion du
# personnel. EMAIL_HOST vide : les messages partent dans les logs du conteneur
# (README 9) et la connexion du personnel echouera faute de code recu.
# Gmail : EMAIL_HOST_PASSWORD est un « mot de passe d'application », pas le mot
# de passe du compte.
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=CHANGEME@gmail.com
EMAIL_HOST_PASSWORD=CHANGEME_mot_de_passe_application
EMAIL_TIMEOUT=20
DEFAULT_FROM_EMAIL=Burkina Suudu Bawde <CHANGEME@gmail.com>
SERVER_EMAIL=CHANGEME@gmail.com
EOF

    echo " .env généré avec valeurs sécurisées"
    echo " Admin email: ${EMAIL}"
    echo " PgAdmin password: ${PGADMIN_PASS}"
    echo " IP serveur: ${SERVER_IP}"
fi

echo "--- Nettoyage des anciens conteneurs ---"
# Jamais de -v ici : ce drapeau supprimerait la base (README 8).
sudo docker compose down --remove-orphans 2>/dev/null

echo "--- Normalisation des droits de ./media et ./backups ---"
./fix_perms.sh

echo "--- Construction et démarrage ---"
sudo docker compose up --build -d

echo ""
echo " Déploiement terminé"
echo ""

echo "------- ACTIONS SUIVANTES -------"
echo ""
echo "================================="
echo " Accès: http://127.0.0.1"
echo " Accès domaine/IP: http://$(grep ALLOWED_HOSTS .env | cut -d= -f2 | cut -d, -f1)"
echo " (si un domaine est servi en HTTPS via un proxy externe, utilisez https://)"
echo ""

echo "================================="
echo "Pour créer un superuser :"
echo "sudo docker exec -it suudu_backend python manage.py createsuperuser"
echo ""

echo "================================="
echo "Pour voir les logs :"
echo "sudo docker compose logs -f --tail=50"
echo ""

echo "================================="
echo " Vérifier les en-têtes de sécurité:"
echo "curl -I http://127.0.0.1"
echo ""

echo "================================="
echo " Logs de sécurité:"
echo "sudo docker exec -it suudu_backend cat /app/security.log"
