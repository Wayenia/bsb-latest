"""numero_identifiant (Eleve) : detection de doublon a la creation ET quand
les champs d'identite (date_naissance, lieu_naissance, type_document,
numero_document, date_etablissement_document) sont modifies ensuite — par
exemple par un agent via EleveForm (back-office), qui ne verrouille pas ces
champs contrairement a ProfilEleveForm cote apprenant."""

from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import Eleve, Utilisateur


def _identite(**overrides):
    base = dict(
        nom="Ouedraogo", prenom="Fatou", adresse="Ouaga",
        lieu_naissance="Ouagadougou", date_naissance=date(2005, 3, 12),
        type_document="extrait_naissance", numero_document="EN-001",
        date_etablissement_document=date(2020, 1, 10),
        nom_pere="T", prenom_pere="P", nom_mere="M", prenom_mere="Q",
    )
    base.update(overrides)
    return base


class NumeroIdentifiantCreationTests(TestCase):
    def test_deux_identites_identiques_refusees_a_la_creation(self):
        Eleve.objects.create(username="e1", email="e1@example.invalid", **_identite())
        with self.assertRaises(ValidationError):
            Eleve.objects.create(username="e2", email="e2@example.invalid", **_identite())

    def test_identites_differentes_autorisees(self):
        Eleve.objects.create(username="e1", email="e1@example.invalid", **_identite())
        # Ne devrait pas lever : lieu de naissance different.
        Eleve.objects.create(
            username="e2", email="e2@example.invalid",
            **_identite(lieu_naissance="Bobo-Dioulasso"),
        )
        self.assertEqual(Eleve.objects.count(), 2)


class NumeroIdentifiantEditionTests(TestCase):
    """Le vrai trou corrige : editer date_naissance/lieu_naissance apres coup
    (ex. EleveForm cote agent) doit redeclencher la detection de doublon."""

    def test_modifier_lieu_naissance_vers_un_doublon_est_refuse(self):
        Eleve.objects.create(username="e1", email="e1@example.invalid", **_identite())
        e2 = Eleve.objects.create(
            username="e2", email="e2@example.invalid",
            **_identite(lieu_naissance="Bobo-Dioulasso"),
        )
        e2.lieu_naissance = "Ouagadougou"  # convergerait vers l'identite de e1
        with self.assertRaises(ValidationError):
            e2.save()

    def test_modifier_date_naissance_vers_un_doublon_est_refuse(self):
        Eleve.objects.create(username="e1", email="e1@example.invalid", **_identite())
        e2 = Eleve.objects.create(
            username="e2", email="e2@example.invalid",
            **_identite(date_naissance=date(2006, 5, 20)),
        )
        e2.date_naissance = date(2005, 3, 12)  # convergerait vers l'identite de e1
        with self.assertRaises(ValidationError):
            e2.save()

    def test_modifier_un_champ_sans_rapport_ne_redeclenche_pas_le_controle(self):
        e1 = Eleve.objects.create(username="e1", email="e1@example.invalid", **_identite())
        identifiant_avant = e1.numero_identifiant
        e1.adresse = "Nouvelle adresse"
        e1.save()
        e1.refresh_from_db()
        self.assertEqual(e1.numero_identifiant, identifiant_avant)

    def test_modifier_legitimement_son_propre_lieu_naissance_fonctionne(self):
        e1 = Eleve.objects.create(username="e1", email="e1@example.invalid", **_identite())
        ancien_identifiant = e1.numero_identifiant
        e1.lieu_naissance = "Koudougou"
        e1.save()
        e1.refresh_from_db()
        self.assertNotEqual(e1.numero_identifiant, ancien_identifiant)
        self.assertIn("KOUDOUGOU", e1.numero_identifiant)


class EleveUpdateViewCollisionTests(TestCase):
    """Le doublon detecte par Eleve.save() lors d'une modification (voir
    ci-dessus) doit remonter comme une erreur de formulaire normale sur
    /bsb/eleves/<id>/modifier, pas comme une page 500 — eleve_update()
    n'attrapait pas ValidationError avant ce correctif."""

    def setUp(self):
        self.staff = Utilisateur.objects.create_superuser(
            username="staff.eleve", password="x", nom="Admin", prenom="Sys",
            email="staff.eleve@example.invalid",
        )

    def _post_data(self, eleve, **overrides):
        data = {
            'nom': eleve.nom, 'prenom': eleve.prenom, 'username': eleve.username,
            'email': eleve.email, 'tel': '', 'sexe': 'm',
            'date_naissance': eleve.date_naissance.isoformat() if eleve.date_naissance else '',
            'adresse': eleve.adresse or '', 'lieu_naissance': eleve.lieu_naissance or '',
            'nationalite': '', 'niveau_scolaire': '', 'password': '',
        }
        data.update(overrides)
        return data

    def test_collision_a_la_modification_naffiche_pas_une_erreur_500(self):
        e1 = Eleve.objects.create(username="e1", email="e1@example.invalid", **_identite())
        e2 = Eleve.objects.create(
            username="e2", email="e2@example.invalid",
            **_identite(lieu_naissance="Bobo-Dioulasso"),
        )
        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse('bsb_admin:eleve_update', args=[e2.id]),
            self._post_data(e2, lieu_naissance="Ouagadougou"),  # convergerait vers e1
        )
        self.assertEqual(resp.status_code, 200)  # formulaire re-affiche, pas un crash
        e2.refresh_from_db()
        self.assertEqual(e2.lieu_naissance, "Bobo-Dioulasso")  # non modifie

    def test_modification_legitime_fonctionne_toujours(self):
        e1 = Eleve.objects.create(username="e1", email="e1@example.invalid", **_identite())
        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse('bsb_admin:eleve_update', args=[e1.id]),
            self._post_data(e1, lieu_naissance="Koudougou"),
        )
        self.assertEqual(resp.status_code, 302)
        e1.refresh_from_db()
        self.assertEqual(e1.lieu_naissance, "Koudougou")
