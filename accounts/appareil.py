"""Appareils reconnus et avis de connexion.

Deux mecanismes qui se completent, pensés pour des agents non techniques.

**Appareil reconnu.** Apres une verification de code reussie, le navigateur
recoit un jeton signe. Sur ce poste, la connexion suivante ne demande plus que
le mot de passe ; sur tout autre appareil, le code reste exige. L'agent qui
travaille depuis son poste habituel subit donc *moins* de friction qu'avant,
tandis qu'une connexion depuis un appareil inconnu reste barree par le code.

**Avis de connexion.** Toute connexion depuis un appareil non reconnu declenche
un courriel court au titulaire. Il n'a rien a faire : s'il reconnait sa propre
connexion, il ignore le message ; sinon, il sait immediatement qu'on utilise
son compte. C'est la seule alerte qui parvienne a la personne concernee sans
passer par un rapport periodique.

Le jeton est signe avec le hachage du mot de passe : **changer de mot de passe
revoque tous les appareils**, sans ecran ni procedure a expliquer.
"""
from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

COOKIE = 'appareil_connu'
DUREE_JOURS = 30
SEL = 'accounts.appareil'


def _valeur(utilisateur):
    """Contenu signe. Le hachage du mot de passe y entre, si bien qu'une
    reinitialisation invalide d'un coup tous les appareils enregistres."""
    return {'u': utilisateur.pk, 'e': utilisateur.password[-16:]}


def est_reconnu(request, utilisateur):
    jeton = request.COOKIES.get(COOKIE)
    if not jeton:
        return False
    try:
        donnees = signing.loads(jeton, salt=SEL, max_age=DUREE_JOURS * 86400)
    except signing.BadSignature:
        return False
    return donnees.get('u') == utilisateur.pk and donnees.get('e') == utilisateur.password[-16:]


def marquer_reconnu(reponse, utilisateur):
    reponse.set_cookie(
        COOKIE,
        signing.dumps(_valeur(utilisateur), salt=SEL),
        max_age=DUREE_JOURS * 86400,
        httponly=True,
        secure=getattr(settings, 'SESSION_COOKIE_SECURE', False),
        samesite='Lax',
    )
    return reponse


def oublier(reponse):
    reponse.delete_cookie(COOKIE)
    return reponse


def avertir(utilisateur, request):
    """Avis de connexion depuis un appareil non reconnu.

    L'echec d'envoi ne doit jamais empecher la connexion : l'agent serait
    bloque par une panne de messagerie sans comprendre pourquoi.
    """
    if not utilisateur.email:
        return False
    from . import ratelimit
    contexte = {
        'utilisateur': utilisateur,
        'date': timezone.localtime(timezone.now()),
        'adresse': ratelimit.adresse_client(request) or 'inconnue',
        'navigateur': (request.META.get('HTTP_USER_AGENT') or '')[:120],
    }
    try:
        message = EmailMultiAlternatives(
            subject="Connexion à votre compte Yupaan",
            body=render_to_string('accounts/avis_connexion.txt', contexte),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[utilisateur.email],
        )
        message.attach_alternative(
            render_to_string('accounts/avis_connexion.html', contexte), 'text/html')
        message.send(fail_silently=True)
        return True
    except Exception:
        return False
