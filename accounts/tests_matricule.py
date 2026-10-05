"""Matricules : numéros croissants par année, jamais réattribués (même après
suppression d'un apprenant), sans collision avec un matricule existant."""

from django.test import TestCase
from django.utils import timezone

from accounts.models import CompteurMatricule, Eleve


def _eleve(nom):
    return Eleve.objects.create(
        username=f"mat.{nom}", nom=nom, prenom="Test", adresse="Ouaga",
        email=f"mat.{nom}@example.invalid", lieu_naissance=f"Ville{nom}",
        nom_pere="T", prenom_pere="P", nom_mere="M", prenom_mere="Q",
        type_document="extrait_naissance", numero_document=f"N-{nom}",
    )


class MatriculeTests(TestCase):
    def setUp(self):
        self.annee = timezone.now().year
        self.prefixe = f"BSB{self.annee}"

    def test_numeros_croissants(self):
        a, b = _eleve("aaa"), _eleve("bbb")
        self.assertEqual(a.matricule, f"{self.prefixe}000001")
        self.assertEqual(b.matricule, f"{self.prefixe}000002")

    def test_numero_non_reattribue_apres_suppression(self):
        _eleve("aaa")
        dernier = _eleve("bbb")
        dernier.delete()
        nouveau = _eleve("ccc")
        self.assertEqual(nouveau.matricule, f"{self.prefixe}000003")

    def test_pas_de_collision_avec_un_matricule_existant(self):
        from accounts.models import Utilisateur
        CompteurMatricule.objects.filter(annee=self.annee).delete()
        Utilisateur.objects.create(
            username="manuel", nom="M", prenom="M", adresse="x",
            email="manuel@example.invalid", matricule=f"{self.prefixe}000001",
        )
        nouveau = _eleve("ddd")
        self.assertNotEqual(nouveau.matricule, f"{self.prefixe}000001")
