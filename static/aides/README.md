# Captures du guide « Aides »

Déposez ici les vraies captures d'écran, par rôle, au chemin attendu par le
guide. Exemple pour le caissier (voir courses/aide_contenu.py) :

    static/aides/caissier/01-accueil.png
    static/aides/caissier/02-bouton-connexion.png
    ...

Formats : PNG ou JPG. Une fois le fichier déposé, lancez `npm run build` n'est
pas nécessaire, mais exécutez `collectstatic` (fait par redeploy.sh) pour qu'il
soit servi. Tant qu'une capture est absente, l'étape affiche « Capture à venir ».
