#!/bin/sh
# Bascule l'interface du back-office, dans un sens comme dans l'autre.
#
#   ./.bascules/bascule_ui.sh nouveau     interface refondue (navigation laterale + ecrans repris)
#   ./.bascules/bascule_ui.sh classique   retour integral a l'interface d'origine
#   ./.bascules/bascule_ui.sh sidebar     bascule la seule navigation vers la barre laterale
#   ./.bascules/bascule_ui.sh navbar      bascule la seule navigation vers la barre horizontale
#   ./.bascules/bascule_ui.sh             affiche l'etat courant
set -e

# Le script vit dans .bascules/ : la racine du projet est le dossier parent.
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE"
ENV="$RACINE/.env"

[ -f "$ENV" ] || { echo "Erreur : .env introuvable. Lancez ce script depuis la racine du projet."; exit 1; }

lire() {
    valeur=$(sed -n "s/^$1=//p" "$ENV" | head -1)
    [ -n "$valeur" ] && echo "$valeur" || echo "$2 (par defaut)"
}

ecrire() {
    if grep -q "^$1=" "$ENV"; then
        sed -i "s/^$1=.*/$1=$2/" "$ENV"
    else
        printf '\n%s=%s\n' "$1" "$2" >> "$ENV"
    fi
}

if [ $# -eq 0 ]; then
    echo "Navigation : $(lire BO_NAVIGATION sidebar)"
    echo "Ecrans     : $(lire BO_UI nouveau)"
    echo "Usage : ./.bascules/bascule_ui.sh [nouveau|classique|sidebar|navbar]"
    exit 0
fi

case "$1" in
    nouveau)   ecrire BO_NAVIGATION sidebar; ecrire BO_UI nouveau
               echo "Interface refondue : navigation laterale et ecrans repris." ;;
    classique) ecrire BO_NAVIGATION navbar;  ecrire BO_UI classique
               echo "Retour integral a l'interface d'origine." ;;
    sidebar|navbar) ecrire BO_NAVIGATION "$1"
               echo "Navigation basculee vers : $1" ;;
    *) echo "Valeur inconnue : $1 (attendu : nouveau, classique, sidebar ou navbar)"; exit 1 ;;
esac

echo "Recreation du conteneur applicatif (un simple restart ne relit pas le .env)..."
docker compose up -d --force-recreate suudu_backend
echo "Termine."
