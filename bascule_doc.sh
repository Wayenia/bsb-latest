#!/bin/sh
# Bascule le modele des documents PDF generes (quittances, recus...).
#
#   ./bascule_doc.sh officiel    mise en page officielle (facon quittance administrative)
#   ./bascule_doc.sh classique   ancien rendu
#   ./bascule_doc.sh             affiche l'etat courant
set -e

RACINE="$(cd "$(dirname "$0")" && pwd)"
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
    echo "Documents : $(lire DOC_MODELE officiel)"
    echo "Usage : ./bascule_doc.sh [officiel|classique]"
    exit 0
fi

case "$1" in
    officiel)  ecrire DOC_MODELE officiel;  echo "Documents : mise en page officielle." ;;
    classique) ecrire DOC_MODELE classique; echo "Documents : ancien rendu." ;;
    *) echo "Valeur inconnue : $1 (attendu : officiel ou classique)"; exit 1 ;;
esac

echo "Recreation du conteneur applicatif (un simple restart ne relit pas le .env)..."
docker compose up -d --force-recreate suudu_backend
echo "Termine."
