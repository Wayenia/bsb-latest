from django.db import migrations

# La personnalisation des carrousels de l'accueil est un contenu du site
# public : mêmes groupes que « gerer_equipe » (fiche DG / équipe « À propos »).
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
        permission = Permission.objects.get(codename='gerer_carrousel')
    except Permission.DoesNotExist:
        return

    for group_name in GROUPES_CIBLES:
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.add(permission)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0051_carrouselaccueil'),
    ]

    operations = [
        migrations.RunPython(seed_permission, noop),
    ]
