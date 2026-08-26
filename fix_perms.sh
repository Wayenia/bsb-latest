#!/bin/sh
# Normalise les droits des deux dossiers montes depuis l'hote (README 9.3).
#   media/    -> uid applicatif : le conteneur y ecrit les fichiers televerses.
#   backups/  -> proprietaire du projet : db_dump.sh y depose ses sauvegardes.
# Docker n'applique pas le chown de l'image a un bind mount : sans cette
# normalisation, les ecritures echouent en PermissionError. Idempotent, et sans
# sudo (le chown passe par un conteneur jetable).
set -e

APP_UID=10001   # doit rester aligne avec le useradd --uid du Dockerfile
RACINE="$(cd "$(dirname "$0")" && pwd)"
HOTE_UID="$(stat -c '%u' "$RACINE")"
HOTE_GID="$(stat -c '%g' "$RACINE")"

normaliser() {
    dossier="$1"; proprietaire="$2"; libelle="$3"
    mkdir -p "$RACINE/$dossier"
    if [ "$(stat -c '%u' "$RACINE/$dossier")" = "${proprietaire%%:*}" ]; then
        echo "Droits de ./$dossier deja corrects ($libelle)."
        return 0
    fi
    echo "Normalisation de ./$dossier vers $libelle..."
    docker run --rm -v "$RACINE/$dossier:/mnt/cible" alpine:3 \
        chown -R "$proprietaire" /mnt/cible
    echo "Droits de ./$dossier normalises."
}

normaliser media   "$APP_UID:$APP_UID"     "uid $APP_UID (conteneur)"
normaliser backups "$HOTE_UID:$HOTE_GID"   "uid $HOTE_UID (hote)"
