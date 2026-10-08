"""Centre d'encaissement : l'argent d'un paiement est attribué au centre dont
la caisse l'a réellement reçu (celui de l'agent — cree_par — quand ce dernier
est rattaché à un centre unique), pas forcément au centre de l'inscription de
l'apprenant. Les rôles sans centre unique (admin, dg, agent comptable, deps,
directeur inter-régional, superutilisateur) retombent sur le centre de
l'inscription, comme avant ce changement."""

from accounts.models import MembreAdministration, Utilisateur
from django.test import TestCase
from django.urls import reverse

from courses.models import Paiement
from courses.tests_hebergement import HebergementBase


class CentreEncaissementBase(HebergementBase):
    """Ajoute un second centre (Centre B) et un caissier qui y est rattaché,
    distinct du centre A (celui de l'apprenant, défini par HebergementBase)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from courses.models import CentreFormation
        cls.centre_b = CentreFormation.objects.create(
            nom_centre="Centre B", province=cls.province,
        )
        cls.caissier_b = MembreAdministration.objects.create_user(
            username="caissier.b", password="x", nom="Caissier", prenom="B",
            email="caissier.b@example.invalid", user_type="caissier",
            emploi="Caissier", categorie="C1",
        )
        cls.caissier_b.structure = cls.centre_b
        cls.caissier_b.save()

        cls.caissier_a = MembreAdministration.objects.create_user(
            username="caissier.a", password="x", nom="Caissier", prenom="A",
            email="caissier.a@example.invalid", user_type="caissier",
            emploi="Caissier", categorie="C1",
        )
        cls.caissier_a.structure = cls.centre
        cls.caissier_a.save()


class DeriverCentreEncaisseurTests(CentreEncaissementBase):
    def test_caissier_rattache_a_un_centre_impose_son_propre_centre(self):
        insc = self._inscription_validee()  # apprenant au Centre A (self.centre)
        centre = Paiement.deriver_centre_encaisseur(self.caissier_b, insc)
        self.assertEqual(centre, self.centre_b)

    def test_role_sans_centre_unique_retombe_sur_le_centre_de_l_inscription(self):
        insc = self._inscription_validee()
        # self.staff est un superutilisateur : pas de MembreAdministration.
        centre = Paiement.deriver_centre_encaisseur(self.staff, insc)
        self.assertEqual(centre, self.centre)

    def test_aucun_agent_retombe_aussi_sur_le_centre_de_l_inscription(self):
        insc = self._inscription_validee()
        centre = Paiement.deriver_centre_encaisseur(None, insc)
        self.assertEqual(centre, self.centre)


class EncaissementCroiseTests(CentreEncaissementBase):
    """Un caissier du centre B encaisse pour un apprenant inscrit au centre A
    : l'argent doit être attribué au centre B partout (quittance, historique,
    stat-globaux), le « dû » restant rattaché au centre A de l'apprenant."""

    def test_paiement_porte_le_centre_du_caissier_pas_celui_de_l_apprenant(self):
        insc = self._inscription_validee()
        dette = insc.dettes.get()
        paiement = Paiement.objects.create(
            dette=dette, montant_paiement=10000, tranche=1, cree_par=self.caissier_b,
        )
        self.assertEqual(paiement.centre_encaissement, self.centre_b)
        self.assertEqual(paiement.centre_apprenant, self.centre)
        self.assertIn(self.centre_b.code_centre or "", paiement.numero_quittance or "")

    def test_regler_solde_inscription_via_caissier_b_impose_le_centre_b(self):
        insc = self._inscription_validee()
        self.client.force_login(self.caissier_b)
        self.client.post(
            reverse('courses:stats_encaisser_solde_inscription', args=[insc.id]),
            {'montant_paiement': '50000', 'mode_paiement': 'espece'}, follow=True,
        )
        paiements = Paiement.objects.filter(dette__inscription=insc, annule=False)
        self.assertTrue(paiements.exists())
        for p in paiements:
            self.assertEqual(p.centre_encaissement, self.centre_b)

    def test_historique_du_caissier_b_affiche_le_paiement(self):
        insc = self._inscription_validee()
        dette = insc.dettes.get()
        Paiement.objects.create(
            dette=dette, montant_paiement=10000, tranche=1, cree_par=self.caissier_b,
        )
        self.client.force_login(self.caissier_b)
        resp = self.client.get(reverse('courses:paiement_historique'))
        lignes = list(resp.context['lignes'])
        self.assertEqual(len(lignes), 1)

    def test_historique_du_caissier_a_n_affiche_pas_le_paiement_encaisse_par_b(self):
        insc = self._inscription_validee()
        dette = insc.dettes.get()
        Paiement.objects.create(
            dette=dette, montant_paiement=10000, tranche=1, cree_par=self.caissier_b,
        )
        self.client.force_login(self.caissier_a)
        resp = self.client.get(reverse('courses:paiement_historique'))
        lignes = list(resp.context['lignes'])
        self.assertEqual(len(lignes), 0)

    def test_stat_globaux_attribue_l_encaisse_au_centre_b_et_le_du_au_centre_a(self):
        insc = self._inscription_validee()
        dette = insc.dettes.get()
        Paiement.objects.create(
            dette=dette, montant_paiement=10000, tranche=1, cree_par=self.caissier_b,
        )
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('courses:statistiques'))
        par_centre = {r['nom_centre']: r for r in resp.context['recouvrement_v2']}
        self.assertEqual(par_centre[self.centre.nom_centre]['total_du'], 50000)
        self.assertEqual(par_centre[self.centre.nom_centre]['encaisse'], 0)
        self.assertEqual(par_centre[self.centre_b.nom_centre]['total_du'], 0)
        self.assertEqual(par_centre[self.centre_b.nom_centre]['encaisse'], 10000)
