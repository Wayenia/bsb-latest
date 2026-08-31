"""Variables de gabarit communes.

`navigation` decide quelle navigation le back-office affiche. Le choix est
pilote par le reglage BO_NAVIGATION, lui-meme lu dans .env : basculer d'une
navigation a l'autre ne demande aucune modification de code ni de gabarit,
seulement une recreation du conteneur (voir ./bascule_ui.sh).
"""
from django.conf import settings

# Prefixes ou la sidebar remplace la barre horizontale. Les pages publiques
# (accueil, a propos, actualites) gardent la charte BSB et n'en font pas partie.
PREFIXES_BACK_OFFICE = ('/bsb/',)


def navigation(request):
    utilisateur = getattr(request, 'user', None)
    actif = (
        getattr(settings, 'BO_NAVIGATION', 'sidebar') == 'sidebar'
        and utilisateur is not None
        and utilisateur.is_authenticated
        and request.path.startswith(PREFIXES_BACK_OFFICE)
    )
    return {'bo_sidebar': actif}
