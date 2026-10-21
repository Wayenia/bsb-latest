"""Permissions par défaut des rôles (Group) telles que seedées par les
migrations de données — gerer_programmations et gerer_frais doivent être des
permissions qu'on octroie explicitement (écran RH → Permissions), pas des
permissions fixées dans le code pour tout le monde. Seuls Admin et Directeur
Général (accès complet, cf. README §3) les conservent par défaut."""

from accounts.models import Utilisateur
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse


class PermissionsParDefautTests(TestCase):
    def _a_la_permission(self, nom_groupe, codename):
        groupe = Group.objects.get(name=nom_groupe)
        return groupe.permissions.filter(codename=codename).exists()

    def test_admin_et_dg_gardent_les_deux_permissions(self):
        for groupe in ('Admin', 'Directeur Général'):
            self.assertTrue(self._a_la_permission(groupe, 'gerer_programmations'), groupe)
            self.assertTrue(self._a_la_permission(groupe, 'gerer_frais'), groupe)

    def test_les_trois_autres_roles_ne_les_ont_plus_par_defaut(self):
        for groupe in ('Directeur Inter-régional', 'DESP', 'Directeur de Centre'):
            self.assertFalse(self._a_la_permission(groupe, 'gerer_programmations'), groupe)
            self.assertFalse(self._a_la_permission(groupe, 'gerer_frais'), groupe)


class PermissionsHebergementParDefautTests(TestCase):
    """gerer_hebergements et valider_demande_hebergement (créées avec le
    modèle Hebergement, 0062) n'étaient rattachées à aucun groupe — seul un
    superutilisateur pouvait gérer l'hébergement. Même règle que ci-dessus :
    Admin/DG les gardent par défaut, les autres rôles les obtiennent via
    l'écran RH → Permissions."""

    def _a_la_permission(self, nom_groupe, codename):
        groupe = Group.objects.get(name=nom_groupe)
        return groupe.permissions.filter(codename=codename).exists()

    def test_admin_et_dg_ont_les_deux_permissions_hebergement(self):
        for groupe in ('Admin', 'Directeur Général'):
            self.assertTrue(self._a_la_permission(groupe, 'gerer_hebergements'), groupe)
            self.assertTrue(self._a_la_permission(groupe, 'valider_demande_hebergement'), groupe)

    def test_les_autres_roles_ne_les_ont_pas_par_defaut(self):
        for groupe in ('Directeur Inter-régional', 'DESP', 'Directeur de Centre', 'Caissier', 'Agent Comptable', 'DAF'):
            self.assertFalse(self._a_la_permission(groupe, 'gerer_hebergements'), groupe)
            self.assertFalse(self._a_la_permission(groupe, 'valider_demande_hebergement'), groupe)

    def test_apparaissent_dans_l_ecran_rh_permissions(self):
        """Avoir la permission ne suffit pas si l'écran RH → Permissions ne la
        propose pas : gerer_hebergements/valider_demande_hebergement doivent
        figurer dans la matrice (MATRIX_PERMISSIONS), sinon personne ne peut
        les accorder à un autre rôle que par migration."""
        staff = Utilisateur.objects.create_superuser(
            username="staff.matrix", password="x", nom="Admin", prenom="Sys",
            adresse="Ouaga", email="staff.matrix@example.invalid",
        )
        self.client.force_login(staff)
        resp = self.client.get(reverse('bsb_admin:permissions_matrix'))
        theme = next(g for g in resp.context['groupes'] if g['titre'] == 'Hébergement')
        codenames = {l['perm'].codename for l in theme['lignes']}
        self.assertEqual(codenames, {'gerer_hebergements', 'valider_demande_hebergement'})
        # Admin coché par défaut sur les deux (seedé par la migration 0067).
        for ligne in theme['lignes']:
            noms_coches = {g.name for g, coche in ligne['cells'] if coche}
            self.assertIn('Admin', noms_coches)
            self.assertIn('Directeur Général', noms_coches)


class PermissionFiltrerHistoriqueAvanceTests(TestCase):
    """filtrer_historique_avance (créée avec les filtres « façon
    Statistiques » de l'historique des paiements, 0061) n'était rattachée à
    aucun groupe et absente de l'écran RH → Permissions : seul un
    superutilisateur voyait ces filtres avancés sur l'historique des
    paiements. Même règle que pour l'hébergement : Admin/DG par défaut, les
    autres rôles (Directeur de Centre compris) via RH → Permissions."""

    def _a_la_permission(self, nom_groupe, codename):
        groupe = Group.objects.get(name=nom_groupe)
        return groupe.permissions.filter(codename=codename).exists()

    def test_admin_et_dg_ont_la_permission(self):
        for groupe in ('Admin', 'Directeur Général'):
            self.assertTrue(self._a_la_permission(groupe, 'filtrer_historique_avance'), groupe)

    def test_les_autres_roles_ne_l_ont_pas_par_defaut(self):
        for groupe in ('Directeur Inter-régional', 'DESP', 'Directeur de Centre', 'Caissier', 'Agent Comptable', 'DAF'):
            self.assertFalse(self._a_la_permission(groupe, 'filtrer_historique_avance'), groupe)

    def test_apparait_dans_l_ecran_rh_permissions(self):
        staff = Utilisateur.objects.create_superuser(
            username="staff.matrix2", password="x", nom="Admin", prenom="Sys",
            adresse="Ouaga", email="staff.matrix2@example.invalid",
        )
        self.client.force_login(staff)
        resp = self.client.get(reverse('bsb_admin:permissions_matrix'))
        theme = next(g for g in resp.context['groupes'] if g['titre'] == 'Paiements de scolarité')
        codenames = {l['perm'].codename for l in theme['lignes']}
        self.assertIn('filtrer_historique_avance', codenames)
        ligne = next(l for l in theme['lignes'] if l['perm'].codename == 'filtrer_historique_avance')
        noms_coches = {g.name for g, coche in ligne['cells'] if coche}
        self.assertIn('Admin', noms_coches)
        self.assertIn('Directeur Général', noms_coches)
        self.assertNotIn('Directeur de Centre', noms_coches)
