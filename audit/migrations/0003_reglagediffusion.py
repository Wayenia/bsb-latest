from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0002_seed_permission'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReglageDiffusion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('frequence', models.CharField(choices=[('desactive', 'Désactivée'), ('quotidien', 'Quotidienne'), ('hebdomadaire', 'Hebdomadaire'), ('mensuel', 'Mensuelle')], default='desactive', max_length=20, verbose_name="Fréquence d'envoi")),
                ('heure', models.PositiveSmallIntegerField(default=7, verbose_name="Heure d'envoi")),
                ('jour_semaine', models.PositiveSmallIntegerField(default=0, verbose_name='Jour de la semaine')),
                ('jour_mois', models.PositiveSmallIntegerField(default=1, verbose_name='Jour du mois')),
                ('derniere_diffusion', models.DateTimeField(blank=True, null=True, verbose_name='Dernière diffusion automatique')),
            ],
            options={
                'verbose_name': "Réglage de diffusion du rapport d'audit",
                'verbose_name_plural': "Réglage de diffusion du rapport d'audit",
            },
        ),
    ]
