from django.db import migrations

# Renomme le Group Django "Gestionnaire de Centre" (déjà seedé en base par
# 0015_seed_role_groups.py) en "Directeur de Centre" — mise à jour du seul
# champ `name`, donc les permissions et les utilisateurs déjà rattachés à ce
# groupe sont conservés (même PK, aucune relation M2M à recréer).
ANCIEN_NOM = "Gestionnaire de Centre"
NOUVEAU_NOM = "Directeur de Centre"


def renommer(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name=ANCIEN_NOM).update(name=NOUVEAU_NOM)


def renommer_arriere(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name=NOUVEAU_NOM).update(name=ANCIEN_NOM)


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0029_alter_effectifreel_unique_together_and_more'),
    ]

    operations = [
        migrations.RunPython(renommer, renommer_arriere),
    ]
