from django.conf import settings
from django.db import models

# Domaines consultables par l'assistant (lecture seule), du plus sollicite au moins.
DOMAINES = [
    ("scolarite", "Scolarité — inscriptions, apprenants"),
    ("finances", "Finances — paiements, dettes, recouvrement"),
    ("offre", "Offre de formation — métiers, centres, programmations"),
    ("facturation", "Facturation DAF — clients, prestations, factures"),
    ("rh", "RH — agents et formateurs"),
    ("actualites", "Actualités — publications et abonnés"),
    ("territoire", "Découpage territorial — directions, régions, provinces"),
    ("supervision", "Supervision — connexions et sécurité"),
]

# Regroupement par theme pour la page de delegation (ordre = utilite decroissante).
DOMAINES_GROUPES = [
    ("Scolarité & finances", ["scolarite", "finances", "offre"]),
    ("Prestations & administration", ["facturation", "rh", "territoire"]),
    ("Communication & supervision", ["actualites", "supervision"]),
]

LIBELLES_DOMAINES = dict(DOMAINES)


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
