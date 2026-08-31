from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0026_alter_eleve_niveau_scolaire'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historiqueconnexion',
            name='type_evenement',
            field=models.CharField(
                choices=[
                    ('connexion', 'Connexion'),
                    ('deconnexion', 'Déconnexion'),
                    ('echec', 'Échec de connexion'),
                ],
                max_length=20,
                verbose_name='Événement',
            ),
        ),
    ]
