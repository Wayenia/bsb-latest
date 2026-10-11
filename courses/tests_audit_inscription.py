"""Traçabilité de la décision sur une inscription : jusqu'ici seules la date
et (pour un rejet) le motif étaient conservés, jamais QUI avait validé ou
rejeté le dossier. Inscription.valide_par / rejete_par comblent ce trou, sur
les deux écrans qui peuvent le faire (back-office « admin » et écran membre
scopé par centre)."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import Eleve, MembreAdministration, Utilisateur
from courses.models import (
    AnneeScolaire, CentreEtFiliere, CentreFormation, Filiere, Frais, Inscription,
    Province, Region, TypeFrais,
)


class AuditInscriptionBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        region = Region.objects.create(nom_region="Centre", chef_lieu="Ouagadougou")
        province = Province.objects.create(region=region, nom_province="Kadiogo", chef_lieu="Ouagadougou")
        cls.centre = CentreFormation.objects.create(nom_centre="Centre Ouaga", province=province)
        filiere = Filiere.objects.create(nom_filiere="Coiffure")
        cls.annee = AnneeScolaire.objects.create(libelle_anne="2025-2026")
        cls.metier = CentreEtFiliere.objects.create(
            centre=cls.centre, filiere=filiere, annee_prog=cls.annee,
            type_programme="formation", type_formation="initiale", is_active=True, duree_jours=270,
        )
        Frais.objects.create(formation=cls.metier, type_frais=TypeFrais.objects.create(libelle="Scolarité"), montant=50000)

        cls.staff = Utilisateur.objects.create_superuser(
            username="staff.audit", password="x", nom="Admin", prenom="Sys",
            adresse="Ouaga", email="staff.audit@example.invalid",
        )
        cls.gestionnaire = MembreAdministration.objects.create_user(
            username="gest.audit", password="x", nom="Gest", prenom="Centre",
            adresse="Ouaga", email="gest.audit@example.invalid", user_type="gestionnaire",
            emploi="Directeur", categorie="DC",
        )
        cls.gestionnaire.structure = cls.centre
        cls.gestionnaire.save()

    def _eleve(self, nom):
        return Eleve.objects.create(
            username=f"eleve.{nom}", nom=nom.upper(), prenom="Test", adresse="Ouaga",
            email=f"eleve.{nom}@example.invalid", lieu_naissance="Ouaga",
            nom_pere="T", prenom_pere="P", nom_mere="M", prenom_mere="Q",
        )

    def _inscription_en_cours(self, nom):
        return Inscription.objects.create(
            eleve=self._eleve(nom), formation=self.metier, annee_scolaire=self.annee, statut="en_cours",
        )


class ValidationRejetAdminTests(AuditInscriptionBase):
    """Écran back-office (bsb_admin)."""

    def test_valider_enregistre_valide_par(self):
        insc = self._inscription_en_cours("a")
        self.client.force_login(self.staff)
        self.client.post(reverse('bsb_admin:gerer_subscription', args=[insc.id]), {'action': 'valide'})
        insc.refresh_from_db()
        self.assertEqual(insc.statut, 'valide')
        self.assertEqual(insc.valide_par, self.staff)
        self.assertIsNone(insc.rejete_par)

    def test_rejeter_enregistre_rejete_par(self):
        insc = self._inscription_en_cours("b")
        self.client.force_login(self.staff)
        self.client.post(reverse('bsb_admin:rejeter_inscription', args=[insc.id]), {'motif': 'Dossier incomplet'})
        insc.refresh_from_db()
        self.assertEqual(insc.statut, 'rejete')
        self.assertEqual(insc.rejete_par, self.staff)
        self.assertIsNone(insc.valide_par)


class ValidationRejetMembreTests(AuditInscriptionBase):
    """Écran membre (courses), scopé par le centre du gestionnaire connecté."""

    def test_valider_enregistre_valide_par(self):
        insc = self._inscription_en_cours("c")
        self.client.force_login(self.gestionnaire)
        self.client.post(reverse('courses:gerer_inscription', args=[insc.id]), {'action': 'valide'})
        insc.refresh_from_db()
        self.assertEqual(insc.statut, 'valide')
        # insc.valide_par remonte un Utilisateur (table de base de la MTI),
        # pas un MembreAdministration : on compare par pk, pas par type.
        self.assertEqual(insc.valide_par_id, self.gestionnaire.pk)

    def test_rejeter_enregistre_rejete_par(self):
        insc = self._inscription_en_cours("d")
        self.client.force_login(self.gestionnaire)
        self.client.post(reverse('courses:rejeter_inscription', args=[insc.id]), {'motif': 'Dossier incomplet'})
        insc.refresh_from_db()
        self.assertEqual(insc.statut, 'rejete')
        self.assertEqual(insc.rejete_par_id, self.gestionnaire.pk)
