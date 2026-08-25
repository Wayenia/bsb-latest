from django.db import migrations

# Django ne renomme jamais un Permission.name deja en base quand le texte
# change dans Meta.permissions (create_permissions ne fait que creer les
# permissions manquantes, par codename) — il faut le faire nous-memes ici,
# meme pattern que 0027_seed_gerer_statistiques_reelles.py.
ANCIEN_NOM = "Saisir et consulter les statistiques réelles (effectifs formés, listes nominatives)"
NOUVEAU_NOM = "Saisir et consulter le bilan des effectifs formés (listes nominatives)"


def renommer(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    Permission.objects.filter(codename='gerer_statistiques_reelles').update(name=NOUVEAU_NOM)


def revenir(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    Permission.objects.filter(codename='gerer_statistiques_reelles').update(name=ANCIEN_NOM)


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0045_alter_permissionsplateforme_options'),
    ]

    operations = [
        migrations.RunPython(renommer, revenir),
    ]
