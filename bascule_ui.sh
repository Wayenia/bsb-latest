#!/bin/sh
# Bascule la navigation du back-office, dans un sens comme dans l'autre.
#
#   ./bascule_ui.sh sidebar   nouvelle navigation laterale groupee par theme
#   ./bascule_ui.sh navbar    retour a la barre horizontale d'origine
#   ./bascule_ui.sh           affiche l'etat courant
#
# Fonctionne a l'identique en developpement et en production : le reglage vit
# dans .env, aucun gabarit ne code en dur l'une ou l'autre navigation. Aucune
# donnee n'est touchee, aucune migration n'est jouee : la bascule est sans
# risque et se refait autant de fois que voulu.
set -e

RACINE="$(cd "$(dirname "$0")" && pwd)"
ENV="$RACINE/.env"

if [ ! -f "$ENV" ]; then
    echo "Erreur : .env introuvable. Lancez ce script depuis la racine du projet."
    exit 1
fi

courant() {
    valeur=$(sed -n 's/^BO_NAVIGATION=//p' "$ENV" | head -1)
    [ -n "$valeur" ] && echo "$valeur" || echo "sidebar (valeur par defaut, absente du .env)"
}

if [ $# -eq 0 ]; then
    echo "Navigation courante : $(courant)"
    echo "Usage : ./bascule_ui.sh [sidebar|navbar]"
    exit 0
fi

case "$1" in
    sidebar|navbar) CIBLE="$1" ;;
    *) echo "Valeur inconnue : $1 (attendu : sidebar ou navbar)"; exit 1 ;;
esac

if grep -q '^BO_NAVIGATION=' "$ENV"; then
    sed -i "s/^BO_NAVIGATION=.*/BO_NAVIGATION=$CIBLE/" "$ENV"
else
    printf '\n# Navigation du back-office : sidebar | navbar\nBO_NAVIGATION=%s\n' "$CIBLE" >> "$ENV"
fi

echo "Navigation basculee vers : $CIBLE"
echo "Recreation du conteneur applicatif (un simple restart ne relit pas le .env)..."
docker compose up -d --force-recreate suudu_backend
echo "Termine. Verifiez sur /bsb/dashboard."
