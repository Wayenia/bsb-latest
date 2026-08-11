from django.db import migrations


ROLE_DEFAULT_PERMISSIONS = {
    'Admin': [
        'gerer_regions', 'gerer_directions', 'gerer_centres', 'gerer_metiers',
        'gerer_programmations', 'gerer_modules', 'gerer_frais', 'gerer_annees',
        'gerer_agents', 'gerer_permissions', 'voir_inscriptions', 'valider_inscription',
        'rejeter_inscription', 'encaisser_paiement', 'gerer_paiements',
        'telecharger_pieces', 'voir_statistiques', 'exporter_donnees',
    ],
    'Directeur Général': [
        'gerer_regions', 'gerer_directions', 'gerer_centres', 'gerer_metiers',
        'gerer_programmations', 'gerer_modules', 'gerer_frais', 'gerer_annees',
        'gerer_agents', 'gerer_permissions', 'voir_inscriptions', 'valider_inscription',
        'rejeter_inscription', 'encaisser_paiement', 'gerer_paiements',
        'telecharger_pieces', 'voir_statistiques', 'exporter_donnees',
    ],
    'Directeur Inter-régional': [
        'gerer_regions', 'gerer_directions', 'gerer_centres', 'gerer_metiers',
        'gerer_programmations', 'gerer_modules', 'gerer_frais',
        'voir_inscriptions', 'valider_inscription', 'rejeter_inscription',
        'telecharger_pieces', 'voir_statistiques', 'exporter_donnees',
    ],
    'DEPS': [
        'gerer_regions', 'gerer_directions', 'gerer_centres', 'gerer_metiers',
        'gerer_programmations', 'gerer_modules', 'gerer_frais',
        'voir_inscriptions', 'valider_inscription', 'rejeter_inscription',
        'telecharger_pieces', 'voir_statistiques', 'exporter_donnees',
    ],
    'Gestionnaire de Centre': [
        'voir_inscriptions', 'valider_inscription', 'rejeter_inscription', 'telecharger_pieces',
    ],
    'Caissier': [
        'voir_inscriptions', 'valider_inscription', 'rejeter_inscription',
        'telecharger_pieces', 'encaisser_paiement',
    ],
    'Agent Comptable': [
        'encaisser_paiement', 'gerer_paiements', 'voir_statistiques', 'exporter_donnees',
    ],
    'Formateur': [],
    'Membre Administration': [
        'voir_inscriptions', 'telecharger_pieces',
    ],
}

ROLE_USER_TYPE = {
    'Admin': 'admin',
    'Directeur Général': 'dg',
    'Directeur Inter-régional': 'dir',
    'DEPS': 'deps',
    'Gestionnaire de Centre': 'gestionnaire',
    'Caissier': 'caissier',
    'Agent Comptable': 'agent_comptable',
    'Formateur': 'formateur',
    'Membre Administration': 'membre',
}


def seed_role_groups(apps, schema_editor):
    # Les permissions déclarées dans Meta.permissions ne sont créées par Django
    # qu'après le signal post_migrate, donc on force leur création ici pour
    # pouvoir les rattacher aux groupes tout de suite dans la même migration.
    from django.contrib.auth.management import create_permissions
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    Utilisateur = apps.get_model('accounts', 'Utilisateur')

    for group_name, codenames in ROLE_DEFAULT_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.set(Permission.objects.filter(codename__in=codenames))

    for group_name, user_type in ROLE_USER_TYPE.items():
        group = Group.objects.get(name=group_name)
        for user in Utilisateur.objects.filter(user_type=user_type):
            user.groups.add(group)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0014_permissionsplateforme_alter_anneescolaire_options_and_more'),
        ('accounts', '0008_alter_utilisateur_options_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_role_groups, noop),
    ]
