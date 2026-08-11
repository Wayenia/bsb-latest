from django.db import migrations

# Complète les permissions par défaut de 4 rôles qui en avaient trop peu
# (voir audit demandé par l'utilisateur) :
#   - Directeur Inter-régional : avait déjà gerer_centres/gerer_programmations/
#     gerer_frais/voir_statistiques (0015) mais aucune permission de paiement,
#     ni rechercher_tous_centres (qui était réservée à Admin/DG/DEPS/Agent
#     Comptable, 0021_seed_rechercher_tous_centres.py).
#   - Directeur de Centre : n'avait que voir_inscriptions/valider_inscription/
#     rejeter_inscription/telecharger_pieces (0015) — rien sur les paiements,
#     statistiques ou programmations/frais de son propre centre.
#   - Caissier : avait déjà encaisser_paiement (0015) mais pas
#     rechercher_tous_centres — un caissier ne pouvait retrouver par
#     recherche que les apprenants de son propre centre.
#   - DAF : n'avait strictement aucune permission par défaut — le module
#     Facturation entier (accounts.gerer_facturation et consorts) renvoyait
#     un 403 tant qu'un admin ne les cochait pas manuellement dans la matrice.
#
# rechercher_tous_centres est volontairement étendue à dir/gestionnaire/
# caissier : l'action d'encaissement elle-même (courses.views.effectuer_paiment)
# n'a jamais été limitée par centre — quiconque a `encaisser_paiement` peut
# déjà régler la dette de n'importe quel apprenant de n'importe quel centre
# s'il en connaît l'identifiant. Sans rechercher_tous_centres, ces 3 rôles
# ne pouvaient simplement pas RETROUVER ces dettes par recherche dans les
# écrans de liste (limités à leur propre centre/direction par défaut) — ce
# n'était pas cohérent avec la capacité réelle déjà accordée par
# encaisser_paiement/gerer_paiements.
#
# Chaque codename est ajouté via .add() (additif, jamais .set()) pour ne pas
# écraser des droits déjà personnalisés via l'écran Permissions.

PERMISSIONS_A_AJOUTER = {
    'Directeur Inter-régional': ['encaisser_paiement', 'gerer_paiements', 'rechercher_tous_centres'],
    'Directeur de Centre': [
        'encaisser_paiement', 'gerer_paiements', 'voir_statistiques',
        'gerer_programmations', 'gerer_frais', 'exporter_donnees',
        'rechercher_tous_centres',
    ],
    'Caissier': ['rechercher_tous_centres'],
    'DAF': ['gerer_facturation', 'valider_facture_prestation', 'encaisser_prestation'],
}


def seed_permissions(apps, schema_editor):
    # Les permissions déclarées dans Meta.permissions ne sont créées par Django
    # qu'après le signal post_migrate ; on force leur création ici pour
    # pouvoir les rattacher aux groupes tout de suite (même pattern que
    # 0015_seed_role_groups.py / 0027_seed_gerer_statistiques_reelles.py).
    from django.contrib.auth.management import create_permissions
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    for group_name, codenames in PERMISSIONS_A_AJOUTER.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        permissions = Permission.objects.filter(codename__in=codenames)
        group.permissions.add(*permissions)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0030_rename_gestionnaire_group'),
        ('accounts', '0013_alter_utilisateur_user_type'),
    ]

    operations = [
        migrations.RunPython(seed_permissions, noop),
    ]
