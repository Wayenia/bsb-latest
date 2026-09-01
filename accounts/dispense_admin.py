"""Dispense d'OTP de l'espace d'administration technique.

Apres une verification reussie sur la page dediee, l'admin recoit un cookie
signe qui evite de redemander le code a chaque connexion, pour une duree qu'il
regle lui-meme : 5 h par defaut, 24 h au maximum, et pour la seule journee en
cours. La dispense ne franchit jamais minuit et le reglage revient a 5 h chaque
jour (README 9.2).

Le jeton est signe avec le hachage du mot de passe : changer de mot de passe
revoque la dispense, comme pour les appareils reconnus.
"""
from django.core import signing
from django.utils import timezone

COOKIE = 'admin_dispense'
SEL = 'accounts.dispense_admin'
DEFAUT_MINUTES = 300      # 5 heures
MAX_MINUTES = 1440        # 24 heures


def minutes_reglees(utilisateur):
    """Duree choisie si elle date d'aujourd'hui, sinon le defaut (remise a 5 h
    chaque jour, sans tache planifiee : la lecture d'un nouveau jour suffit)."""
    jour = getattr(utilisateur, 'admin_otp_grace_jour', None)
    if jour and jour == timezone.localdate():
        valeur = getattr(utilisateur, 'admin_otp_grace_minutes', DEFAUT_MINUTES)
        return max(1, min(int(valeur), MAX_MINUTES))
    return DEFAUT_MINUTES


def _secondes_jusqu_a_expiration(utilisateur, maintenant=None):
    """Duree de dispense en secondes, bornee au prochain minuit."""
    maintenant = maintenant or timezone.now()
    local = timezone.localtime(maintenant)
    minuit = (local + timezone.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0)
    fin_fenetre = local + timezone.timedelta(minutes=minutes_reglees(utilisateur))
    fin = min(fin_fenetre, minuit)
    return max(0, int((fin - local).total_seconds()))


def _valeur(utilisateur):
    return {'u': utilisateur.pk, 'e': utilisateur.password[-16:]}


def est_dispense(request, utilisateur):
    jeton = request.COOKIES.get(COOKIE)
    if not jeton:
        return False
    try:
        donnees = signing.loads(jeton, salt=SEL, max_age=MAX_MINUTES * 60)
    except signing.BadSignature:
        return False
    return (donnees.get('u') == utilisateur.pk
            and donnees.get('e') == utilisateur.password[-16:])


def poser(reponse, request, utilisateur):
    from django.conf import settings
    duree = _secondes_jusqu_a_expiration(utilisateur)
    if duree <= 0:
        return reponse
    reponse.set_cookie(
        COOKIE,
        signing.dumps(_valeur(utilisateur), salt=SEL),
        max_age=duree,
        httponly=True,
        secure=getattr(settings, 'SESSION_COOKIE_SECURE', False),
        samesite='Lax',
    )
    return reponse


def oublier(reponse):
    reponse.delete_cookie(COOKIE)
    return reponse
