import ipaddress

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import HistoriqueConnexion


def _adresse_ip(request):
    """Adresse IP du client, en tenant compte du proxy nginx devant Django.
    Validee avant assignation : X-Forwarded-For vient d'un en-tete HTTP,
    donc potentiellement mal forme ou usurpe cote client."""
    if not request:
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    brute = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
    if not brute:
        return None
    try:
        ipaddress.ip_address(brute)
    except ValueError:
        return None
    return brute


def _centre_utilisateur(user):
    """Centre associe a l'utilisateur au moment de la connexion, si son role
    en a un (formateur, membre de l'administration d'un centre)."""
    formateur = getattr(user, 'formateur', None)
    if formateur and formateur.centre_id:
        return formateur.centre
    membre = getattr(user, 'membreadministration', None)
    if membre and membre.structure_id:
        return membre.structure
    return None


def _enregistrer(user, request, type_evenement):
    HistoriqueConnexion.objects.create(
        utilisateur=user,
        username=user.get_username(),
        nom_complet=f"{user.nom} {user.prenom}".strip(),
        est_apprenant=(user.user_type == 'eleve'),
        type_evenement=type_evenement,
        centre=_centre_utilisateur(user),
        adresse_ip=_adresse_ip(request),
    )


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    _enregistrer(user, request, 'connexion')


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if user is None:
        return
    _enregistrer(user, request, 'deconnexion')
