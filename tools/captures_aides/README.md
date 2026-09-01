# Captures d'ecran du guide « Aides »

Produit de vraies captures des pages reelles, par navigateur sans interface,
sans passer par l'OTP (on injecte une session pre-authentifiee).

## Prerequis
- Chrome/Chromium sur l'hote (`/usr/bin/google-chrome`).
- `npm i puppeteer-core` (utilise le Chrome de l'hote, aucun telechargement).
- L'application accessible sur `http://localhost`.

## Etapes
1. Generer les cookies de session (caissier + page OTP) et les identifiants de
   donnees (dette, eleve) via `manage.py shell` — voir sessions.json d'exemple :
   `{ "caissier": "<sessionid>", "otp": "<sessionid>", "eleve_id": N, "dette_id": N, "inscription_id": N }`.
2. Lancer : `NODE_PATH=./node_modules node tools/captures_aides/capture.js sessions.json static/aides/caissier`
3. `collectstatic` pour servir les images.

Le plan (pages, cookie, action) est en tete de `capture.js`. Aucune capture
n'est inventee : ce sont les pages reellement rendues.
