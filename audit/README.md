# Application `audit`

Analyse des traces d'activite de la plateforme et diffusion de rapports
d'inspection. Cette application **ne produit aucune trace** : elle consomme
celles qu'ecrivent les autres applications.

- `accounts.signals` ecrit les evenements d'authentification dans
  `accounts.HistoriqueConnexion` (connexion, deconnexion, echec).
- `audit` les lit, en tire des indicateurs et des alertes, produit un classeur
  Excel avec graphiques, et l'envoie par courrier electronique.

Ce decoupage la rend supprimable sans consequence : retirer `audit`
d'`INSTALLED_APPS` desactive les rapports, la journalisation continue.

## Contenu

| Fichier | Role |
|---|---|
| `services.py` | Agregation et detection d'anomalies |
| `classeur.py` | Construction du classeur Excel et de ses graphiques |
| `management/commands/envoyer_rapport_audit.py` | Commande de diffusion |

## Usage

```bash
# Rapport des 7 derniers jours, envoye aux destinataires du .env
docker compose exec suudu_backend python manage.py envoyer_rapport_audit

# Periode et destinataires explicites
docker compose exec suudu_backend python manage.py envoyer_rapport_audit \
    --jours 30 --a inspection@example.org

# Produire le fichier sans envoyer de courriel (mise au point)
docker compose exec suudu_backend python manage.py envoyer_rapport_audit \
    --fichier /tmp/audit.xlsx --sans-envoi

# Mode planifie : n'envoie que si une echeance du reglage d'ecran est atteinte
docker compose exec suudu_backend python manage.py envoyer_rapport_audit --auto
```

## Parametres (`.env`)

| Variable | Defaut | Role |
|---|---|---|
| `AUDIT_DESTINATAIRES` | vide | Adresses separees par des virgules. S'ajoutent a celles saisies dans l'ecran « Envoi du rapport » (`/bsb/historique-connexions/destinataires`). |
| `AUDIT_PERIODE_JOURS` | 7 | Profondeur de la periode analysee |
| `AUDIT_SEUIL_ECHECS_COMPTE` | 5 | Echecs sur un meme compte avant alerte |
| `AUDIT_SEUIL_COMPTES_PAR_IP` | 3 | Comptes distincts vises depuis une IP avant alerte |
| `AUDIT_SEUIL_IP_PAR_COMPTE` | 3 | Adresses distinctes pour un compte avant alerte |
| `AUDIT_HEURE_OUVREE_DEBUT` | 7 | Debut des heures ouvrees (UTC, cf. TIME_ZONE) |
| `AUDIT_HEURE_OUVREE_FIN` | 19 | Fin des heures ouvrees |
| `AUDIT_SCAN_INTERVAL` | 3600 | Intervalle (s) entre deux verifications du planificateur `suudu_audit` |

Les destinataires se gerent aussi depuis l'ecran **Envoi du rapport**, accessible
depuis l'historique des connexions : ajout a l'unite, import d'un fichier Excel
dont le modele est pre-rempli des adresses deja enregistrees, et suspension sans
suppression — on garde trace de qui recevait le rapport. Les deux sources se
cumulent ; `--a` les remplace, pour un envoi ponctuel cible.

## Envoi automatique planifie

L'ecran **Reglage d'envoi** (`/bsb/historique-connexions/destinataires`) permet de
programmer une diffusion **quotidienne, hebdomadaire ou mensuelle** (jour et heure
choisis au clic), en plus de l'envoi immediat « Envoyer maintenant ». Le service
`suudu_audit` de `docker-compose.yml` execute `envoyer_rapport_audit --auto` toutes les
`AUDIT_SCAN_INTERVAL` secondes ; la commande lit le reglage, n'envoie qu'a echeance et
jamais deux fois la meme (la date de derniere diffusion est conservee en base). Aucune
tache `cron` sur l'hote n'est donc necessaire, et la fenetre du rapport suit la
frequence choisie (1, 7 ou 31 jours).

Sans aucun destinataire ni `--a`, la commande s'arrete sans rien envoyer.
Rappel : tant que `EMAIL_HOST` est vide, Django ecrit les courriels dans les
journaux du conteneur (voir README principal, section 9.4).
