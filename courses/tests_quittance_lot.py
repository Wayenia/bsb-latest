"""Règlement de l'inscription en une seule action : plusieurs types de frais,
avec ou sans tranches (Frais A à 2 tranches, Frais 2 à 3, Frais 3 à 1,
Frais 4 sans tranche) → une seule quittance, côté apprenant et côté agent."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from courses.models import Frais, Paiement, TrancheFrais, TypeFrais
from courses.tests_hebergement import HebergementBase


class QuittanceLotInscriptionTests(HebergementBase):
    def _tranches(self, libelle, pourcentages, montant):
        """pourcentages : liste dont la somme doit faire 100 (sinon un reliquat reste dû)."""
        tf = TypeFrais.objects.create(libelle=libelle)
        for i, pct in enumerate(pourcentages, 1):
            TrancheFrais.objects.create(
                type_frais=tf, libelle=f"{libelle} t{i}", ordre=i,
                pourcentage=Decimal(str(pct)), est_primordiale=False,
            )
        Frais.objects.create(formation=self.metier, type_frais=tf, montant=montant)

    def test_quatre_frais_un_paiement_une_seule_quittance(self):
        self._tranches("Frais A", [50, 50], 20000)
        self._tranches("Frais 2", [34, 33, 33], 30000)  # somme = 100
        self._tranches("Frais 3", [100], 10000)
        self._tranches("Frais 4", [], 5000)  # sans tranche
        insc = self._inscription_validee()  # + Scolarité 50 000 déjà présente
        total = 50000 + 20000 + 30000 + 10000 + 5000

        self.client.force_login(self.staff)
        self.client.post(
            reverse('courses:stats_encaisser_solde_inscription', args=[insc.id]),
            {'montant_paiement': str(total), 'mode_paiement': 'espece'}, follow=True,
        )

        paiements = Paiement.objects.filter(dette__inscription=insc, annule=False)
        self.assertEqual(sum(p.montant_paiement for p in paiements), total)
        self.assertEqual(len(set(paiements.values_list('groupe_id', flat=True))), 1)
        self.assertEqual(len(set(paiements.values_list('numero_quittance', flat=True))), 1)

        # Côté apprenant : une seule ligne, téléchargeable en quittance groupée.
        self.client.force_login(self.eleve)
        mes = self.client.get(reverse('courses:mes_paiements'))
        items = list(mes.context['paiements'])
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].get('groupe'))
        groupe = items[0]['groupe_id']
        dl = self.client.get(reverse('courses:stats_download_quittance_groupe', args=[groupe]))
        self.assertEqual(dl.status_code, 200)

        # Côté agent : l'historique regroupe aussi le lot en une seule ligne.
        self.client.force_login(self.staff)
        hist = self.client.get(reverse('courses:paiement_historique'))
        lignes_du_lot = [l for l in hist.context['lignes'] if l['principal'].groupe_id == groupe]
        self.assertEqual(len(lignes_du_lot), 1)


class QuittanceLotDetailDetteTests(HebergementBase):
    """Sur la page de détail d'un type de frais, un paiement qui couvre
    plusieurs types de frais doit pointer vers la même quittance de lot pour
    chacun, pas vers une quittance par tranche différente."""

    def test_detail_dette_pointe_vers_la_quittance_du_lot(self):
        from django.urls import reverse as r
        tf = TypeFrais.objects.create(libelle="Frais B")
        Frais.objects.create(formation=self.metier, type_frais=tf, montant=10000)
        insc = self._inscription_validee()  # Scolarité 50 000 + Frais B 10 000

        self.client.force_login(self.staff)
        self.client.post(
            r('courses:stats_encaisser_solde_inscription', args=[insc.id]),
            {'montant_paiement': '60000', 'mode_paiement': 'espece'}, follow=True,
        )
        groupe = Paiement.objects.filter(dette__inscription=insc).first().groupe_id

        for dette in insc.dettes.all():
            html = self.client.get(r('courses:stats_detail_dette', args=[dette.id])).content.decode()
            self.assertIn(r('courses:stats_download_quittance_groupe', args=[groupe]), html)
            self.assertNotIn(r('courses:stats_quittance_tranche', args=[dette.id, 1]), html)
