import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    """Permission « gerer_equipe » et validateurs d'extension manquants.

    - `gerer_equipe` : le back-office /bsb/equipe/ remplace l'admin Django,
      supprime du projet, pour la fiche du Directeur General et les membres de
      l'equipe affiches sur la page publique « A propos ».
    - `curricula` et `communique` etaient les deux seuls FileField du projet
      sans FileExtensionValidator ; tous les autres en avaient un.
    """

    dependencies = [
        ('courses', '0047_paiement_annule_paiement_annule_par_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='membre',
            options={
                'ordering': ['order', 'created_at'],
                'permissions': [('gerer_equipe', "Gérer le Directeur Général et l'équipe")],
                'verbose_name': "Membre de l'administration",
                'verbose_name_plural': "Membres de l'administration",
            },
        ),
        migrations.AlterField(
            model_name='filiere',
            name='curricula',
            field=models.FileField(
                blank=True, null=True,
                upload_to='curricula_filieres/',
                validators=[django.core.validators.FileExtensionValidator(['pdf'])],
                verbose_name='Curricula (programme de formation)',
            ),
        ),
        migrations.AlterField(
            model_name='centreetfiliere',
            name='communique',
            field=models.FileField(
                blank=True, null=True,
                upload_to='communiques_filieres/',
                validators=[django.core.validators.FileExtensionValidator(['pdf'])],
                verbose_name='Communique de la formation',
            ),
        ),
    ]
