import secrets

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Actualite(models.Model):
    """Publication rédigée par l'administration et diffusée aux abonnés."""

    STATUT_CHOICES = [
        ("brouillon", "Brouillon"),
        ("publiee", "Publiée"),
    ]

    titre = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(max_length=220, unique=True, blank=True, verbose_name="Adresse de la page")
    chapeau = models.CharField(max_length=300, verbose_name="Chapeau",
                               help_text="Résumé affiché dans la liste et dans l'e-mail envoyé aux abonnés.")
    contenu = models.TextField(verbose_name="Contenu")
    image = models.ImageField(upload_to="actualites/", null=True, blank=True, verbose_name="Image")
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                               null=True, blank=True, related_name="actualites", verbose_name="Auteur")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="brouillon", verbose_name="Statut")
    date_publication = models.DateTimeField(null=True, blank=True, verbose_name="Date de publication")
    # Evalue a chaque requete, sans tache planifiee. Le statut en base reste
    # « publiee » : c'est un retrait d'affichage, pas une suppression.
    date_fin_publication = models.DateTimeField(null=True, blank=True, verbose_name="Fin de publication")
    # Empêche un second envoi si l'actualité est modifiée puis republiée.
    abonnes_notifies = models.BooleanField(default=False, verbose_name="Abonnés déjà notifiés")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Actualité"
        verbose_name_plural = "Actualités"
        ordering = ["-date_publication", "-date_creation"]
        permissions = [
            ("gerer_actualites", "Créer/modifier/supprimer une actualité"),
            ("publier_actualite", "Publier une actualité et notifier les abonnés"),
            ("gerer_newsletter", "Consulter et gérer les abonnés à la newsletter"),
        ]

    def __str__(self):
        return self.titre

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.titre)[:200] or "actualite"
            slug, n = base, 2
            while Actualite.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("actualites:detail", args=[self.slug])

    @property
    def est_visible(self):
        """Publiée, date de publication atteinte, et pas (encore) expirée."""
        maintenant = timezone.now()
        if self.statut != "publiee" or not self.date_publication or self.date_publication > maintenant:
            return False
        return not (self.date_fin_publication and self.date_fin_publication <= maintenant)

    @property
    def est_expiree(self):
        """Publiée mais dont la fin de publication est passee (masquee du public)."""
        return bool(self.date_fin_publication and self.date_fin_publication <= timezone.now())


class AbonneNewsletter(models.Model):
    """Adresse inscrite pour recevoir un e-mail à chaque nouvelle actualité."""

    email = models.EmailField(unique=True, verbose_name="Adresse e-mail")
    actif = models.BooleanField(default=True, verbose_name="Abonnement actif")
    # Jeton imprévisible : seul moyen de se désabonner, aucun identifiant en clair dans le lien.
    token = models.CharField(max_length=64, unique=True, editable=False)
    date_inscription = models.DateTimeField(auto_now_add=True)
    date_desinscription = models.DateTimeField(null=True, blank=True)
    # Adresse desactivee automatiquement apres 3 echecs d'envoi consecutifs.
    nb_echecs = models.PositiveSmallIntegerField(default=0, verbose_name="Échecs d'envoi consécutifs")

    class Meta:
        verbose_name = "Abonné à la newsletter"
        verbose_name_plural = "Abonnés à la newsletter"
        ordering = ["-date_inscription"]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def lien_desabonnement(self):
        return reverse("actualites:desabonnement", args=[self.token])


class Annonce(models.Model):
    """Annonce courte affichée dans le bandeau défilant, avec lien cliquable
    optionnel et fenêtre d'affichage (début et expiration)."""

    texte = models.CharField(max_length=200, verbose_name="Texte de l'annonce")
    lien = models.CharField(max_length=300, blank=True, verbose_name="Lien (URL) — optionnel")
    libelle_lien = models.CharField(max_length=60, blank=True, verbose_name="Libellé du lien",
                                    help_text="Texte du bouton cliquable (ex. « En savoir plus »).")
    actif = models.BooleanField(default=True, verbose_name="Affichée")
    ordre = models.PositiveSmallIntegerField(default=0, verbose_name="Ordre d'affichage")
    date_debut = models.DateTimeField(null=True, blank=True, verbose_name="Début d'affichage",
                                      help_text="Vide = tout de suite.")
    date_fin = models.DateTimeField(null=True, blank=True, verbose_name="Expiration",
                                    help_text="Vide = sans expiration.")
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Annonce défilante"
        verbose_name_plural = "Annonces défilantes"
        ordering = ["ordre", "-cree_le"]

    def __str__(self):
        return self.texte

    @property
    def visible(self):
        maintenant = timezone.now()
        if not self.actif:
            return False
        if self.date_debut and self.date_debut > maintenant:
            return False
        return not (self.date_fin and self.date_fin <= maintenant)

    @classmethod
    def actives(cls):
        """Annonces à afficher : actives, commencées, non expirées."""
        from django.db.models import Q
        maintenant = timezone.now()
        return (cls.objects.filter(actif=True)
                .filter(Q(date_debut__isnull=True) | Q(date_debut__lte=maintenant))
                .filter(Q(date_fin__isnull=True) | Q(date_fin__gt=maintenant)))


class AnnonceVue(models.Model):
    """Mémorise qu'un utilisateur a acquitté une annonce : elle ne lui est plus
    réaffichée. Propre au compte (suit l'utilisateur sur tous ses appareils)."""

    annonce = models.ForeignKey(Annonce, on_delete=models.CASCADE, related_name="vues")
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name="annonces_vues")
    vu_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Annonce vue"
        unique_together = ("annonce", "utilisateur")
