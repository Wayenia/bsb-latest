from django.db import migrations

# Les permissions doivent être octroyées explicitement (écran RH → Permissions),
# pas fixées par défaut dans une migration : gerer_programmations ("Gérer les
# associations centre-métier") et gerer_frais ("Gérer les frais et types de
# frais") étaient incluses par défaut pour 5 rôles depuis 0015/0031. Elles sont
# retirées ici pour les rôles qui n'ont pas vocation à un accès complet —
# Admin et Directeur Général les conservent (accès complet, cf. README §3) ;
# un administrateur peut les réaccorder à tout moment via la matrice.
#
# .remove() (jamais .set()) pour ne retirer que ces deux codenames précis,
# sans toucher aux autres permissions déjà personnalisées via l'écran
# Permissions — même précaution que 0031_seed_permissions_dir_gestionnaire_daf.

PERMISSIONS_A_RETIRER = {
    'Directeur Inter-régional': ['gerer_programmations', 'gerer_frais'],
    'DESP': ['gerer_programmations', 'gerer_frais'],
    'Directeur de Centre': ['gerer_programmations', 'gerer_frais'],
}


def retirer_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    for group_name, codenames in PERMISSIONS_A_RETIRER.items():
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            continue
        permissions = Permission.objects.filter(codename__in=codenames)
        group.permissions.remove(*permissions)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0063_alter_inscription_options_inscription_annule_par_and_more'),
    ]

    operations = [
        migrations.RunPython(retirer_permissions, noop),
    ]
