# Environnement de test (staging)

Le staging est une copie isolée de la plateforme, réservée aux tests des agents.
Il tourne en même temps que la production, sur le même code, mais avec sa propre
base de données. La production n'est jamais touchée par le staging.

## Ce qui est séparé

| Élément | Production | Staging |
|---|---|---|
| Adresse | port 80 | port 8081 |
| Base de données | volume prod | volume staging (séparé) |
| Réseau, conteneurs | projet prod | projet staging (séparé) |
| Fichiers téléversés | `./media` | `./media_staging` |
| Sauvegardes | `./backups` | `./backups_staging` |
| E-mail | SMTP réel | mode console (aucun e-mail réel envoyé) |
| Bandeau à l'écran | aucun | « STAGING — Environnement de test » |

Le fichier `.env.staging` (généré automatiquement, non versionné) contient les
réglages du staging. La production garde son `.env` habituel.

## Commandes

Toujours depuis la racine du projet.

```bash
./.bascules/staging.sh up        # démarre le staging (port 8081)
./.bascules/staging.sh refresh   # remplace la base staging par une copie de la prod
./.bascules/staging.sh seed      # base staging neuve avec les données de référence
./.bascules/staging.sh down      # arrête le staging (les données sont conservées)
./.bascules/staging.sh           # affiche l'état
```

Après `up`, ouvrir : http://localhost:8081

## Utilisation pendant les tests

1. Démarrer le staging : `./.bascules/staging.sh up`.
2. Charger des données réalistes : `./.bascules/staging.sh refresh` (copie la prod).
   La commande demande une confirmation avant d'écraser la base staging.
3. Les agents testent sur le port 8081. Les vrais utilisateurs restent sur le
   port 80 (production).

Le bandeau « STAGING » est visible en bas de chaque page du staging : impossible
de le confondre avec la production.

## Passage en production après les tests

Le staging et la production étant deux environnements distincts, il n'y a pas de
« bascule » technique : la production tourne déjà et n'a jamais été modifiée par
les tests.

Avant l'ouverture aux vrais apprenants et formateurs, faire une seule chose :
repartir d'une base de production propre, pour que les données de test des agents
ne se retrouvent pas en production.

- Si les agents ont testé directement en production auparavant, vider les données
  de test puis recharger les seules données de référence (centres, filières,
  frais). La remise à zéro d'une base est une action manuelle et volontaire
  (voir README principal, section « Réinitialisation de la base de données »).
- Si les agents ont testé uniquement sur le staging, la production est déjà propre :
  il n'y a rien à faire.

Le déploiement de la production se fait comme d'habitude : `git push` puis
`./redeploy.sh` sur le serveur. Le staging n'intervient pas dans ce processus.

## Suspendre le staging

Arrêt simple, les données sont conservées et peuvent être relancées plus tard :

```bash
./.bascules/staging.sh down
```

## Supprimer le staging complètement

Supprime les conteneurs, la base de données, les fichiers et les réglages du
staging. La production n'est pas concernée.

```bash
./.bascules/staging.sh down
docker volume rm suudu_staging_suudu_postgres_data_18 suudu_staging_suudu_staticfiles \
  suudu_staging_suudu_redis_data suudu_staging_suudu_security_logs \
  suudu_staging_suudu_pgadmin_data suudu_staging_suudu_ollama_data
rm -rf media_staging backups_staging .env.staging
```

Après cela, il ne reste aucune trace du staging. La commande `./.bascules/staging.sh up`
peut le recréer à neuf à tout moment.

## Point important

Le staging n'affecte jamais la production : bases, réseaux, volumes et ports sont
séparés. Vérifié : la production reste accessible et intacte pendant que le
staging tourne, et l'inverse est vrai aussi.
