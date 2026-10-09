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
