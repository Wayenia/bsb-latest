from pathlib import Path
import os
import environ 
from datetime import timedelta

#BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# env
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


# secret key
SECRET_KEY = env("SECRET_KEY")
DEBUG = env('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')


CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS')
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_CREDENTIALS = env('CORS_ALLOW_CREDENTIALS', default=True)

# IP du serveur hôte, détectée automatiquement au déploiement (voir docker-compose.yml
# / README : HOST_IP=$(hostname -I | awk '{print $1}' | head -1)) et injectée dans le
# conteneur. Permet d'accéder à l'application via l'IP du serveur, en plus du nom de domaine.
HOST_IP = os.environ.get('HOST_IP', '').strip()
if HOST_IP:
    ALLOWED_HOSTS.append(HOST_IP)
    CSRF_TRUSTED_ORIGINS.append(f'http://{HOST_IP}')
    CORS_ALLOWED_ORIGINS.append(f'http://{HOST_IP}')


# Application definition
INSTALLED_APPS = [
    # 'jazzmin' et 'django.contrib.admin' ont ete retires : l'admin Django
    # n'avait servi qu'au debogage, toute l'administration passe par /bsb/.
    # Note : la table django_admin_log subsiste en base, orpheline et inerte ;
    # elle peut etre supprimee manuellement (DROP TABLE django_admin_log) apres
    # verification, aucun code du projet ne la lit.
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'django_filters',
    'corsheaders',

     # my apps
    'accounts',
    'apis', 
    'courses.apps.DetteConfig',
    'actualites',
   

    # third party for erd
    'django_extensions',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.middleware.SecurityHeadersMiddleware',
    'django.middleware.csp.ContentSecurityPolicyMiddleware',
    # En dernier volontairement : quand ce middleware court-circuite une requete
    # (verrou anti-force brute), la reponse 429 remonte quand meme a travers
    # TOUS les middlewares declares au-dessus et herite donc de la CSP et des
    # en-tetes de securite. Place plus haut, la page de blocage sortirait sans.
    'config.middleware.LimitationConnexionMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.csp',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),
        'HOST': env('POSTGRES_HOST'),
        'PORT': env('POSTGRES_PORT'),
    }
}

# Cache Redis. Indispensable au verrou anti-force brute (accounts/ratelimit.py) :
# le compteur doit etre partage par les trois workers gunicorn, sans quoi le
# seuil serait de fait trois fois plus permissif. django-redis figurait deja
# dans requirements.txt mais aucun CACHES n'etait declare : Django retombait
# silencieusement sur LocMemCache, local a chaque processus.
#
# IGNORE_EXCEPTIONS : si Redis tombe, on prefere que le site reste debout plutot
# que de renvoyer 500 sur chaque page. Le verrou s'ouvre alors (fail-open) ; les
# erreurs sont journalisees pour que la panne ne passe pas inapercue, et le
# service Redis n'expose aucun port hors du reseau Docker interne.
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_LOCATION_URL', default='redis://suudu_redis:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,
        },
    }
}
DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.Utilisateur'



# Login URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'courses:redirect_to_dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Messages
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.ERROR: 'error',
    messages.SUCCESS: 'success',
    messages.INFO: 'info',
    messages.WARNING: 'warning',
}

# Les messages transitent par la session, jamais par un cookie.
# Le stockage par defaut (FallbackStorage) essaie CookieStorage en premier. Or
# Django, quand il *efface* ce cookie, appelle response.delete_cookie(), qui ne
# transmet ni httponly ni secure (cf. HttpResponseBase.delete_cookie : le drapeau
# Secure n'est pose que pour les noms prefixes __Secure-/__Host-). D'ou les deux
# alertes « Cookies Not Marked as HttpOnly / Secure » du scan Acunetix du
# 24/08/2026 — sans risque reel puisque le cookie signale est vide et deja
# expire, mais impossible a corriger a la source.
# SessionStorage supprime purement et simplement ce cookie, ferme les deux
# alertes, et garde le contenu des messages cote serveur.
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'



SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
# DENY et non SAMEORIGIN : l'unique raison de SAMEORIGIN etait l'admin Django,
# dont jazzmin encadrait certaines pages dans des iframes (related_modal_active).
# L'admin ayant ete retire, plus aucun gabarit du projet n'utilise <iframe>.
X_FRAME_OPTIONS = 'DENY'

# HTTPS termine par le proxy amont : Django s'y fie via X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# HSTS (findings V07) : force le navigateur a n'utiliser que HTTPS pendant 1 an.
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# SECURE_SSL_REDIRECT reste False : la terminaison TLS est en amont (cf. CLAUDE.md).
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
# True car le site est servi en HTTPS réel via le proxy externe (TLS terminé en
# amont, cf. règle "jamais de redirection HTTPS ici"). En local (http://localhost),
# le navigateur n'enverra pas ces cookies : login/CSRF sembleront "casser" en dev
# HTTP pur, c'est attendu — utiliser un tunnel HTTPS local ou DEBUG-only override
# si besoin de tester ce flux précis en clair.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = False
CSRF_COOKIE_SECURE = not DEBUG
from django.utils.csp import CSP

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    # data: conserve pour img-src : deux gabarits du projet dessinent leur motif
    # de fond avec url("data:image/svg+xml,...") — admin/center/form.html et
    # member/statistiques/statistiques.html. (Les 632 occurrences des CSS
    # vendorises de jazzmin ont disparu avec l'admin Django.)
    # Contrairement a ce qu'annonce le rapport Acunetix, data: dans img-src ne
    # permet PAS d'executer de script : il faudrait pour cela le trouver dans
    # script-src, object-src ou frame-src.
    "img-src": [CSP.SELF, "data:"],
    # data: retire de font-src : aucune @font-face en data: dans le projet.
    "font-src": [CSP.SELF],
    "connect-src": [CSP.SELF],
    "frame-ancestors": [CSP.SELF],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
    "object-src": [CSP.NONE],
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 30*1024*1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 30*1024*1024
# E-mail : SMTP si renseigne dans .env, sinon affichage en console (dev)
# ATTENTION : sans EMAIL_HOST, le backend console ecrit l'integralite du message
# — adresses des abonnes comprises — sur la sortie standard, donc dans les logs
# du conteneur. A n'utiliser qu'en developpement.
EMAIL_HOST = env('EMAIL_HOST', default='')
if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_PORT = env.int('EMAIL_PORT', default=587)
    EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
    EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Sans timeout, un SMTP qui ne repond pas bloque le worker gunicorn jusqu'au
# --timeout de 120 s. La diffusion newsletter ouvre une connexion par lot de 50.
EMAIL_TIMEOUT = env.int('EMAIL_TIMEOUT', default=20)

# Pilotes par .env : avec Google Workspace, l'adresse d'expedition doit
# correspondre a EMAIL_HOST_USER (ou a un alias « Envoyer en tant que » verifie),
# sinon Gmail reecrit silencieusement l'en-tete From.
SERVER_EMAIL = env('SERVER_EMAIL', default='admin@burkinasuudu.com')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@burkinasuudu.com')

# URL publique du site, utilisee pour construire les liens absolus des e-mails
# envoyes hors requete HTTP (commande `notifier_actualites`). Sans elle, le
# repli fabriquait « http://<premier ALLOWED_HOSTS> », soit un lien en clair
# vers un site servi exclusivement en HTTPS.
SITE_URL = env('SITE_URL', default='')

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'security.log'),
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
