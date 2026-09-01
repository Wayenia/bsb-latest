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


class ReglageDiffusion(models.Model):
    """Periodicite d'envoi automatique du rapport (enregistrement unique).

    Se regle a l'ecran, par clics : frequence, jour et heure. La commande
    `envoyer_rapport_audit --auto`, lancee regulierement par le planificateur,
    lit ce reglage et n'envoie que lorsqu'une echeance est atteinte, sans jamais
    envoyer deux fois la meme (README 9.5).
    """
    DESACTIVE = 'desactive'
    QUOTIDIEN = 'quotidien'
    HEBDOMADAIRE = 'hebdomadaire'
    MENSUEL = 'mensuel'
    FREQUENCES = [
        (DESACTIVE, "Désactivée"),
        (QUOTIDIEN, "Quotidienne"),
        (HEBDOMADAIRE, "Hebdomadaire"),
        (MENSUEL, "Mensuelle"),
    ]
    # Fenetre du rapport selon la frequence, en jours.
    FENETRE = {QUOTIDIEN: 1, HEBDOMADAIRE: 7, MENSUEL: 31}

    frequence = models.CharField(max_length=20, choices=FREQUENCES, default=DESACTIVE,
                                 verbose_name="Fréquence d'envoi")
    heure = models.PositiveSmallIntegerField(default=7, verbose_name="Heure d'envoi")
    jour_semaine = models.PositiveSmallIntegerField(default=0, verbose_name="Jour de la semaine")
    jour_mois = models.PositiveSmallIntegerField(default=1, verbose_name="Jour du mois")
    derniere_diffusion = models.DateTimeField(null=True, blank=True,
                                              verbose_name="Dernière diffusion automatique")

    class Meta:
        verbose_name = "Réglage de diffusion du rapport d'audit"
        verbose_name_plural = "Réglage de diffusion du rapport d'audit"

    def __str__(self):
        return self.get_frequence_display()

    @classmethod
    def charge(cls):
        """Enregistrement unique (cree au premier acces)."""
        objet, _ = cls.objects.get_or_create(pk=1)
        return objet

    @property
    def actif(self):
        return self.frequence != self.DESACTIVE

    @property
    def periode_jours(self):
        from django.conf import settings
        return self.FENETRE.get(self.frequence, getattr(settings, 'AUDIT_PERIODE_JOURS', 7))

    def creneau_courant(self, maintenant):
        """Dernier instant planifie a <= maintenant, ou None si desactive."""
        from datetime import timedelta
        from django.utils import timezone
        if not self.actif:
            return None
        local = timezone.localtime(maintenant)
        base = local.replace(hour=self.heure, minute=0, second=0, microsecond=0)
        if self.frequence == self.QUOTIDIEN:
            creneau = base
            if creneau > local:
                creneau -= timedelta(days=1)
            return creneau
        if self.frequence == self.HEBDOMADAIRE:
            recul = (local.weekday() - self.jour_semaine) % 7
            creneau = base - timedelta(days=recul)
            if creneau > local:
                creneau -= timedelta(days=7)
            return creneau
        if self.frequence == self.MENSUEL:
            jour = min(self.jour_mois, 28)
            creneau = base.replace(day=jour)
            if creneau > local:
                fin_mois_precedent = base.replace(day=1) - timedelta(days=1)
                creneau = fin_mois_precedent.replace(
                    day=jour, hour=self.heure, minute=0, second=0, microsecond=0)
            return creneau
        return None

    def est_du(self, maintenant):
        """Vrai si une echeance non encore honoree est atteinte."""
        creneau = self.creneau_courant(maintenant)
        if creneau is None:
            return False
        return self.derniere_diffusion is None or self.derniere_diffusion < creneau

    def prochaine(self, maintenant):
        """Prochaine echeance planifiee (pour affichage), ou None si desactive."""
        from datetime import timedelta
        creneau = self.creneau_courant(maintenant)
        if creneau is None:
            return None
        if self.frequence == self.QUOTIDIEN:
            return creneau + timedelta(days=1)
        if self.frequence == self.HEBDOMADAIRE:
            return creneau + timedelta(days=7)
        if self.frequence == self.MENSUEL:
            jour = min(self.jour_mois, 28)
            annee = creneau.year + (1 if creneau.month == 12 else 0)
            mois = 1 if creneau.month == 12 else creneau.month + 1
            return creneau.replace(year=annee, month=mois, day=jour)
        return None
