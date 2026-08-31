"""Destinataires du rapport d'inspection.

Les adresses vivent en base plutot que dans .env : ajouter ou retirer un
inspecteur ne doit pas demander une modification de fichier ni une recreation
de conteneur. Les adresses declarees dans AUDIT_DESTINATAIRES restent lues, et
s'ajoutent a celles-ci — une installation deja configuree continue de
fonctionner sans rien changer.
"""
from django.db import models


class DestinataireRapport(models.Model):
    email = models.EmailField(unique=True, verbose_name="Adresse e-mail")
    nom = models.CharField(max_length=150, blank=True, verbose_name="Nom du destinataire")
    fonction = models.CharField(max_length=150, blank=True, verbose_name="Fonction")
    # Desactiver plutot que supprimer : on garde trace de qui recevait le
    # rapport, ce qui compte pour un dispositif de surveillance.
    actif = models.BooleanField(default=True, verbose_name="Reçoit le rapport")
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name="Ajouté le")

    class Meta:
        ordering = ['nom', 'email']
        verbose_name = "Destinataire du rapport d'audit"
        verbose_name_plural = "Destinataires du rapport d'audit"
        permissions = [
            ('gerer_destinataires_audit', "Gérer les destinataires du rapport d'inspection"),
        ]

    def __str__(self):
        return f"{self.nom} <{self.email}>" if self.nom else self.email

    @classmethod
    def adresses_actives(cls):
        return list(cls.objects.filter(actif=True).values_list('email', flat=True))
