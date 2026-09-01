from django.db import migrations


def octroyer_a_admin(apps, schema_editor):
    """Attribue la nouvelle permission au groupe Admin. Les superutilisateurs
    l'ont d'office ; les comptes user_type='admin' l'obtiennent via ce groupe.

    Les permissions ne sont creees qu'en post_migrate, donc apres cette fonction :
    on force leur creation ici, sans quoi le groupe ne recevrait rien lors d'une
    installation neuve."""
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions
    create_permissions(global_apps.get_app_config('accounts'), verbosity=0)

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    perm = Permission.objects.filter(codename='acces_administration_technique').first()
    if perm is None:
        return
    admin, _ = Group.objects.get_or_create(name='Admin')
    admin.permissions.add(perm)


def retirer(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    try:
        perm = Permission.objects.get(codename='acces_administration_technique')
    except Permission.DoesNotExist:
        return
    for g in Group.objects.filter(permissions=perm):
        g.permissions.remove(perm)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0028_utilisateur_photo'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='utilisateur',
            options={
                'verbose_name': 'Utilisateur',
                'verbose_name_plural': 'Tous les utilisateurs',
                'permissions': [
                    ('gerer_agents', 'Gérer les comptes utilisateurs'),
                    ('gerer_permissions', 'Gérer les permissions'),
                    ('acces_administration_technique', "Accès à l'espace d'administration technique"),
                ],
            },
        ),
        migrations.RunPython(octroyer_a_admin, retirer),
    ]
