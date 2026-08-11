from django.db import migrations

ROLES_GLOBAL = ['Admin', 'Directeur Général', 'DEPS', 'Agent Comptable']


def seed_permission(apps, schema_editor):
    from django.contrib.auth.management import create_permissions
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    try:
        perm = Permission.objects.get(codename='rechercher_tous_centres')
    except Permission.DoesNotExist:
        return

    for group_name in ROLES_GLOBAL:
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.add(perm)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0020_add_rechercher_tous_centres_permission'),
    ]

    operations = [
        migrations.RunPython(seed_permission, noop),
    ]
