import re

from django.db import migrations, models

MATRICULE_RE = re.compile(r"^BSB(\d{4})(\d{6})$")


def initialiser_compteurs(apps, schema_editor):
    Utilisateur = apps.get_model('accounts', 'Utilisateur')
    CompteurMatricule = apps.get_model('accounts', 'CompteurMatricule')
    maxima = {}
    for matricule in Utilisateur.objects.filter(matricule__startswith='BSB').values_list('matricule', flat=True):
        m = MATRICULE_RE.match(matricule or '')
        if m:
            annee, numero = int(m.group(1)), int(m.group(2))
            maxima[annee] = max(maxima.get(annee, 0), numero)
    for annee, dernier in maxima.items():
        CompteurMatricule.objects.update_or_create(annee=annee, defaults={'dernier': dernier})


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0032_add_niveau_scolaire_cqp_bqp_bpt_bpts'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompteurMatricule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('annee', models.PositiveIntegerField(unique=True)),
                ('dernier', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.RunPython(initialiser_compteurs, migrations.RunPython.noop),
    ]
