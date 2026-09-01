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
   - 9.1 Éléments présents mais non exploités · 9.2 Sécurité applicative ·
     9.3 Exécution en conteneur non privilégié · 9.4 Courrier électronique ·
     9.5 Rapport d'inspection · 9.6 Peuplement initial · 9.7 Facturation ·
     9.8 Réversibilité de l'interface · 9.9 Réversibilité du format des documents ·
     9.10 Pages d'erreur personnalisées
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

Le site publie enfin des **actualités**, auxquelles le public peut s'abonner pour
recevoir une notification par courrier électronique.

**Ce que ce dépôt contient.** Le code source complet de l'application (backend
Django, gabarits HTML, feuilles de styles Tailwind CSS) ainsi que la configuration
nécessaire pour la faire fonctionner avec Docker (base de données, serveur web,
cache, sauvegarde quotidienne).

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

Le projet est découpé en cinq applications Django, chacune avec une
responsabilité précise :

- **`accounts`** — Comptes utilisateurs, connexion/inscription, et le module de
  facturation DAF (clients, prestations, factures, encaissements).
- **`courses`** — Le cœur métier : centres de formation, filières (métiers),
  modules, programmations de formation, inscriptions, frais, dettes, paiements de
  scolarité, statistiques, et tout le back-office d'administration (`/bsb/`).
- **`actualites`** — Actualités publiques, abonnement à la lettre d'information et
  diffusion par courrier électronique. Cette application dispose de sa propre
  documentation : [actualites/docs/README.md](actualites/docs/README.md).
- **`apis`** — Contient uniquement un « sérialiseur » (`UserRegisterSerializer`)
  utilisé par la page d'inscription. Ce n'est **pas** une API exposée publiquement
  (aucune route n'y est raccordée) ; le nom peut prêter à confusion mais il s'agit
  d'un outil interne de validation de formulaire.
- **`config`** — Réglages globaux du projet (`settings.py`), routage racine
  (`urls.py`), et deux middlewares maison : l'un renforce les en-têtes de sécurité
  HTTP, l'autre bloque les tentatives de connexion répétées (voir 9.2).

### 2.3 Services Docker

Le fichier `docker-compose.yml` définit six services :

| Service | Conteneur | Rôle | Accès depuis l'extérieur |
|---|---|---|---|
| `suudu_backend` | Django + Gunicorn | Traite les requêtes de l'application | Non (uniquement via nginx) |
| `suudu_db` | PostgreSQL 15 | Stocke toutes les données | Non |
| `suudu_nginx` | Nginx | Sert les pages, les fichiers statiques et médias | Oui, port **80** |
| `suudu_redis` | Redis | Compteur du verrou anti-force brute (voir 9.2) | Non |
| `suudu_backup` | PostgreSQL 15 | Sauvegarde quotidienne de la base | Non |
| `suudu_pgadmin` | pgAdmin | Interface d'administration de la base de données | Non exposé par défaut (voir 9.1) |

Au démarrage, le conteneur `suudu_backend` exécute automatiquement, dans l'ordre :
application des migrations (`migrate`), regroupement des fichiers statiques
(`collectstatic --clear`), puis lancement du serveur (`gunicorn`). Cette séquence est
définie dans `entrypoint.sh`. Le peuplement initial des données n'y figure plus : il se
lance manuellement (voir 9.5).

Le conteneur applicatif tourne sans privilèges, sous un compte dédié et non sous `root`.
Cette contrainte a des conséquences sur les droits des dossiers montés : voir 9.3.

### 2.4 Schéma de routage général

| Préfixe d'URL | Destination | Public visé |
|---|---|---|
| `/` | `courses.urls` | Élèves, formateurs, personnel de centre |
| `/accounts/` | `accounts.urls` | Connexion, inscription, module DAF |
| `/bsb/` | `courses.urls_admin` | Back-office : direction, DEPS, administrateurs |
| `/actualites/` | `actualites.urls` | Actualités publiques et abonnement |
| `/bsb/actualites/` | `actualites.urls_admin` | Rédaction et diffusion des actualités |

**L'administration technique fournie par Django a été retirée.** L'adresse `/admin/` ne
répond plus, et les modules correspondants ne sont plus installés. `/bsb/` est désormais
la seule interface d'administration : c'est l'outil de travail quotidien du personnel de
direction, et toute intervention passe par lui. Cette suppression est délibérée et ne doit
pas être annulée pour dépanner : elle ferme une porte d'entrée connue des attaquants.

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
| **Super-utilisateur** | — | Compte technique Django : accès total à `/bsb/`, sans passer par les permissions. À réserver aux personnes chargées de la maintenance du système. |

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

À la différence de l'élève, tout membre du personnel franchit une **vérification
en deux étapes** à la première connexion depuis un appareil : après le mot de
passe, un code à quatre chiffres reçu par courriel (section 9.2). L'appareil est
ensuite reconnu pendant quatorze jours et le code n'est plus redemandé sur ce
poste ; tout autre appareil reste soumis au code.

### 4.4 Direction (Administrateur, Directeur Général, Directeur inter-régional, DEPS)

Utilisent le back-office `/bsb/` pour :

- configurer l'offre de formation : directions régionales, centres, métiers
  (filières), modules, programmations de formation, types de frais et tranches,
  années scolaires ;
- gérer le personnel (création de comptes, quel que soit le rôle) depuis
  **RH → Agents** ;
- ajuster la matrice des permissions **par rôle** depuis **RH → Permissions** ;
- déléguer à **une personne précise** un rôle et des permissions **en plus** de
  celles de son rôle, depuis **RH → Agents → Permissions** (bouton par agent) :
  les droits déjà couverts par le rôle sont signalés, l'admin coche seulement ce
  qu'il accorde en supplément. Modèle additif : pour retirer un droit hérité du
  rôle, on change le rôle ou la matrice ;
- suivre les statistiques et exporter les données (PDF, CSV, Excel).

Le back-office présente une **barre latérale** regroupant les accès par thème
(pilotage, scolarité, encaissements, offre de formation, RH et permissions,
communication, supervision, territoire, paramétrage), chaque agent ne voyant que
les rubriques ouvertes par ses permissions. Cette interface est **réversible**
par une commande, sans redéploiement (section 9.8). Chaque compte peut porter une
**photo de profil** (facultative), affichée dans la barre latérale, la liste des
agents et la fiche du compte ; à défaut, les initiales servent de repli.

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

### 7.5 Mise à niveau majeure de PostgreSQL

Les répertoires de données PostgreSQL ne sont pas compatibles d'une version
majeure à l'autre : démarrer une nouvelle version majeure sur le volume d'une
ancienne échoue au lancement (« database files are incompatible with server »).
Le serveur ne corrompt donc rien de lui-même — le risque de perte vient d'une
suppression de volume faite dans la précipitation. La voie sûre est la
sauvegarde logique (`pg_dump` puis `pg_restore`), qui traverse n'importe quel
écart de version.

**Cette bascule est automatique et intégrée à `redeploy.sh`.** Après le
`git pull`, le script `pg_migrate.sh` est appelé ; il n'agit que si une bascule
est réellement nécessaire :

- si le cluster de la version cible tourne déjà, il ne fait rien ;
- s'il n'existe aucune donnée antérieure (première installation), il ne fait
  rien et laisse l'initialisation normale opérer ;
- sinon, il sauvegarde l'ancien cluster au moyen d'un conteneur temporaire à
  l'ancienne version (dans `./backups/premigration_pg<ancienne>_<horodatage>.dump`),
  initialise le cluster de la version cible sur un **nouveau volume**
  (`suudu_postgres_data_18`) et y restaure les données.

L'opération est **non destructive** : l'ancien volume
(`suudu_postgres_data`) est conservé intact et sert de point de retour. Pour
revenir en arrière, il suffit de rétablir dans `docker-compose.yml` l'ancienne
image et l'ancien nom de volume, puis `docker compose up -d`. Une fois la
migration validée en production, l'ancien volume peut être supprimé
manuellement (`docker volume rm <projet>_suudu_postgres_data`).

Deux points à respecter pour le versionnage du dépôt :

- **Les deux services PostgreSQL** (`suudu_db` et `suudu_backup`) portent le
  même tag d'image : un `pg_dump` d'une version antérieure ne peut pas
  sauvegarder un serveur plus récent.
- PostgreSQL 18 range par défaut ses données dans un sous-dossier par version
  sous `/var/lib/postgresql`. La variable `PGDATA: /var/lib/postgresql/data`
  du service `suudu_db` conserve l'emplacement classique, si bien que le volume
  et les scripts `db_dump.sh` / `db_restore.sh` restent inchangés.

Le déploiement d'une nouvelle version majeure se résume donc, côté serveur, à
un `git pull` puis `./redeploy.sh` — la bascule est prise en charge une seule
fois, automatiquement, et les exécutions suivantes ne la rejouent pas.

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
- **Ne pas contourner la vérification en deux étapes du personnel** (code par
  courriel depuis un appareil non reconnu, section 9.2). Elle suppose que chaque
  compte d'agent porte une adresse de courriel valide : un compte sans adresse ne
  peut pas se connecter et doit en recevoir une depuis **RH → Agents**.
- Toute permission accordée à un rôle doit passer par l'écran **RH → Permissions**
  plutôt que par une modification de code, afin de garder une trace claire et
  réversible des accès accordés.
- **Ne jamais retirer les exclusions du fichier `.dockerignore`.** Sans elles, le
  `COPY . .` du `Dockerfile` recopie l'intégralité du dossier de travail dans
  l'image, `.env` compris : la clé secrète et les mots de passe de la base et de
  pgAdmin deviennent lisibles par toute personne ayant accès à l'image, alors
  même que le fichier est exclu de Git. Sont également exclus `.git`, `backups/`
  (dumps de la base), `media/` (documents déposés par les usagers) et
  `staticfiles/`. Si une image a été construite sans ces exclusions et diffusée,
  considérer les secrets du `.env` comme compromis et procéder à leur rotation.

---

## 9. Points de vigilance techniques

Cette section rassemble les comportements non évidents du projet : ceux qu'une
lecture du code seule ne permet pas de deviner, et dont l'ignorance conduit à des
diagnostics erronés. Les commentaires du code y renvoient plutôt que de répéter
ces explications.

### 9.1 Éléments présents mais non exploités

- **Celery** est installé et configuré (`CELERY_BROKER_URL`,
  `CELERY_RESULT_BACKEND`), mais aucune tâche asynchrone n'est définie dans le
  code. Aucune file de traitement n'existe. Redis, en revanche, est bien utilisé
  depuis la mise en place du verrou anti-force brute (voir 9.3).
- **`djangorestframework_simplejwt`** est installé mais aucune authentification
  par jeton n'est activée ; l'authentification utilisée est celle des sessions
  Django classiques.
- **pgAdmin** (`suudu_pgadmin`) ne publie aucun port vers l'hôte, malgré la
  variable `PGADMIN_PORT` définie dans `.env`. Pour y accéder, ajouter
  explicitement le mappage de port dans `docker-compose.yml`.
- **`apis`** est une application au nom trompeur : elle ne sert qu'à valider le
  formulaire d'inscription et ne constitue pas une API publique.
- **La table `django_admin_log`** subsiste en base, orpheline, depuis le retrait
  de l'administration Django. Aucun code ne la lit. Sa suppression manuelle
  (`DROP TABLE django_admin_log`) est possible après vérification.
- **Fuseau horaire** : `TIME_ZONE` vaut `UTC`, et non l'heure de Ouagadougou. Les
  horodatages affichés sont donc en UTC, sauf conversion explicite dans le
  gabarit.

### 9.2 Sécurité applicative

- **Politique de sécurité du contenu (CSP)** : la directive `style-src` combine
  `'self'` et un nonce. Un nonce et `'unsafe-inline'` sont mutuellement
  exclusifs — dès qu'un nonce figure dans une directive, le navigateur ignore
  `'unsafe-inline'`. Il n'existe donc pas de position intermédiaire : tout
  attribut `style=` écrit dans un gabarit sera bloqué. Une valeur calculée
  (largeur de barre, position) se pose en JavaScript depuis un attribut `data-*`.
  Le passage par `el.style.width` reste autorisé ; `setAttribute("style", ...)`
  et `style.cssText` sont bloqués.
- Les gabarits de **PDF (WeasyPrint) et de courrier électronique** conservent
  leurs styles en ligne : ils ne passent pas par un navigateur, la CSP ne s'y
  applique pas.
- `data:` est conservé dans `img-src` pour deux gabarits qui dessinent leur motif
  de fond en SVG intégré. Contrairement à ce qu'indiquent certains rapports
  d'audit, `data:` dans `img-src` ne permet pas l'exécution de script : il
  faudrait pour cela le retrouver dans `script-src`, `object-src` ou `frame-src`.
- **Messages Django** : `MESSAGE_STORAGE` utilise la session et non un cookie. Le
  stockage par défaut essaie d'abord le cookie ; or, lorsqu'il l'efface, Django
  appelle `delete_cookie()`, qui ne transmet ni `HttpOnly` ni `Secure`. Un audit
  signale alors un cookie non protégé — sans risque réel, le cookie étant vide et
  expiré, mais impossible à corriger à la source. Le stockage en session
  supprime le cookie et l'alerte.
- **Cookies en développement local** : `SESSION_COOKIE_SECURE` et
  `CSRF_COOKIE_SECURE` valent `not DEBUG`. En HTTP simple (`http://localhost`),
  le navigateur n'envoie pas ces cookies : la connexion et la vérification CSRF
  échouent. Ce comportement est attendu et ne doit pas être « corrigé » en
  production. Pour tester ce flux en local, utiliser un tunnel HTTPS.
- **Limitation des tentatives de connexion** : deux garde-fous complémentaires
  cohabitent. Nginx plafonne le débit par adresse IP (`limit_req_zone`), tandis
  que `accounts/ratelimit.py` verrouille le compte visé — lequel, contrairement à
  une adresse IP, ne peut pas être usurpé. Le compteur applicatif est stocké dans
  Redis afin d'être partagé par les trois processus `gunicorn` ; sans cela, le
  seuil serait trois fois plus permissif. Si Redis devient indisponible, le
  verrou s'ouvre (`IGNORE_EXCEPTIONS`) : le site reste accessible et les erreurs
  sont journalisées, plutôt que de renvoyer une erreur 500 sur chaque page.
- **Connexion du personnel en deux étapes.** Un élève se connecte directement ;
  tout autre rôle passe par un code à quatre chiffres envoyé par courriel, valable
  deux minutes, à usage unique. Le code n'est jamais stocké en clair — seul son
  haché figure dans la session anonyme du visiteur, le temps de la vérification —
  et il tolère cinq saisies puis quatre envois au maximum. Un appareil validé
  reçoit un cookie signé (`appareil_connu`, `HttpOnly`, quatorze jours) qui dispense
  du code sur ce seul poste. Le cookie est signé avec une empreinte du mot de
  passe : **changer de mot de passe révoque d'un coup tous les appareils**, sans
  écran ni procédure. Toute connexion depuis un appareil non reconnu envoie en
  outre un **avis au titulaire** : c'est la seule alerte qui lui parvienne
  directement, sans attendre le rapport d'inspection (section 9.5). L'échec
  d'envoi de l'un ou l'autre courriel n'interrompt jamais la connexion.
- **Connexion séparée des comptes d'administration technique.** Les comptes
  capables de modifier la base (superutilisateurs, rôle « admin », ou tout compte
  ayant reçu la permission `acces_administration_technique` via **RH →
  Permissions**) ne se connectent **pas** par la page publique : celle-ci les
  refuse par un message générique, si bien qu'un mot de passe d'administrateur
  volé y est inutile — indépendamment de toute URL secrète. Ils passent par une
  **page dédiée** dont le chemin vient du `.env` (`ADMIN_LOGIN_PATH`, jamais écrit
  dans le dépôt, renouvelable), n'est lié depuis aucune page et n'apparaît pas
  dans un `robots.txt`. Cette page n'authentifie que les comptes habilités
  (message générique pour les autres), **exige le code à chaque connexion** (aucune
  dispense d'appareil pour ces comptes), et peut être restreinte à des plages
  d'adresses IP (`ADMIN_LOGIN_IPS`, en notation CIDR) : hors liste, elle renvoie
  un **404** plutôt qu'un refus, pour ne pas confirmer son existence. La liste vide
  (défaut) désactive ce filtrage. Le **Directeur Général** fait exception et peut
  se connecter par les deux portes. L'obscurité du chemin n'est qu'un filtre de
  bruit ; la sécurité réelle tient à la fermeture de la page publique, au code
  e-mail et, le cas échéant, au filtrage par adresse.
  Le code n'est pas exigé à *chaque* connexion : après une vérification
  réussie, l'admin bénéficie d'une **dispense** de 5 h par défaut sur son
  appareil, qu'il peut porter jusqu'à 24 h **pour la journée** depuis « mon
  compte » (réglage propre à lui seul). La dispense ne franchit jamais minuit
  et le réglage revient à 5 h chaque jour. Elle repose sur un cookie signé
  avec l'empreinte du mot de passe, donc révoqué au changement de mot de passe.
- **Photo de profil.** Le champ est facultatif et restreint aux formats JPG, PNG
  et WEBP ; le contenu réel est vérifié par Pillow (un exécutable renommé en
  `.png` est refusé) et le poids plafonné à deux mégaoctets. Les fichiers
  déposés sont servis par Nginx en pièce jointe (`Content-Disposition: attachment`,
  `X-Content-Type-Options: nosniff`), jamais rendus dans le navigateur.

### 9.3 Exécution en conteneur non privilégié

Le conteneur applicatif ne tourne pas en `root` mais sous le compte `appuser`
(uid 10001, défini dans le `Dockerfile`). Cette contrainte a trois conséquences
que Docker ne résout pas seul.

- **Un montage lié (`bind mount`) ignore le `chown` de l'image** et conserve les
  droits du dossier de l'hôte. Un dossier rempli par une version antérieure du
  conteneur, qui tournait alors en `root`, devient inaccessible en écriture.
- **`staticfiles` est un volume nommé** (`suudu_staticfiles`) et non un montage
  lié. Docker initialise un volume nommé avec les droits de l'image : il reste
  donc inscriptible quel que soit l'hôte. Il s'agit de données dérivées,
  régénérées à chaque démarrage par `collectstatic --clear`. Le même volume est
  monté en lecture seule par Nginx.
- **`media` reste un montage lié**, les documents déposés par les usagers devant
  rester consultables depuis l'hôte. Son propriétaire doit donc être aligné sur
  l'uid 10001, faute de quoi tout téléversement échoue en `PermissionError`.
- **`backups` est également un montage lié**, mais dans l'autre sens : c'est le
  conteneur `suudu_backup` qui y écrit, en tant que `root`, si bien que le dossier
  devient inaccessible en écriture pour l'utilisateur de l'hôte. `db_dump.sh`
  échoue alors à l'étape `docker cp` avec `permission denied`. Le dossier doit donc
  appartenir à l'utilisateur du projet ; le conteneur, qui écrit en `root`,
  continue de fonctionner sans changement.
- Le script `./fix_perms.sh` réalise ces deux alignements. Il est idempotent, ne
  requiert pas de `sudo`, et est appelé automatiquement par `deploy.sh` et
  `redeploy.sh`. Le lancer à la main après avoir restauré une sauvegarde ou copié
  des fichiers dans `media/` depuis un autre poste.
- **`logs` est également un volume nommé** (`suudu_security_logs`), pour la même
  raison : le journal de sécurité doit rester inscriptible indépendamment des
  droits du dossier de travail sur l'hôte.
- **Sous WSL2**, les chemins `/mnt/c` refusent l'appel `chmod()` même lorsque
  l'écriture aboutit. `FILE_UPLOAD_PERMISSIONS` et
  `FILE_UPLOAD_DIRECTORY_PERMISSIONS` sont donc fixés à `None`, ce qui désactive
  le `chmod` appliqué par Django après chaque écriture.

### 9.4 Courrier électronique

- Tant que `EMAIL_HOST` est vide, Django utilise le backend « console » : le
  message complet, **adresses des abonnés comprises**, est écrit sur la sortie
  standard, donc dans les journaux du conteneur. À réserver au développement.
- Avec Google Workspace, `DEFAULT_FROM_EMAIL` doit correspondre à
  `EMAIL_HOST_USER`, ou à un alias « Envoyer en tant que » vérifié. Dans le cas
  contraire, Gmail réécrit silencieusement l'en-tête `From`.
- `SITE_URL` sert à construire les liens absolus des messages envoyés hors
  requête HTTP (commande `notifier_actualites`). Laissée vide, la valeur de repli
  fabrique un lien en `http://` vers un site servi exclusivement en HTTPS.
- `EMAIL_TIMEOUT` est indispensable : sans délai d'attente, un serveur SMTP qui
  ne répond pas immobilise un processus `gunicorn` pendant 120 secondes.

### 9.5 Rapport d'inspection des connexions

L'application `audit` produit un classeur Excel — indicateurs, alertes, graphiques et
journal détaillé — et l'envoie par courrier électronique. Elle est prévue pour une
exécution planifiée :

```bash
docker compose exec suudu_backend python manage.py envoyer_rapport_audit
```

Les destinataires se gèrent aussi à l'écran **Supervision → Réglage d'envoi**
(`/bsb/historique-connexions/destinataires`), qui permet en plus de **déclencher un
envoi immédiat** et de **programmer un envoi automatique** (quotidien, hebdomadaire ou
mensuel, avec le jour et l'heure), le tout par clics. Les adresses de cet écran
s'ajoutent à celles de `AUDIT_DESTINATAIRES`.

L'envoi automatique est assuré par le service `suudu_audit` de `docker-compose.yml` :
il exécute `envoyer_rapport_audit --auto` à intervalle régulier
(`AUDIT_SCAN_INTERVAL`, 3600 s par défaut). La commande est **auto-régulée** : elle lit
le réglage d'écran, n'envoie que lorsqu'une échéance est atteinte et jamais deux fois la
même (l'horodatage de la dernière diffusion est conservé en base). Une vérification
fréquente est donc sans risque, et aucune tâche `cron` sur l'hôte n'est nécessaire. La
fenêtre du rapport suit la fréquence choisie (un jour, sept jours, un mois).

Les seuils de déclenchement des alertes et les destinataires par défaut se règlent
dans `.env` (`AUDIT_DESTINATAIRES`, `AUDIT_PERIODE_JOURS`, `AUDIT_SEUIL_*`). Le détail
figure dans [audit/README.md](audit/README.md).

Point de vigilance : ce rapport n'a de valeur que si les **échecs** de connexion sont
journalisés. Ils le sont dans `HistoriqueConnexion` avec le type `echec` — le compteur
Redis anti-force brute, lui, expire au bout de quinze minutes et ne laisse aucune trace
exploitable a posteriori.

---

### 9.6 Peuplement initial des données

`populate_data.py` n'est plus exécuté au démarrage du conteneur ; la ligne
correspondante de `entrypoint.sh` est volontairement commentée. Ce script crée un
superutilisateur et 51 comptes d'agents dont les mots de passe sont écrits en dur
dans un fichier suivi par Git, et les affiche dans les journaux de déploiement.
Il n'a sa place qu'en phase de recette, lancé manuellement, une seule fois, sur
une base neuve :

```bash
docker compose exec suudu_backend python manage.py shell < populate_data.py
```

Désactiver cette exécution empêche la recréation de comptes supprimés, mais ne
change rien aux comptes déjà présents en base : seule la rotation des mots de
passe existants lève le risque.

Deux précisions sur les données transcrites, à ne pas « corriger » de nouveau :

- Le fichier source mélange les ordres « NOM Prénom » et « Prénom NOM ». C'est le
  nom d'utilisateur (`Prénom.NOM`, colonne fiable) qui fait foi pour départager.
- Quatre anomalies ont été résolues avant transcription : deux comptes avaient
  leurs identifiants et adresses inversés et réutilisaient l'adresse d'un
  troisième ; deux adresses manquantes ou tronquées ont été remplacées par une
  valeur d'attente. Le champ `sexe` n'est fourni par aucune ligne : la valeur par
  défaut du modèle s'applique à tous. Ces valeurs sont à corriger par chaque
  titulaire via l'écran « Mon profil ».

### 9.7 Facturation

Le numéro de facture est unique sur l'ensemble de la table, factures proforma et
définitives confondues. Le compteur ne doit donc jamais être filtré par
`type_facture` : une proforma et une facture définitive de la même année
calculeraient alors le même numéro. Le numéro est régénéré chaque fois qu'il est
remis à vide, ce qui correspond au passage d'une proforma à une facture
définitive.

### 9.8 Réversibilité de l'interface du back-office

La refonte du back-office (barre latérale, écrans repris, tableaux adaptés au
téléphone) est **réversible sans redéploiement**, en développement comme en
production. Deux réglages, lus depuis `.env`, la commandent :

- `BO_NAVIGATION` (`sidebar` par défaut, ou `navbar`) : forme de la navigation ;
- `BO_UI` (`nouveau` par défaut, ou `classique`) : choix des écrans rendus.

Toute refonte d'écran conserve son gabarit d'origine sous le même nom suffixé
`_classique`. `courses/ui.py` décide lequel est rendu selon `BO_UI` ; un écran
sans variante `_classique` est rendu tel quel, si bien que la bascule ne peut
jamais provoquer d'erreur de gabarit introuvable.

Le script `./bascule_ui.sh` écrit ces variables et recrée le conteneur (un simple
`restart` ne relit pas le `.env`) :

```bash
./bascule_ui.sh              # affiche l'état courant
./bascule_ui.sh nouveau      # interface refondue (barre latérale + écrans repris)
./bascule_ui.sh classique    # retour intégral à l'interface d'origine
./bascule_ui.sh sidebar      # bascule la seule navigation vers la barre latérale
./bascule_ui.sh navbar       # bascule la seule navigation vers la barre horizontale
```

Sur les tableaux de plus de trois colonnes, l'excédent est replié dans une fiche
dépliable au téléphone (`static/js/bo-tableau.js`), et les conteneurs de ces pages
occupent toute la largeur disponible sous la barre latérale. L'inventaire de ces
pages est tenu dans `docs_pages_responsives.md`.

### 9.9 Réversibilité du format des documents générés

Les pièces PDF (quittances élève et caissier, récépissé, attestation, facture DAF,
reçu de prestation) sont rendues au **format officiel** calqué sur la quittance de la
DGI : en-tête *Burkina Faso / MESFPT / Burkina Suudu Bawdè*, fond marbré grisâtre,
tableau transparent, code QR de vérification et pied de page normalisé. Le gabarit
unique est `templates/documents/quittance_officielle.html`, alimenté dynamiquement par
un contexte (titre, parties, colonnes, total, mentions) construit dans les vues.

Ce format est **réversible sans redéploiement**, comme le back-office. Le réglage
`DOC_MODELE` (lu depuis `.env`, `officiel` par défaut, ou `classique`) commande le
rendu ; chaque vue teste ce réglage et retombe sur son ancien tracé (ReportLab A5 pour
les quittances, WeasyPrint d'origine pour les autres) quand il vaut `classique`.

```bash
./bascule_doc.sh             # affiche l'état courant
./bascule_doc.sh officiel    # format officiel (défaut)
./bascule_doc.sh classique   # retour intégral aux anciens tracés
```

La police du rendu officiel est **Liberation Sans** (métrique Arial), installée dans
l'image applicative via `fonts-liberation` (Dockerfile). Le fond marbré et le filigrane
gris sont générés une fois par Pillow puis mémoïsés, sans fichier image à embarquer.

### 9.10 Pages d'erreur personnalisées

Les pages d'erreur portent la charte Yupaan. Django rend `templates/40*.html` et
`templates/500.html` (400, 403, 403 CSRF, 404, 429, 500) ; les pages 500 et CSRF sont
autonomes car leurs gestionnaires n'ont pas de contexte de requête. Nginx sert lui-même
`nginx/errors/429.html` (dépassement de débit) et `nginx/errors/50x.html` (backend
injoignable), bakées dans son image, sans intercepter les erreurs applicatives de Django.

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
bsb-latest/
├── accounts/             Comptes utilisateurs, connexion/inscription, module DAF
├── actualites/           Actualités publiques et diffusion aux abonnés
├── apis/                 Sérialiseur d'inscription (usage interne)
├── config/               Réglages Django, routage racine, middlewares de sécurité
├── courses/              Cœur métier : centres, métiers, inscriptions, paiements, back-office /bsb/
├── nginx/                Configuration du serveur web (nginx.conf, Dockerfile)
├── static/               Fichiers statiques sources (dont static/src/input.css pour Tailwind)
├── templates/            Gabarits HTML communs
├── media/                Documents déposés par les usagers (non versionné, voir 9.3)
├── backups/              Sauvegardes de la base produites par db_dump.sh (non versionné)
├── docker-compose.yml    Définition des services (backend, base, nginx, redis, pgadmin, sauvegarde)
├── Dockerfile            Image de l'application Django
├── .dockerignore         Exclusions du contexte de build (voir section 8)
├── entrypoint.sh         Séquence de démarrage du conteneur applicatif
├── deploy.sh             Premier déploiement (génère un .env de secours si absent)
├── redeploy.sh           Mise à jour d'un déploiement existant
├── fix_perms.sh          Alignement des droits de media/ et backups/ (voir 9.3)
├── db_dump.sh            Sauvegarde de la base
├── db_restore.sh         Restauration d'une sauvegarde
├── populate_data.py      Peuplement initial, à lancer manuellement (voir 9.5)
├── requirements.txt      Dépendances Python
├── package.json          Dépendances et scripts de compilation Tailwind CSS
└── test_security.py      Script manuel de vérification des en-têtes de sécurité HTTP
```

Les fichiers statiques regroupés par `collectstatic` ne figurent plus dans un
dossier de l'hôte : ils résident dans le volume nommé `suudu_staticfiles`
(voir 9.3). Pour les inspecter :

```bash
docker compose exec suudu_backend ls /app/staticfiles
```
