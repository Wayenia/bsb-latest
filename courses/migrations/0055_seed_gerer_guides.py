from django.db import migrations

# Les guides d'utilisation sont un contenu transverse du site : memes groupes
# que « gerer_carrousel » (contenu de la page d'accueil).
GROUPES_CIBLES = ['Admin', 'Directeur Général']


def seed_permission(apps, schema_editor):
    from django.contrib.auth.management import create_permissions
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    try:
        permission = Permission.objects.get(codename='gerer_guides')
    except Permission.DoesNotExist:
        return

    for group_name in GROUPES_CIBLES:
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.add(permission)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0054_guideutilisation'),
    ]

    operations = [
        migrations.RunPython(seed_permission, noop),
    ]
