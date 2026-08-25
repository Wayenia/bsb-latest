import ipaddress

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from . import ratelimit
from .models import HistoriqueConnexion


def _adresse_ip(request):
    """Adresse IP du client, en tenant compte du proxy nginx devant Django.
    Validee avant assignation : X-Forwarded-For vient d'un en-tete HTTP,
    donc potentiellement mal forme ou usurpe cote client.

    La lecture de l'en-tete est deleguee a `ratelimit.adresse_client`, qui
    prend l'avant-derniere entree de la chaine et non la premiere : la
    premiere est fournie par le client et peut donc etre falsifiee, ce qui
    permettrait d'empoisonner ce journal d'audit."""
    if not request:
        return None
    brute = ratelimit.adresse_client(request)
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
    # Une connexion reussie solde les echecs precedents : un utilisateur qui
    # retrouve son mot de passe ne reste pas verrouille pour autant.
    ratelimit.reinitialiser(request, user.get_username())


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if user is None:
        return
    _enregistrer(user, request, 'deconnexion')


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request=None, **kwargs):
    """Comptabilise l'echec pour la limitation anti-force brute.

    `user_login_failed` est emis par `authenticate()` : brancher le compteur
    ici couvre d'un seul geste la page de connexion applicative, l'admin
    Django et l'API DRF, sans decorer chaque vue."""
    if request is None:
        return
    ratelimit.enregistrer_echec(request, (credentials or {}).get('username', ''))
