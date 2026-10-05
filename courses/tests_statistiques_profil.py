"""Filtres de profil sur /statistiques/stat-globaux/ : âge (min/max), niveau
d'études, handicap, parrain/organisation — ils doivent restreindre à la fois
les compteurs de dossiers et les montants, comme les autres filtres."""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import Eleve, Utilisateur
from courses.models import (
    AnneeScolaire, CentreEtFiliere, CentreFormation, Filiere, Frais, Inscription, Province, Region, TypeFrais,
)


class FiltresProfilStatistiquesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        region = Region.objects.create(nom_region="Centre", chef_lieu="Ouagadougou")
        province = Province.objects.create(region=region, nom_province="Kadiogo", chef_lieu="Ouagadougou")
        centre = CentreFormation.objects.create(nom_centre="Centre Ouaga", province=province)
        annee = AnneeScolaire.objects.create(libelle_anne="2025-2026")
        metier = CentreEtFiliere.objects.create(
            centre=centre, filiere=Filiere.objects.create(nom_filiere="Coiffure"), annee_prog=annee,
            type_programme="formation", type_formation="initiale", is_active=True, duree_jours=270,
        )
        Frais.objects.create(formation=metier, type_frais=TypeFrais.objects.create(libelle="Scolarité"), montant=50000)
        cls.annee = annee
        cls.metier = metier
        cls.staff = Utilisateur.objects.create_superuser(
            username="staff.profil", password="x", nom="Admin", prenom="Sys", email="staff.profil@example.invalid",
        )

        cls.jeune = cls._eleve("jeune", date(date.today().year - 18, 1, 1), "terminale", True)
        cls.adulte = cls._eleve("adulte", date(date.today().year - 40, 1, 1), "licence", False)

        for eleve, org in ((cls.jeune, "Association Sante"), (cls.adulte, "")):
            insc = Inscription.objects.create(eleve=eleve, formation=metier, annee_scolaire=annee, statut="en_cours")
            insc.statut = "valide"
            insc.organisation_nom = org
            insc.save()

    @classmethod
    def _eleve(cls, nom, naissance, niveau, handicap):
        return Eleve.objects.create(
            username=f"eleve.{nom}", nom=nom.upper(), prenom="Test", adresse="Ouaga",
            email=f"eleve.{nom}@example.invalid", lieu_naissance="Ouaga", date_naissance=naissance,
            niveau_scolaire=niveau, a_handicap=handicap,
            nom_pere="T", prenom_pere="P", nom_mere="M", prenom_mere="Q",
            type_document="extrait_naissance", numero_document=f"N-{nom}",
            date_etablissement_document=date(2020, 1, 1),
        )
        return e

    def setUp(self):
        self.client.force_login(self.staff)

    def _total(self, params):
        resp = self.client.get(reverse('courses:statistiques'), params)
        return resp.context['stats']['total_dossiers']

    def test_sans_filtre_les_deux_dossiers(self):
        self.assertEqual(self._total({}), 2)

    def test_age_min_retient_les_plus_ages(self):
        self.assertEqual(self._total({'age_min': '30'}), 1)

    def test_age_max_retient_les_plus_jeunes(self):
        self.assertEqual(self._total({'age_max': '25'}), 1)

    def test_niveau_scolaire(self):
        self.assertEqual(self._total({'niveau_scolaire': 'licence'}), 1)

    def test_handicap_oui(self):
        self.assertEqual(self._total({'handicap': 'oui'}), 1)

    def test_handicap_non(self):
        self.assertEqual(self._total({'handicap': 'non'}), 1)

    def test_organisation_renseignee(self):
        self.assertEqual(self._total({'organisation': 'oui'}), 1)

    def test_organisation_non_renseignee(self):
        self.assertEqual(self._total({'organisation': 'non'}), 1)

    def test_combinaison_avec_filtre_existant(self):
        # Synergie : jeune (18 ans) + handicap oui + organisation oui → 1 dossier.
        self.assertEqual(self._total({'handicap': 'oui', 'organisation': 'oui', 'age_max': '25'}), 1)
        # Mais adulte + handicap oui → aucun.
        self.assertEqual(self._total({'handicap': 'oui', 'age_min': '30'}), 0)
