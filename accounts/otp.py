"""Vérification en deux étapes par code à usage unique (OTP) pour la connexion
du personnel — tous les rôles sauf l'apprenant (« eleve »).

Le code (4 chiffres, valable 2 minutes) n'est jamais stocké en clair ni en
base : seul son haché est conservé dans la session anonyme du visiteur, le
temps de la vérification. La session porte aussi l'identifiant du compte en
attente de validation, le nombre de tentatives de saisie et l'horodatage du
dernier envoi (anti-spam du bouton « Renvoyer »).
"""

import secrets
from email.utils import make_msgid, parseaddr

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.html import escape

CLE_SESSION = 'otp_connexion'

DUREE_VALIDITE = 120   # secondes — 2 minutes
MAX_TENTATIVES = 5     # essais de saisie avant invalidation du code
DELAI_RENVOI = 60      # secondes minimum entre deux envois
MAX_ENVOIS = 4         # nombre total d'envois pour une même session


def _generer_code():
    return f"{secrets.randbelow(10000):04d}"


def _envoyer_email(user, code):
    """E-mail transactionnel du code de connexion.

    Plusieurs réglages visent à ne pas finir en indésirables : en-têtes
    transactionnels standard (``Auto-Submitted``, ``X-Auto-Response-Suppress``,
    ``Precedence: transactional``), ``Message-ID`` sur le domaine de l'adresse
    expéditrice (aligné avec la signature DKIM du serveur SMTP), ``Reply-To``
    réel, et un corps en texte + HTML soigné plutôt qu'une seule ligne avec un
    nombre (signal classique de pourriel)."""
    minutes = DUREE_VALIDITE // 60
    nom = f"{user.prenom} {user.nom}".strip() or user.get_username()

    sujet = f"Code de connexion Yupaan : {code}"

    texte = (
        f"Bonjour {nom},\n\n"
        f"Voici votre code de connexion a la plateforme Yupaan (Burkina Suudu Bawde) :\n\n"
        f"    {code}\n\n"
        f"Ce code est valable {minutes} minutes et ne sert qu'une fois.\n"
        "Ne le communiquez a personne : aucun agent de la plateforme ne vous le demandera.\n\n"
        "Si vous n'etes pas a l'origine de cette connexion, ignorez ce message "
        "puis changez votre mot de passe.\n\n"
        "-- \n"
        "Plateforme Yupaan\n"
        "Burkina Suudu Bawde -- la maison des competences\n"
        "Message automatique, merci de ne pas y repondre."
    )

    html = f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:480px;margin:0 auto;color:#1f2937">
  <p style="margin:0 0 16px">Bonjour {escape(nom)},</p>
  <p style="margin:0 0 8px">Voici votre code de connexion à la plateforme
     <strong>Yupaan</strong> (Burkina Suudu Bawdè) :</p>
  <p style="font-size:32px;font-weight:bold;letter-spacing:8px;margin:16px 0;color:#ca8a04">{code}</p>
  <p style="margin:0 0 16px">Ce code est valable <strong>{minutes} minutes</strong> et ne sert
     qu'une fois. Ne le communiquez à personne : aucun agent de la plateforme ne vous le demandera.</p>
  <p style="margin:0 0 16px;color:#6b7280;font-size:13px">Si vous n'êtes pas à l'origine de cette
     connexion, ignorez ce message puis changez votre mot de passe.</p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0">
  <p style="margin:0;color:#6b7280;font-size:12px">
     Plateforme Yupaan — Burkina Suudu Bawdè.<br>
     Message automatique, merci de ne pas y répondre.</p>
</div>"""

    expediteur = settings.DEFAULT_FROM_EMAIL
    domaine = parseaddr(expediteur)[1].rsplit('@', 1)[-1] or 'burkinasuudu.com'

    msg = EmailMultiAlternatives(
        subject=sujet,
        body=texte,
        from_email=expediteur,
        to=[user.email],
        reply_to=[getattr(settings, 'SERVER_EMAIL', expediteur)],
        headers={
            'Message-ID': make_msgid(domain=domaine),
            'Auto-Submitted': 'auto-generated',
            'X-Auto-Response-Suppress': 'All',
            'Precedence': 'transactional',
        },
    )
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=False)


def envoyer_code(request, user, *, premier_envoi=True, admin=False):
    """Génère un nouveau code, l'envoie par e-mail puis l'enregistre (haché) en
    session. Lève une exception si l'e-mail ne part pas : l'appelant annule
    alors la connexion et ne laisse pas le visiteur sur une page sans code."""
    code = _generer_code()
    maintenant = timezone.now()

    ancien = request.session.get(CLE_SESSION, {})
    nb_envois = 0 if premier_envoi else ancien.get('nb_envois', 0)

    _envoyer_email(user, code)

    request.session[CLE_SESSION] = {
        'user_id': user.pk,
        'email': user.email,
        'code_hache': make_password(code),
        'expire_le': (maintenant + timezone.timedelta(seconds=DUREE_VALIDITE)).isoformat(),
        'tentatives': 0,
        'nb_envois': nb_envois + 1,
        'dernier_envoi': maintenant.isoformat(),
        'admin': admin,
    }
    request.session.modified = True


def etat(request):
    """Données OTP de la session, ou None si aucune vérification en cours."""
    return request.session.get(CLE_SESSION)


def secondes_restantes(donnees):
    expire = parse_datetime(donnees['expire_le'])
    return max(0, int((expire - timezone.now()).total_seconds()))


def peut_renvoyer(donnees):
    """(ok, message_erreur) — respecte le délai minimum et le plafond d'envois."""
    if donnees.get('nb_envois', 0) >= MAX_ENVOIS:
        return False, "Nombre maximal d'envois atteint. Reprenez la connexion depuis le début."
    dernier = parse_datetime(donnees['dernier_envoi'])
    ecoule = (timezone.now() - dernier).total_seconds()
    if ecoule < DELAI_RENVOI:
        return False, f"Veuillez patienter {int(DELAI_RENVOI - ecoule)} s avant de demander un nouveau code."
    return True, None


def verifier(request, code_saisi):
    """(ok, message_erreur). En cas de succès, l'entrée de session est
    consommée (le code est à usage unique)."""
    donnees = request.session.get(CLE_SESSION)
    if not donnees:
        return False, "Session expirée. Veuillez vous reconnecter."

    if secondes_restantes(donnees) <= 0:
        return False, "Code expiré. Demandez un nouveau code."

    if donnees['tentatives'] >= MAX_TENTATIVES:
        return False, "Trop de tentatives. Demandez un nouveau code."

    code_saisi = (code_saisi or '').strip()
    if not code_saisi.isdigit() or len(code_saisi) != 4:
        donnees['tentatives'] += 1
        request.session.modified = True
        return False, "Le code doit comporter 4 chiffres."

    if not check_password(code_saisi, donnees['code_hache']):
        donnees['tentatives'] += 1
        restants = MAX_TENTATIVES - donnees['tentatives']
        request.session.modified = True
        if restants <= 0:
            return False, "Code incorrect. Trop de tentatives : demandez un nouveau code."
        return False, f"Code incorrect. Il vous reste {restants} tentative(s)."

    del request.session[CLE_SESSION]
    request.session.modified = True
    return True, None


def annuler(request):
    if CLE_SESSION in request.session:
        del request.session[CLE_SESSION]
        request.session.modified = True
