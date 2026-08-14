"""Jeu de données de démonstration pour l'app actualites.

    python manage.py actualites_demo              # crée les données
    python manage.py actualites_demo --supprimer  # les retire
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from actualites.models import AbonneNewsletter, Actualite

PREFIXE = "[DEMO] "

ACTUALITES = [
    {
        "titre": "Ouverture des inscriptions à la formation initiale 2026-2027",
        "chapeau": "Les candidatures sont ouvertes dans l'ensemble des centres du réseau "
                   "jusqu'au 30 septembre 2026.",
        "contenu": "La campagne de recrutement pour l'année de formation 2026-2027 est lancée. "
                   "Les candidats déposent leur dossier en ligne sur la plateforme Yu-Paan, "
                   "en choisissant un métier, un centre et une année scolaire.\n\n"
                   "Les pièces justificatives exigées varient selon le centre de formation. "
                   "Chaque dossier est instruit par le centre concerné, qui notifie sa décision "
                   "sur la plateforme.",
        "jours": 2,
        "statut": "publiee",
    },
    {
        "titre": "Remise des titres professionnels au CRFP de Ziniaré",
        "chapeau": "Cent vingt apprenants ont reçu leur brevet de qualification professionnelle.",
        "contenu": "La cérémonie s'est tenue en présence des autorités régionales et des "
                   "représentants du ministère de tutelle.\n\n"
                   "Les lauréats se répartissent entre les filières génie civil, génie électrique "
                   "et textile habillement cuir peau.",
        "jours": 9,
        "statut": "publiee",
    },
    {
        "titre": "Nouvelle spécialité : domoticien au CFPI de Bobo-Dioulasso",
        "chapeau": "La filière génie électrique accueille une spécialité supplémentaire "
                   "à la rentrée prochaine.",
        "contenu": "La spécialité domoticien complète l'offre du centre en matière "
                   "d'installations électriques du bâtiment.\n\n"
                   "La formation dure neuf mois et débouche sur un brevet de qualification "
                   "professionnelle.",
        "jours": 16,
        "statut": "publiee",
    },
    {
        "titre": "Journées portes ouvertes dans les trois directions inter-régionales",
        "chapeau": "Les centres accueillent le public pour présenter les métiers "
                   "et les conditions d'accès.",
        "contenu": "Les visites sont organisées à Ouagadougou, Bobo-Dioulasso et Ziniaré. "
                   "Les ateliers de chaque filière sont ouverts aux visiteurs.",
        "jours": 24,
        "statut": "publiee",
    },
    {
        "titre": "Mise en service du module de facturation des prestations",
        "chapeau": "La Direction Administrative et Financière dispose désormais d'un circuit "
                   "complet, du devis à l'encaissement.",
        "contenu": "Le module couvre la création du client, la facture proforma, sa validation "
                   "en facture définitive et l'encaissement, avec édition des reçus.",
        "jours": 40,
        "statut": "publiee",
    },
    {
        "titre": "Communiqué en préparation : calendrier des évaluations",
        "chapeau": "Brouillon de démonstration, non visible du public.",
        "contenu": "Ce contenu sert à vérifier qu'une actualité en brouillon reste inaccessible "
                   "depuis le site public et n'entraîne aucun envoi aux abonnés.",
        "jours": 0,
        "statut": "brouillon",
    },
]

ABONNES = [
    ("awa.sawadogo@exemple.bf", True),
    ("ibrahim.ouedraogo@exemple.bf", True),
    ("mariam.kabore@exemple.bf", True),
    ("service.communication@exemple.bf", True),
    ("ancien.abonne@exemple.bf", False),
]


class Command(BaseCommand):
    help = "Crée ou supprime un jeu d'actualités et d'abonnés de démonstration."

    def add_arguments(self, parser):
        parser.add_argument("--supprimer", action="store_true",
                            help="Supprime les données de démonstration au lieu de les créer.")

    def handle(self, *args, **options):
        if options["supprimer"]:
            actus = Actualite.objects.filter(titre__startswith=PREFIXE).delete()[0]
            abonnes = AbonneNewsletter.objects.filter(email__endswith="@exemple.bf").delete()[0]
            self.stdout.write(self.style.SUCCESS(
                f"Supprimé : {actus} actualité(s), {abonnes} abonné(s)."))
            return

        maintenant = timezone.now()
        crees = 0
        for donnees in ACTUALITES:
            publiee = donnees["statut"] == "publiee"
            _, cree = Actualite.objects.get_or_create(
                titre=PREFIXE + donnees["titre"],
                defaults={
                    "chapeau": donnees["chapeau"],
                    "contenu": donnees["contenu"],
                    "statut": donnees["statut"],
                    "date_publication": maintenant - timedelta(days=donnees["jours"]) if publiee else None,
                    # déjà notifiés : le jeu de démonstration n'envoie aucun e-mail
                    "abonnes_notifies": publiee,
                },
            )
            crees += int(cree)

        abonnes_crees = 0
        for email, actif in ABONNES:
            abonne, cree = AbonneNewsletter.objects.get_or_create(email=email)
            if cree:
                abonne.actif = actif
                if not actif:
                    abonne.date_desinscription = maintenant
                abonne.save()
                abonnes_crees += 1

        self.stdout.write(self.style.SUCCESS(
            f"Créé : {crees} actualité(s), {abonnes_crees} abonné(s). "
            f"Retrait : python manage.py actualites_demo --supprimer"))
