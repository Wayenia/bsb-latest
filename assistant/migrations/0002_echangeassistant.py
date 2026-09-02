from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("assistant", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EchangeAssistant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.TextField()),
                ("reponse", models.TextField(blank=True)),
                ("domaines", models.JSONField(default=list)),
                ("refuse", models.BooleanField(default=False)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
                ("utilisateur", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="echanges_assistant", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Échange avec l'assistant",
                "ordering": ["-cree_le"],
            },
        ),
    ]
