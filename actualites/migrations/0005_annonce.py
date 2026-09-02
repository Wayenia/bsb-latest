from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("actualites", "0004_actualite_date_fin_publication"),
    ]

    operations = [
        migrations.CreateModel(
            name="Annonce",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("texte", models.CharField(max_length=200, verbose_name="Texte de l'annonce")),
                ("lien", models.CharField(blank=True, max_length=300, verbose_name="Lien (URL) — optionnel")),
                ("libelle_lien", models.CharField(blank=True, help_text="Texte du bouton cliquable (ex. « En savoir plus »).", max_length=60, verbose_name="Libellé du lien")),
                ("actif", models.BooleanField(default=True, verbose_name="Affichée")),
                ("ordre", models.PositiveSmallIntegerField(default=0, verbose_name="Ordre d'affichage")),
                ("date_debut", models.DateTimeField(blank=True, help_text="Vide = tout de suite.", null=True, verbose_name="Début d'affichage")),
                ("date_fin", models.DateTimeField(blank=True, help_text="Vide = sans expiration.", null=True, verbose_name="Expiration")),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Annonce défilante",
                "verbose_name_plural": "Annonces défilantes",
                "ordering": ["ordre", "-cree_le"],
            },
        ),
    ]
