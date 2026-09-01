from django.conf import settings
from django.db import models

# Domaines de donnees consultables par l'assistant (lecture seule).
DOMAINES = [
    ("scolarite", "Scolarité (inscriptions, apprenants)"),
    ("finances", "Finances (paiements, dettes)"),
    ("facturation", "Facturation DAF (prestations)"),
    ("rh", "RH (effectifs des agents)"),
]


class ReglageAssistant(models.Model):
    """Singleton : modele local actif de l'assistant."""
    modele_actif = models.CharField(max_length=120, default="qwen2:0.5b")
    maj = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Réglage de l'assistant"
        permissions = [
            ("utiliser_assistant_ia", "Utiliser l'assistant IA"),
            ("gerer_assistant_ia", "Gérer l'assistant IA (accès et modèles)"),
        ]

    def __str__(self):
        return f"Assistant ({self.modele_actif})"

    @classmethod
    def actuel(cls):
        obj = cls.objects.first()
        return obj or cls.objects.create(modele_actif=settings.AI_MODEL)


class AccesAssistant(models.Model):
    """Délégation d'accès à un agent + périmètre de domaines consultables."""
    utilisateur = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                       related_name="acces_assistant")
    domaines = models.JSONField(default=list)
    actif = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Accès délégué à l'assistant"

    def __str__(self):
        return f"{self.utilisateur} → {', '.join(self.domaines) or 'aucun domaine'}"
