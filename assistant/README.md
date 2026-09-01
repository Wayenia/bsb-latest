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
./bascule_ai.sh activer      # démarre Ollama, télécharge le modèle, ouvre l'assistant
./bascule_ai.sh desactiver   # arrête Ollama et masque l'assistant (plateforme intacte)
./bascule_ai.sh              # affiche l'état courant
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
