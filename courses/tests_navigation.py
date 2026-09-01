"""Navigation du back-office (config/navigation.py).

Elle est declaree en donnees, donc verifiable. Le test le plus utile est celui
qui resout toutes les routes : renommer une route ailleurs dans le projet
ferait disparaitre un lien de la barre en silence, et l'ecran deviendrait
inatteignable sans que rien ne signale la panne.
"""
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from accounts.models import Utilisateur
from config.navigation import COULEURS, GROUPES, ICONES, construire_menu


class NavigationTests(TestCase):

    def _agent(self, *codenames):
        """Compte sans groupe de role : `Utilisateur.save()` rattache tout role
        metier a son groupe Django, lequel porte deja des permissions. Partir
        d'un role sans groupe donne une base vide, et les permissions ajoutees
        ici sont donc les seules en jeu."""
        agent = Utilisateur.objects.create_user(
            username=f"agent{len(codenames)}", password='x', nom='N', prenom='P',
            email=f"a{len(codenames)}@example.invalid", user_type='eleve')
        for code in codenames:
            agent.user_permissions.add(Permission.objects.get(codename=code))
        return Utilisateur.objects.get(pk=agent.pk)   # vide le cache de permissions

    def test_toutes_les_routes_declarees_existent(self):
        """Garde-fou : une route renommee ferait disparaitre un lien en silence."""
        introuvables = []
        for groupe in GROUPES:
            for lien in groupe['liens']:
                try:
                    reverse(lien['nom_url'], args=lien['args'])
                except NoReverseMatch:
                    introuvables.append(lien['nom_url'])
        self.assertEqual(introuvables, [])

    def test_chaque_groupe_declare_une_couleur_et_une_icone_connues(self):
        for groupe in GROUPES:
            self.assertIn(groupe['couleur'], COULEURS, groupe['titre'])
            self.assertIn(groupe['icone'], ICONES, groupe['titre'])

    def test_sans_permission_aucun_groupe(self):
        self.assertEqual(construire_menu(self._agent(), '/bsb/dashboard'), [])

    def test_une_permission_ouvre_le_seul_groupe_correspondant(self):
        menu = construire_menu(self._agent('gerer_agents'), '/bsb/dashboard')
        self.assertEqual([g['titre'] for g in menu], ['RH et Permissions'])
        self.assertEqual([l['libelle'] for l in menu[0]['liens']], ['Agents et formateurs'])

    def test_le_groupe_de_la_page_courante_est_marque(self):
        menu = construire_menu(self._agent('gerer_agents'), '/bsb/rh/agents')
        self.assertTrue(menu[0]['actif'])
        self.assertTrue(menu[0]['liens'][0]['actif'])

    def test_un_autre_ecran_ne_marque_aucun_groupe(self):
        menu = construire_menu(self._agent('gerer_agents'), '/bsb/dashboard')
        self.assertFalse(any(g['actif'] for g in menu))

    def test_ordre_des_groupes_du_plus_consulte_au_plus_rare(self):
        """L'ordre est un choix d'ergonomie : le figer evite qu'il derive."""
        superutilisateur = Utilisateur.objects.create_superuser(
            username='chef', password='x', nom='N', prenom='P', email='c@example.invalid')
        titres = [g['titre'] for g in construire_menu(superutilisateur, '/bsb/dashboard')]
        self.assertEqual(titres[:4], [
            'Statistiques', 'Scolarité', 'Prestation et facturation', 'Offre de formation',
        ])
        self.assertEqual(titres[-1], 'Paramétrage')

    def test_le_superutilisateur_voit_tous_les_groupes(self):
        superutilisateur = Utilisateur.objects.create_superuser(
            username='chef2', password='x', nom='N', prenom='P', email='c2@example.invalid')
        menu = construire_menu(superutilisateur, '/bsb/dashboard')
        self.assertEqual(len(menu), len(GROUPES))
