# Fichier .env en production

Le `.env` contient tous les réglages sensibles (clés, mots de passe, adresses).
Il n'est pas versionné (`.gitignore`) et n'est jamais inclus dans l'image Docker.

`deploy.sh` en génère un automatiquement s'il est absent, avec des mots de passe
aléatoires. Ce document liste **toutes** les variables lues par l'application :
celles générées par `deploy.sh`, et celles qui reposent sur une valeur par
défaut sûre dans le code (à ajouter seulement si on veut changer le défaut).

Avertissement : ne jamais régénérer le `.env` sur un volume PostgreSQL déjà
peuplé. PostgreSQL ne prend le mot de passe qu'à la première initialisation ;
un nouveau `.env` provoque `password authentication failed` (voir CLAUDE.md).

---

## 1. Obligatoires — générés par deploy.sh

```
SECRET_KEY=<aléatoire, 50+ caractères>
DEBUG=False
ALLOWED_HOSTS=mon-domaine.bf,IP_SERVEUR,127.0.0.1,localhost

CORS_ALLOWED_ORIGINS=https://mon-domaine.bf,http://IP_SERVEUR
CORS_ALLOW_CREDENTIALS=True
CSRF_TRUSTED_ORIGINS=https://mon-domaine.bf,http://IP_SERVEUR

POSTGRES_DB=suudu_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<aléatoire>
POSTGRES_HOST=suudu_db
POSTGRES_PORT=5432

REDIS_LOCATION_URL=redis://suudu_redis:6379/1

PGADMIN_DEFAULT_EMAIL=admin@exemple.bf
PGADMIN_DEFAULT_PASSWORD=<aléatoire>
```

Point critique — `CSRF_TRUSTED_ORIGINS` et `CORS_ALLOWED_ORIGINS` doivent
contenir l'URL **avec le protocole exact vu par le navigateur** (`https://`
quand un proxy termine le TLS en amont). Sinon : erreur CSRF 403 à la connexion.

## 2. Obligatoire à compléter — e-mail (SMTP)

Sans SMTP réel, le code de vérification à 4 chiffres envoyé à la connexion du
personnel ne part pas : **le personnel et les administrateurs ne peuvent plus se
connecter**. `deploy.sh` place des marqueurs `CHANGEME` à remplacer.

```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=adresse@gmail.com
EMAIL_HOST_PASSWORD=<mot de passe d'application, pas le mot de passe du compte>
EMAIL_TIMEOUT=20
DEFAULT_FROM_EMAIL=Burkina Suudu Bawde <adresse@gmail.com>
SERVER_EMAIL=adresse@gmail.com
```

Laisser `EMAIL_HOST` vide bascule en mode console (les e-mails partent dans les
logs du conteneur) : réservé au développement.

**Serveurs où le SMTP sortant est bloqué (cas de la prod).** Si les ports SMTP
(25/465/587/2525) sont fermés par le réseau et que seul le HTTPS (443) passe,
l'envoi se fait par **API HTTPS (Brevo)** au lieu du SMTP :

```
BREVO_API_KEY=xkeysib-…                 # clé API v3 de Brevo
DEFAULT_FROM_EMAIL=Yupaan BSB <expediteur-verifie@domaine.bf>
SERVER_EMAIL=expediteur-verifie@domaine.bf
```

Dès que `BREVO_API_KEY` est renseignée, elle est **prioritaire** sur le SMTP.
L'adresse expéditrice doit être **validée dans Brevo** (expéditeur ou domaine).
Aucune ligne `EMAIL_HOST` n'est alors nécessaire.

## 3. Recommandés en production

```
SITE_URL=https://mon-domaine.bf     # liens absolus des e-mails hors requête HTTP
HOST_IP=IP_SERVEUR                  # ajoute http://IP aux origines CSRF/CORS

ADMIN_LOGIN_PATH=<aléatoire>        # URL secrète de connexion à privilèges (/<valeur>)
ADMIN_LOGIN_IPS=                    # CIDR autorisés, vide = aucun filtrage (optionnel)
```

## 4. Optionnels — modules (défauts sûrs, à laisser tels quels)

À ajouter uniquement pour changer le comportement par défaut.

```
DOC_MODELE=officiel        # documents PDF : officiel (défaut) ou classique. ./.bascules/bascule_doc.sh
BO_UI=nouveau              # écrans back-office : nouveau (défaut) ou classique. ./.bascules/bascule_ui.sh
BO_NAVIGATION=sidebar      # navigation : sidebar (défaut) ou navbar. ./.bascules/bascule_ui.sh
ENV_LABEL=                 # bandeau à l'écran ; vide en prod = aucun bandeau (STAGING l'utilise)
```

## 5. Optionnels — Yupaan-IA (désactivé par défaut)

```
AI_MODULE=off                          # ./.bascules/bascule_ai.sh activer le passe à on
AI_MODEL=qwen2.5:1.5b                  # EN PROD : ce modèle (≤1 Go, garde-fous fiables). PAS le 0.5b.
AI_OLLAMA_URL=http://suudu_ollama:11434
```

Le modèle `qwen2:0.5b` (défaut du code) sert au développement local : trop léger,
il dérape. En production, fixer `AI_MODEL=qwen2.5:1.5b` avant d'activer l'IA.

## 6. Optionnels — audit et sauvegardes (défauts sûrs)

```
AUDIT_DESTINATAIRES=email1@x.bf,email2@x.bf   # destinataires du rapport ; sinon via l'écran RH
AUDIT_PERIODE_JOURS=7
AUDIT_SCAN_INTERVAL=3600
AUDIT_SEUIL_ECHECS_COMPTE=5
AUDIT_SEUIL_COMPTES_PAR_IP=3
AUDIT_SEUIL_IP_PAR_COMPTE=3
AUDIT_HEURE_OUVREE_DEBUT=7
AUDIT_HEURE_OUVREE_FIN=19

BACKUP_INTERVAL=86400      # sauvegarde automatique : toutes les 24 h
BACKUP_RETENTION=14        # nombre de sauvegardes conservées
```

---

## Résumé

- **Générés automatiquement** par `deploy.sh` : section 1.
- **À compléter à la main avant la mise en service** : section 2 (SMTP), et les
  origines `https://` de la section 1 si un domaine est utilisé.
- **Tout le reste** a un défaut sûr : ne l'ajouter que pour le modifier.
- **Yupaan-IA en prod** : si activée, fixer `AI_MODEL=qwen2.5:1.5b`.
