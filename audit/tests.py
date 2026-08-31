"""Tests de l'application d'audit.

Chaque detection a son test : ce sont elles qui donnent sa valeur au rapport,
et une detection qui cesse silencieusement de se declencher est pire que pas
de detection du tout, puisqu'elle laisse croire que rien ne se passe.
"""
import datetime as dt
from io import BytesIO

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone
from openpyxl import load_workbook

from accounts.models import HistoriqueConnexion, Utilisateur
from audit import services
from audit.classeur import construire_classeur


class BaseAudit(TestCase):

    def setUp(self):
        self.maintenant = timezone.now()
        self.agent = Utilisateur.objects.create_user(
            username='agent.un', password='x', nom='Un', prenom='Agent',
            email='agent.un@example.invalid', user_type='membre')

    def evt(self, username, type_evt, quand, ip='203.0.113.1', user=None, apprenant=False):
        return HistoriqueConnexion.objects.create(
            utilisateur=user, username=username, est_apprenant=apprenant,
            type_evenement=type_evt, date_evenement=quand, adresse_ip=ip)

    def motifs(self, rapport):
        return {a.motif for a in rapport.alertes}


class DetectionTests(BaseAudit):

    def test_sondage_de_comptes_depuis_une_ip(self):
        for i in range(5):
            self.evt(f'inconnu{i}', 'echec', self.maintenant - dt.timedelta(minutes=i), '203.0.113.7')
        r = services.construire_rapport(jours=7)
        alerte = next(a for a in r.alertes if 'Sondage' in a.motif)
        self.assertEqual(alerte.severite, services.CRITIQUE)
        self.assertEqual(alerte.cible, '203.0.113.7')

    def test_sondage_sous_le_seuil_ne_declenche_pas(self):
        self.evt('inconnu1', 'echec', self.maintenant, '203.0.113.7')
        self.assertNotIn("Sondage de comptes depuis une meme adresse",
                         self.motifs(services.construire_rapport(jours=7)))

    def test_compromission_probable_apres_serie_d_echecs(self):
        base = self.maintenant - dt.timedelta(days=1)
        for i in range(6):
            self.evt('agent.un', 'echec', base + dt.timedelta(minutes=i), user=self.agent)
        self.evt('agent.un', 'connexion', base + dt.timedelta(minutes=30), user=self.agent)
        r = services.construire_rapport(jours=7)
        alerte = next(a for a in r.alertes if 'Connexion reussie' in a.motif)
        self.assertEqual(alerte.severite, services.CRITIQUE)

    def test_reussite_longtemps_apres_les_echecs_ne_declenche_pas(self):
        """Au-dela d'une heure, le lien de causalite n'est plus etabli."""
        base = self.maintenant - dt.timedelta(days=2)
        for i in range(6):
            self.evt('agent.un', 'echec', base + dt.timedelta(minutes=i), user=self.agent)
        self.evt('agent.un', 'connexion', base + dt.timedelta(hours=5), user=self.agent)
        self.assertNotIn("Connexion reussie apres une serie d'echecs",
                         self.motifs(services.construire_rapport(jours=7)))

    def test_acharnement_sur_un_compte(self):
        for i in range(6):
            self.evt('agent.un', 'echec', self.maintenant - dt.timedelta(minutes=i), user=self.agent)
        self.assertIn("Echecs repetes sur un meme compte",
                      self.motifs(services.construire_rapport(jours=7)))

    def test_compte_utilise_depuis_plusieurs_adresses(self):
        for i, ip in enumerate(['10.0.0.1', '10.0.0.2', '10.0.0.3']):
            self.evt('agent.un', 'connexion', self.maintenant - dt.timedelta(hours=i),
                     ip=ip, user=self.agent)
        self.assertIn("Compte utilise depuis plusieurs adresses",
                      self.motifs(services.construire_rapport(jours=7)))

    def test_connexions_hors_heures_ouvrees(self):
        for i in range(3):
            nuit = (self.maintenant - dt.timedelta(days=i + 1)).replace(hour=3, minute=0)
            self.evt('agent.un', 'connexion', nuit, user=self.agent)
        self.assertIn("Connexions d'agent hors heures ouvrees",
                      self.motifs(services.construire_rapport(jours=7)))

    def test_apprenant_hors_heures_n_est_pas_signale(self):
        """Un apprenant consulte son dossier a toute heure : c'est attendu."""
        eleve = Utilisateur.objects.create_user(
            username='eleve.un', password='x', nom='Un', prenom='Eleve',
            email='e.un@example.invalid', user_type='eleve')
        for i in range(4):
            nuit = (self.maintenant - dt.timedelta(days=i + 1)).replace(hour=2)
            self.evt('eleve.un', 'connexion', nuit, user=eleve, apprenant=True)
        self.assertNotIn("Connexions d'agent hors heures ouvrees",
                         self.motifs(services.construire_rapport(jours=7)))

    def test_periode_vide_ne_produit_aucune_alerte(self):
        r = services.construire_rapport(jours=7)
        self.assertEqual(r.total, 0)
        self.assertEqual(r.alertes, [])
        self.assertEqual(r.taux_echec, 0.0)

    def test_evenements_hors_periode_sont_exclus(self):
        self.evt('agent.un', 'echec', self.maintenant - dt.timedelta(days=40), user=self.agent)
        self.assertEqual(services.construire_rapport(jours=7).total, 0)


class IndicateurTests(BaseAudit):

    def test_taux_echec_et_comptes_vises(self):
        for i in range(3):
            self.evt('agent.un', 'connexion', self.maintenant - dt.timedelta(hours=i), user=self.agent)
        self.evt('inconnu', 'echec', self.maintenant)
        r = services.construire_rapport(jours=7)
        self.assertEqual((r.connexions, r.echecs), (3, 1))
        self.assertEqual(r.taux_echec, 25.0)
        self.assertEqual(r.comptes_vises, 1)
        self.assertEqual(r.echecs_compte_inconnu, 1)

    def test_serie_quotidienne_couvre_les_jours_sans_evenement(self):
        """Un graphique a trous laisse croire a une absence de donnees."""
        r = services.construire_rapport(jours=7)
        self.assertEqual(len(r.par_jour), 8)
        self.assertEqual(len(r.par_heure), 24)


class ClasseurTests(BaseAudit):

    def test_structure_du_classeur(self):
        self.evt('inconnu', 'echec', self.maintenant, '203.0.113.7')
        r = services.construire_rapport(jours=7)
        wb = load_workbook(BytesIO(construire_classeur(r, list(HistoriqueConnexion.objects.all()))))
        self.assertEqual(wb.sheetnames,
                         ['Synthèse', 'Alertes', 'Graphiques', 'Journal', 'Données'])
        self.assertEqual(len(wb['Graphiques']._charts), 4)

    def test_classeur_sans_donnees_reste_valide(self):
        r = services.construire_rapport(jours=7)
        wb = load_workbook(BytesIO(construire_classeur(r, [])))
        self.assertIn('Synthèse', wb.sheetnames)
        # Sans compte vise ni source, seuls les deux graphiques temporels subsistent.
        self.assertEqual(len(wb['Graphiques']._charts), 2)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CommandeTests(BaseAudit):

    def test_envoi_avec_piece_jointe(self):
        self.evt('inconnu', 'echec', self.maintenant, '203.0.113.7')
        call_command('envoyer_rapport_audit', '--jours', '7', '--a', 'audit@example.invalid')
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['audit@example.invalid'])
        self.assertIn('text/html', [t for _, t in message.alternatives])
        nom, _, type_mime = message.attachments[0]
        self.assertTrue(nom.endswith('.xlsx'))
        self.assertIn('spreadsheetml', type_mime)

    def test_sans_destinataire_la_commande_refuse(self):
        with override_settings(AUDIT_DESTINATAIRES=[]):
            with self.assertRaises(CommandError):
                call_command('envoyer_rapport_audit')

    def test_sans_envoi_ne_produit_aucun_courriel(self):
        call_command('envoyer_rapport_audit', '--sans-envoi')
        self.assertEqual(len(mail.outbox), 0)

    def test_periode_invalide_refusee(self):
        with self.assertRaises(CommandError):
            call_command('envoyer_rapport_audit', '--jours', '0', '--sans-envoi')
