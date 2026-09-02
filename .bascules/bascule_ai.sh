#!/bin/sh
# Active ou desactive l'assistant IA local (Ollama), en lecture seule.
#
#   ./.bascules/bascule_ai.sh activer      demarre Ollama, telecharge le modele, ouvre l'assistant
#   ./.bascules/bascule_ai.sh desactiver   arrete Ollama et ferme l'assistant (plateforme intacte)
#   ./.bascules/bascule_ai.sh              affiche l'etat courant
set -e

# Le script vit dans .bascules/ : la racine du projet est le dossier parent.
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE"
ENV="$RACINE/.env"

[ -f "$ENV" ] || { echo "Erreur : .env introuvable. Lancez ce script depuis la racine du projet."; exit 1; }

lire() {
    valeur=$(sed -n "s/^$1=//p" "$ENV" | head -1)
    [ -n "$valeur" ] && echo "$valeur" || echo "$2"
}
ecrire() {
    if grep -q "^$1=" "$ENV"; then
        sed -i "s#^$1=.*#$1=$2#" "$ENV"
    else
        printf '\n%s=%s\n' "$1" "$2" >> "$ENV"
    fi
}

MODELE=$(lire AI_MODEL "qwen2:0.5b")

if [ $# -eq 0 ]; then
    echo "Assistant IA : $(lire AI_MODULE off)"
    echo "Modele       : $MODELE"
    echo "Usage : ./.bascules/bascule_ai.sh [activer|desactiver]"
    exit 0
fi

case "$1" in
    activer)
        ecrire AI_MODULE on
        ecrire COMPOSE_PROFILES ai
        echo "Demarrage d'Ollama..."
        docker compose --profile ai up -d suudu_ollama
        echo "Attente du service (10s)..."
        sleep 10
        echo "Telechargement du modele : $MODELE (peut prendre quelques minutes)..."
        docker exec suudu_ollama ollama pull "$MODELE" || echo "Avertissement : le telechargement a echoue, reessayez depuis l'ecran Modeles."
        docker compose up -d --force-recreate suudu_backend
        echo "Assistant IA active."
        ;;
    desactiver)
        ecrire AI_MODULE off
        ecrire COMPOSE_PROFILES ""
        docker compose stop suudu_ollama 2>/dev/null || true
        docker compose rm -f suudu_ollama 2>/dev/null || true
        docker compose up -d --force-recreate suudu_backend
        echo "Assistant IA desactive (la plateforme continue normalement)."
        ;;
    *)
        echo "Valeur inconnue : $1 (attendu : activer ou desactiver)"; exit 1 ;;
esac
