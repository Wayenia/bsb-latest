# Reste a faire — a arbitrer

Liste etablie a partir d'un releve du depot, pas de memoire. Chaque volume est
verifiable : compte des gabarits employant le systeme `bo-`, compte des `<th>`
par tableau, et etat de Git.

Indiquez les numeros a traiter en priorite.

---

## A. Reprise des ecrans — responsive et charte

Etat : **11 gabarits repris sur 111**. Les 100 autres gardent l'ancien style et
ne sont pas responsives.

| N° | Tache | Volume | Pourquoi |
|---|---|---|---|
| **1** | `member_dashboard` (`/membre/dashboard`) | 1 ecran | Ecran d'atterrissage de **50 comptes sur 53** : 29 gestionnaires, 15 membres, 3 directeurs, caissier, DEPS, agent comptable. Le tableau de bord deja refait n'en sert que 3. Le plus rentable de la liste. |
| **2** | Pages de **8 colonnes et plus** | 7 pages | Au telephone, huit a onze colonnes imposent un defilement horizontal qui rend la lecture impraticable. Detail dans `docs_pages_responsives.md`. |
| **3** | Pages de **6 a 7 colonnes** | 14 pages | Meme probleme, moins aigu. |
| **4** | Pages de **4 a 5 colonnes** | 16 pages | Passables en l'etat, a traiter pour l'homogeneite. |
| **5** | Import des statistiques reelles (`upload_form`, `upload_result`) | 2 ecrans | La liste a ete refaite, pas le parcours d'import qui la prolonge. |
| **6** | Ecrans sans tableau (formulaires, detail, confirmation) | 59 gabarits | Homogeneite de la charte et du responsive. |
| **7** | Espace apprenant | 17 gabarits, dont 1 tableau large | **Point a trancher** : vous avez justifie l'exigence mobile par les apprenants, puis demande l'inventaire « sauf etudiant d'abord ». C'est donc le seul espace que je n'ai pas examine. |

## B. Decisions qui vous appartiennent

| N° | Sujet | Etat |
|---|---|---|
| **8** | `CLAUDE.md` exclu par `.gitignore` | Mes 293 lignes de corrections — dont celles retablissant des affirmations devenues fausses — ne partiront pas au push. Une ligne a retirer du `.gitignore`. |
| **9** | Mots de passe de `populate_data.py` | 52 comptes avec mots de passe en dur dans un fichier versionne, affiches lors du peuplement (`admin / Admin@2024`). Seule leur rotation leve le risque. |
| **10** | `rapport_audit_demo.xlsx` | **Réglé** : artefact de démonstration retiré du dépôt. Le classeur reste généré à la demande par l'app audit. |
| **11** | Pousser les commits | 23 commits d'avance sur `origin/main`, rien n'est pousse. |

## C. Sujet ouvert, jamais repris

| N° | Sujet | Etat |
|---|---|---|
| **12** | Connexion des agents par la page publique | **En grande partie reglee.** Le personnel franchit une verification en deux etapes (code par courriel), avec appareils reconnus 30 jours et avis de connexion (commits 29d5a37, a6550e6 ; README 9.2). Reste ouvert : la page de connexion demeure commune au public et aux agents, et `accounts/appareil.oublier()` n'est branche sur aucun bouton (pas d'ecran « oublier cet appareil »). |

---

## Recommandation

**1**, puis **2**. Le premier touche 50 comptes sur 53 pour un seul ecran ; le
second leve le blocage reel au telephone. **8** et **9** ne coutent presque rien
et ont des consequences durables.
