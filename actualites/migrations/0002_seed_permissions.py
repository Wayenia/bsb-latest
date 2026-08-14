from django.db import migrations

# Mêmes groupes que les autres écrans d'administration (cf. courses/0015_seed_role_groups).
GROUPES = ['Admin', 'Directeur Général']
CODENAMES = ['gerer_actualites', 'publier_actualite', 'gerer_newsletter']


def seed(apps, schema_editor):
    from django.contrib.auth.management import create_permissions
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    for nom in GROUPES:
        groupe, _ = Group.objects.get_or_create(name=nom)
        for codename in CODENAMES:
            try:
                groupe.permissions.add(Permission.objects.get(codename=codename))
            except Permission.DoesNotExist:
                pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [('actualites', '0001_initial')]

    operations = [migrations.RunPython(seed, noop)]
