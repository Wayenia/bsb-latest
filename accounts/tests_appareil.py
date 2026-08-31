"""Appareils reconnus et avis de connexion.

Ces tests fixent un equilibre : moins de friction pour l'agent sur son poste
habituel, et une alerte qui lui parvient directement des qu'un appareil inconnu
se connecte. Les deux se degraderaient en silence — on cesserait de demander le
code, ou d'envoyer l'avis — sans que rien ne le signale.
"""
import re

from django.core import mail
from django.test import TestCase, override_settings
from urllib.parse import urlencode

from accounts import appareil
from accounts.models import Utilisateur

FORM = 'application/x-www-form-urlencoded'
MDP = 'MotDePasseSolide!1'


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AppareilReconnuTests(TestCase):

    def setUp(self):
        self.agent = Utilisateur.objects.create_user(
            username='agent.test', password=MDP, nom='Test', prenom='Agent',
            email='agent.test@example.invalid', user_type='membre')
        mail.outbox = []

    def _connexion(self, client=None, mot_de_passe=MDP):
        client = client or self.client
        return client.post('/accounts/login',
                           data=urlencode({'identifiant': 'agent.test', 'password': mot_de_passe}),
                           content_type=FORM)

    def _code_recu(self):
        return re.search(r'\b(\d{4,6})\b', mail.outbox[0].body).group(1)

    def _cycle_complet(self):
        self._connexion()
        reponse = self.client.post('/accounts/login/verification',
                                   data=urlencode({'code': self._code_recu()}),
                                   content_type=FORM)
        return reponse

    def test_premiere_connexion_exige_le_code(self):
        reponse = self._connexion()
        self.assertEqual(reponse.status_code, 302)
        self.assertIn('verification', reponse['Location'])
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_le_code_valide_pose_le_temoin_d_appareil(self):
        reponse = self._cycle_complet()
        self.assertIn('_auth_user_id', self.client.session)
        self.assertIn(appareil.COOKIE, reponse.cookies)

    def test_un_avis_part_a_la_premiere_connexion(self):
        self._cycle_complet()
        avis = [m for m in mail.outbox if 'Connexion' in m.subject]
        self.assertEqual(len(avis), 1)
        self.assertEqual(avis[0].to, ['agent.test@example.invalid'])

    def test_appareil_reconnu_le_code_n_est_plus_demande(self):
        """Le gain pour l'agent : plus de code a chaque connexion sur son poste."""
        self._cycle_complet()
        self.client.post('/accounts/logout')
        mail.outbox = []
        reponse = self._connexion()
        self.assertIn('_auth_user_id', self.client.session)
        self.assertNotIn('verification', reponse.get('Location', ''))

    def test_aucun_avis_sur_un_appareil_deja_reconnu(self):
        """Sinon l'agent recevrait un courriel a chaque connexion et cesserait
        de les lire — l'alerte perdrait tout son sens."""
        self._cycle_complet()
        self.client.post('/accounts/logout')
        mail.outbox = []
        self._connexion()
        self.assertEqual(mail.outbox, [])

    def test_un_autre_appareil_repasse_par_le_code(self):
        self._cycle_complet()
        autre = self.client_class()
        mail.outbox = []
        reponse = self._connexion(client=autre)
        self.assertIn('verification', reponse['Location'])
        self.assertNotIn('_auth_user_id', autre.session)

    def test_changer_de_mot_de_passe_revoque_les_appareils(self):
        """Revocation sans ecran ni procedure : le temoin est signe avec le
        hachage du mot de passe."""
        self._cycle_complet()
        self.agent.refresh_from_db()
        self.agent.set_password('NouveauMotDePasse!2')
        self.agent.save()

        class Requete:
            COOKIES = {}
        Requete.COOKIES = {appareil.COOKIE: self.client.cookies[appareil.COOKIE].value}
        self.assertFalse(appareil.est_reconnu(Requete(), self.agent))

    def test_temoin_falsifie_refuse(self):
        class Requete:
            COOKIES = {appareil.COOKIE: 'valeur.forgee.par.un.tiers'}
        self.assertFalse(appareil.est_reconnu(Requete(), self.agent))

    def test_temoin_d_un_autre_compte_refuse(self):
        autre = Utilisateur.objects.create_user(
            username='autre.agent', password=MDP, nom='A', prenom='B',
            email='autre@example.invalid', user_type='membre')
        self._cycle_complet()

        class Requete:
            COOKIES = {appareil.COOKIE: self.client.cookies[appareil.COOKIE].value}
        self.assertFalse(appareil.est_reconnu(Requete(), autre))

    def test_l_apprenant_n_est_pas_concerne(self):
        """Un apprenant se connecte directement : ni code, ni avis."""
        eleve = Utilisateur.objects.create_user(
            username='eleve.test', password=MDP, nom='E', prenom='T',
            email='eleve@example.invalid', user_type='eleve')
        mail.outbox = []
        self.client.post('/accounts/login',
                         data=urlencode({'identifiant': 'eleve.test', 'password': MDP}),
                         content_type=FORM)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(mail.outbox, [])

    def test_un_avis_sans_adresse_ne_bloque_pas_la_connexion(self):
        """Une panne de messagerie ne doit jamais empecher de travailler."""
        self.agent.email = ''
        self.agent.save()
        self.assertFalse(appareil.avertir(self.agent, type('R', (), {'META': {}})()))
