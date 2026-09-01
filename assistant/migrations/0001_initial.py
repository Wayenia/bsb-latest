from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def octroyer_a_admin(apps, schema_editor):
    """Cree les permissions et les attribue au groupe Admin (installation neuve incluse)."""
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions
    create_permissions(global_apps.get_app_config("assistant"), verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    admin, _ = Group.objects.get_or_create(name="Admin")
    for code in ("utiliser_assistant_ia", "gerer_assistant_ia"):
        perm = Permission.objects.filter(codename=code).first()
        if perm:
            admin.permissions.add(perm)


def retirer(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for code in ("utiliser_assistant_ia", "gerer_assistant_ia"):
        perm = Permission.objects.filter(codename=code).first()
        if perm:
            for g in Group.objects.filter(permissions=perm):
                g.permissions.remove(perm)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReglageAssistant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("modele_actif", models.CharField(default="qwen2:0.5b", max_length=120)),
                ("maj", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Réglage de l'assistant",
                "permissions": [
                    ("utiliser_assistant_ia", "Utiliser l'assistant IA"),
                    ("gerer_assistant_ia", "Gérer l'assistant IA (accès et modèles)"),
                ],
            },
        ),
        migrations.CreateModel(
            name="AccesAssistant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("domaines", models.JSONField(default=list)),
                ("actif", models.BooleanField(default=True)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
                ("utilisateur", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                    related_name="acces_assistant", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Accès délégué à l'assistant",
            },
        ),
        migrations.RunPython(octroyer_a_admin, retirer),
    ]
