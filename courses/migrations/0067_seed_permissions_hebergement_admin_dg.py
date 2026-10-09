from django.db import migrations

# gerer_hebergements ("Créer/modifier/désactiver un hébergement") et
# valider_demande_hebergement ("Valider ou rejeter une demande d'hébergement")
# ont été créées avec le modèle Hebergement (0062) mais jamais rattachées à
# un groupe : seul un superutilisateur pouvait gérer l'hébergement. Comme
# pour gerer_programmations/gerer_frais (voir 0064), Admin et Directeur
# Général gardent l'accès complet par défaut ; les autres rôles (Gestionnaire
# de Centre, etc.) l'obtiennent au cas par cas via l'écran RH → Permissions.
#
# .add() (jamais .set()) pour ne rattacher que ces deux codenames précis,
# sans toucher aux permissions déjà personnalisées via l'écran Permissions —
# même précaution que 0031/0064.

PERMISSIONS_A_AJOUTER = {
    'Admin': ['gerer_hebergements', 'valider_demande_hebergement'],
    'Directeur Général': ['gerer_hebergements', 'valider_demande_hebergement'],
}


def seed_permissions(apps, schema_editor):
    # Les permissions déclarées dans Meta.permissions ne sont créées par Django
    # qu'après le signal post_migrate ; on force leur création ici pour
    # pouvoir les rattacher aux groupes tout de suite (même pattern que
    # 0015_seed_role_groups.py / 0031_seed_permissions_dir_gestionnaire_daf.py).
    from django.contrib.auth.management import create_permissions
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

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
        ('courses', '0066_paiement_centre_encaissement'),
    ]

    operations = [
        migrations.RunPython(seed_permissions, retirer_permissions),
    ]
