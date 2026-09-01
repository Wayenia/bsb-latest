"""Variables de gabarit communes.

`navigation` decide quelle navigation s'affiche. Le choix depend de deux
conditions : le reglage BO_NAVIGATION, et le fait que l'on soit sur un ecran de
travail d'agent. Les pages publiques et l'espace des apprenants gardent la
barre horizontale et la charte publique.
"""
from django.conf import settings

from .navigation import construire_menu

# Ecrans de travail des agents. Le back-office ne tient pas dans le seul
# prefixe /bsb/ : les statistiques, les encaissements de scolarite, les centres
# et tout le module de facturation sont montes ailleurs dans le routage.
PREFIXES_ESPACE_AGENT = (
    '/bsb/',
    '/aide',
    '/centres/',
    '/statistiques/',
    '/statistiques-reelles/',
    '/membre/',
    '/accounts/facturation/',
    '/accounts/encaissement',
    '/accounts/daf/',
    '/accounts/mon-compte',
    '/accounts/mon-profil',
    '/accounts/changer-mot-de-passe',
)


def _est_agent(utilisateur):
    """Un apprenant n'est pas un agent, meme sur une page partagee.

    `/accounts/mon-compte` sert aux deux : sans ce test, un apprenant y verrait
    la navigation d'administration.
    """
    if not utilisateur or not utilisateur.is_authenticated:
        return False
    if utilisateur.is_staff or utilisateur.is_superuser:
        return True
    return getattr(utilisateur, 'user_type', 'eleve') != 'eleve'


def navigation(request):
    utilisateur = getattr(request, 'user', None)
    actif = (
        getattr(settings, 'BO_NAVIGATION', 'sidebar') == 'sidebar'
        and _est_agent(utilisateur)
        and request.path.startswith(PREFIXES_ESPACE_AGENT)
    )
    if not actif:
        return {'bo_sidebar': False}
    return {
        'bo_sidebar': True,
        'bo_menu': construire_menu(utilisateur, request.path),
    }
