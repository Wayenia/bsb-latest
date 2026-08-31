from django.db import migrations

GROUPES = ['Admin', 'Directeur Général']
CODENAME = 'gerer_destinataires_audit'


def accorder(apps, schema_editor):
    """Accorde la permission aux groupes de direction.

    Comme partout dans le projet, la distribution passe par une migration de
    seed : l'ecran RH > Permissions permet ensuite de l'ajuster sans code.
    """
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    perm = Permission.objects.filter(codename=CODENAME).first()
    if not perm:
        return
    for nom in GROUPES:
        groupe = Group.objects.filter(name=nom).first()
        if groupe:
            groupe.permissions.add(perm)


def retirer(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    perm = Permission.objects.filter(codename=CODENAME).first()
    if not perm:
        return
    for nom in GROUPES:
        groupe = Group.objects.filter(name=nom).first()
        if groupe:
            groupe.permissions.remove(perm)


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [migrations.RunPython(accorder, retirer)]
