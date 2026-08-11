from django.db import migrations

# Mêmes groupes que ceux qui ont déjà 'voir_statistiques' (voir
# 0015_seed_role_groups.py : ROLE_DEFAULT_PERMISSIONS) — la saisie/consultation
# des statistiques réelles suit le même périmètre que les statistiques
# existantes.
GROUPES_CIBLES = [
    'Admin', 'Directeur Général', 'Directeur Inter-régional', 'DEPS',
    'Agent Comptable',
]


def seed_permission(apps, schema_editor):
    # Les permissions déclarées dans Meta.permissions ne sont créées par Django
    # qu'après le signal post_migrate ; on force leur création ici pour
    # pouvoir les rattacher aux groupes tout de suite (même pattern que
    # 0015_seed_role_groups.py).
    from django.contrib.auth.management import create_permissions
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    try:
        permission = Permission.objects.get(codename='gerer_statistiques_reelles')
    except Permission.DoesNotExist:
        return

    for group_name in GROUPES_CIBLES:
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.add(permission)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0026_alter_permissionsplateforme_options_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_permission, noop),
    ]
