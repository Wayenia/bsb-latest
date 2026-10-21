"""Le filtre « Statut inscription » (stat-globaux et historique des
paiements) ne doit plus proposer « Validé et payé » (valide_paye) :
Inscription.statut ne prend jamais cette valeur — il reste "valide" quel
que soit l'avancement du paiement (voir Inscription.libelle_statut_paiement)
— donc ce choix ne retournait jamais aucun résultat. Le filtre "Statut de
paiement" est le bon outil pour ça."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import Utilisateur
from courses.models import Inscription
from courses.tests_hebergement import HebergementBase


class FiltreStatutMortTests(HebergementBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.insc = cls._inscription_validee(cls)

    def test_valide_paye_n_est_jamais_stocke(self):
        """Confirme la prémisse du bug : aucune inscription, même validée et
        totalement payée, ne porte jamais ce statut en base."""
        self.assertEqual(
            Inscription.objects.filter(statut='valide_paye').count(), 0,
        )
        self.assertTrue(
            Inscription.objects.filter(statut='valide').exists(),
        )

    def test_option_valide_paye_absente_des_pages(self):
        self.client.force_login(self.staff)
        for url_name in ('courses:statistiques', 'courses:paiement_historique'):
            html = self.client.get(reverse(url_name)).content.decode()
            self.assertNotIn('value="valide_paye"', html, url_name)
