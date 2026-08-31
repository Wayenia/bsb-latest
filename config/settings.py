from pathlib import Path
import os
import environ 
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


SECRET_KEY = env("SECRET_KEY")
DEBUG = env('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')


CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS')
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_CREDENTIALS = env('CORS_ALLOW_CREDENTIALS', default=True)

# IP du serveur injectee par docker-compose : acces par IP en plus du domaine.
HOST_IP = os.environ.get('HOST_IP', '').strip()
if HOST_IP:
    ALLOWED_HOSTS.append(HOST_IP)
    CSRF_TRUSTED_ORIGINS.append(f'http://{HOST_IP}')
    CORS_ALLOWED_ORIGINS.append(f'http://{HOST_IP}')


# Application definition
INSTALLED_APPS = [
    # jazzmin et django.contrib.admin retires : administration via /bsb/ (README 9).
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
    'audit',
   

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
    # En dernier : la reponse 429 traverse ainsi les middlewares au-dessus et
    # herite de la CSP et des en-tetes de securite.
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
                'config.context_processors.navigation',
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

# Compteur du verrou anti-force brute (accounts/ratelimit.py), partage par les
# workers gunicorn. IGNORE_EXCEPTIONS ouvre le verrou si Redis tombe (README 9).
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

# Sous WSL2, /mnt/c refuse chmod() : desactive le chmod post-ecriture de Django.
FILE_UPLOAD_PERMISSIONS = None
FILE_UPLOAD_DIRECTORY_PERMISSIONS = None

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

# Messages en session et non en cookie : delete_cookie() ne pose ni HttpOnly ni
# Secure sur le cookie efface (README 9).
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'



SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
# DENY : l'admin Django, seule raison du SAMEORIGIN, a ete retire.
X_FRAME_OPTIONS = 'DENY'

# HTTPS termine par le proxy amont : Django s'y fie via X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# HSTS : HTTPS obligatoire pendant un an.
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# SECURE_SSL_REDIRECT reste False : terminaison TLS en amont.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
# Cookies Secure hors DEBUG : en HTTP local, login et CSRF echouent (README 9).
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = False
CSRF_COOKIE_SECURE = not DEBUG
from django.utils.csp import CSP

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
    # Nonce sans 'unsafe-inline' : les deux sont exclusifs (README 9).
    "style-src": [CSP.SELF, CSP.NONCE],
    # data: requis par deux gabarits qui dessinent leur fond en SVG inline.
    "img-src": [CSP.SELF, "data:"],
    "font-src": [CSP.SELF],
    "connect-src": [CSP.SELF],
    "frame-ancestors": [CSP.SELF],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
    "object-src": [CSP.NONE],
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 30*1024*1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 30*1024*1024
# SMTP si EMAIL_HOST est renseigne, sinon console : le backend console ecrit les
# adresses des abonnes dans les logs du conteneur, developpement uniquement.
EMAIL_HOST = env('EMAIL_HOST', default='')
if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_PORT = env.int('EMAIL_PORT', default=587)
    EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
    EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Sans timeout, un SMTP muet bloque le worker gunicorn pendant 120 s.
EMAIL_TIMEOUT = env.int('EMAIL_TIMEOUT', default=20)

# Avec Google Workspace, doit correspondre a EMAIL_HOST_USER (README 9).
SERVER_EMAIL = env('SERVER_EMAIL', default='admin@burkinasuudu.com')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@burkinasuudu.com')

# Liens absolus des e-mails envoyes hors requete HTTP ; vide, le repli produit
# un lien en http:// (README 9).
SITE_URL = env('SITE_URL', default='')

# Navigation du back-office : 'sidebar' (nouvelle) ou 'navbar' (ancienne barre
# horizontale). Bascule reversible a tout moment par ./bascule_ui.sh, sans
# modification de code — aucun gabarit ne code en dur l'une ou l'autre.
BO_NAVIGATION = env('BO_NAVIGATION', default='sidebar')

# --- Audit et surveillance (application `audit`) ---
# Seuils de declenchement des alertes du rapport d'inspection. Les relever
# reduit le bruit, les abaisser augmente la sensibilite (voir audit/README.md).
AUDIT_DESTINATAIRES = env.list('AUDIT_DESTINATAIRES', default=[])
AUDIT_PERIODE_JOURS = env.int('AUDIT_PERIODE_JOURS', default=7)
AUDIT_SEUIL_ECHECS_COMPTE = env.int('AUDIT_SEUIL_ECHECS_COMPTE', default=5)
AUDIT_SEUIL_COMPTES_PAR_IP = env.int('AUDIT_SEUIL_COMPTES_PAR_IP', default=3)
AUDIT_SEUIL_IP_PAR_COMPTE = env.int('AUDIT_SEUIL_IP_PAR_COMPTE', default=3)
AUDIT_HEURE_OUVREE_DEBUT = env.int('AUDIT_HEURE_OUVREE_DEBUT', default=7)
AUDIT_HEURE_OUVREE_FIN = env.int('AUDIT_HEURE_OUVREE_FIN', default=19)

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

(BASE_DIR / 'logs').mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            # /app/logs est un volume nomme, donc inscriptible par appuser (README 9).
            'filename': os.path.join(BASE_DIR, 'logs', 'security.log'),
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
