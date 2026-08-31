import ipaddress

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from . import ratelimit
from .models import HistoriqueConnexion, Utilisateur


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


# Routes de connexion, seules sur lesquelles request.POST peut etre lu sans
# risque : elles ne recoivent jamais de fichier. Doit rester aligne avec
# CHEMINS_CONNEXION de config/middleware.py (duplique pour eviter un import
# circulaire, le middleware important deja accounts.ratelimit).
CHEMINS_CONNEXION = ('/accounts/login',)


def _identifiant_saisi(request):
    """Identifiant reellement saisi, quand `authenticate()` a ete appele a vide.

    La vue de connexion appelle `authenticate(username='', ...)` lorsque
    l'identifiant ne correspond a aucun compte, afin que la reponse mette le
    meme temps qu'un mot de passe faux — sans quoi on enumererait les comptes
    au chronometre. Le signal ne transporte donc pas l'identifiant essaye, et
    le journal perdrait la trace des comptes sondes : c'est precisement ce
    qu'une enumeration cherche a faire passer inapercu.

    La lecture est restreinte aux routes de connexion : ailleurs, toucher a
    request.POST consommerait le flux d'un envoi multipart avant les
    gestionnaires d'upload de Django.
    """
    if request.method != 'POST':
        return ''
    if not request.path.startswith(CHEMINS_CONNEXION):
        return ''
    return request.POST.get('identifiant', '').strip()


def _enregistrer_echec(username, request):
    """Journalise une tentative de connexion refusee.

    Le compte vise est rattache s'il existe : c'est ce qui permet de distinguer
    un sondage de comptes inexistants d'une attaque ciblee sur un compte reel.
    Le nom d'utilisateur est tronque a la largeur du champ — une saisie erronee
    peut y deposer n'importe quoi, y compris un mot de passe."""
    username = (username or '')[:150]
    compte = Utilisateur.objects.filter(username=username).first() if username else None
    HistoriqueConnexion.objects.create(
        utilisateur=compte,
        username=username,
        nom_complet=f"{compte.nom} {compte.prenom}".strip() if compte else '',
        est_apprenant=(compte.user_type == 'eleve') if compte else False,
        type_evenement='echec',
        centre=_centre_utilisateur(compte) if compte else None,
        adresse_ip=_adresse_ip(request),
    )


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request=None, **kwargs):
    """Comptabilise l'echec pour la limitation anti-force brute et le journalise.

    `user_login_failed` est emis par `authenticate()` : brancher le compteur
    ici couvre d'un seul geste la page de connexion applicative et l'API DRF,
    sans decorer chaque vue.

    Le compteur anti-force brute vit dans Redis et expire en 15 minutes : il
    arrete une attaque en cours mais n'en garde aucune trace exploitable. La
    ligne d'historique, elle, permet l'inspection a posteriori."""
    if request is None:
        return
    username = (credentials or {}).get('username', '')
    ratelimit.enregistrer_echec(request, username)
    _enregistrer_echec(username or _identifiant_saisi(request), request)
