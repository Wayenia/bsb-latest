from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_eleve_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='eleve',
            name='nom_pere',
            field=models.CharField(default='', max_length=150, verbose_name='Nom du père'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='eleve',
            name='prenom_pere',
            field=models.CharField(default='', max_length=150, verbose_name='Prénom du père'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='eleve',
            name='nom_mere',
            field=models.CharField(default='', max_length=150, verbose_name='Nom de la mère'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='eleve',
            name='prenom_mere',
            field=models.CharField(default='', max_length=150, verbose_name='Prénom de la mère'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='eleve',
            name='nip',
            field=models.CharField(
                blank=True, max_length=20, null=True,
                help_text="Obligatoire à partir de 18 ans.",
                verbose_name="NIP (Numéro d'Identification Personnel)",
            ),
        ),
    ]
