# Generated manually, suivant le format de 0003_abonnenewsletter_nb_echecs.py

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('actualites', '0003_abonnenewsletter_nb_echecs'),
    ]

    operations = [
        migrations.AddField(
            model_name='actualite',
            name='date_fin_publication',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Fin de publication'),
        ),
    ]
