# Application `actualites`

Publication d'actualités par l'administration et diffusion par courrier électronique
aux personnes abonnées.

Cette application est autonome : elle ne dépend d'aucun modèle de `courses` ni de
`accounts`, à l'exception du décorateur de permissions `courses.permissions.require_permission`
et du modèle utilisateur du projet, référencé par `settings.AUTH_USER_MODEL`.

---

## Sommaire

1. [Périmètre fonctionnel](#1-périmètre-fonctionnel)
2. [Modèle de données](#2-modèle-de-données)
3. [Parcours utilisateur](#3-parcours-utilisateur)
4. [Permissions](#4-permissions)
5. [Routage](#5-routage)
6. [Envoi des courriers électroniques](#6-envoi-des-courriers-électroniques)
7. [Mesures de sécurité](#7-mesures-de-sécurité)
8. [Données de démonstration](#8-données-de-démonstration)
9. [Organisation des fichiers](#9-organisation-des-fichiers)
10. [Limites connues](#10-limites-connues)
11. [Annonces défilantes](#11-annonces-défilantes)

---

## 1. Périmètre fonctionnel

L'application couvre trois besoins :

- rédiger et publier des actualités depuis le back-office ;
- consulter ces actualités sur le site public ;
- prévenir par courrier électronique les personnes abonnées lors de chaque publication,
  avec possibilité de se désabonner à tout moment.

Elle ne gère ni catégories, ni commentaires, ni campagnes rédigées séparément des
actualités. Le courrier envoyé est construit à partir de l'actualité elle-même.

---

## 2. Modèle de données

### 2.1 `Actualite`

| Champ | Type | Rôle |
|---|---|---|
| `titre` | texte, 200 | Titre affiché et repris dans l'objet du courrier |
| `slug` | slug, unique | Adresse de la page, calculée depuis le titre si laissée vide |
| `chapeau` | texte, 300 | Résumé affiché dans la liste et dans le courrier |
| `contenu` | texte long | Corps de l'article |
| `image` | image, facultatif | Illustration, stockée dans `media/actualites/` |
| `auteur` | clé étrangère | Utilisateur ayant créé l'actualité |
| `statut` | `brouillon` ou `publiee` | Seules les actualités publiées sont visibles |
| `date_publication` | date et heure | Renseignée automatiquement à la publication si absente |
| `date_fin_publication` | date et heure, facultatif | Retrait automatique de l'affichage à l'échéance |
| `abonnes_notifies` | booléen | Empêche un second envoi si l'actualité est modifiée puis republiée |

Une actualité est visible du public lorsque son statut vaut `publiee`, que sa date de
publication est atteinte, et que sa date de fin de publication — si elle est renseignée —
ne l'est pas encore (`Actualite.est_visible`). Une date de début future permet de préparer
une publication à l'avance : l'article reste masqué jusqu'à l'échéance.

La fin de publication est **un retrait d'affichage, pas une suppression** : le statut en base
reste `publiee` et l'article demeure consultable depuis le back-office. La condition est
évaluée à chaque requête, sans tâche planifiée. Le formulaire refuse une date de fin
antérieure ou égale à la date de publication.

Le calcul du `slug` garantit l'unicité en suffixant un numéro (`titre`, `titre-2`, `titre-3`).

### 2.2 `AbonneNewsletter`

| Champ | Type | Rôle |
|---|---|---|
| `email` | courriel, unique | Normalisé en minuscules à l'enregistrement |
| `actif` | booléen | Faux après désabonnement ; la ligne est conservée |
| `token` | texte, unique | Jeton de désabonnement, 32 octets aléatoires |
| `date_inscription` | date et heure | Renseignée automatiquement |
| `date_desinscription` | date et heure | Renseignée au désabonnement |
| `nb_echecs` | entier | Refus d'envoi consécutifs ; l'abonnement est désactivé au troisième |

Une adresse désabonnée qui s'inscrit à nouveau réactive sa ligne existante : aucun
doublon n'est créé et le jeton reste le même.

---

## 3. Parcours utilisateur

### 3.1 Visiteur

1. Consulte la liste des actualités publiées, paginée par neuf.
2. Ouvre une actualité et se voit proposer trois autres articles récents.
3. Saisit son adresse électronique dans le bloc d'abonnement présent en bas des deux pages.
4. Reçoit un courrier à chaque publication ultérieure.
5. Se désabonne par le lien figurant en pied de chaque courrier, sans avoir à se connecter.

### 3.2 Administration

1. Ouvre `/bsb/actualites/`, où figurent toutes les actualités, brouillons compris.
2. Crée ou modifie une actualité. Tant que le statut reste `brouillon`, rien n'est
   visible du public et aucun courrier n'est envoyé.
3. Déclenche « Publier et notifier ». Une confirmation est demandée, car l'action
   entraîne un envoi à l'ensemble des abonnés actifs.
4. Consulte la liste des abonnés depuis le bouton « Abonnés ».

La publication est enregistrée **avant** la tentative d'envoi. Si le serveur de
courrier est indisponible, l'actualité reste publiée et un message d'avertissement
signale l'échec de l'envoi.

---

## 4. Permissions

Trois permissions sont déclarées sur le modèle `Actualite` :

| Codename | Portée |
|---|---|
| `gerer_actualites` | Créer, modifier, supprimer une actualité |
| `publier_actualite` | Publier et déclencher l'envoi aux abonnés |
| `gerer_newsletter` | Consulter la liste des abonnés |

La migration `0002_seed_permissions` les attribue aux groupes **Admin** et
**Directeur Général**. Comme pour le reste de la plateforme, l'attribution se modifie
ensuite depuis l'écran **RH → Permissions**, sans intervention sur le code.

Les vues du back-office sont protégées par `@require_permission(...)`, le décorateur
du projet : un refus produit une page 403 et jamais une redirection vers la connexion.

---

## 5. Routage

### 5.1 Public — préfixe `/actualites/`

| Adresse | Nom | Rôle |
|---|---|---|
| `/actualites/` | `actualites:liste` | Liste paginée des actualités publiées |
| `/actualites/<slug>` | `actualites:detail` | Une actualité |
| `/actualites/abonnement` | `actualites:abonnement` | Inscription, `POST` uniquement |
| `/actualites/desabonnement/<token>` | `actualites:desabonnement` | Désabonnement par jeton |

### 5.2 Back-office — préfixe `/bsb/actualites/`

| Adresse | Nom |
|---|---|
| `/bsb/actualites/` | `bsb_actualites:actualite_list` |
| `/bsb/actualites/create` | `bsb_actualites:actualite_create` |
| `/bsb/actualites/<id>/update` | `bsb_actualites:actualite_update` |
| `/bsb/actualites/<id>/delete` | `bsb_actualites:actualite_delete` |
| `/bsb/actualites/<id>/publier` | `bsb_actualites:actualite_publier` |
| `/bsb/actualites/abonnes` | `bsb_actualites:abonne_list` |

---

## 6. Envoi des courriers électroniques

### 6.1 Configuration

`config/settings.py` choisit le mode d'envoi selon la présence de `EMAIL_HOST` dans
le fichier `.env` :

- **variable absente** : les courriers sont affichés dans la console du conteneur.
  C'est le comportement en développement ; aucun message ne part réellement.
- **variable renseignée** : envoi par SMTP. Les variables attendues sont
  `EMAIL_HOST`, `EMAIL_PORT` (587 par défaut), `EMAIL_HOST_USER`,
  `EMAIL_HOST_PASSWORD` et `EMAIL_USE_TLS` (vrai par défaut).

L'expéditeur est `DEFAULT_FROM_EMAIL`, défini dans `settings.py`.

### 6.2 Contenu

Chaque destinataire reçoit un message à deux versions, texte et HTML, comportant le
titre de l'actualité, son chapeau, un lien vers la page de l'article et un lien de
désabonnement qui lui est propre. Les gabarits se trouvent dans
`templates/actualites/email/`.

L'objet du message suit la forme : `Nouvelle actualité sur Yu-Paan : {titre}`.

### 6.3 Diffusion différée

Une commande d'administration reprend les actualités publiées, dont la date est
atteinte, et dont les abonnés n'ont pas encore été prévenus :

```bash
docker exec -it suudu_backend python manage.py notifier_actualites --simulation
docker exec -it suudu_backend python manage.py notifier_actualites
```

Elle couvre deux cas que le bouton du back-office ne traite pas : les **publications
planifiées**, dont la date était encore à venir au moment de l'enregistrement, et les
**envois interrompus**. Programmée toutes les quinze minutes, elle rend la diffusion
indépendante de la requête web.

### 6.4 Fonctionnement

La fonction `notifications.notifier_abonnes(actualite, request=None)` :

1. ne fait rien si l'actualité n'est pas visible ou si les abonnés ont déjà été prévenus ;
2. construit les adresses absolues à partir de la requête lorsqu'elle est fournie,
   sinon à partir du premier nom de `ALLOWED_HOSTS` ;
3. envoie les messages un à un, cinquante par connexion SMTP : le refus d'une adresse
   n'interrompt pas la diffusion aux suivantes ;
4. incrémente `nb_echecs` sur l'abonné en cas de refus, remet le compteur à zéro après
   un envoi réussi, et désactive l'abonnement après trois refus consécutifs ;
5. marque l'actualité comme notifiée et retourne le nombre d'envois réussis.

Cette fonction est appelée par la vue de publication, mais reste utilisable seule
depuis un shell ou une commande d'administration.

---

## 7. Mesures de sécurité

| Risque | Mesure |
|---|---|
| Accès non autorisé au back-office | `@require_permission` sur toutes les vues d'administration |
| Modification par requête forgée | Jeton CSRF sur tous les formulaires |
| Écriture par simple lien | Suppression et publication acceptées en `POST` uniquement |
| Inscriptions automatisées | Champ piège masqué dans le formulaire d'abonnement |
| Découverte d'adresses inscrites | Message de retour identique que l'adresse soit connue ou non |
| Désabonnement par un tiers | Jeton aléatoire de 32 octets, aucun identifiant en clair dans l'adresse |
| Injection de code dans un article | Contenu rendu avec le filtre `linebreaks`, qui échappe le HTML saisi |
| Divulgation des brouillons | Réponse 404, et non 403, pour ne pas révéler leur existence |
| Dépôt d'un fichier hostile en illustration | `ImageField` vérifie le contenu du fichier ; `clean_image()` restreint en outre aux types JPEG, PNG et WebP, et à 5 Mo |
| Épuisement du disque par abonnements répétés | Débit plafonné par nginx sur `/actualites/abonnement` |

L'attribut `accept` du sélecteur de fichier n'est qu'un confort d'interface : le contrôle qui
compte est `clean_image()`, côté serveur.

Les en-têtes de sécurité HTTP et la politique de mots de passe restent ceux du projet,
appliqués globalement par `config.middleware.SecurityHeadersMiddleware` et par nginx.

---

## 8. Données de démonstration

Une commande d'administration crée un jeu de données représentatif, destiné aux
essais et aux démonstrations.

```bash
docker exec -it suudu_backend python manage.py actualites_demo
docker exec -it suudu_backend python manage.py actualites_demo --supprimer
```

Le jeu comprend six actualités, dont cinq publiées à des dates échelonnées et un
brouillon permettant de vérifier qu'il reste inaccessible depuis le site public, ainsi
que cinq abonnés dont un désabonné.

Les actualités de démonstration portent le préfixe `[DEMO]` dans leur titre et les
adresses utilisent le domaine `exemple.bf` : le retrait ne touche donc jamais aux
données réelles. Elles sont créées avec l'indicateur `abonnes_notifies` déjà positionné,
afin qu'aucun courrier ne parte lors du chargement.

---

## 9. Organisation des fichiers

```
actualites/
├── models.py                  Actualite et AbonneNewsletter
├── forms.py                   Formulaire d'abonnement et formulaire d'actualité
├── views.py                   Vues publiques
├── views_admin.py             Vues du back-office
├── notifications.py           Construction et envoi des courriers
├── urls.py                    Routes publiques
├── urls_admin.py              Routes du back-office
├── management/commands/
│   ├── actualites_demo.py     Jeu de données de démonstration
│   └── notifier_actualites.py Diffusion des notifications en attente
├── migrations/
│   ├── 0001_initial.py
│   ├── 0002_seed_permissions.py
│   ├── 0003_abonnenewsletter_nb_echecs.py
│   └── 0004_actualite_date_fin_publication.py
├── templates/
│   ├── actualites/            Pages publiques et gabarits de courrier
│   └── admin/actualite/       Écrans du back-office
└── docs/
    └── README.md              Le présent document
```

---

## 10. Limites connues

- **Envoi synchrone depuis le bouton.** « Publier et notifier » envoie pendant la
  requête ; au-delà de quelques milliers d'abonnés, elle risque d'expirer. Contournement
  disponible : publier avec une date atteinte sans utiliser le bouton, puis laisser la
  commande `notifier_actualites` faire la diffusion en arrière-plan.
- **Pas de confirmation d'adresse.** L'inscription est immédiate ; une adresse erronée
  ou saisie par un tiers reste inscrite jusqu'à ce que quelqu'un utilise le lien de
  désabonnement. Une confirmation en deux temps serait à ajouter si le volume
  d'inscriptions le justifiait.
- **Retours de courrier non traités.** Les refus détectés sont ceux que le serveur SMTP
  signale au moment de la soumission (authentification, syntaxe, destinataire refusé
  immédiatement). Un serveur qui accepte le message puis renvoie un avis de non-remise
  quelques minutes plus tard n'est pas détecté : il faudrait pour cela dépouiller la
  boîte de retour. Le compteur `nb_echecs` ne couvre donc que la première catégorie.
- **Contenu en texte seul.** Le corps de l'article n'accepte pas de mise en forme riche
  (gras, listes, titres). Les retours à la ligne deviennent des paragraphes et les
  adresses web saisies en clair deviennent des liens cliquables, par le filtre `urlize`.

---

## 11. Annonces défilantes

Bandeau court qui défile en haut du site, indépendant des actualités. Chaque annonce
porte un texte, un **lien facultatif** (où coller l'adresse concernée, sinon vide) et
une **fenêtre d'affichage** (début et expiration).

### 11.1 Modèles

- `Annonce` : `texte`, `lien` (facultatif), `libelle_lien`, `ordre`, `date_debut`,
  `date_fin`, `actif`. `Annonce.actives()` renvoie celles qui sont affichables
  maintenant (actives, commencées, non expirées).
- `AnnonceVue` : mémorise qu'un utilisateur connecté a acquitté une annonce (bouton
  « J'ai vu »). Elle ne lui est alors plus réaffichée, sur aucun de ses appareils.

### 11.2 Affichage

Le context processor `config.context_processors.annonces` fournit `annonces_defilantes`
à tous les gabarits ; le partiel `templates/partials/annonces_defilantes.html` (inclus
dans `base.html`) trace le bandeau. Pour un connecté, les annonces déjà acquittées sont
retirées de la liste. Les visiteurs anonymes voient toutes les annonces actives.

### 11.3 Acquittement (« J'ai vu »)

Le bouton envoie un POST sur `actualites:annonce_vue` (connecté requis), qui crée une
ligne `AnnonceVue` puis retire l'annonce du bandeau. Une expiration (`date_fin`) masque
l'annonce pour tout le monde ; un acquittement la masque pour ce seul utilisateur.

### 11.4 Gestion

Back-office : **Communication → Annonces défilantes** (`/bsb/actualites/annonces`), sous
la permission `gerer_actualites`. Créer, modifier, afficher/masquer, supprimer.

→ **Suivant :** l'assistant en lecture seule et son journal d'audit, dans
[`assistant/README.md`](../../assistant/README.md).
