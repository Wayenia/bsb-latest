"""Historique générique avant/après (django-simple-history) sur les modèles
métier : chaque création/modification/suppression laisse une trace — qui,
quand, avec l'état du champ — y compris quand l'enregistrement vivant a
depuis disparu (cas qui avait motivé cette demande : un apprenant supprimé
sans laisser de trace)."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import Eleve, Utilisateur
from courses.models import (
    AnneeScolaire, CentreEtFiliere, CentreFormation, Filiere, Frais, Inscription,
    Province, Region, TypeFrais,
)


class HistoriqueGeneriqueTests(TestCase):
    def test_creation_laisse_une_trace(self):
        region = Region.objects.create(nom_region="Est", chef_lieu="Fada")
        self.assertEqual(region.history.count(), 1)
        self.assertEqual(region.history.first().history_type, '+')

    def test_modification_laisse_une_trace_avec_avant_apres(self):
        region = Region.objects.create(nom_region="Est", chef_lieu="Fada")
        region.chef_lieu = "Fada N'Gourma"
        region.save()
        self.assertEqual(region.history.count(), 2)
        dernier, premier = region.history.all()  # plus récent d'abord
        self.assertEqual(dernier.history_type, '~')
        self.assertEqual(premier.chef_lieu, "Fada")
        self.assertEqual(dernier.chef_lieu, "Fada N'Gourma")

    def test_suppression_laisse_une_trace_avec_l_etat_final(self):
        """Le cas qui a motive cette demande : meme si l'enregistrement
        vivant disparait, son dernier etat reste consultable."""
        eleve = Eleve.objects.create(
            username="eleve.hist", nom="Ouedraogo", prenom="Fatou", adresse="Ouaga",
            email="eleve.hist@example.invalid", lieu_naissance="Ouaga",
            nom_pere="T", prenom_pere="P", nom_mere="M", prenom_mere="Q",
        )
        eleve_id = eleve.id
        eleve.delete()

        self.assertFalse(Eleve.objects.filter(id=eleve_id).exists())
        historique = Eleve.history.filter(id=eleve_id)
        self.assertEqual(historique.count(), 2)  # création puis suppression
        self.assertEqual(historique.order_by('-history_date').first().history_type, '-')
        self.assertEqual(historique.order_by('-history_date').first().nom, "Ouedraogo")


class HistoriqueAuteurViaRequeteTests(TestCase):
    """L'auteur d'un changement passé par une requête HTTP doit être capturé
    automatiquement (HistoryRequestMiddleware), sans rien coder dans la vue
    elle-même."""

    @classmethod
    def setUpTestData(cls):
        region = Region.objects.create(nom_region="Centre", chef_lieu="Ouagadougou")
        province = Province.objects.create(region=region, nom_province="Kadiogo", chef_lieu="Ouagadougou")
        cls.centre = CentreFormation.objects.create(nom_centre="Centre Ouaga", province=province)
        filiere = Filiere.objects.create(nom_filiere="Coiffure")
        annee = AnneeScolaire.objects.create(libelle_anne="2025-2026")
        cls.metier = CentreEtFiliere.objects.create(
            centre=cls.centre, filiere=filiere, annee_prog=annee,
            type_programme="formation", type_formation="initiale", is_active=True, duree_jours=270,
        )
        Frais.objects.create(formation=cls.metier, type_frais=TypeFrais.objects.create(libelle="Scolarité"), montant=50000)
        cls.annee = annee
        cls.staff = Utilisateur.objects.create_superuser(
            username="staff.hist", password="x", nom="Admin", prenom="Sys",
            adresse="Ouaga", email="staff.hist@example.invalid",
        )
        cls.eleve = Eleve.objects.create(
            username="eleve.hist2", nom="Sawadogo", prenom="Awa", adresse="Ouaga",
            email="eleve.hist2@example.invalid", lieu_naissance="Ouaga",
            nom_pere="T", prenom_pere="P", nom_mere="M", prenom_mere="Q",
        )

    def test_validation_inscription_capture_l_auteur(self):
        insc = Inscription.objects.create(
            eleve=self.eleve, formation=self.metier, annee_scolaire=self.annee, statut="en_cours",
        )
        self.client.force_login(self.staff)
        self.client.post(reverse('bsb_admin:gerer_subscription', args=[insc.id]), {'action': 'valide'})

        dernier = insc.history.order_by('-history_date').first()
        self.assertEqual(dernier.statut, 'valide')
        self.assertEqual(dernier.history_user_id, self.staff.pk)
