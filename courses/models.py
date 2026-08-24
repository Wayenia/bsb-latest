from datetime import timedelta

from django.db import models
from django.core.validators import FileExtensionValidator
from accounts.models import phone_validator
from django.utils import timezone

##########   COMMON MODEL   ##########
class TimeStampModel(models.Model):
    date_creation= models.DateTimeField(auto_now_add=True, verbose_name="Creer le")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Modifier le")

    class Meta:
        abstract = True


##########   ABOUT LEVEL    ##########

class Region(TimeStampModel):
    nom_region = models.CharField(max_length=225, unique=True, verbose_name="Nom de la région")
    chef_lieu = models.CharField(max_length=225, verbose_name="Chef-lieu")

    def __str__(self):
        return self.nom_region

    class Meta:
        verbose_name = "Région"
        verbose_name_plural = "Régions"
        permissions = [
            ("gerer_regions", "Créer/modifier/supprimer une région ou province"),
        ]


class Province(TimeStampModel):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, verbose_name="Région", related_name="provinces")
    nom_province = models.CharField(max_length=225, unique=True, verbose_name="Nom de la province")
    chef_lieu = models.CharField(max_length=225, verbose_name="Chef-lieu")

    def __str__(self):
        return self.nom_province

    class Meta:
        verbose_name = "Province"
        verbose_name_plural = "Provinces"
        
# DG
class DG(models.Model):
    full_name = models.CharField(max_length=225, unique=True, verbose_name="Nom complet")
    photo = models.ImageField(
        upload_to='team/dg/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        help_text="Format accepté: JPG, JPEG, PNG, WEBP",
        verbose_name="Photo"
    )
    position = models.CharField(
        max_length=200,
        default="Directeur Général",
        verbose_name="Position"
    )
    message = models.TextField(
        verbose_name="Message/Citation",
        help_text="Message inspirant ou citation du DG"
    )
    commitment = models.TextField(
        verbose_name="Engagement",
        help_text="Texte court sur l'engagement",
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif",
        help_text="Indique si ce DG est l'actuel directeur général"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Directeur Général"
        verbose_name_plural = "Directeur Général"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.position}"

    def save(self, *args, **kwargs):
        """Ensure only one active DG exists"""
        if self.is_active:
            # Deactivate all other DGs
            DG.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

# MEMBER
class Membre(models.Model):
    full_name = models.CharField(max_length=225, unique=True, verbose_name="Nom complet")
    photo = models.ImageField(
        upload_to='team/members/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        help_text="Format accepté: JPG, JPEG, PNG, WEBP",
        verbose_name="Photo"
    )
    position = models.CharField(
        max_length=200,
        verbose_name="Poste/Position"
    )
    description = models.TextField(
        verbose_name="Description",
        help_text="Brève description de l'expertise ou du rôle"
    )
    order = models.IntegerField(
        default=0,
        verbose_name="Ordre d'affichage",
        help_text="Ordre d'apparition sur la page (plus petit = premier)"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif",
        help_text="Indique si ce membre est actuellement actif"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Membre de l'administration"
        verbose_name_plural = "Membres de l'administration"
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.full_name} - {self.position}"

##########  COURSES LEVEL    ##########

# DIRECTION
class Direction_reg(TimeStampModel):
    directeur = models.ForeignKey(DG, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Directeur")#
    nom_direction = models.CharField(max_length=225, unique=True, verbose_name="Nom de la direction")
    chef_lieu = models.CharField(max_length=225, verbose_name="Chef-lieu")#
    region = models.CharField(max_length=225, verbose_name="Region")#
    
    def __str__(self):
        return self.nom_direction
    
    class Meta:
        verbose_name = "Direction regionale"
        verbose_name_plural = "Directions regionales"
        permissions = [
            ("gerer_directions", "Créer/modifier/supprimer une direction inter-régionale"),
        ]


# FIELD
TITRE_PROFESSIONNEL_CHOICE = [
    ("CQP", "Certificat de Qualification Professionnelle"),
    ("BQP", "Brevet de Qualification Professionnelle"),
    ("BPT", "Brevet Professionnel de Technicien"),
    ("BPTS", "Brevet Professionnel de Technicien Spécialiste"),
]

class Filiere(TimeStampModel):
    nom_filiere = models.CharField(max_length=225, unique=True, verbose_name="Nom de la filiere")
    nom_diplome = models.CharField(max_length=225, verbose_name="Nom du diplome",null=True,blank=True)# a supprimmer
    titre_professionnel = models.CharField(max_length=10, choices=TITRE_PROFESSIONNEL_CHOICE, verbose_name="Titre professionnel", null=True,blank=True)  # ← remplace nom_diplom
    niveau_diplome = models.TextField(blank=True, null=True, verbose_name="Niveau du diplome")
    texte_defilante = models.TextField(blank=True, null=True, verbose_name="Texte défilant")
    is_active = models.BooleanField(default=True)
    curricula = models.FileField(
        upload_to='curricula_filieres/', null=True, blank=True,
        verbose_name="Curricula (programme de formation)"
    )

    
    def __str__(self):
        return self.nom_filiere
    
    class Meta:
        verbose_name = "Filiere"
        verbose_name_plural = "Filieres"
        permissions = [
            ("gerer_metiers", "Créer/modifier/supprimer un métier"),
        ]

# CENTER
class CentreFormation(TimeStampModel):
    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Province", related_name="centre_formations")  # ← AJOUTER
    direction = models.ForeignKey(Direction_reg, on_delete=models.CASCADE, verbose_name="Direction du centre", related_name="centre_formations", null=True, blank=True)
    parent=models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True,verbose_name="Centre parent",related_name="centre_enfants")
    nom_centre = models.CharField(max_length=225, unique=True, verbose_name="Nom du centre")
    code_centre = models.CharField(max_length=10, unique=True, blank=True, null=True, verbose_name="Code du centre")
    filieres = models.ManyToManyField(Filiere, through="CentreEtFiliere", verbose_name="Filieres")
    niveau_centre = models.IntegerField(verbose_name="Niveau du centre", null=True, blank=True)
    adresse = models.CharField(max_length=225, verbose_name="Adresse/localisition du centre",null=True, blank=True)
    ville = models.CharField(max_length=225, verbose_name="Ville du centre", null=True, blank=True)
    tel=models.CharField(max_length=20, verbose_name="Numéro de téléphone du centre",null=True, blank=True, validators=[phone_validator])

    
    def get_descendants(self):
        """Retourne la liste des centres enfants jusqu'aux feuilles"""
        descendants = []
        enfants = self.centre_enfants.all()
        for enfant in enfants:
            descendants.append(enfant)
            descendants.extend(enfant.get_descendants())
        return descendants
    
    def get_ancestors(self):
        """Retourne la liste des centres parents jusqu'à la racine"""
        ancestors = []
        parent = self.parent
        while parent:
            ancestors.append(parent)
            parent = parent.parent
        return ancestors
    
    def visible_centres(self):
        """Retourne les centres visibles pour ce centre (soit lui-même, soit ses enfants)"""
        if self.centre_enfants.exists():
            return [self] + self.get_descendants()
        return [self]
    
    def __str__(self):
        return self.nom_centre
    
    class Meta:
        verbose_name = "Centre de formation"
        verbose_name_plural = "Centres de formation"
        permissions = [
            ("gerer_centres", "Créer/modifier/supprimer un centre de formation"),
        ]


# MODULE
class Module(TimeStampModel):
    filieres = models.ManyToManyField(Filiere, related_name="modules", blank=True, verbose_name="Métiers")
    nom_module = models.CharField(max_length=225, verbose_name="Nom du module")
    volume_h_cours = models.IntegerField(verbose_name="Volume d'heure")

    def __str__(self):
        return self.nom_module
    
    class Meta:
        verbose_name = "Module"
        verbose_name_plural = "Modules"
        permissions = [
            ("gerer_modules", "Gérer les modules et cours"),
        ]


# COURSE
class Cours(TimeStampModel):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, verbose_name="Module")
    libelle_cours = models.CharField(max_length=225, verbose_name="Libelle du cours")
    volume_h_cours = models.CharField(max_length=225, verbose_name="Volume d'heure")

    def __str__(self):
        return self.libelle_cours
    
    class Meta:
        verbose_name = "Cours"
        verbose_name_plural = "Cours"

class AnneeScolaire(models.Model):
     libelle_anne=models.CharField(max_length=25)
     date_creation = models.DateTimeField(auto_now_add=True, null=True, verbose_name="Date de création")

     def __str__(self):
         return self.libelle_anne
     class Meta:
         verbose_name = "Année de formation"
         verbose_name_plural = "Années de formation"
         permissions = [
             ("gerer_annees", "Gérer les années de formation"),
         ]

# CENTER-FIELD JUNCTION

TYPE_FORMATION_CHOICE = [
    ("initiale", "Initiale"),
    ("continue", "Continue"),
    ("modulaire_qualifiante", "Modulaire qualifiante"),
]


def _format_duree_en_jours(total_jours):
    """Formate un nombre de jours en texte lisible ("15 jrs", "9 mois",
    "1 an / 2 mois"...) — utilisé par CentreEtFiliere.duree_display, que la
    durée vienne du champ `duree_jours` ou d'un calcul par différence de
    dates."""
    if not total_jours or total_jours <= 0:
        return "—"

    if total_jours < 30:
        return f"{total_jours} jr{'s' if total_jours > 1 else ''}"

    mois_total = total_jours // 30
    jours_restants = total_jours % 30

    if mois_total >= 12:
        annees = mois_total // 12
        mois_restants = mois_total % 12
        parties = [f"{annees} an{'s' if annees > 1 else ''}"]
        if mois_restants:
            parties.append(f"{mois_restants} mois")
        if jours_restants:
            parties.append(f"{jours_restants} jrs")
        return " / ".join(parties)

    parties = [f"{mois_total} mois"]
    if jours_restants:
        parties.append(f"{jours_restants} jrs")
    return " / ".join(parties)


class CentreEtFiliere(models.Model):
    centre = models.ForeignKey(CentreFormation, on_delete=models.CASCADE, verbose_name="Centre")
    type_formation = models.CharField(max_length=30, choices=TYPE_FORMATION_CHOICE, verbose_name="Type de formation", null=True,blank=True)  # ← AJOUTE
    filiere = models.ForeignKey(Filiere, on_delete=models.CASCADE, verbose_name="Filiere associee")
    is_active = models.BooleanField(default=True, verbose_name="Rendre actif")
    communique = models.FileField(
    upload_to='communiques_filieres/',
    null=True,
    blank=True,
    verbose_name="Communique de la formation"
    )
    annee_prog=models.ForeignKey(AnneeScolaire,on_delete=models.SET_NULL,null=True,blank=True,verbose_name="Année de formation")
    date_lancement = models.DateTimeField(null=True, blank=True, verbose_name="Date de lancement", default=timezone.now)
    duree_jours = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Durée (en jours)",
        help_text="Ex : 15, 45, 270 (≈ 9 mois). La date de fin est calculée automatiquement."
    )
    date_fin = models.DateTimeField(null=True, blank=True, verbose_name="Date de fin (calculée automatiquement)")
    date_limite_inscription = models.DateTimeField(null=True, blank=True, verbose_name="Date limite d'inscription")
    date_creation = models.DateTimeField(auto_now_add=True, null=True, verbose_name="Date de création")

    def __str__(self):
        return f"Centre: {self.centre}, Métier: {self.filiere}"

    def save(self, *args, **kwargs):
        if self.duree_jours and self.date_lancement:
            self.date_fin = self.date_lancement + timedelta(days=self.duree_jours)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Programmer une formation"
        verbose_name_plural = "Programmations"

        unique_together = ('centre', 'filiere')
        permissions = [
            ("gerer_programmations", "Gérer les associations centre-métier"),
        ]

    @property
    def duree_display(self):
        if self.duree_jours:
            return _format_duree_en_jours(self.duree_jours)
        if self.date_lancement and self.date_fin:
            total_jours = (self.date_fin - self.date_lancement).days
            if total_jours > 0:
                return _format_duree_en_jours(total_jours)
        return "—"


# ─────────────────────────────────────────────
# STATISTIQUES RÉELLES — effectifs formés (saisie manuelle DSI)
# ─────────────────────────────────────────────
class EffectifReel(models.Model):
    """Effectif réel (H/F) formé pour une formation (CentreEtFiliere), pour
    un site donné. Saisi/corrigé manuellement par le DSI via le module
    "Statistiques réelles" : l'app ne sait pas qui a effectivement suivi la
    formation, contrairement aux inscriptions qu'elle gère nativement."""
    formation = models.ForeignKey(
        CentreEtFiliere, on_delete=models.CASCADE, related_name="effectifs_reels",
        verbose_name="Formation"
    )
    site = models.CharField(
        max_length=150, blank=True, default="",
        verbose_name="Site/antenne", help_text="Laisser vide pour le centre principal"
    )
    # Une formation (CentreEtFiliere) n'est PAS unique par année (unique_together
    # = centre+filière seulement, réutilisée d'une année sur l'autre) — les
    # effectifs doivent donc porter leur propre année pour ne pas s'écraser
    # d'une année sur l'autre.
    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.CASCADE, null=True, blank=True,
        related_name="effectifs_reels", verbose_name="Année de formation"
    )
    effectif_hommes = models.PositiveIntegerField(default=0, verbose_name="Effectif hommes inscrits")
    effectif_femmes = models.PositiveIntegerField(default=0, verbose_name="Effectif femmes inscrits")

    # Statistiques réelles — "RESULTATS AUX EXAMENS DE CERTIFICATION" : l'app
    # gère les inscrits, mais ni la présence à l'examen ni la réussite
    # (admission) ne sont des données qu'elle connaît — saisie manuelle DSI.
    effectif_hommes_presents = models.PositiveIntegerField(default=0, verbose_name="Effectif hommes présents à l'examen")
    effectif_femmes_presents = models.PositiveIntegerField(default=0, verbose_name="Effectif femmes présentes à l'examen")
    effectif_hommes_admis = models.PositiveIntegerField(default=0, verbose_name="Effectif hommes admis")
    effectif_femmes_admis = models.PositiveIntegerField(default=0, verbose_name="Effectif femmes admises")

    # Statistiques réelles — "RÉPARTITION DES APPRENANTS VIVANT AVEC UN
    # HANDICAP PAR MÉTIER ET PAR SEXE" : saisie/corrigée manuellement par le
    # DSI, par site/formation, agrégée par métier à l'export — le modèle
    # Excel les pré-suggère à partir du handicap déclaré à l'inscription
    # (Eleve.a_handicap/type_handicap) tant qu'aucun EffectifReel n'existe
    # encore pour cette formation (cf. courses/views_stats_reel.py), mais le
    # DSI reste seul responsable de la valeur finale.
    effectif_hommes_handicap_moteur = models.PositiveIntegerField(default=0, verbose_name="Handicap moteur — hommes")
    effectif_femmes_handicap_moteur = models.PositiveIntegerField(default=0, verbose_name="Handicap moteur — femmes")
    effectif_hommes_handicap_visuel = models.PositiveIntegerField(default=0, verbose_name="Handicap sensoriel (visuel) — hommes")
    effectif_femmes_handicap_visuel = models.PositiveIntegerField(default=0, verbose_name="Handicap sensoriel (visuel) — femmes")
    effectif_hommes_handicap_auditif = models.PositiveIntegerField(default=0, verbose_name="Handicap sensoriel (auditif) — hommes")
    effectif_femmes_handicap_auditif = models.PositiveIntegerField(default=0, verbose_name="Handicap sensoriel (auditif) — femmes")
    effectif_hommes_epilepsie = models.PositiveIntegerField(default=0, verbose_name="Maladie invalidante — épilepsie (hommes)")
    effectif_femmes_epilepsie = models.PositiveIntegerField(default=0, verbose_name="Maladie invalidante — épilepsie (femmes)")
    effectif_hommes_asthme = models.PositiveIntegerField(default=0, verbose_name="Maladie invalidante — asthme (hommes)")
    effectif_femmes_asthme = models.PositiveIntegerField(default=0, verbose_name="Maladie invalidante — asthme (femmes)")
    effectif_hommes_autres_maladies = models.PositiveIntegerField(default=0, verbose_name="Autres maladies — hommes")
    effectif_femmes_autres_maladies = models.PositiveIntegerField(default=0, verbose_name="Autres maladies — femmes")

    date_maj = models.DateTimeField(auto_now=True, verbose_name="Dernière mise à jour")

    @property
    def effectif_total(self):
        return self.effectif_hommes + self.effectif_femmes

    @property
    def effectif_total_presents(self):
        return self.effectif_hommes_presents + self.effectif_femmes_presents

    @property
    def effectif_total_admis(self):
        return self.effectif_hommes_admis + self.effectif_femmes_admis

    @property
    def effectif_total_handicap(self):
        """Total apprenants en situation de handicap/maladie invalidante,
        toutes catégories confondues (H+F) — les 6 catégories de la
        Répartition par métier et par sexe."""
        return (
            self.effectif_hommes_handicap_moteur + self.effectif_femmes_handicap_moteur
            + self.effectif_hommes_handicap_visuel + self.effectif_femmes_handicap_visuel
            + self.effectif_hommes_handicap_auditif + self.effectif_femmes_handicap_auditif
            + self.effectif_hommes_epilepsie + self.effectif_femmes_epilepsie
            + self.effectif_hommes_asthme + self.effectif_femmes_asthme
            + self.effectif_hommes_autres_maladies + self.effectif_femmes_autres_maladies
        )

    def __str__(self):
        return f"{self.formation} — {self.site or 'centre principal'} ({self.annee_scolaire or 'année non précisée'})"

    class Meta:
        verbose_name = "Effectif réel formé"
        verbose_name_plural = "Effectifs réels formés"
        unique_together = ("formation", "site", "annee_scolaire")


#Type de frais
class TypeFrais(models.Model):
    libelle=models.CharField(max_length=100,verbose_name="Type de frais")
    est_frais_de_dossier = models.BooleanField(
        default=False,
        verbose_name="Frais de dossier",
        help_text="Ce type de frais doit être réglé en priorité, avant tout autre type de frais de l'inscription."
    )

    def __str__(self):
        return self.libelle
    class Meta:
        verbose_name="Type de frais "


class TrancheFrais(models.Model):
    """
    Tranche de paiement d'un type de frais. Le montant réel d'une tranche pour
    une formation donnée se calcule à partir du pourcentage : montant_dette *
    pourcentage / 100 (le montant du type de frais varie selon la formation,
    via Frais.montant — le pourcentage est donc la seule donnée stable ici).
    """
    type_frais = models.ForeignKey(TypeFrais, on_delete=models.CASCADE, related_name="tranches", verbose_name="Type de frais")
    libelle = models.CharField(max_length=100, verbose_name="Libellé de la tranche")
    ordre = models.PositiveIntegerField(default=1, verbose_name="Ordre de paiement")
    pourcentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Pourcentage du montant total")
    est_primordiale = models.BooleanField(
        default=False,
        verbose_name="Tranche primordiale",
        help_text="Doit être intégralement réglée avant toute autre tranche ou tout autre type de frais."
    )

    def __str__(self):
        return f"{self.type_frais} — {self.libelle} ({self.pourcentage}%)"

    class Meta:
        verbose_name = "Tranche de frais"
        verbose_name_plural = "Tranches de frais"
        ordering = ["type_frais", "ordre"]
        constraints = [
            models.UniqueConstraint(
                fields=["type_frais"],
                condition=models.Q(est_primordiale=True),
                name="une_seule_tranche_primordiale_par_type_frais",
            ),
        ]


# FEE
class Frais(TimeStampModel):
    formation=models.ForeignKey(CentreEtFiliere,on_delete=models.CASCADE,verbose_name="Formations",null=True)
    type_frais=models.ForeignKey(TypeFrais,on_delete=models.CASCADE,verbose_name="Frais",default="Scolarité")
    montant = models.FloatField(verbose_name="Motant")

    def __str__(self):
        return f"{self.formation} {self.type_frais} {self.montant}"
    
    class Meta:
        verbose_name = "Frais"
        verbose_name_plural = "Frais"
        permissions = [
            ("gerer_frais", "Gérer les frais et types de frais"),
        ]

# SUBSCRIPTION
class Inscription(models.Model):
    STATUT_CHOICE = [
        ("en_cours", "En cours de traitement"),
        ("valide", "Validé - Non payé"),
        ("Valide","Validé-partiellement payé "),
        ("valide_paye", "Validé et payé avec succès"),
        ("rejete", "Rejeté"),
    ]

    eleve = models.ForeignKey("accounts.Eleve", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Eleve")
    formation = models.ForeignKey(CentreEtFiliere, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Formation")
    date_inscription = models.DateTimeField(auto_now_add=True, verbose_name="Date d'inscription")
    annee_scolaire = models.ForeignKey(AnneeScolaire,on_delete=models.CASCADE, null=True, blank=True, verbose_name="Annee scolaire")
    statut = models.CharField(max_length=30, choices=STATUT_CHOICE, default="en_cours", verbose_name="Statut de l'inscription")
    date_validation=models.DateTimeField(blank=True,null=True)
    motif_rejet=models.TextField(blank=True,null=True)

    # Personne à prévenir en cas de besoin
    TYPE_PERSONNE_CONTACT_CHOICES = [
        ("parent", "Parent"),
        ("organisation", "Organisation/Parrain"),
        ("les_deux", "Parent et Organisation/Parrain"),
    ]
    type_personne_contact = models.CharField(
        max_length=20, choices=TYPE_PERSONNE_CONTACT_CHOICES, blank=True, null=True,
        verbose_name="Type de personne à prévenir"
    )
    # Parent
    personne_contact_nom = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nom du parent")
    personne_contact_prenom = models.CharField(max_length=100, blank=True, null=True, verbose_name="Prénom du parent")
    personne_contact_fonction = models.CharField(max_length=100, blank=True, null=True, verbose_name="Fonction du contact")
    personne_contact_tel = models.CharField(max_length=100, blank=True, null=True, verbose_name="Contact du parent", validators=[phone_validator])
    personne_contact_email = models.EmailField(blank=True, null=True, verbose_name="Email du parent")
    # Organisation / parrain
    organisation_nom = models.CharField(max_length=150, blank=True, null=True, verbose_name="Nom de l'organisation/parrain")
    organisation_adresse = models.CharField(max_length=225, blank=True, null=True, verbose_name="Adresse de l'organisation/parrain")
    organisation_tel = models.CharField(max_length=100, blank=True, null=True, verbose_name="Téléphone de l'organisation/parrain", validators=[phone_validator])
    organisation_email = models.EmailField(blank=True, null=True, verbose_name="Email de l'organisation/parrain")

    # Réinscription après rejet : pointe vers l'inscription rejetée à laquelle celle-ci fait suite
    id_inscription_rejeter = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reinscriptions", verbose_name="Inscription rejetée d'origine"
    )

    # Statistiques réelles (saisies manuellement par le DSI — voir module
    # "Statistiques réelles") : l'app gère les inscriptions mais ne sait pas,
    # par exemple, si l'apprenant est en internat/résidentiel ou en duale.
    MODE_FORMATION_CHOICES = [
        ("residentielle", "Résidentielle"),
        ("duale", "Duale"),
    ]
    mode_formation = models.CharField(
        max_length=20, choices=MODE_FORMATION_CHOICES, blank=True, null=True,
        verbose_name="Mode de formation"
    )
    observations_reel = models.TextField(
        blank=True, null=True, verbose_name="Observations (statistiques réelles)"
    )

    def __str__(self):
        return self.statut

    @property
    def libelle_statut_paiement(self):
        """Libellé affiché à l'apprenant : reflète l'avancement réel du paiement
        plutôt que le seul statut d'inscription (qui reste "valide" quel que
        soit le montant déjà payé)."""
        if self.statut != 'valide':
            return self.get_statut_display()
        total = sum(d.montant_total for d in self.dettes.all())
        paye = sum(d.montant_paye() for d in self.dettes.all())
        if total <= 0 or paye <= 0:
            return "Validé - Non payé"
        if paye < total:
            return "Validé - Partiellement payé"
        return "Validé - Payé"

    def dette_et_tranche_bloquantes(self):
        """
        Retourne (dette, tranche_frais) de la dette/tranche qui doit être
        réglée en priorité avant toute autre dette de cette inscription — ou
        (None, None) si aucune ne bloque.

        Ordre de priorité :
        1. Le(s) type(s) de frais marqué(s) « frais de dossier »
           (TypeFrais.est_frais_de_dossier) : ils doivent être intégralement
           soldés avant tout le reste, quel que soit l'ordre des dettes ou
           l'existence d'une tranche primordiale ailleurs dans l'inscription.
           `tranche_frais` vaut alors la prochaine tranche à régler pour
           cette dette (logique de tranches inchangée), ou None si ce type
           de frais n'a pas de tranches (réglé en un seul versement).
        2. À défaut, la tranche primordiale non soldée de la première dette
           (par id) qui en a une — comportement historique inchangé.
        """
        dettes = list(
            self.dettes.select_related('frais_formation__type_frais').prefetch_related(
                'frais_formation__type_frais__tranches', 'paiements'
            ).order_by('id')
        )

        for dette in dettes:
            if dette.frais_formation.type_frais.est_frais_de_dossier and dette.reste_a_payer() > 0:
                return dette, dette.tranche_a_payer()

        for dette in dettes:
            primordiale = dette.tranche_primordiale()
            if primordiale and dette.reste_pour_tranche(primordiale) > 0:
                return dette, primordiale
        return None, None

    class Meta:
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        permissions = [
            ("voir_inscriptions", "Voir les candidatures"),
            ("valider_inscription", "Valider une candidature"),
            ("rejeter_inscription", "Rejeter une candidature"),
        ]

class Dette(models.Model):
    STATUT_CHOICES=[
        ("non_soldé","Non soldé"),
        ("soldé","Soldée"),
    ]
    inscription=models.ForeignKey(Inscription,on_delete=models.CASCADE,verbose_name="Inscription",related_name="dettes")
    frais_formation=models.ForeignKey(Frais,on_delete=models.CASCADE,verbose_name="Frais de la formation")
    montant_total=models.FloatField(verbose_name="Montant total lié au type de frais")
    etat_dette=models.CharField(max_length=20,choices=STATUT_CHOICES,default='non_soldé')
    date_echeance=models.DateTimeField(blank=True,null=True)

    def montant_paye(self):
         return sum(p.montant_paiement for p in self.paiements.all())

    def reste_a_payer(self):
        return self.montant_total-self.montant_paye()

    def montant_pour_tranche(self, tranche_frais):
        """Montant dû pour cette tranche, calculé à partir de son pourcentage."""
        return self.montant_total * float(tranche_frais.pourcentage) / 100

    def paye_pour_tranche(self, tranche_frais):
        return sum(
            p.montant_paiement for p in self.paiements.all()
            if p.tranche_frais_id == tranche_frais.id
        )

    def reste_pour_tranche(self, tranche_frais):
        return self.montant_pour_tranche(tranche_frais) - self.paye_pour_tranche(tranche_frais)

    def tranche_primordiale(self):
        """Tranche primordiale du type de frais de cette dette, si elle existe."""
        return self.frais_formation.type_frais.tranches.filter(est_primordiale=True).first()

    def tranche_a_payer(self):
        """
        Prochaine tranche à régler pour cette dette : la primordiale si elle
        n'est pas soldée, sinon la première tranche (par ordre) encore due.
        None si le type de frais n'a pas de tranches (dette payée en un bloc)
        ou si toutes les tranches sont soldées.
        """
        tranches = list(self.frais_formation.type_frais.tranches.all())
        if not tranches:
            return None
        primordiale = next((t for t in tranches if t.est_primordiale), None)
        if primordiale and self.reste_pour_tranche(primordiale) > 0:
            return primordiale
        for t in sorted(tranches, key=lambda t: t.ordre):
            if self.reste_pour_tranche(t) > 0:
                return t
        return None

    def montant_a_payer(self):
        """Montant restant dû pour la prochaine tranche à régler, ou le reste global si pas de tranches."""
        tranche = self.tranche_a_payer()
        if tranche:
            return self.reste_pour_tranche(tranche)
        return self.reste_a_payer()

    def bloquee_par_autre_dette(self):
        """
        True si une tranche primordiale d'une AUTRE dette de la même inscription
        doit être réglée avant que celle-ci puisse recevoir un paiement.
        """
        dette_bloquante, _ = self.inscription.dette_et_tranche_bloquantes()
        return dette_bloquante is not None and dette_bloquante.id != self.id

    def tranches_detail(self):
        """
        Détail de chaque tranche du type de frais de cette dette : montant,
        payé, reste, si elle est soldée, et si c'est la tranche à régler
        actuellement (en tenant compte du blocage éventuel par une autre dette).
        """
        tranche_cible = self.tranche_a_payer()
        bloquee = self.bloquee_par_autre_dette()
        detail = []
        for tranche in self.frais_formation.type_frais.tranches.all().order_by('ordre'):
            montant = self.montant_pour_tranche(tranche)
            paye = self.paye_pour_tranche(tranche)
            reste = max(montant - paye, 0)
            est_cible = tranche_cible is not None and tranche.id == tranche_cible.id
            detail.append({
                'tranche': tranche,
                'montant': montant,
                'paye': paye,
                'reste': reste,
                'soldee': reste <= 0,
                'est_cible': est_cible,
                'payable': est_cible and not bloquee,
            })
        return detail

    def __str__(self):
        return f"{self.inscription} {self.frais_formation} {self.montant_total}"

    class Meta:
      verbose_name="Dette lié a l'inscription d'un apprenant"
      verbose_name_plural="Dettes liées à l'inscription d'un apprenant"

# DOCUMENTS
class PieceJointeInscription(models.Model):
    TYPE_PIECE = [
        ("type_1", "CNIB"),
        ("type_2", "BULLETIN"),
        ("type_3", "PHOTO"),
        ("type_4", "Identification"),
        ("type_5", "Diplome/Attestation"),
    ]
    formation = models.ForeignKey(CentreEtFiliere, on_delete=models.CASCADE, verbose_name="Formation")
    # formation = models.ForeignKey(Filiere, on_delete=models.CASCADE, verbose_name="Metier")
    libelle_piece = models.CharField(max_length=225, verbose_name="Libelle de la piece")
    type_piece = models.CharField(max_length=30, choices=TYPE_PIECE, default="type_1", verbose_name="Type de piece")
    est_requis = models.BooleanField(default=True)


    def __str__(self):
        return self.libelle_piece
    
    class Meta:
        verbose_name = "Piece jointe de l'inscription"
        verbose_name_plural = "Pieces jointe de l'inscription"
        permissions = [
            ("telecharger_pieces", "Télécharger les pièces jointes des candidats"),
        ]


#Piece pour suivre les documents d'un élève en fait pur une formation donnée
class DocumentEleve(models.Model):
    inscription=models.ForeignKey(Inscription,on_delete=models.SET_NULL, null=True, blank=True,verbose_name="Inscriptions")
    piece_requise=models.ForeignKey(PieceJointeInscription,on_delete=models.SET_NULL, null=True, blank=True,verbose_name="Documents requis")
    piece = models.FileField(
        upload_to='eleves/pieces', blank=True, null=True, verbose_name="Fichier",
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])],
    )
    date_depot = models.DateTimeField(blank=True,null=True, verbose_name="Date de depot")

    def __str__(self):
        return f"{self.inscription} - {self.piece_requise}"
    


# PAYMENT
class Paiement(models.Model):
    # PAYMENT_STATUS = [
    #     ("paye", "Paye"),
    #     ("non_paye", "Non paye"),
    # ]
    PAYMENT_MODE = [
        ("chèque", "Chèque"),
        ("mobile", "Mobile Money"),
        ("espece", "Espèce"),
    ]
    dette=models.ForeignKey(Dette,on_delete=models.CASCADE,verbose_name="Dettes",related_name='paiements',null=True)
    montant_paiement = models.FloatField(verbose_name="Montant")
    date_paiement = models.DateTimeField(default=timezone.now ,verbose_name="Date de Paiement")
    mode_paiement = models.CharField(max_length=30, choices=PAYMENT_MODE, default="espece", verbose_name="Mode de paiement")
    tranche = models.IntegerField(verbose_name="Tranche de paiement")
    tranche_frais = models.ForeignKey(
        TrancheFrais, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Tranche de frais soldée",
        help_text="Tranche du type de frais à laquelle ce versement est affecté (le cas échéant)."
    )
    numero_quittance=models.CharField(  max_length=100, unique=True,
        null=True, blank=True, verbose_name="Numéro de quittance"
        )
    motif_derogation = models.TextField(
        blank=True, null=True, verbose_name="Motif de la dérogation",
        help_text="Obligatoire si le montant versé est inférieur au montant dû pour une tranche primordiale."
    )
    piece_jointe_derogation = models.FileField(
        upload_to='paiements/derogations/', blank=True, null=True,
        verbose_name="Pièce jointe justificative de la dérogation",
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])],
    )
    effectue_par = models.ForeignKey(
    'accounts.Utilisateur',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    verbose_name="Paiement effectué par",
    related_name="paiements_effectues"
    )
    cree_par = models.ForeignKey(
        'accounts.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        related_name="paiements_crees"
    )
    
    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        permissions = [
            ("encaisser_paiement", "Encaisser un paiement"),
            ("gerer_paiements", "Modifier/supprimer un paiement"),
        ]

    def __str__(self):
        return f"{self.inscription} - {self.tranche}- {self.dette}"

    def _code_centre(self):
        centre = self.dette.inscription.formation.centre if self.dette and self.dette.inscription.formation else None
        return centre.code_centre if centre and centre.code_centre else "CENTRE"

    def save(self, *args, **kwargs):
        from django.db import transaction, IntegrityError
        if not self.numero_quittance:
            annee = timezone.now().year
            code_centre = self._code_centre()
            dernier = Paiement.objects.filter(
                numero_quittance__startswith=f"QUIT-{annee}-{code_centre}-"
            ).count() + 1
            for _ in range(20):
                self.numero_quittance = f"QUIT-{annee}-{code_centre}-{dernier:04d}"
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    self.numero_quittance = None
                    dernier += 1
                    continue
            raise IntegrityError("Impossible de générer un numéro de quittance unique après plusieurs tentatives.")
        return super().save(*args, **kwargs)
        
#Realtion entre administrationmembre et centre de formation pour la gestion des centres de formation
# class Affectation(models.Model):
#      membre=models.ForeignKey("accounts.MembreAdministration",on_delete=models.CASCADE,verbose_name="Membre de l'administration")
#      centre=models.ForeignKey(CentreFormation,on_delete=models.CASCADE,verbose_name="Centre de formation")
#      date_debut=models.DateField(verbose_name="Date de debut")
#      date_fin=models.DateField(verbose_name="Date de fin",null=True, blank=True)


# MODÈLE MARQUEUR — ne porte aucune donnée, sert uniquement à rattacher des
# permissions transverses qui ne concernent pas un seul modèle métier précis.
class PermissionsPlateforme(models.Model):
    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ("voir_statistiques", "Voir les statistiques"),
            ("exporter_donnees", "Exporter des données (CSV/Excel/PDF)"),
            ("rechercher_tous_centres", "Rechercher un apprenant dans tous les centres (paiements)"),
            ("gerer_statistiques_reelles", "Saisir et consulter le bilan des effectifs formés (listes nominatives)"),
        ]