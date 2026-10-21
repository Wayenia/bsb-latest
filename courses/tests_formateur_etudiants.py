"""Badge « Statut dossier » de la page formateur (liste des étudiants d'une
filière) : devait afficher « Validé & payé » pour un dossier validé et
totalement réglé, mais vérifiait Inscription.statut == 'valide_paye' — une
valeur jamais stockée en pratique (le champ reste "valide" quel que soit le
paiement, voir Inscription.libelle_statut_paiement). Le badge restait donc
toujours "Validé", même pour un apprenant qui a tout payé."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import Eleve, Formateur
from courses.models import (
    AnneeScolaire, CentreEtFiliere, CentreFormation, Dette, Filiere, Frais,
    Inscription, Paiement, Province, Region, TypeFrais,
)


class BadgeStatutDossierTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        region = Region.objects.create(nom_region="Centre", chef_lieu="Ouagadougou")
        province = Province.objects.create(region=region, nom_province="Kadiogo", chef_lieu="Ouagadougou")
        cls.centre = CentreFormation.objects.create(nom_centre="Centre Ouaga", province=province)
        cls.filiere = Filiere.objects.create(nom_filiere="Coiffure")
        annee = AnneeScolaire.objects.create(libelle_anne="2025-2026")
        cls.metier = CentreEtFiliere.objects.create(
            centre=cls.centre, filiere=cls.filiere, annee_prog=annee,
            type_programme="formation", type_formation="initiale", is_active=True, duree_jours=270,
        )
        Frais.objects.create(formation=cls.metier, type_frais=TypeFrais.objects.create(libelle="Scolarité"), montant=50000)
        cls.annee = annee

        cls.formateur = Formateur.objects.create_user(
            username="form.test", password="x", nom="Prof", prenom="Un", adresse="Ouaga",
            email="form.test@example.invalid", user_type="formateur",
            emploi="Formateur", specialite="Coiffure", date_integration="2024-01-01",
        )
        cls.formateur.centre = cls.centre
        cls.formateur.filiere = cls.filiere
        cls.formateur.save()

    def _eleve(self, nom):
        return Eleve.objects.create(
            username=f"eleve.{nom}", nom=nom.upper(), prenom="Test", adresse="Ouaga",
            email=f"eleve.{nom}@example.invalid", lieu_naissance="Ouaga",
            nom_pere="T", prenom_pere="P", nom_mere="M", prenom_mere="Q",
        )

    def _inscription_validee(self, nom):
        insc = Inscription.objects.create(
            eleve=self._eleve(nom), formation=self.metier, annee_scolaire=self.annee, statut="en_cours",
        )
        insc.statut = "valide"
        insc.save()
        return insc

    def test_dossier_totalement_paye_affiche_valide_et_paye(self):
        insc = self._inscription_validee("paye")
        Paiement.objects.create(dette=insc.dettes.get(), montant_paiement=50000, tranche=1)

        self.client.force_login(self.formateur)
        html = self.client.get(reverse('courses:formateur_etudiants', args=[self.metier.id])).content.decode()
        self.assertIn("Validé & payé", html)

    def test_dossier_partiellement_paye_affiche_valide_partiel(self):
        insc = self._inscription_validee("partiel")
        Paiement.objects.create(dette=insc.dettes.get(), montant_paiement=10000, tranche=1)

        self.client.force_login(self.formateur)
        html = self.client.get(reverse('courses:formateur_etudiants', args=[self.metier.id])).content.decode()
        self.assertIn("Validé - partiel", html)

    def test_dossier_non_paye_affiche_simplement_valide(self):
        self._inscription_validee("nonpaye")

        self.client.force_login(self.formateur)
        html = self.client.get(reverse('courses:formateur_etudiants', args=[self.metier.id])).content.decode()
        self.assertIn(">Validé</span>", html)
        self.assertNotIn("Validé & payé", html)
