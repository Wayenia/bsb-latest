"""Niveaux d'études : BEPC, BAC et Master ajoutés comme des codes à part
entière, Maîtrise revenue à son libellé d'origine — une seule liste source
(Eleve.NIVEAU_SCOLAIRE_CHOICES) alimente tous les formulaires et le filtre
« Niveau d'études » de stat-globaux, donc rien à dupliquer ailleurs."""

from django.test import TestCase

from accounts.models import Eleve


class NiveauScolaireChoicesTests(TestCase):
    def _libelle(self, code):
        return dict(Eleve.NIVEAU_SCOLAIRE_CHOICES)[code]

    def test_bepc_bac_master_presents(self):
        codes = dict(Eleve.NIVEAU_SCOLAIRE_CHOICES)
        self.assertEqual(codes['bepc'], 'BEPC')
        self.assertEqual(codes['bac'], 'BAC')
        self.assertEqual(codes['master'], 'Master')

    def test_maitrise_a_retrouve_son_libelle(self):
        self.assertEqual(self._libelle('maitrise'), 'Maîtrise')

    def test_maitrise_et_master_sont_deux_codes_distincts(self):
        codes = dict(Eleve.NIVEAU_SCOLAIRE_CHOICES)
        self.assertIn('maitrise', codes)
        self.assertIn('master', codes)
        self.assertNotEqual(codes['maitrise'], codes['master'])
