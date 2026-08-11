from django.db import migrations

# Nouvel écran "Gestion des apprenants" (liste + modification complète, y
# compris le mot de passe) — mêmes groupes que ceux qui gèrent déjà les
# comptes utilisateurs/agents (voir 0015_seed_role_groups.py : gerer_agents).
GROUPES_CIBLES = ['Admin', 'Directeur Général', 'DEPS']


def seed_permission(apps, schema_editor):
    from django.contrib.auth.management import create_permissions
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    try:
        permission = Permission.objects.get(codename='gerer_eleves')
    except Permission.DoesNotExist:
        return

    for group_name in GROUPES_CIBLES:
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.add(permission)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0033_centreetfiliere_date_creation'),
        ('accounts', '0014_eleve_permissions'),
    ]

    operations = [
        migrations.RunPython(seed_permission, noop),
    ]
