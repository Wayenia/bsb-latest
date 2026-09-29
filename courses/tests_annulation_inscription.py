"""Annulation d'une inscription déjà validée (/bsb/subscriptions) : retour à
"en cours", suppression des dettes, bloquée s'il existe un paiement (même
annulé) pour ne jamais perdre sa traçabilité, et la personne qui annule est
enregistrée (annule_par/motif_annulation/date_annulation)."""

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from accounts.models import Eleve, Utilisateur
from courses.models import (
    AnneeScolaire, CentreEtFiliere, CentreFormation, Dette, Filiere, Frais,
    Inscription, Paiement, Province, Region, TypeFrais,
)


class AnnulationInscriptionBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        region = Region.objects.create(nom_region="Centre", chef_lieu="Ouagadougou")
        cls.province = Province.objects.create(region=region, nom_province="Kadiogo", chef_lieu="Ouagadougou")
        cls.centre = CentreFormation.objects.create(nom_centre="Centre Ouaga", province=cls.province)

        cls.filiere = Filiere.objects.create(nom_filiere="Coiffure")
        cls.annee = AnneeScolaire.objects.create(libelle_anne="2025-2026")

        cls.metier = CentreEtFiliere.objects.create(
            centre=cls.centre, filiere=cls.filiere, annee_prog=cls.annee,
            type_programme="formation", type_formation="initiale", is_active=True, duree_jours=270,
        )
        tf_scol = TypeFrais.objects.create(libelle="Scolarité")
        Frais.objects.create(formation=cls.metier, type_frais=tf_scol, montant=50000)

        cls.eleve = Eleve.objects.create(
            username="eleve.annul", nom="Ouedraogo", prenom="Fatou", adresse="Ouaga",
            email="eleve.annul@example.invalid", lieu_naissance="Ouaga",
            nom_pere="T", prenom_pere="P", nom_mere="M", prenom_mere="Q",
        )
        cls.staff = Utilisateur.objects.create_superuser(
            username="staff.annul", password="x", nom="Admin", prenom="Sys",
            email="staff.annul@example.invalid",
        )

    def _inscription_validee(self):
        insc = Inscription.objects.create(
            eleve=self.eleve, formation=self.metier, annee_scolaire=self.annee, statut="en_cours",
        )
        insc.statut = "valide"
        insc.save()  # signal -> crée une Dette pour le frais de scolarité
        return insc


class AnnulationInscriptionTests(AnnulationInscriptionBase):
    def test_annulation_supprime_les_dettes_et_enregistre_lauteur(self):
        insc = self._inscription_validee()
        self.assertTrue(Dette.objects.filter(inscription=insc).exists())

        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse('bsb_admin:annuler_inscription', args=[insc.id]),
            {'motif': 'Erreur de saisie'}, follow=True,
        )
        insc.refresh_from_db()
        self.assertEqual(insc.statut, 'en_cours')
        self.assertIsNone(insc.date_validation)
        self.assertEqual(insc.motif_annulation, 'Erreur de saisie')
        self.assertIsNotNone(insc.date_annulation)
        self.assertEqual(insc.annule_par, self.staff)
        self.assertFalse(Dette.objects.filter(inscription=insc).exists())

    def test_motif_obligatoire(self):
        insc = self._inscription_validee()
        self.client.force_login(self.staff)
        self.client.post(
            reverse('bsb_admin:annuler_inscription', args=[insc.id]),
            {'motif': ''}, follow=True,
        )
        insc.refresh_from_db()
        self.assertEqual(insc.statut, 'valide')  # inchangé
        self.assertTrue(Dette.objects.filter(inscription=insc).exists())

    def test_refuse_si_pas_valide(self):
        insc = Inscription.objects.create(
            eleve=self.eleve, formation=self.metier, annee_scolaire=self.annee, statut="en_cours",
        )
        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse('bsb_admin:annuler_inscription', args=[insc.id]),
            {'motif': 'x'}, follow=True,
        )
        insc.refresh_from_db()
        self.assertEqual(insc.statut, 'en_cours')

    def test_bloque_si_paiement_existe_meme_annule(self):
        insc = self._inscription_validee()
        dette = insc.dettes.get()
        paiement = Paiement.objects.create(
            dette=dette, montant_paiement=10000, tranche=1, effectue_par=self.staff,
        )
        # Le paiement est ensuite annulé : la ligne reste en base pour la traçabilité.
        paiement.annule = True
        paiement.save()

        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse('bsb_admin:annuler_inscription', args=[insc.id]),
            {'motif': 'Erreur'}, follow=True,
        )
        insc.refresh_from_db()
        self.assertEqual(insc.statut, 'valide')  # inchangé
        self.assertTrue(Dette.objects.filter(inscription=insc).exists())
        self.assertTrue(Paiement.objects.filter(pk=paiement.pk).exists())  # pas supprimé

    def test_permission_requise(self):
        insc = self._inscription_validee()
        agent = Utilisateur.objects.create_user(
            username="sans.permission", password="x", nom="N", prenom="P",
            email="sans.permission@example.invalid", user_type='eleve',
        )
        self.client.force_login(agent)
        resp = self.client.post(
            reverse('bsb_admin:annuler_inscription', args=[insc.id]),
            {'motif': 'x'},
        )
        self.assertNotEqual(resp.status_code, 200)
        insc.refresh_from_db()
        self.assertEqual(insc.statut, 'valide')

    def test_revalidation_apres_annulation_recree_les_dettes(self):
        """Vérifie que la suppression réelle (option a) permet au signal
        creer_dettes_automatiquement de refonctionner normalement, sans
        modification, si l'inscription est revalidée après annulation."""
        insc = self._inscription_validee()
        self.client.force_login(self.staff)
        self.client.post(
            reverse('bsb_admin:annuler_inscription', args=[insc.id]),
            {'motif': 'Erreur'}, follow=True,
        )
        insc.refresh_from_db()
        self.assertEqual(insc.statut, 'en_cours')
        self.assertFalse(Dette.objects.filter(inscription=insc).exists())

        insc.statut = 'valide'
        insc.save()
        self.assertTrue(Dette.objects.filter(inscription=insc).exists())
