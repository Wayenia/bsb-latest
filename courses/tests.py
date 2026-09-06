from django.test import TestCase

from courses.forms import PersonalInfoForm

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
