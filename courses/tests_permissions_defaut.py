"""Permissions par défaut des rôles (Group) telles que seedées par les
migrations de données — gerer_programmations et gerer_frais doivent être des
permissions qu'on octroie explicitement (écran RH → Permissions), pas des
permissions fixées dans le code pour tout le monde. Seuls Admin et Directeur
Général (accès complet, cf. README §3) les conservent par défaut."""

from django.contrib.auth.models import Group
from django.test import TestCase


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
