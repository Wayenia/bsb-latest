# Yupaan-IA — assistant local (application `assistant`)

**Yupaan-IA** est un assistant qui **lit** les données de Yupaan et **explique / analyse**, pour
aider l'administration. Il tourne **en local** (aucune donnée n'est envoyée sur
Internet) grâce à **Ollama** + un modèle **DeepSeek/Qwen**.

## Règle d'or : lecture seule

Yupaan-IA **ne modifie jamais la base de données** — jamais de création, de
modification ni de suppression, pour personne (y compris l'administrateur).
Trois protections :

1. Il n'a **aucun accès direct** à la base : il reçoit un résumé déjà calculé.
2. Il ne dispose **d'aucun outil d'action** (pas de fonction qui écrit).
3. Les données qu'il voit respectent le **périmètre** de l'utilisateur connecté.

## Activer / désactiver (réversible à tout moment)

```bash
./.bascules/bascule_ai.sh activer      # démarre Ollama, télécharge le modèle, ouvre l'assistant
./.bascules/bascule_ai.sh desactiver   # arrête Ollama et masque l'assistant (plateforme intacte)
./.bascules/bascule_ai.sh              # affiche l'état courant
```

Désactivé (**valeur par défaut**), l'écran de Yupaan-IA disparaît et le conteneur Ollama ne
tourne pas : **aucun impact** sur le reste de la plateforme.

## Modèles (un seul actif à la fois)

- **Développement** : petit modèle de test — `qwen2:0.5b` (~0,35 Go).
- **Production** : modèle avancé et stable — `qwen2.5:1.5b` (~1 Go) ou
  `deepseek-r1:1.5b` (~1,1 Go).

Le modèle se choisit dans `.env` (`AI_MODEL=...`) ou depuis l'écran
**Assistant → Modèles** en back-office. Changer de modèle le télécharge en
arrière-plan si besoin, **sans arrêter la plateforme** ; si Ollama est absent,
Yupaan-IA affiche « indisponible » et le reste fonctionne normalement.

## Qui y a accès

- **Administrateur** : accès complet par défaut.
- **Délégation** : écran **Assistant → Accès délégués**. L'admin accorde l'accès
  à un agent et coche les **domaines** qu'il pourra consulter (scolarité,
  finances, facturation, RH). L'agent ne voit que ces domaines, dans son propre
  périmètre.

## Journal d'audit des échanges

Chaque question posée et la réponse de Yupaan-IA sont enregistrées (qui, quand,
question, réponse, domaines interrogés, refusé oui/non) dans la table
`EchangeAssistant`. C'est la **plateforme** qui écrit ce journal, pas l'IA : l'IA
reste en lecture seule et ne touche jamais aux données métier. Les échanges de
plus de **90 jours** sont supprimés automatiquement.

Consultation : écran **Assistant → Journal**, réservé à la permission
`gerer_assistant_ia` (admin et gestionnaires délégués).

Le fil de discussion à l'écran est mémorisé **dans le navigateur** de chaque
utilisateur (`localStorage`) : il reste affiché après un rechargement ou un
retour sur la page. Ce n'est qu'un confort local, propre à l'appareil, jamais
partagé ni envoyé au serveur. Trois boutons le gèrent : **Nouveau** (repartir à
zéro), **Nettoyer** (vider), **Copier** (copier tout le fil). Le journal
serveur, lui, reste la trace d'audit officielle.

## Réglages `.env`

| Variable | Rôle | Défaut |
|---|---|---|
| `AI_MODULE` | `on` / `off` — active l'assistant | `off` |
| `AI_MODEL` | modèle Ollama actif | `qwen2:0.5b` |
| `AI_OLLAMA_URL` | adresse interne d'Ollama | `http://suudu_ollama:11434` |

## En bref (scalabilité)

Tout est isolé dans l'app `assistant` (Yupaan-IA) et le service `suudu_ollama` (profil Docker
`ai`). Pour ajouter un domaine consultable : compléter `DOMAINES` et
`contexte_lecture_seule` dans `assistant/`. Pour un autre modèle : le choisir
dans l'écran Modèles. Rien d'autre dans la plateforme n'est touché.
