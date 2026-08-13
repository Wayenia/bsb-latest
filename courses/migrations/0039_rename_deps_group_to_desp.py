from django.db import migrations


def rename_deps_to_desp(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='DEPS').update(name='DESP')


def rename_desp_to_deps(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='DESP').update(name='DEPS')


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0038_duree_formation_a_la_programmation'),
    ]

    operations = [
        migrations.RunPython(rename_deps_to_desp, rename_desp_to_deps),
    ]
