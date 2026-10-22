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

    def test_aucune_fuite_de_commentaire_template(self):
        """Un commentaire Django {# ... #} qui s'étend sur plusieurs lignes
        n'est PAS supprimé par le moteur de template (restriction propre à ce
        tag, contrairement à {% comment %}/{% endcomment %}) : son texte
        brut, accolades comprises, se retrouve alors affiché tel quel sur la
        page — exactement le bug introduit (puis corrigé) par le commentaire
        multi-ligne ajouté avec ce correctif. Garde-fou générique pour ne pas
        reproduire l'erreur ailleurs sur ces deux pages."""
        self.client.force_login(self.staff)
        for url_name in ('courses:statistiques', 'courses:paiement_historique'):
            html = self.client.get(reverse(url_name)).content.decode()
            self.assertNotIn('{#', html, url_name)
            self.assertNotIn('#}', html, url_name)

    def test_exports_partagent_le_meme_filtre_donc_deja_couverts(self):
        """Les exports (CSV/Excel/PDF, stat-globaux et historique) réutilisent
        tous _apply_stats_filters / _appliquer_filtres_avances_historique —
        la même fonction que la page à l'écran. Retirer l'option du <select>
        suffit donc : aucun code d'export séparé ne pouvait produire
        statut=valide_paye autrement que par une URL tapée à la main, et dans
        ce cas il ne plante pas, il retourne simplement 0 ligne (jamais un
        résultat faussé)."""
        self.client.force_login(self.staff)
        export_urls = [
            reverse('courses:export_csv') + '?type=inscriptions&statut=valide_paye',
            reverse('courses:export_excel') + '?type=inscriptions&statut=valide_paye',
            reverse('courses:export_pdf') + '?type=inscriptions&statut=valide_paye',
            reverse('courses:paiement_historique_export_csv') + '?statut=valide_paye',
            reverse('courses:paiement_historique_export_excel') + '?statut=valide_paye',
            reverse('courses:paiement_historique_export_pdf') + '?statut=valide_paye',
        ]
        for url in export_urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)

        # Le même export, filtré sur le statut réel ("valide"), retrouve bien
        # l'inscription créée dans setUpTestData — la fonction de filtrage
        # marche, seule la valeur morte ne matchait jamais rien.
        resp = self.client.get(reverse('courses:export_csv') + '?type=inscriptions&statut=valide')
        self.assertIn(self.eleve.nom, resp.content.decode('utf-8-sig'))
