from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='DestinataireRapport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='Adresse e-mail')),
                ('nom', models.CharField(blank=True, max_length=150, verbose_name='Nom du destinataire')),
                ('fonction', models.CharField(blank=True, max_length=150, verbose_name='Fonction')),
                ('actif', models.BooleanField(default=True, verbose_name='Reçoit le rapport')),
                ('date_ajout', models.DateTimeField(auto_now_add=True, verbose_name='Ajouté le')),
            ],
            options={
                'verbose_name': "Destinataire du rapport d'audit",
                'verbose_name_plural': "Destinataires du rapport d'audit",
                'ordering': ['nom', 'email'],
                'permissions': [('gerer_destinataires_audit',
                                 "Gérer les destinataires du rapport d'inspection")],
            },
        ),
    ]
