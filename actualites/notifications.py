"""Envoi de l'e-mail « nouvelle actualité » aux abonnés."""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

from .models import AbonneNewsletter

LOT = 50        # messages par connexion SMTP
ECHECS_MAX = 3  # refus consecutifs avant desactivation d'une adresse


def notifier_abonnes(actualite, request=None):
    """Envoie une notification à chaque abonné actif. Retourne le nombre d'envois.

    Ne fait rien si l'actualité n'est pas publiée ou si les abonnés ont déjà été
    prévenus : republier une actualité modifiée n'entraîne pas un second envoi.
    """
    if not actualite.est_visible or actualite.abonnes_notifies:
        return 0

    def absolu(chemin):
        if request is not None:
            return request.build_absolute_uri(chemin)
        hote = (settings.ALLOWED_HOSTS or ["localhost"])[0]
        return f"http://{hote}{chemin}"

    lien_actu = absolu(actualite.get_absolute_url())
    abonnes = list(AbonneNewsletter.objects.filter(actif=True))
    if not abonnes:
        return 0

    envoyes, echecs = 0, 0
    for debut in range(0, len(abonnes), LOT):
        connexion = get_connection(fail_silently=False)
        try:
            connexion.open()
        except Exception:
            return envoyes
        for abonne in abonnes[debut:debut + LOT]:
            contexte = {
                "actualite": actualite,
                "lien_actu": lien_actu,
                "lien_desabonnement": absolu(abonne.lien_desabonnement()),
            }
            message = EmailMultiAlternatives(
                subject=f"Nouvelle actualité sur Yu-Paan : {actualite.titre}",
                body=render_to_string("actualites/email/nouvelle_actualite.txt", contexte),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[abonne.email],
                connection=connexion,
            )
            message.attach_alternative(
                render_to_string("actualites/email/nouvelle_actualite.html", contexte), "text/html")
            try:
                message.send()
                envoyes += 1
                if abonne.nb_echecs:
                    abonne.nb_echecs = 0
                    abonne.save(update_fields=["nb_echecs"])
            except Exception:
                echecs += 1
                abonne.nb_echecs += 1
                # Trois refus consecutifs : l'adresse est retiree de la diffusion.
                if abonne.nb_echecs >= ECHECS_MAX:
                    abonne.actif = False
                abonne.save(update_fields=["nb_echecs", "actif"])
        connexion.close()

    actualite.abonnes_notifies = True
    actualite.save(update_fields=["abonnes_notifies"])
    return envoyes
