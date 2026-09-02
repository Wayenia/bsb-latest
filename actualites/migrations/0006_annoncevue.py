from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("actualites", "0005_annonce"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnnonceVue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vu_le", models.DateTimeField(auto_now_add=True)),
                ("annonce", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vues", to="actualites.annonce")),
                ("utilisateur", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="annonces_vues", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Annonce vue",
                "unique_together": {("annonce", "utilisateur")},
            },
        ),
    ]
