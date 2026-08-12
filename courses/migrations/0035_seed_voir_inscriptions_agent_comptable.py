from django.db import migrations

# Agent Comptable a (0015) encaisser_paiement/gerer_paiements et (0021)
# rechercher_tous_centres, mais jamais voir_inscriptions. Or _can_access_dette_finances
# / _can_access_eleve_finances (courses/views.py) exigent voir_inscriptions comme
# porte d'entrée avant même de regarder le scope/rechercher_tous_centres : sans
# elle, l'apprenant apparaît bien dans la liste des encaissements (paiement_list
# ne teste que encaisser_paiement/gerer_paiements) mais "Voir les dettes" et
# "Encaisser" renvoient un 403 — Agent Comptable ne pouvait donc jamais
# effectivement encaisser malgré ses permissions par défaut.
GROUPES_CIBLES = ['Agent Comptable']


def seed_permission(apps, schema_editor):
    from django.contrib.auth.management import create_permissions
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    try:
        permission = Permission.objects.get(codename='voir_inscriptions')
    except Permission.DoesNotExist:
        return

    for group_name in GROUPES_CIBLES:
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.add(permission)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0034_seed_gerer_eleves'),
    ]

    operations = [
        migrations.RunPython(seed_permission, noop),
    ]
