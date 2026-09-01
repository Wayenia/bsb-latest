"""Diffusion du rapport d'inspection des connexions.

Destinee a une execution planifiee (cron sur l'hote, appelant docker compose
exec). Elle n'ecrit rien en base : elle lit le journal, en tire un classeur et
l'envoie. La relancer deux fois de suite est sans consequence.
"""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.models import HistoriqueConnexion
from audit import services
from audit.models import DestinataireRapport, ReglageDiffusion
from audit.classeur import construire_classeur

PLAFOND_JOURNAL = 5000


class Command(BaseCommand):
    help = "Construit le rapport d'inspection des connexions et l'envoie par courriel."

    def add_arguments(self, p):
        p.add_argument('--jours', type=int, default=None,
                       help="Profondeur de la periode (defaut : AUDIT_PERIODE_JOURS).")
        p.add_argument('--a', action='append', default=[], metavar='ADRESSE',
                       help="Destinataire. Repetable. Remplace AUDIT_DESTINATAIRES.")
        p.add_argument('--fichier', default=None, metavar='CHEMIN',
                       help="Ecrit aussi le classeur sur disque (mise au point).")
        p.add_argument('--sans-envoi', action='store_true',
                       help="Construit le rapport sans envoyer de courriel.")
        p.add_argument('--auto', action='store_true',
                       help="Mode planifie : n'envoie que si le reglage d'ecran est echu.")

    def handle(self, *args, **o):
        # Mode planifie : le planificateur appelle cette commande a intervalle
        # regulier ; on n'envoie que lorsqu'une echeance du reglage d'ecran est
        # atteinte, et jamais deux fois la meme (README 9.5).
        reglage = None
        if o['auto']:
            reglage = ReglageDiffusion.charge()
            if not reglage.actif:
                self.stdout.write("Envoi automatique desactive : rien a faire.")
                return
            if not reglage.est_du(timezone.now()):
                self.stdout.write("Aucune echeance atteinte : rien a envoyer.")
                return
            if o['jours'] is None:
                o['jours'] = reglage.periode_jours

        # `is None` et non `or` : --jours 0 doit etre refuse, pas retomber
        # silencieusement sur la valeur par defaut.
        jours = o['jours'] if o['jours'] is not None else getattr(settings, 'AUDIT_PERIODE_JOURS', 7)
        if jours < 1:
            raise CommandError("--jours doit valoir au moins 1.")

        # Les adresses de l'ecran de parametrage s'ajoutent a celles du .env :
        # une installation deja configuree continue de fonctionner sans rien
        # changer. --a, lui, remplace tout, pour un envoi ponctuel cible.
        if o['a']:
            destinataires = o['a']
        else:
            destinataires = sorted(set(
                list(getattr(settings, 'AUDIT_DESTINATAIRES', []))
                + DestinataireRapport.adresses_actives()))
        if not destinataires and not o['sans_envoi'] and not o['fichier']:
            raise CommandError(
                "Aucun destinataire. Ajoutez-en depuis l'ecran « Destinataires du "
                "rapport », renseignez AUDIT_DESTINATAIRES dans .env, passez "
                "--a adresse@example.org, ou utilisez --sans-envoi.")

        rapport = services.construire_rapport(jours=jours)
        evenements = list(
            HistoriqueConnexion.objects
            .filter(date_evenement__gte=rapport.debut, date_evenement__lte=rapport.fin)
            .select_related('centre')
            .order_by('-date_evenement')[:PLAFOND_JOURNAL])

        classeur = construire_classeur(rapport, evenements)
        nom = f"audit_connexions_{timezone.localtime(rapport.fin):%Y%m%d}.xlsx"

        self.stdout.write(
            f"Periode : {rapport.debut:%d/%m/%Y} au {rapport.fin:%d/%m/%Y} "
            f"({rapport.jours} j) — {rapport.total} evenement(s), "
            f"{rapport.echecs} echec(s), {len(rapport.alertes)} alerte(s) "
            f"dont {len(rapport.alertes_critiques)} critique(s).")
        if len(evenements) == PLAFOND_JOURNAL:
            self.stdout.write(self.style.WARNING(
                f"Journal tronque a {PLAFOND_JOURNAL} lignes : reduisez --jours "
                f"pour un detail complet."))

        if o['fichier']:
            with open(o['fichier'], 'wb') as f:
                f.write(classeur)
            self.stdout.write(self.style.SUCCESS(f"Classeur ecrit : {o['fichier']}"))

        if o['sans_envoi'] or not destinataires:
            self.stdout.write("Envoi non demande.")
            return

        contexte = {'r': rapport, 'nb_evenements': len(evenements)}
        texte = render_to_string('audit/rapport_email.txt', contexte)
        html = render_to_string('audit/rapport_email.html', contexte)

        sujet = (f"[BSB] Inspection des connexions — "
                 f"{rapport.echecs} echec(s), {len(rapport.alertes_critiques)} alerte(s) critique(s)")
        message = EmailMultiAlternatives(
            subject=sujet, body=texte,
            from_email=settings.DEFAULT_FROM_EMAIL, to=destinataires,
            connection=get_connection())
        message.attach_alternative(html, "text/html")
        message.attach(
            nom, classeur,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        envoyes = message.send(fail_silently=False)
        if envoyes:
            if reglage is not None:
                reglage.derniere_diffusion = timezone.now()
                reglage.save(update_fields=['derniere_diffusion'])
            self.stdout.write(self.style.SUCCESS(
                f"Rapport envoye a {', '.join(destinataires)} (piece jointe : {nom})."))
        else:
            raise CommandError("Le serveur de messagerie n'a accepte aucun message.")
