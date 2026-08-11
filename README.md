# Yupaan — Plateforme de gestion Burkina Suudu Bawdè (BSB)

Plateforme de gestion des centres de formation professionnelle, développée pour le
Ministère de l'Enseignement Secondaire, de la Formation Professionnelle et Technique
(MESFPT) du Burkina Faso. Elle couvre l'inscription des élèves, le suivi des paiements
de scolarité, la facturation de prestations de services (module DAF) et
l'administration des centres, filières et personnels.

Ce document décrit le fonctionnement du projet, les parcours utilisateurs, la
procédure d'installation et de déploiement, ainsi que les règles à respecter pour
maintenir le projet en bon état.

---

## Sommaire

1. [Présentation générale](#1-présentation-générale)
2. [Architecture du projet](#2-architecture-du-projet)
3. [Rôles et profils utilisateurs](#3-rôles-et-profils-utilisateurs)
4. [Parcours utilisateurs](#4-parcours-utilisateurs)
5. [Module Facturation et Prestations (DAF)](#5-module-facturation-et-prestations-daf)
6. [Installation et démarrage (environnement de développement)](#6-installation-et-démarrage-environnement-de-développement)
7. [Déploiement en production](#7-déploiement-en-production)
8. [Sécurité — règles à respecter](#8-sécurité--règles-à-respecter)
9. [Points de vigilance techniques](#9-points-de-vigilance-techniques)
10. [Résolution des incidents courants](#10-résolution-des-incidents-courants)
11. [Organisation des fichiers](#11-organisation-des-fichiers)

---

## 1. Présentation générale

**Qui utilise la plateforme.** Trois grandes catégories de personnes :

- Les **élèves** (apprenants), qui s'inscrivent en ligne à une formation, suivent
  leur dossier et paient leur scolarité.
- Le **personnel des centres et des directions** (gestionnaires, caissiers,
  formateurs, membres de l'administration, directeurs inter-régionaux, DEPS), qui
  traite les dossiers, encaisse les paiements et consulte les statistiques.
- La **direction générale et les administrateurs**, qui configurent l'offre de
  formation (métiers, centres, frais) et gèrent les comptes du personnel.

Une brique supplémentaire, indépendante du parcours scolaire, gère la **facturation
de prestations de services** pour le compte de la Direction Administrative et
Financière (DAF) : devis, factures, encaissements.

**Ce que ce dépôt contient.** Le code source complet de l'application (backend
Django, gabarits HTML, feuilles de styles Tailwind CSS) ainsi que la configuration
nécessaire pour la faire fonctionner avec Docker (base de données, serveur web,
cache).

---

## 2. Architecture du projet

### 2.1 Vue d'ensemble technique

| Composant | Rôle | Technologie |
|---|---|---|
| Backend | Logique métier, pages web, formulaires | Django 5.2 (Python) |
| Base de données | Stockage des données | PostgreSQL 15 |
| Serveur d'application | Exécute Django en production | Gunicorn |
| Reverse proxy | Reçoit les requêtes, sert les fichiers statiques | Nginx |
| Feuilles de style | Mise en forme des pages | Tailwind CSS (compilé) |
| Génération de PDF | Reçus, quittances, factures | WeasyPrint et ReportLab |
| Conteneurisation | Isolation et démarrage des services | Docker / Docker Compose |

Le projet **n'utilise pas** de framework JavaScript (pas de React/Vue) : les pages
sont générées côté serveur par Django, avec un peu de JavaScript classique pour
l'interactivité (formulaires en plusieurs étapes, menus).

### 2.2 Applications Django

Le projet est découpé en quatre applications Django, chacune avec une
responsabilité précise :

- **`accounts`** — Comptes utilisateurs, connexion/inscription, et le module de
  facturation DAF (clients, prestations, factures, encaissements).
- **`courses`** — Le cœur métier : centres de formation, filières (métiers),
  modules, programmations de formation, inscriptions, frais, dettes, paiements de
  scolarité, statistiques, et tout le back-office d'administration (`/bsb/`).
- **`apis`** — Contient uniquement un « sérialiseur » (`UserRegisterSerializer`)
  utilisé par la page d'inscription. Ce n'est **pas** une API exposée publiquement
  (aucune route n'y est raccordée) ; le nom peut prêter à confusion mais il s'agit
  d'un outil interne de validation de formulaire.
- **`config`** — Réglages globaux du projet (`settings.py`), routage racine
  (`urls.py`), et un middleware maison qui renforce les en-têtes de sécurité HTTP.

### 2.3 Services Docker

Le fichier `docker-compose.yml` définit cinq services :

| Service | Conteneur | Rôle | Accès depuis l'extérieur |
|---|---|---|---|
| `suudu_backend` | Django + Gunicorn | Traite les requêtes de l'application | Non (uniquement via nginx) |
| `suudu_db` | PostgreSQL 15 | Stocke toutes les données | Non |
| `suudu_nginx` | Nginx | Sert les pages, les fichiers statiques et médias | Oui, port **80** |
| `suudu_redis` | Redis | Prévu pour le cache/les tâches asynchrones | Non |
| `suudu_pgadmin` | pgAdmin | Interface d'administration de la base de données | Non exposé par défaut (voir section 9) |

Au démarrage, le conteneur `suudu_backend` exécute automatiquement, dans l'ordre :
application des migrations de base de données (`migrate`), regroupement des
fichiers statiques (`collectstatic`), puis lancement du serveur (`gunicorn`). Cette
séquence est définie dans `entrypoint.sh`.

### 2.4 Schéma de routage général

| Préfixe d'URL | Destination | Public visé |
|---|---|---|
| `/` | `courses.urls` | Élèves, formateurs, personnel de centre |
| `/accounts/` | `accounts.urls` | Connexion, inscription, module DAF |
| `/bsb/` | `courses.urls_admin` | Back-office : direction, DEPS, administrateurs |
| `/admin/` | Administration Django native | Développeurs et super-utilisateurs uniquement |

`/admin/` (l'administration technique fournie par Django) et `/bsb/` (l'interface
métier propre à l'application) sont deux choses différentes : la première sert
surtout à la maintenance technique, la seconde est l'outil de travail quotidien du
personnel de direction.

---

## 3. Rôles et profils utilisateurs

Chaque compte porte un type d'utilisateur (`user_type`). À chaque enregistrement du
compte, celui-ci est automatiquement rattaché à un groupe de permissions
correspondant — il n'y a jamais besoin de le faire à la main.

| Type de compte | Rattachement | Ce qu'il peut faire |
|---|---|---|
| **Élève** | — | S'inscrit à une formation, dépose ses documents, suit son dossier, paie sa scolarité, télécharge ses reçus. Ne détient aucune permission d'administration. |
| **Formateur** | Un centre, un métier | Consulte son tableau de bord, la liste de ses élèves et leur situation de paiement. Rôle en lecture seule. |
| **Membre de l'administration** | Un centre ou une direction | Consulte les dossiers d'inscription et les pièces jointes. |
| **Gestionnaire de centre** | Un centre | Valide ou rejette les dossiers d'inscription de son centre. |
| **Caissier(ère)** | Un centre | Comme le gestionnaire, plus l'encaissement des paiements de scolarité. |
| **Agent comptable** | Un centre ou une direction | Encaissement, gestion des paiements, statistiques et exports. |
| **DEPS** (Direction des Études, de la Planification et des Statistiques) | Global | Accès large à la configuration (centres, métiers, frais, programmations) et aux statistiques, sans gestion des comptes ni des permissions. |
| **Directeur inter-régional** | Une direction régionale | Vue et statistiques limitées à sa direction et aux centres qui en dépendent. |
| **DAF** (Directeur Administratif et Financier) | Un centre (optionnel) | Utilise exclusivement le module de facturation de prestations (section 5). |
| **Administrateur / Directeur Général** | Global | Accès complet : configuration de l'offre de formation, gestion des comptes du personnel, gestion des permissions, statistiques globales. |
| **Super-utilisateur** | — | Compte technique Django : accès total, y compris à `/admin/`. À réserver aux personnes chargées de la maintenance du système. |

**Note technique.** Les permissions ne sont pas figées dans le code : un
administrateur peut, depuis l'écran **Gestion des permissions**
(`/bsb/rh/permissions`), ajouter ou retirer une permission précise à un groupe de
rôle, sans intervention d'un développeur. Il est donc possible d'ajuster finement ce
que peut faire, par exemple, un « Agent comptable », après la mise en service.

---

## 4. Parcours utilisateurs

### 4.1 Élève

1. Inscription sur le site public (`/accounts/register`) — création automatique du
   compte et connexion immédiate.
2. Parcourt les formations proposées (filières ouvertes dans un centre pour l'année
   scolaire en cours).
3. Sélectionne une formation, puis remplit un formulaire en quatre étapes :
   informations personnelles, coordonnées, informations complémentaires,
   mot de passe (au moment de l'inscription initiale) — puis, pour chaque
   candidature à une formation : informations personnelles, pièces jointes
   demandées, récapitulatif et validation.
4. Une fois le dossier **validé** par le personnel du centre, les échéances de
   paiement (« dettes ») apparaissent automatiquement sur le tableau de bord de
   l'élève.
5. L'élève paie ses tranches de scolarité dans l'ordre prévu (une tranche dite
   « primordiale » doit être soldée avant que les autres puissents être réglées) et
   télécharge sa quittance (document PDF avec QR code de vérification).

### 4.2 Formateur

Consulte, sans pouvoir les modifier, son tableau de bord, la liste des élèves de son
métier/centre et leur situation de paiement ; peut exporter cette liste (CSV/Excel).

### 4.3 Personnel de centre (gestionnaire, caissier, membre, agent comptable, DEPS)

Ces profils travaillent sur les pages accessibles à la racine du site (et non dans
`/bsb/`) : traitement des dossiers d'inscription (validation, rejet motivé),
encaissement des paiements de scolarité, consultation des statistiques — le
périmètre exact (un centre, une direction, ou l'ensemble du réseau) dépend du rôle
et des permissions accordées.

### 4.4 Direction (Administrateur, Directeur Général, Directeur inter-régional, DEPS)

Utilisent le back-office `/bsb/` pour :

- configurer l'offre de formation : directions régionales, centres, métiers
  (filières), modules, programmations de formation, types de frais et tranches,
  années scolaires ;
- gérer le personnel (création de comptes, quel que soit le rôle) depuis
  **RH → Agents** ;
- ajuster la matrice des permissions depuis **RH → Permissions** ;
- suivre les statistiques et exporter les données (PDF, CSV, Excel).

### 4.5 DAF — voir section 5.

---

## 5. Module Facturation et Prestations (DAF)

Ce module est **indépendant** du parcours de scolarité des élèves : il sert à
facturer des prestations de services quelconques (formations sur mesure,
locations de salle, etc.) à des clients externes, personnes physiques ou
entreprises.

Fonctionnement :

1. Recherche ou création d'un **client** (téléphone pour un particulier, numéro
   IFU pour une entreprise).
2. Sélection d'une ou plusieurs **prestations** au catalogue (ou création rapide
   d'une nouvelle prestation directement depuis le formulaire de facture).
3. Génération d'une **facture proforma** (devis).
4. Validation de la facture : elle devient **définitive** et reçoit un nouveau
   numéro officiel (format `ANNÉE_NUMÉRO/MESFPT/SG/BSB/DAF`). Seule une facture
   définitive peut être encaissée.
5. **Encaissement** : paiement total (doit correspondre exactement au solde
   restant) ou paiement ligne par ligne. Un reçu numéroté est généré
   automatiquement (`REC-ANNÉE-NUMÉRO`).
6. Téléchargement des documents (facture, reçu) au format PDF, avec l'en-tête
   officiel du ministère.

Accès réservé au rôle **DAF**, via des permissions dédiées
(`gerer_facturation`, `valider_facture_prestation`, `encaisser_prestation`).

---

## 6. Installation et démarrage (environnement de développement)

### 6.1 Prérequis

- Docker et Docker Compose (ou Docker Desktop sous Windows/Mac).
- Node.js, uniquement si l'on souhaite modifier les feuilles de style Tailwind.

### 6.2 Fichier `.env`

Toute la configuration sensible (clé secrète, mots de passe, domaines autorisés)
se trouve dans un fichier `.env` à la racine du projet, **jamais versionné dans
Git** (voir section 8). Un modèle est fourni dans `.env.example` : le copier vers
`.env` et renseigner chaque valeur.

Variables principales :

| Variable | Rôle |
|---|---|
| `SECRET_KEY` | Clé cryptographique interne de Django. À générer, ne jamais réutiliser d'un environnement à l'autre. |
| `DEBUG` | `False` en production. En développement local uniquement, peut être mis à `True` pour obtenir des pages d'erreur détaillées. |
| `ALLOWED_HOSTS` | Liste des noms de domaine/IP autorisés à servir l'application. |
| `CORS_ALLOWED_ORIGINS` | Origines autorisées à faire des requêtes avec identifiants (cookies) vers l'application. |
| `CSRF_TRUSTED_ORIGINS` | Origines dont les formulaires (POST) sont acceptés. Doit obligatoirement inclure le **protocole exact** (`http://` ou `https://`) réellement utilisé par les visiteurs — voir section 10. |
| `POSTGRES_*` | Connexion à la base de données. |
| `PGADMIN_*` | Identifiants de l'interface pgAdmin. |
| `REDIS_LOCATION_URL`, `CELERY_*` | Prévus pour un usage futur (cache, tâches de fond) — non exploités par le code actuel, voir section 9. |

### 6.3 Démarrage

```bash
docker compose up --build -d
```

Cette commande construit les images, crée les conteneurs et lance l'ensemble des
services. Les migrations de base de données et la préparation des fichiers
statiques se font automatiquement au démarrage du conteneur `suudu_backend`.

### 6.4 Premier compte administrateur

```bash
docker exec -it suudu_backend python manage.py createsuperuser
```

Ce compte permet de se connecter sur `/accounts/login` et d'accéder directement au
back-office (`/bsb/`). Depuis **RH → Agents**, créer ensuite les premiers comptes
réels (DAF, gestionnaires, formateurs, etc.).

### 6.5 Feuilles de style (Tailwind CSS)

Si une modification visuelle est nécessaire :

```bash
npm install
npm run dev      # recompile en continu pendant le développement
npm run build    # version optimisée, à lancer avant un déploiement
```

Le fichier source est `static/src/input.css` ; le fichier compilé
`static/css/output.css` est celui réellement chargé par les pages — il doit être
régénéré (`npm run build`) et inclus dans le dépôt avant chaque mise en production
si des styles ont changé, car `collectstatic` ne fait que copier ce fichier, il ne
le compile pas.

---

## 7. Déploiement en production

### 7.1 Ce qui n'est jamais transmis par `git pull`

Le fichier `.env` est volontairement exclu du dépôt (`.gitignore`). Une mise à jour
du code (`git pull`) sur le serveur **ne modifie jamais** ce fichier. Toute
modification de configuration (domaine, origines autorisées, mots de passe) doit
être appliquée **manuellement** sur le fichier `.env` du serveur.

### 7.2 Procédure de mise à jour

```bash
git pull
docker compose down
docker compose up --build -d
```

`docker compose down` puis `up --build` (et non un simple `restart`) sont
nécessaires dès qu'un fichier de code a changé : un `restart` relance les mêmes
conteneurs avec la même image, sans reconstruire ni relire un `.env` modifié.

### 7.3 Vérification après déploiement

```bash
docker compose logs -f suudu_backend
```

Toute erreur d'authentification, de connexion refusée ou de vérification CSRF
apparaît dans ces journaux, ainsi que dans `security.log` (à l'intérieur du
conteneur).

### 7.4 Réinitialisation de la base de données

Pour vider entièrement les données et repartir de zéro **sans** perdre la structure
des tables (schéma, permissions) :

```bash
docker exec -it suudu_backend python manage.py flush
```

Cette commande demande une confirmation explicite et est **irréversible** : à
n'utiliser que si l'on est certain de vouloir supprimer toutes les données
existantes.

---

## 8. Sécurité — règles à respecter

- **Ne jamais valider `.env` dans Git.** Il contient des mots de passe et la clé
  secrète de l'application.
- **Ne jamais réduire `DEBUG` à `True` en production.** Cela exposerait le détail
  technique des erreurs (chemins de fichiers, requêtes SQL) à n'importe quel
  visiteur.
- **Ne jamais ajouter de redirection HTTP → HTTPS dans ce projet** si la
  terminaison TLS (certificat) est gérée par un équipement en amont (pare-feu,
  répartiteur de charge). Ce dépôt ne gère volontairement aucun certificat : Nginx
  n'écoute qu'en HTTP sur le port 80. Ajouter une redirection forcée casserait
  l'accès pour tout le monde sans résoudre un éventuel problème de certificat, qui
  se règle uniquement du côté de l'infrastructure réseau.
- **Ne jamais modifier les ports déjà fonctionnels en production** sans
  concertation avec les personnes responsables du serveur.
- **Ne jamais faire suivre `docker compose down` du drapeau `-v` (ou
  `--volumes`) dans une procédure de redéploiement.** Ce drapeau supprime les
  volumes nommés — donc la base de données PostgreSQL, pgAdmin et Redis — et
  provoque une perte totale des données à chaque redéploiement. `deploy.sh` et
  la procédure de mise à jour (section 7.2) n'utilisent volontairement jamais
  ce drapeau ; toute réinitialisation de données doit rester une action
  manuelle et délibérée (`manage.py flush`, section 7.4), jamais une
  conséquence automatique d'une mise à jour.
- Les mots de passe sont validés par quatre règles Django (similarité avec le nom
  d'utilisateur, longueur minimale, mots de passe courants, mots de passe
  entièrement numériques) — ne pas les désactiver.
- Toute permission accordée à un rôle doit passer par l'écran **RH → Permissions**
  plutôt que par une modification de code, afin de garder une trace claire et
  réversible des accès accordés.

---

## 9. Points de vigilance techniques

Ces éléments existent dans la configuration mais ne sont, à ce jour, pas
pleinement exploités par le code applicatif. Ils sont documentés ici pour éviter
toute fausse hypothèse lors d'une future intervention :

- **Redis et Celery** sont installés et configurés (`REDIS_LOCATION_URL`,
  `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, conteneur `suudu_redis`), mais
  aucun cache Django (`CACHES`) ni aucune tâche asynchrone Celery n'est
  actuellement défini dans le code. Le conteneur Redis tourne sans consommateur
  réel — prévu pour un usage futur.
- **`djangorestframework_simplejwt`** est installé mais aucune authentification
  par jeton (JWT) n'est activée ; l'authentification utilisée est celle des
  sessions Django classiques (cookies).
- **pgAdmin** (`suudu_pgadmin`) ne publie aucun port vers l'hôte dans
  `docker-compose.yml` actuel, malgré la variable `PGADMIN_PORT` définie dans
  `.env`. Pour y accéder depuis un navigateur, il faut ajouter explicitement le
  mappage de port correspondant dans `docker-compose.yml`, ou s'y connecter
  depuis l'intérieur du réseau Docker.
- **Fuseau horaire** : `TIME_ZONE` est réglé sur `UTC` dans `config/settings.py`,
  et non sur l'heure de Ouagadougou. Les horodatages affichés (dates de création,
  de paiement) sont donc en UTC sauf conversion explicite côté gabarit.
- **`apis`** est une application au nom trompeur : elle ne sert qu'à valider le
  formulaire d'inscription (`UserRegisterSerializer`) et ne constitue pas une API
  publique.

---

## 10. Résolution des incidents courants

### « La vérification CSRF a échoué » (erreur 403)

Cause la plus fréquente : le navigateur accède au site avec un protocole
(`http://` ou `https://`) qui n'est pas listé, avec ce protocole exact, dans
`CSRF_TRUSTED_ORIGINS` (et `CORS_ALLOWED_ORIGINS`) du fichier `.env`. Cela arrive
typiquement lorsqu'un équipement réseau termine le HTTPS en amont du serveur : le
navigateur envoie une origine `https://...`, alors que le fichier `.env` ne
déclarait que la version `http://...`.

**Vérification** : consulter `docker compose logs suudu_backend`, qui indique
explicitement l'origine rejetée (« Origin checking failed »). **Correction** :
ajouter cette origine exacte, avec son protocole, à `CSRF_TRUSTED_ORIGINS` et
`CORS_ALLOWED_ORIGINS`, puis recréer le conteneur (`docker compose up -d`).

### « Ce site présente un certificat incorrect » (avertissement du navigateur/antivirus)

Ce message ne concerne **pas** le code de cette application (aucun certificat n'y
est géré). Il indique qu'un équipement en amont (pare-feu, proxy) présente un
certificat auto-signé ou émis par une autorité non reconnue. La correction se fait
exclusivement du côté de l'infrastructure réseau — voir section 8.

### Erreur de doublon (`IntegrityError`, contrainte unique) à la création d'un compte

Vérifier qu'aucun champ marqué comme unique dans `accounts/models.py` (par exemple
un champ laissé vide par deux comptes différents) n'entre en collision. Un champ
optionnel ne doit jamais porter à la fois `unique=True` et une valeur par défaut
partagée par plusieurs comptes.

### Après une modification du code, rien ne change en production

Vérifier qu'un `docker compose down` puis `up --build -d` a bien été exécuté (voir
section 7.2) — un simple `restart` ne suffit pas.

---

## 11. Organisation des fichiers

```
bsb-full-stack/
├── accounts/           Comptes utilisateurs, connexion/inscription, module DAF
├── apis/                Sérialiseur d'inscription (usage interne)
├── config/               Réglages Django, routage racine, middleware de sécurité
├── courses/             Cœur métier : centres, filières, inscriptions, paiements, back-office /bsb/
├── nginx/                Configuration du serveur web (nginx.conf, Dockerfile)
├── static/               Fichiers statiques sources (dont static/src/input.css pour Tailwind)
├── staticfiles/          Fichiers statiques regroupés (générés, non versionnés)
├── templates/            Gabarits HTML communs
├── media/                Fichiers déposés par les utilisateurs (non versionné)
├── docker-compose.yml    Définition des services (backend, base, nginx, redis, pgadmin)
├── Dockerfile             Image de l'application Django
├── entrypoint.sh          Séquence de démarrage du conteneur applicatif
├── deploy.sh              Script de déploiement (génère un .env de secours si absent)
├── requirements.txt       Dépendances Python
├── package.json           Dépendances et scripts de compilation Tailwind CSS
├── .env.example           Modèle de configuration (à copier en .env)
└── test_security.py       Script manuel de vérification des en-têtes de sécurité HTTP
```
