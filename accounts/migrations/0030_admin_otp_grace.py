from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0029_acces_administration_technique'),
    ]

    operations = [
        migrations.AddField(
            model_name='utilisateur',
            name='admin_otp_grace_minutes',
            field=models.PositiveSmallIntegerField(default=300, verbose_name='Dispense OTP (minutes)'),
        ),
        migrations.AddField(
            model_name='utilisateur',
            name='admin_otp_grace_jour',
            field=models.DateField(blank=True, null=True, verbose_name='Jour du dernier reglage de dispense'),
        ),
    ]
