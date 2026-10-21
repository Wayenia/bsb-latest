from django.db import migrations

# filtrer_historique_avance ("Filtrer l'historique des paiements par critères
# avancés") existe depuis l'ajout des filtres "façon Statistiques" sur
# l'historique des paiements (0061_alter_paiement_options) mais n'a jamais été
# rattachée à un groupe : seul un superutilisateur voyait ces filtres
# (Direction, Centre, Métier, Année, Statut, Région, Genre, Statut de
# paiement, Type de programme) sur /membre/paiements/historique — un
# Directeur de Centre, par exemple, n'avait accès qu'à la recherche libre et
# aux dates. Même règle que gerer_hebergements/valider_demande_hebergement
# (voir 0067) : Admin et Directeur Général gardent l'accès complet par
# défaut ; les autres rôles l'obtiennent au cas par cas via l'écran RH →
# Permissions (désormais possible : voir l'ajout dans MATRIX_PERMISSIONS).
#
# .add() (jamais .set()) pour ne rattacher que ce codename précis, sans
# toucher aux permissions déjà personnalisées via l'écran Permissions —
# même précaution que 0031/0064/0067.

PERMISSIONS_A_AJOUTER = {
    'Admin': ['filtrer_historique_avance'],
    'Directeur Général': ['filtrer_historique_avance'],
}


def seed_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    for group_name, codenames in PERMISSIONS_A_AJOUTER.items():
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            continue
        permissions = Permission.objects.filter(codename__in=codenames)
        group.permissions.add(*permissions)


def retirer_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    for group_name, codenames in PERMISSIONS_A_AJOUTER.items():
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            continue
        permissions = Permission.objects.filter(codename__in=codenames)
        group.permissions.remove(*permissions)


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0069_historique_audit_simple_history'),
    ]

    operations = [
        migrations.RunPython(seed_permissions, retirer_permissions),
    ]
