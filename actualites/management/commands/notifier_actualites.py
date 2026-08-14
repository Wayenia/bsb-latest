"""Envoie les notifications en attente.

Reprend les actualités publiées dont la date est atteinte et dont les abonnés
n'ont pas encore été prévenus : publications planifiées, ou envois interrompus.

    python manage.py notifier_actualites
    python manage.py notifier_actualites --simulation
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from actualites.models import Actualite
from actualites.notifications import notifier_abonnes


class Command(BaseCommand):
    help = "Envoie les notifications des actualités publiées et non encore diffusées."

    def add_arguments(self, parser):
        parser.add_argument("--simulation", action="store_true",
                            help="Liste ce qui serait envoyé, sans rien envoyer.")

    def handle(self, *args, **options):
        en_attente = Actualite.objects.filter(
            statut="publiee", abonnes_notifies=False,
            date_publication__lte=timezone.now()).order_by("date_publication")

        if not en_attente:
            self.stdout.write("Aucune actualité en attente de diffusion.")
            return

        for actualite in en_attente:
            if options["simulation"]:
                self.stdout.write(f"[simulation] {actualite.titre}")
                continue
            envoyes = notifier_abonnes(actualite)
            self.stdout.write(self.style.SUCCESS(f"{actualite.titre} : {envoyes} envoi(s)"))
