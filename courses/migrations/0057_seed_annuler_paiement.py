from django.db import migrations

# Permission dediee « annuler_paiement » : accordee d'emblee aux roles qui,
# jusqu'ici, pouvaient deja annuler un versement (detenteurs de
# encaisser_paiement ou gerer_paiements). Le comportement reste donc identique ;
# la permission devient simplement visible et revocable dans la matrice RH.
GROUPES_CIBLES = [
    'Admin',
    'Directeur Général',
    'Directeur Inter-régional',
    'Directeur de Centre',
    'Caissier',
    'Agent Comptable',
]


def seed_permission(apps, schema_editor):
    from django.contrib.auth.management import create_permissions
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    try:
        permission = Permission.objects.get(codename='annuler_paiement')
    except Permission.DoesNotExist:
        return

    for group_name in GROUPES_CIBLES:
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.add(permission)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0056_alter_paiement_options'),
    ]

    operations = [
        migrations.RunPython(seed_permission, noop),
    ]
