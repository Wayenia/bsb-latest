from django.test import TestCase

from courses.forms import FraisForm, PersonalInfoForm
from courses.models import TypeFrais

_BASE = {
    'nom': 'OUEDRAOGO', 'prenom': 'Ali', 'sexe': 'M',
    'tel': '+22670000000', 'date_naissance': '2000-01-01',
    'lieu_naissance': 'Ouagadougou', 'niveau_scolaire': '3e',
}


class PersonalInfoFormTests(TestCase):
    def test_personne_a_contacter_optionnelle(self):
        """« Type de personne à contacter » n'est plus obligatoire : le
        formulaire (donc le bouton « Suivant ») passe sans elle."""
        form = PersonalInfoForm(data=dict(_BASE, type_personne_contact=''))
        self.assertTrue(form.is_valid(), form.errors)

    def test_parent_choisi_exige_ses_champs(self):
        form = PersonalInfoForm(data=dict(_BASE, type_personne_contact='parent'))
        self.assertFalse(form.is_valid())
        self.assertIn('nom_personne', form.errors)


class FraisFormTests(TestCase):
    """Frais.formation est devenu blank=True au niveau modele pour permettre
    les frais d'hebergement (formation=None, hebergement rempli — cf.
    contrainte frais_formation_xor_hebergement). Le formulaire de frais
    « classique » (hors formset hebergement) doit garder ce champ obligatoire,
    sinon la sauvegarde declenche un IntegrityError non rattrape (formation
    et hebergement tous deux nuls)."""

    def test_formation_reste_obligatoire(self):
        tf = TypeFrais.objects.create(libelle="Scolarité")
        form = FraisForm(data={'formation': '', 'type_frais': tf.id, 'montant': '50000'})
        self.assertFalse(form.is_valid())
        self.assertIn('formation', form.errors)
