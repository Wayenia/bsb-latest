import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0027_alter_historiqueconnexion_type_evenement'),
    ]

    operations = [
        migrations.AddField(
            model_name='utilisateur',
            name='photo',
            field=models.ImageField(
                blank=True, null=True, upload_to='profils/',
                validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
                help_text='JPG, PNG ou WEBP, 2 Mo maximum', verbose_name='Photo de profil'),
        ),
    ]
