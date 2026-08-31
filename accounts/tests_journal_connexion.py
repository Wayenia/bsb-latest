"""Journalisation des evenements d'authentification.

Ces tests verrouillent l'articulation entre la vue de connexion et le journal
`HistoriqueConnexion`. Elle est fragile : la vue appelle volontairement
`authenticate(username='', ...)` quand l'identifiant est inconnu, pour que la
reponse mette le meme temps qu'un mot de passe faux. Le signal ne transporte
alors aucun identifiant, et le journal perdait la trace des comptes sondes —
exactement ce qu'une enumeration de comptes cherche a rendre invisible.
"""
from django.test import TestCase

from accounts.models import HistoriqueConnexion, Utilisateur


class JournalConnexionTests(TestCase):

    def setUp(self):
        self.agent = Utilisateur.objects.create_user(
            username='agent.test', password='MotDePasseSolide!1',
            nom='Test', prenom='Agent', email='agent.test@example.invalid',
            user_type='membre')
        HistoriqueConnexion.objects.all().delete()

    def _tenter(self, identifiant, mot_de_passe='MAUVAIS'):
        return self.client.post('/accounts/login',
                                {'identifiant': identifiant, 'password': mot_de_passe})

    def _echecs(self):
        return HistoriqueConnexion.objects.filter(type_evenement='echec')

    def test_echec_sur_compte_reel_est_rattache(self):
        self._tenter('agent.test')
        echec = self._echecs().get()
        self.assertEqual(echec.username, 'agent.test')
        self.assertEqual(echec.utilisateur_id, self.agent.pk)

    def test_echec_sur_identifiant_inconnu_conserve_l_identifiant(self):
        """Sans cela, tous les sondages se confondent en une seule ligne vide."""
        self._tenter('compte.inexistant')
        echec = self._echecs().get()
        self.assertEqual(echec.username, 'compte.inexistant')
        self.assertIsNone(echec.utilisateur_id)

    def test_echec_par_email_inconnu_conserve_l_adresse(self):
        self._tenter('inconnu@example.invalid')
        self.assertEqual(self._echecs().get().username, 'inconnu@example.invalid')

    def test_sondage_de_plusieurs_comptes_reste_distinguable(self):
        """Le coeur de la detection d'enumeration : chaque identifiant sonde
        doit rester compte separement."""
        for identifiant in ('fantome1', 'fantome2', 'fantome3', 'agent.test'):
            self._tenter(identifiant)
        self.assertEqual(self._echecs().count(), 4)
        self.assertEqual(self._echecs().values('username').distinct().count(), 4)

    def test_connexion_reussie_d_un_apprenant_est_journalisee(self):
        eleve = Utilisateur.objects.create_user(
            username='eleve.test', password='MotDePasseSolide!1',
            nom='Test', prenom='Eleve', email='eleve.test@example.invalid',
            user_type='eleve')
        self._tenter('eleve.test', 'MotDePasseSolide!1')
        journal = HistoriqueConnexion.objects.get(type_evenement='connexion')
        self.assertEqual(journal.utilisateur_id, eleve.pk)
        self.assertTrue(journal.est_apprenant)

    def test_identifiant_trop_long_ne_fait_pas_echouer_l_ecriture(self):
        """Une saisie erronee peut deposer n'importe quoi dans ce champ."""
        self._tenter('x' * 400)
        self.assertEqual(len(self._echecs().get().username), 150)
