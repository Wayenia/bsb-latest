"""Programme « Reconversion » : parcours d'inscription par ville/pack (centre
masqué côté apprenant) et règlement intégral en une seule fois."""

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from accounts.models import Eleve, Utilisateur
from courses.models import (
    AnneeScolaire, CentreEtFiliere, CentreFormation, Dette, Filiere, Frais,
    Inscription, Paiement, Province, Region, TypeFrais,
)


class ReconversionBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        region = Region.objects.create(nom_region="Centre", chef_lieu="Ouagadougou")
        cls.prov_ouaga = Province.objects.create(region=region, nom_province="Kadiogo", chef_lieu="Ouagadougou")
        cls.prov_bobo = Province.objects.create(region=region, nom_province="Houet", chef_lieu="Bobo-Dioulasso")

        cls.centre_ouaga = CentreFormation.objects.create(nom_centre="Centre Ouaga", province=cls.prov_ouaga)
        cls.centre_bobo = CentreFormation.objects.create(nom_centre="Centre Bobo", province=cls.prov_bobo)

        cls.filiere_reconv = Filiere.objects.create(nom_filiere="Soudure — pack")
        cls.filiere_form = Filiere.objects.create(nom_filiere="Coiffure")

        cls.annee = AnneeScolaire.objects.create(libelle_anne="2025-2026")

        cls.pack = CentreEtFiliere.objects.create(
            centre=cls.centre_ouaga, filiere=cls.filiere_reconv, annee_prog=cls.annee,
            type_programme="reconversion", type_formation="continue", is_active=True, duree_jours=90,
        )
        cls.form_classique = CentreEtFiliere.objects.create(
            centre=cls.centre_ouaga, filiere=cls.filiere_form, annee_prog=cls.annee,
            type_programme="formation", type_formation="initiale", is_active=True, duree_jours=270,
        )

        tf_dossier = TypeFrais.objects.create(libelle="Frais de dossier", est_frais_de_dossier=True)
        tf_scol = TypeFrais.objects.create(libelle="Scolarité")
        Frais.objects.create(formation=cls.pack, type_frais=tf_dossier, montant=5000)
        Frais.objects.create(formation=cls.pack, type_frais=tf_scol, montant=45000)

        cls.eleve = Eleve.objects.create(
            username="eleve.reconv", nom="Traore", prenom="Awa", adresse="Ouaga", email="eleve.reconv@example.invalid",
            lieu_naissance="Ouaga", nom_pere="T", prenom_pere="P", nom_mere="M", prenom_mere="Q",
        )
        cls.staff = Utilisateur.objects.create_superuser(
            username="staff", password="x", nom="Admin", prenom="Sys", adresse="Ouaga",
            email="staff@example.invalid",
        )

    def _inscription_validee(self):
        insc = Inscription.objects.create(
            eleve=self.eleve, formation=self.pack, annee_scolaire=self.annee, statut="en_cours",
        )
        insc.statut = "valide"
        insc.save()  # signal -> crée une Dette par Frais
        return insc


class HelpersTests(ReconversionBase):
    def test_est_reconversion(self):
        self.assertTrue(self.pack.est_reconversion)
        self.assertFalse(self.form_classique.est_reconversion)

    def test_inscription_paiement_integral(self):
        insc = Inscription.objects.create(eleve=self.eleve, formation=self.pack, annee_scolaire=self.annee)
        self.assertTrue(insc.est_reconversion)
        self.assertTrue(insc.paiement_integral_obligatoire)
        insc2 = Inscription.objects.create(eleve=self.eleve, formation=self.form_classique, annee_scolaire=self.annee)
        self.assertFalse(insc2.paiement_integral_obligatoire)


class Etape1Tests(ReconversionBase):
    def test_formation_exclut_les_packs_reconversion(self):
        resp = self.client.get(reverse('courses:subscribe_selection'), {
            'annee': self.annee.id, 'type_programme': 'formation', 'centre': self.centre_ouaga.id,
        })
        ids = {c.id for c in resp.context['careers']}
        self.assertIn(self.form_classique.id, ids)
        self.assertNotIn(self.pack.id, ids)

    def test_reconversion_liste_les_villes_concernees(self):
        resp = self.client.get(reverse('courses:subscribe_selection'), {
            'annee': self.annee.id, 'type_programme': 'reconversion',
        })
        self.assertTrue(resp.context['reconversion_dispo'])
        self.assertEqual(resp.context['villes'], ["Ouagadougou"])  # pas Bobo : aucun pack là-bas

    def test_reconversion_packs_par_ville(self):
        resp = self.client.get(reverse('courses:subscribe_selection'), {
            'annee': self.annee.id, 'type_programme': 'reconversion', 'ville': 'Ouagadougou',
        })
        ids = {c.id for c in resp.context['careers']}
        self.assertEqual(ids, {self.pack.id})
        self.assertNotContains(resp, "Centre Ouaga")  # centre masqué côté apprenant

    def test_reconversion_absente_du_selecteur_si_aucun_pack(self):
        self.pack.is_active = False
        self.pack.save()
        resp = self.client.get(reverse('courses:subscribe_selection'), {'annee': self.annee.id})
        self.assertFalse(resp.context['reconversion_dispo'])


class ValidationPermissionTests(ReconversionBase):
    """La validation d'une candidature Reconversion exige la permission
    `courses.valider_inscription_reconversion` en plus de `valider_inscription`."""

    def setUp(self):
        # user_type='deps' → portée globale + `valider_inscription` (groupe DESP),
        # mais PAS `valider_inscription_reconversion` (réservé Admin/DG par défaut).
        self.agent = Utilisateur.objects.create_user(
            username="deps1", password="x", nom="D", prenom="E", adresse="Ouaga", user_type="deps",
            email="deps1@example.invalid",
        )
        self.client.force_login(self.agent)

    def _inscription_en_cours(self, formation):
        return Inscription.objects.create(
            eleve=self.eleve, formation=formation, annee_scolaire=self.annee, statut="en_cours",
        )

    def test_validation_reconversion_refusee_sans_permission(self):
        insc = self._inscription_en_cours(self.pack)
        self.client.post(reverse('bsb_admin:gerer_subscription', args=[insc.id]), {'action': 'valide'})
        insc.refresh_from_db()
        self.assertEqual(insc.statut, "en_cours")

    def test_validation_formation_classique_reste_permise(self):
        insc = self._inscription_en_cours(self.form_classique)
        self.client.post(reverse('bsb_admin:gerer_subscription', args=[insc.id]), {'action': 'valide'})
        insc.refresh_from_db()
        self.assertEqual(insc.statut, "valide")

    def test_validation_reconversion_ok_avec_permission(self):
        self.agent.user_permissions.add(
            Permission.objects.get(codename='valider_inscription_reconversion')
        )
        agent = Utilisateur.objects.get(pk=self.agent.pk)  # vide le cache de perms
        self.client.force_login(agent)
        insc = self._inscription_en_cours(self.pack)
        self.client.post(reverse('bsb_admin:gerer_subscription', args=[insc.id]), {'action': 'valide'})
        insc.refresh_from_db()
        self.assertEqual(insc.statut, "valide")

    def test_admin_a_la_permission_par_defaut(self):
        admin = Utilisateur.objects.create_user(
            username="adm1", password="x", nom="A", prenom="D", adresse="Ouaga", user_type="admin",
            email="adm1@example.invalid",
        )
        self.assertTrue(admin.has_perm('courses.valider_inscription_reconversion'))


class EncaissementTests(ReconversionBase):
    def setUp(self):
        self.client.force_login(self.staff)

    def test_page_dettes_eleve_se_rend_pour_reconversion(self):
        insc = self._inscription_validee()
        resp = self.client.get(
            reverse('courses:stats_dettes_eleve', args=[self.eleve.id]) + f"?inscription={insc.id}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Régler l'inscription")
        self.assertNotContains(resp, "Solder ce frais")
        # Après règlement intégral : bouton de quittance groupée.
        self.client.post(
            reverse('courses:stats_encaisser_solde_inscription', args=[insc.id]),
            {'montant_paiement': '50000', 'mode_paiement': 'espece'},
        )
        resp = self.client.get(reverse('courses:stats_dettes_eleve', args=[self.eleve.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Télécharger la quittance")

    def test_liste_paiement_se_rend_pour_reconversion(self):
        self._inscription_validee()
        # Superuser => vue en accordéon : ouvrir le centre pour voir les modales.
        resp = self.client.get(reverse('courses:paiement_list'), {'centre': self.centre_ouaga.id})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Inscription Reconversion")

    def test_solde_dette_refuse_pour_reconversion(self):
        insc = self._inscription_validee()
        dette = insc.dettes.first()
        resp = self.client.post(
            reverse('courses:stats_encaisser_solde_dette', args=[dette.id]),
            {'montant_paiement': '5000', 'mode_paiement': 'espece'},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Paiement.objects.count(), 0)

    def test_solde_inscription_exige_le_total_exact(self):
        insc = self._inscription_validee()
        url = reverse('courses:stats_encaisser_solde_inscription', args=[insc.id])

        # Montant partiel -> refusé, aucun paiement.
        self.client.post(url, {'montant_paiement': '10000', 'mode_paiement': 'espece'})
        self.assertEqual(Paiement.objects.count(), 0)

        # Montant exact (5000 + 45000) -> encaissé, dettes soldées.
        self.client.post(url, {'montant_paiement': '50000', 'mode_paiement': 'espece'})
        self.assertEqual(sum(p.montant_paiement for p in Paiement.objects.all()), 50000)
        for dette in insc.dettes.all():
            self.assertEqual(dette.reste_a_payer(), 0)

    def test_quittance_groupee_disponible_apres_reglement(self):
        insc = self._inscription_validee()
        self.client.post(
            reverse('courses:stats_encaisser_solde_inscription', args=[insc.id]),
            {'montant_paiement': '50000', 'mode_paiement': 'espece'},
        )
        groupe_id = Paiement.objects.first().groupe_id
        self.assertIsNotNone(groupe_id)
        resp = self.client.get(
            reverse('courses:stats_download_quittance_groupe', args=[groupe_id])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
