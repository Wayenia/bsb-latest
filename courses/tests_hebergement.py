"""Hébergement : offre côté administration, demande côté apprenant, validation
et génération de dette, encaissement/quittance réutilisés depuis la scolarité."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import Eleve, Utilisateur
from courses.forms import HebergementForm
from courses.models import (
    AnneeScolaire, CentreEtFiliere, CentreFormation, DemandeHebergement, Dette,
    Filiere, Frais, Hebergement, Inscription, Paiement, Province, Region, TypeFrais,
)


class HebergementBase(TestCase):
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

        cls.tf_heb = TypeFrais.objects.create(libelle="Hébergement")

        cls.eleve = Eleve.objects.create(
            username="eleve.heb", nom="Ouedraogo", prenom="Fatou", adresse="Ouaga",
            email="eleve.heb@example.invalid", lieu_naissance="Ouaga",
            nom_pere="T", prenom_pere="P", nom_mere="M", prenom_mere="Q",
        )
        cls.staff = Utilisateur.objects.create_superuser(
            username="staff.heb", password="x", nom="Admin", prenom="Sys", adresse="Ouaga",
            email="staff.heb@example.invalid",
        )

    def _inscription_validee(self):
        insc = Inscription.objects.create(
            eleve=self.eleve, formation=self.metier, annee_scolaire=self.annee, statut="en_cours",
        )
        insc.statut = "valide"
        insc.save()  # signal -> crée une Dette pour le frais de scolarité
        return insc

    def _hebergement(self, nombre_places=2, metiers=None):
        heb = Hebergement.objects.create(
            centre=self.centre, annee_scolaire=self.annee, nombre_places=nombre_places,
            statut="actif", cree_par=self.staff,
        )
        if metiers:
            heb.metiers.set(metiers)
        Frais.objects.create(hebergement=heb, type_frais=self.tf_heb, montant=20000)
        return heb


class FraisConstraintTests(HebergementBase):
    def test_frais_generalise_str(self):
        heb = self._hebergement()
        frais = heb.frais.get()
        self.assertIn("Hébergement", str(frais))

    def test_hebergement_places(self):
        heb = self._hebergement(nombre_places=1)
        self.assertEqual(heb.places_disponibles, 1)
        self.assertFalse(heb.complet)


class HebergementFormOverlapTests(HebergementBase):
    """Deux hébergements actifs qui se chevauchent (même centre/année, au
    moins un métier en commun) rendraient le choix arbitraire côté
    my_subscriptions (.first() sans ordre garanti) — le formulaire doit
    refuser ce chevauchement à la création comme à la modification."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        autre_filiere = Filiere.objects.create(nom_filiere="Menuiserie")
        cls.metier2 = CentreEtFiliere.objects.create(
            centre=cls.centre, filiere=autre_filiere, annee_prog=cls.annee,
            type_programme="formation", type_formation="continue", is_active=True, duree_jours=90,
        )

    def _data(self, metiers=None, statut='actif', nombre_places=10):
        return {
            'centre': self.centre.id,
            'annee_scolaire': self.annee.id,
            'nombre_places': nombre_places,
            'statut': statut,
            'metiers': [m.id for m in metiers] if metiers else [],
        }

    def test_second_hebergement_ouvert_a_tous_refuse_si_le_premier_existe(self):
        self._hebergement()  # actif, metiers vide = ouvert a tous
        form = HebergementForm(data=self._data())
        self.assertFalse(form.is_valid())
        message = str(form.non_field_errors())
        self.assertIn("chevauche", message)
        self.assertIn(self.centre.nom_centre, message)
        self.assertIn("tous les métiers du centre", message)

    def test_second_hebergement_metier_specifique_refuse_si_le_premier_couvre_tout(self):
        self._hebergement()  # metiers vide = ouvre a tous les metiers du centre
        form = HebergementForm(data=self._data(metiers=[self.metier]))
        self.assertFalse(form.is_valid())
        message = str(form.non_field_errors())
        self.assertIn(self.centre.nom_centre, message)
        self.assertIn(self.filiere.nom_filiere, message)

    def test_deux_hebergements_metiers_disjoints_autorises(self):
        self._hebergement(metiers=[self.metier])
        form = HebergementForm(data=self._data(metiers=[self.metier2]))
        self.assertTrue(form.is_valid(), form.errors)

    def test_message_ne_cite_que_le_metier_en_commun(self):
        # Premier hebergement : metier + metier2. Second : uniquement metier2.
        # Seul metier2 est en conflit, metier ne doit pas apparaitre dans le message.
        self._hebergement(metiers=[self.metier, self.metier2])
        form = HebergementForm(data=self._data(metiers=[self.metier2]))
        self.assertFalse(form.is_valid())
        message = str(form.non_field_errors())
        self.assertIn(self.metier2.filiere.nom_filiere, message)
        self.assertNotIn(self.metier.filiere.nom_filiere, message)

    def test_hebergement_inactif_nautorise_pas_le_chevauchement_a_ignorer(self):
        self._hebergement()  # actif
        # Creer le second en inactif : pas de conflit tant qu'il n'est pas actif.
        form = HebergementForm(data=self._data(statut='inactif'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_modifier_son_propre_hebergement_ne_se_bloque_pas_lui_meme(self):
        heb = self._hebergement()
        form = HebergementForm(data=self._data(), instance=heb)
        self.assertTrue(form.is_valid(), form.errors)

    def test_case_metiers_affiche_seulement_le_metier_pas_le_centre(self):
        form = HebergementForm(data=self._data(metiers=[self.metier]))
        choix = list(form.fields['metiers'].choices)
        labels = [label for _, label in choix]
        self.assertIn(self.filiere.nom_filiere, labels)
        self.assertNotIn(self.centre.nom_centre, "".join(labels))


class DashboardButtonTests(HebergementBase):
    def test_bouton_affiche_a_cote_de_deposer_candidature(self):
        self._inscription_validee()
        self._hebergement()
        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:student_dashboard'))
        self.assertContains(resp, "Demande d'hébergement")
        self.assertContains(resp, "Déposer ma candidature")

    def test_bouton_absent_si_aucun_hebergement_disponible(self):
        self._inscription_validee()
        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:student_dashboard'))
        self.assertNotContains(resp, "Demande d'hébergement")
        self.assertContains(resp, "Déposer ma candidature")

    def test_bouton_absent_si_demande_deja_soumise(self):
        insc = self._inscription_validee()
        heb = self._hebergement()
        DemandeHebergement.objects.create(hebergement=heb, inscription=insc)
        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:student_dashboard'))
        self.assertNotContains(resp, "Demande d'hébergement")


class MySubscriptionsButtonTests(HebergementBase):
    def test_bouton_affiche_si_hebergement_ouvert_a_tous(self):
        insc = self._inscription_validee()
        self._hebergement()  # metiers vide = ouvert à tous
        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:my_subscriptions'))
        self.assertContains(resp, "Demande d'hébergement")

    def test_pas_de_bouton_si_metier_non_eligible(self):
        insc = self._inscription_validee()
        autre_filiere = Filiere.objects.create(nom_filiere="Menuiserie")
        autre_metier = CentreEtFiliere.objects.create(
            centre=self.centre, filiere=autre_filiere, annee_prog=self.annee,
            type_programme="formation", type_formation="continue", is_active=True, duree_jours=90,
        )
        self._hebergement(metiers=[autre_metier])
        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:my_subscriptions'))
        self.assertNotContains(resp, "Demande d'hébergement")

    def test_pas_de_bouton_si_dossier_non_valide(self):
        insc = Inscription.objects.create(
            eleve=self.eleve, formation=self.metier, annee_scolaire=self.annee, statut="en_cours",
        )
        self._hebergement()
        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:my_subscriptions'))
        self.assertNotContains(resp, "Demande d'hébergement")


class DemandeBriefTests(HebergementBase):
    def test_get_brief(self):
        insc = self._inscription_validee()
        heb = self._hebergement()
        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:demande_hebergement_brief', args=[heb.id, insc.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Confirmer ma demande")

    def test_post_brief_cree_la_demande(self):
        insc = self._inscription_validee()
        heb = self._hebergement()
        self.client.force_login(self.eleve)
        resp = self.client.post(reverse('courses:demande_hebergement_brief', args=[heb.id, insc.id]), follow=True)
        self.assertTrue(DemandeHebergement.objects.filter(hebergement=heb, inscription=insc).exists())
        self.assertContains(resp, "soumise avec succès")

    def test_404_si_autre_centre(self):
        insc = self._inscription_validee()
        autre_centre = CentreFormation.objects.create(nom_centre="Autre Centre", province=self.province)
        heb = Hebergement.objects.create(
            centre=autre_centre, annee_scolaire=self.annee, nombre_places=1, statut="actif",
        )
        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:demande_hebergement_brief', args=[heb.id, insc.id]))
        self.assertEqual(resp.status_code, 404)

    def test_complet_bloque_la_soumission(self):
        insc = self._inscription_validee()
        heb = self._hebergement(nombre_places=1)
        # Une autre inscription valide déjà occuper l'unique place.
        autre_eleve = Eleve.objects.create(
            username="eleve.heb2", nom="Sawadogo", prenom="Awa", adresse="Ouaga",
            email="eleve.heb2@example.invalid", lieu_naissance="Bobo",
            nom_pere="X", prenom_pere="Y", nom_mere="Z", prenom_mere="W",
        )
        autre_insc = Inscription.objects.create(
            eleve=autre_eleve, formation=self.metier, annee_scolaire=self.annee, statut="valide",
        )
        DemandeHebergement.objects.create(hebergement=heb, inscription=autre_insc, statut="validee")
        self.assertTrue(heb.complet)

        self.client.force_login(self.eleve)
        resp = self.client.post(reverse('courses:demande_hebergement_brief', args=[heb.id, insc.id]), follow=True)
        self.assertFalse(DemandeHebergement.objects.filter(hebergement=heb, inscription=insc).exists())
        self.assertContains(resp, "complet")


class ValidationEtDetteTests(HebergementBase):
    def setUp(self):
        self.staff.user_permissions.clear()

    def test_validation_genere_une_dette_et_notifie(self):
        insc = self._inscription_validee()
        heb = self._hebergement()
        demande = DemandeHebergement.objects.create(hebergement=heb, inscription=insc)

        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande.id]),
            {'action': 'valider'}, follow=True,
        )
        demande.refresh_from_db()
        self.assertEqual(demande.statut, 'validee')
        self.assertTrue(
            Dette.objects.filter(inscription=insc, frais_formation__hebergement=heb).exists()
        )

    def test_rejet_exige_un_motif(self):
        insc = self._inscription_validee()
        heb = self._hebergement()
        demande = DemandeHebergement.objects.create(hebergement=heb, inscription=insc)

        self.client.force_login(self.staff)
        self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande.id]),
            {'action': 'rejeter', 'motif_rejet': ''}, follow=True,
        )
        demande.refresh_from_db()
        self.assertEqual(demande.statut, 'en_attente')

        self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande.id]),
            {'action': 'rejeter', 'motif_rejet': 'Plus de place'}, follow=True,
        )
        demande.refresh_from_db()
        self.assertEqual(demande.statut, 'rejetee')
        self.assertEqual(demande.motif_rejet, 'Plus de place')

    def test_ne_depasse_pas_nombre_places_meme_avec_demandes_concurrentes(self):
        """Deux demandes en attente sur un hebergement a une seule place :
        valider la premiere doit reussir, valider la seconde ensuite doit
        echouer proprement (complet) plutot que de depasser nombre_places —
        couvre la relecture sous verrou (select_for_update) dans la branche
        'valider', pas seulement le controle fait avant la transaction."""
        heb = self._hebergement(nombre_places=1)
        insc1 = self._inscription_validee()
        autre_eleve = Eleve.objects.create(
            username="eleve.heb.conc", nom="Kabore", prenom="Awa", adresse="Ouaga",
            email="eleve.heb.conc@example.invalid", lieu_naissance="Koudougou",
            nom_pere="X", prenom_pere="Y", nom_mere="Z", prenom_mere="W",
        )
        insc2 = Inscription.objects.create(
            eleve=autre_eleve, formation=self.metier, annee_scolaire=self.annee, statut="valide",
        )
        demande1 = DemandeHebergement.objects.create(hebergement=heb, inscription=insc1)
        demande2 = DemandeHebergement.objects.create(hebergement=heb, inscription=insc2)

        self.client.force_login(self.staff)
        self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande1.id]),
            {'action': 'valider'}, follow=True,
        )
        resp = self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande2.id]),
            {'action': 'valider'}, follow=True,
        )

        demande1.refresh_from_db()
        demande2.refresh_from_db()
        self.assertEqual(demande1.statut, 'validee')
        self.assertEqual(demande2.statut, 'en_attente')  # refusee, pas de depassement
        self.assertContains(resp, "complet")
        self.assertFalse(
            Dette.objects.filter(inscription=insc2, frais_formation__hebergement=heb).exists()
        )


class RecepisseHebergementTests(HebergementBase):
    def test_telechargement_apres_validation(self):
        insc = self._inscription_validee()
        heb = self._hebergement()
        demande = DemandeHebergement.objects.create(hebergement=heb, inscription=insc)
        self.client.force_login(self.staff)
        self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande.id]),
            {'action': 'valider'}, follow=True,
        )
        demande.refresh_from_db()

        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:telecharger_recepisse_hebergement', args=[demande.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_telechargement_apres_rejet(self):
        insc = self._inscription_validee()
        heb = self._hebergement()
        demande = DemandeHebergement.objects.create(hebergement=heb, inscription=insc)
        self.client.force_login(self.staff)
        self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande.id]),
            {'action': 'rejeter', 'motif_rejet': 'Complet'}, follow=True,
        )
        demande.refresh_from_db()

        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:telecharger_recepisse_hebergement', args=[demande.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_refuse_tant_que_en_attente(self):
        insc = self._inscription_validee()
        heb = self._hebergement()
        demande = DemandeHebergement.objects.create(hebergement=heb, inscription=insc)

        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:telecharger_recepisse_hebergement', args=[demande.id]), follow=True)
        self.assertNotEqual(resp.get('Content-Type'), 'application/pdf')

    def test_refuse_pour_un_autre_apprenant(self):
        insc = self._inscription_validee()
        heb = self._hebergement()
        demande = DemandeHebergement.objects.create(hebergement=heb, inscription=insc, statut='validee')
        autre_eleve = Eleve.objects.create(
            username="eleve.heb4", nom="Ouattara", prenom="Ali", adresse="Ouaga",
            email="eleve.heb4@example.invalid", lieu_naissance="Bobo",
            nom_pere="X", prenom_pere="Y", nom_mere="Z", prenom_mere="W",
        )
        self.client.force_login(autre_eleve)
        resp = self.client.get(reverse('courses:telecharger_recepisse_hebergement', args=[demande.id]), follow=True)
        self.assertNotEqual(resp.get('Content-Type'), 'application/pdf')


class NotificationTests(HebergementBase):
    def test_demande_validee_apparait_en_notification(self):
        insc = self._inscription_validee()
        heb = self._hebergement()
        demande = DemandeHebergement.objects.create(hebergement=heb, inscription=insc)
        self.client.force_login(self.staff)
        self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande.id]),
            {'action': 'valider'}, follow=True,
        )

        self.client.force_login(self.eleve)

        count_resp = self.client.get(reverse('courses:notifications_count'))
        self.assertGreaterEqual(count_resp.json()['count'], 1)

        resp = self.client.get(reverse('courses:notifications'))
        self.assertContains(resp, "Hébergement validé")

        # Après consultation de la page, le compteur ne compte plus cette demande.
        count_resp = self.client.get(reverse('courses:notifications_count'))
        self.assertEqual(count_resp.json()['count'], 0)

    def test_demande_rejetee_apparait_en_notification(self):
        insc = self._inscription_validee()
        heb = self._hebergement()
        demande = DemandeHebergement.objects.create(hebergement=heb, inscription=insc)
        self.client.force_login(self.staff)
        self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande.id]),
            {'action': 'rejeter', 'motif_rejet': 'Complet'}, follow=True,
        )

        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:notifications'))
        self.assertContains(resp, "Hébergement rejeté")
        self.assertContains(resp, "Complet")


class ScolariteEleveVoitLePaiementTests(HebergementBase):
    def test_paiement_hebergement_visible_cote_eleve(self):
        insc = self._inscription_validee()
        heb = self._hebergement()
        demande = DemandeHebergement.objects.create(hebergement=heb, inscription=insc)
        self.client.force_login(self.staff)
        self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande.id]),
            {'action': 'valider'}, follow=True,
        )
        dette_heb = Dette.objects.get(inscription=insc, frais_formation__hebergement=heb)
        paiement = Paiement.objects.create(
            dette=dette_heb, montant_paiement=20000, tranche=1, effectue_par=self.staff,
        )

        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:mes_paiements'))
        self.assertEqual(resp.status_code, 200)
        items = list(resp.context['paiements'])
        self.assertIn(paiement, [it['p'] for it in items if not it['groupe']])

        quittance_resp = self.client.get(reverse('courses:quittance', args=[paiement.id]))
        self.assertEqual(quittance_resp.status_code, 200)
        self.assertEqual(quittance_resp['Content-Type'], 'application/pdf')


class EncaisserHebergementListTests(HebergementBase):
    def test_seules_les_inscriptions_avec_dette_hebergement_apparaissent(self):
        insc = self._inscription_validee()
        heb = self._hebergement()
        demande = DemandeHebergement.objects.create(hebergement=heb, inscription=insc)
        self.client.force_login(self.staff)
        self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande.id]),
            {'action': 'valider'}, follow=True,
        )

        # Une deuxième inscription valide, sans demande d'hébergement, ne doit
        # pas apparaître sur cet écran même si elle a un reste de scolarité.
        autre_eleve = Eleve.objects.create(
            username="eleve.heb3", nom="Kabore", prenom="Awa", adresse="Ouaga",
            email="eleve.heb3@example.invalid", lieu_naissance="Koudougou",
            nom_pere="A", prenom_pere="B", nom_mere="C", prenom_mere="D",
        )
        Inscription.objects.create(
            eleve=autre_eleve, formation=self.metier, annee_scolaire=self.annee, statut="valide",
        )

        resp = self.client.get(reverse('courses:hebergement_paiement_list'), {'centre': self.centre.id})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Ouedraogo")
        self.assertNotContains(resp, "Kabore")

    def test_totaux_scoped_a_lhebergement(self):
        insc = self._inscription_validee()  # dette scolarité 50000
        heb = self._hebergement()  # dette hébergement 20000
        demande = DemandeHebergement.objects.create(hebergement=heb, inscription=insc)
        self.client.force_login(self.staff)
        self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande.id]),
            {'action': 'valider'}, follow=True,
        )

        resp = self.client.get(reverse('courses:hebergement_paiement_list'), {'centre': self.centre.id})
        inscriptions = list(resp.context['inscriptions'])
        insc_annotee = next(i for i in inscriptions if i.id == insc.id)
        self.assertEqual(insc_annotee.total_du, 20000)
        self.assertEqual(insc_annotee.reste, 20000)

    def test_permission_requise(self):
        insc = self._inscription_validee()
        self.client.force_login(self.eleve)
        resp = self.client.get(reverse('courses:hebergement_paiement_list'))
        self.assertNotEqual(resp.status_code, 200)


class StatistiquesTypeFraisFilterTests(HebergementBase):
    """/statistiques/stat-globaux/ : le filtre Type de frais (Formation /
    Hébergement) doit isoler les montants dus/encaissés/taux de recouvrement,
    et la répartition soldé/partiellement soldé par centre, sans quoi ils
    mélangent les deux (obs. DG)."""

    def _setup_dettes_et_paiement(self):
        insc = self._inscription_validee()  # dette scolarité 50000, non réglée
        heb = self._hebergement()  # dette hébergement 20000
        demande = DemandeHebergement.objects.create(hebergement=heb, inscription=insc)
        self.client.force_login(self.staff)
        self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande.id]),
            {'action': 'valider'}, follow=True,
        )
        dette_heb = Dette.objects.get(inscription=insc, frais_formation__hebergement=heb)
        Paiement.objects.create(dette=dette_heb, montant_paiement=20000, tranche=1, effectue_par=self.staff)
        return insc, heb

    def test_sans_filtre_les_deux_types_sont_cumules(self):
        self._setup_dettes_et_paiement()
        resp = self.client.get(reverse('courses:statistiques'))
        self.assertEqual(resp.context['stats']['total_du'], 70000)   # 50000 + 20000
        self.assertEqual(resp.context['stats']['total_encaisse'], 20000)

    def test_filtre_hebergement_isole_les_montants(self):
        self._setup_dettes_et_paiement()
        resp = self.client.get(reverse('courses:statistiques'), {'type_frais': 'hebergement'})
        self.assertEqual(resp.context['stats']['total_du'], 20000)
        self.assertEqual(resp.context['stats']['total_encaisse'], 20000)

    def test_filtre_formation_isole_les_montants(self):
        self._setup_dettes_et_paiement()
        resp = self.client.get(reverse('courses:statistiques'), {'type_frais': 'formation'})
        self.assertEqual(resp.context['stats']['total_du'], 50000)
        self.assertEqual(resp.context['stats']['total_encaisse'], 0)

    def test_dossiers_soldes_respecte_le_filtre(self):
        # Dette hebergement soldee (20000 payes), scolarite non reglee : le
        # dossier ne doit compter "solde" que sous le filtre hebergement.
        self._setup_dettes_et_paiement()
        resp = self.client.get(reverse('courses:statistiques'), {'type_frais': 'hebergement'})
        dossiers = list(resp.context['dossiers_centres'])
        self.assertEqual(sum(d['soldes'] for d in dossiers), 1)

        resp = self.client.get(reverse('courses:statistiques'), {'type_frais': 'formation'})
        dossiers = list(resp.context['dossiers_centres'])
        self.assertEqual(sum(d['soldes'] for d in dossiers), 0)


class HistoriqueTypeFilterTests(HebergementBase):
    def test_filtre_type_hebergement_ne_montre_que_les_versements_hebergement(self):
        insc = self._inscription_validee()
        dette_scol = insc.dettes.get()
        heb = self._hebergement()
        demande = DemandeHebergement.objects.create(hebergement=heb, inscription=insc)
        self.client.force_login(self.staff)
        self.client.post(
            reverse('bsb_admin:demande_hebergement_detail', args=[demande.id]),
            {'action': 'valider'}, follow=True,
        )
        dette_heb = Dette.objects.get(inscription=insc, frais_formation__hebergement=heb)

        p_scol = Paiement.objects.create(dette=dette_scol, montant_paiement=10000, tranche=1, effectue_par=self.staff)
        p_heb = Paiement.objects.create(dette=dette_heb, montant_paiement=20000, tranche=1, effectue_par=self.staff)

        resp = self.client.get(reverse('courses:paiement_historique'), {'type': 'hebergement'})
        ids = {p.id for p in resp.context['paiements']}
        self.assertIn(p_heb.id, ids)
        self.assertNotIn(p_scol.id, ids)

        resp = self.client.get(reverse('courses:paiement_historique'), {'type': 'formation'})
        ids = {p.id for p in resp.context['paiements']}
        self.assertIn(p_scol.id, ids)
        self.assertNotIn(p_heb.id, ids)
