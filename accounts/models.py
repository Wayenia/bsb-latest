from django.utils import timezone
import random
import string

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# Format international (E.164) : + suivi de l'indicatif pays puis du numéro
# local. La validation précise du nombre de chiffres selon le pays est faite
# côté client (intl-tel-input) ; ce validateur sert de garde-fou serveur.
phone_validator = RegexValidator(
    regex=r'^\+[1-9]\d{6,14}$',
    message="Le numéro doit être au format international avec l'indicatif du pays (ex : +226 70 00 00 00)."
)

# COMMON MODEL
class Utilisateur(AbstractUser):
    SEXE_CHOICE = [
        ("m", "Masculin"),
        ("f", "Feminin")
    ]
    USER_TYPE = [
        ("eleve", "Eleve"),
        ("formateur", "Formateur"),
        ("admin", "Administrateur"),
        ("membre","Membre Administration"),
        ("dg", "Directeur Général"),
        ("dir", "Directeur Inter-régional"),
        ("gestionnaire", "Directeur de Centre"),
        ("caissier", "Caissière / Caissier"),
        ("agent_comptable", "Agent Comptable"),
        ("deps", "Direction des Études, de la Planification et des Statistiques"),
        ("daf", "Directeur Administratif et Financier"),
    ]
    username = models.CharField(max_length=150, verbose_name="Nom d'utilisateur", unique=True) 
    nom = models.CharField(max_length=150, verbose_name="Nom de famille")
    prenom = models.CharField(max_length=225, verbose_name="Prénom")
    user_type = models.CharField(max_length=20, choices=USER_TYPE, default="eleve", verbose_name="Type d'utilisateur")
    matricule = models.CharField(max_length=150, verbose_name="Matricule", unique=True, null=True, blank=True)
    email = models.EmailField(verbose_name="Adresse email",unique=True,default="ah@gmail.com")
    adresse = models.CharField(max_length=225, verbose_name="Adresse")
    tel = models.CharField(max_length=25, verbose_name="Telephone",null=True,blank=True, validators=[phone_validator])
    sexe = models.CharField(max_length=2, choices=SEXE_CHOICE, default="m", verbose_name="Sexe")
    date_naissance = models.DateField(verbose_name="Date de naissance", null=True, blank=True)
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='Groupes',
        blank=True,
        help_text='Groupe  de l\'utilisateur.',
        related_name="utilisateur_set",
        related_query_name="utilisateur",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='Permissions des utilisateurs',
        blank=True,
        help_text='Permission specifique.',
        related_name="utilisateur_set",
        related_query_name="utilisateur",
    )

    # Rôle métier (user_type) -> nom du groupe Django correspondant. Un utilisateur
    # est automatiquement rattaché à ce groupe à chaque save(), quel que soit
    # l'endroit où le compte est créé/modifié (formulaire RH, admin Django, etc.).
    # 'eleve' est volontairement absent : les élèves ne portent aucune permission.
    ROLE_GROUPS = {
        'admin': 'Admin',
        'dg': 'Directeur Général',
        'dir': 'Directeur Inter-régional',
        'deps': 'DEPS',
        'gestionnaire': 'Directeur de Centre',
        'caissier': 'Caissier',
        'agent_comptable': 'Agent Comptable',
        'formateur': 'Formateur',
        'membre': 'Membre Administration',
        'daf': 'DAF',
    }

    def __str__(self):
        return f"{self.nom} {self.prenom}" if self.nom and self.prenom else self.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        group_name = self.ROLE_GROUPS.get(self.user_type)
        if group_name:
            from django.contrib.auth.models import Group
            group, _ = Group.objects.get_or_create(name=group_name)
            other_role_groups = self.groups.filter(name__in=self.ROLE_GROUPS.values()).exclude(pk=group.pk)
            self.groups.remove(*other_role_groups)
            self.groups.add(group)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Tous les utilisateurs"
        permissions = [
            ("gerer_agents", "Gérer les comptes utilisateurs"),
            ("gerer_permissions", "Gérer les permissions"),
        ]


class Eleve(Utilisateur):
    lieu_naissance = models.CharField(max_length=225, verbose_name="Lieu de naissance")

    numero_identifiant = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Identifiant élève"
    )

    # Statistiques réelles (saisies manuellement par le DSI, absentes du
    # parcours d'inscription — voir module "Statistiques réelles").
    nationalite = models.CharField(
        max_length=100, blank=True, null=True, default="Burkinabè",
        verbose_name="Nationalité"
    )
    niveau_scolaire = models.CharField(
        max_length=150, blank=True, null=True,
        verbose_name="Niveau scolaire"
    )

    def generate_identifiant(self):
        annee = timezone.now().year

        ville_code = (self.lieu_naissance[:3] if self.lieu_naissance else "XXX").upper()

        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        count = Eleve.objects.count() + 1

        return f"BSB-{annee}-{ville_code}-{random_part}-{str(count).zfill(6)}"

    def generate_matricule(self):
        annee = timezone.now().year
        prefix = f"BSB{annee}"

        count = Utilisateur.objects.filter(matricule__startswith=prefix).count() + 1
        matricule = f"{prefix}{str(count).zfill(6)}"

        while Utilisateur.objects.filter(matricule=matricule).exists():
            count += 1
            matricule = f"{prefix}{str(count).zfill(6)}"

        return matricule

    def save(self, *args, **kwargs):
        if not self.matricule:
            self.matricule = self.generate_matricule()

        if not self.numero_identifiant:
            identifiant = self.generate_identifiant()

            while Eleve.objects.filter(numero_identifiant=identifiant).exists():
                identifiant = self.generate_identifiant()

            self.numero_identifiant = identifiant

        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"
        permissions = [
            ("gerer_eleves", "Gérer les comptes apprenants"),
        ]


# TEACHER MODEL
class Formateur(Utilisateur):
    centre = models.ForeignKey('courses.CentreFormation', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Centre de formation associe", related_name="formateurs")
    emploi = models.CharField(max_length=225, verbose_name="Emploi") # don't understand
    specialite = models.CharField(max_length=225, verbose_name="Specialite")
    date_integration = models.DateField(verbose_name="Date d'integration")
    filiere = models.ForeignKey(
        'courses.Filiere',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='formateurs',
        verbose_name="Métier dispensé"
    )
    module = models.ForeignKey(
        'courses.Module',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='formateurs',
        verbose_name="Module dispensé"
    )

    def __str__(self):
        return self.username
    
    class Meta:
        verbose_name = "Formateur"
        verbose_name_plural = "Formateurs"
    
class MembreAdministration(Utilisateur):
     structure=models.ForeignKey('courses.CentreFormation',on_delete=models.SET_NULL,null=True,blank=True,verbose_name="Centre de formation",related_name="membres_administration")
     direction=models.ForeignKey('courses.Direction_reg',on_delete=models.SET_NULL,null=True,blank=True,verbose_name="Direction",related_name="membres_administration")
     emploi=models.CharField(max_length=225, verbose_name="Emploi")
     categorie=models.CharField(max_length=225, verbose_name="Catégorie")
     date_integration=models.DateField(verbose_name="Date d'integration",auto_now_add=True)
     
     
     def clean(self):
         
         if not self.structure and not self.direction:
             raise ValidationError("Un membre de l'administration doit être associé à une structure (centre de formation ou direction).")
     
     def est_direction(self):
         return self.direction_id is not None
     
     def get_centres_visibles(self):
         from courses.models import CentreFormation
         if self.est_direction():
             return CentreFormation.objects.filter(direction_id=self.direction_id)
         descendants = self.structure.get_descendants()
         ids=[self.structure.id]+[descendant.id for descendant in descendants]
         return CentreFormation.objects.filter(id__in=ids)
  

     def __str__(self):
         return f'{self.nom} {self.prenom}' if self.nom and self.prenom else self.username
    
     class Meta:
         verbose_name = "Membre de l'administration"
         verbose_name_plural = "Membres de l'administration"
         
class DirecteurInterRegional(Utilisateur):
    direction=models.ForeignKey('courses.Direction_reg',on_delete=models.SET_NULL,null=True,blank=True,verbose_name="directeurs",related_name="direction_interregionale")

    class Meta:
        verbose_name = "Directeur Inter-régional"
        verbose_name_plural = "Directeurs Inter-régionaux"

    def save(self, *args, **kwargs):
        self.user_type = "dir"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nom} {self.prenom} - {self.direction.nom_direction}"

class DAF(Utilisateur):
    structure = models.ForeignKey(
        'courses.CentreFormation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dafs",
        verbose_name="Centre de rattachement"
    )

    date_integration = models.DateField(
        auto_now_add=True,
        verbose_name="Date d'intégration"
    )

    def save(self, *args, **kwargs):
        self.user_type = "daf"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Directeur Administratif et Financier"
        verbose_name_plural = "Directeurs Administratifs et Financiers"

    def __str__(self):
        return f"{self.nom} {self.prenom}"
    
class Client_prestation(models.Model):

    TYPE_CLIENT = [
        ("personne", "Personne physique"),
        ("entreprise", "Entreprise"),
        ("autre", "Autre"),
    ]

    TYPE_PIECE = [
        ("cni", "Carte Nationale d'Identité"),
        ("passport", "Passeport"),
        ("consulaire", "Carte consulaire"),
        ("militaire", "Carte militaire"),
        ("autre", "Autre"),
    ]

    type_client = models.CharField(max_length=20, choices=TYPE_CLIENT)

    nom = models.CharField(max_length=150, blank=True)
    prenom = models.CharField(max_length=150, blank=True)

    telephone = models.CharField(
        max_length=25,
        blank=True,
        validators=[phone_validator]
    )

    adresse = models.CharField(max_length=255)

    type_piece = models.CharField(
        max_length=20,
        choices=TYPE_PIECE,
        blank=True
    )

    numero_piece = models.CharField(
        max_length=100,
        blank=True
    )

    raison_sociale = models.CharField(
        max_length=255,
        blank=True
    )

    ifu = models.CharField(
        max_length=100,
        blank=True
    )

    statut = models.CharField(
        max_length=255,
        blank=True
    )

    date_creation = models.DateField(
        null=True,
        blank=True
    )

    class Meta:
        verbose_name="Client"
        verbose_name_plural="Clients"

    def __str__(self):
        if self.type_client=="personne":
            return f"{self.nom} {self.prenom}"
        return self.raison_sociale
    
class Prestation_prestation(models.Model):

    libelle = models.CharField(max_length=255)

    description = models.TextField(blank=True, null=True)

    prix_unitaire = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    actif = models.BooleanField(default=True)

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.libelle
    
class Facture_prestation(models.Model):

    TYPE_FACTURE = [
        ("proforma","Proforma"),
        ("definitive","Définitive"),
    ]

    numero = models.CharField(
        max_length=50,
        unique=True,
        editable=False
    )

    client = models.ForeignKey(
        Client_prestation,
        on_delete=models.PROTECT,
        related_name="factures"
    )

    type_facture = models.CharField(
        max_length=20,
        choices=TYPE_FACTURE
    )

    objet = models.CharField(max_length=255)

    montant_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    cree_par=models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="factures_prestation"
    )

    date_creation=models.DateTimeField(auto_now_add=True)

    date_validation=models.DateTimeField(
        null=True,
        blank=True
    )
    def save(self, *args, **kwargs):
        from django.db import transaction, IntegrityError

        # Générer le numéro à la création, et de nouveau chaque fois qu'il est
        # explicitement remis à vide (cas de la validation proforma -> définitive,
        # qui doit obtenir un nouveau numéro). `numero` est unique sur TOUTE la
        # table (proforma et définitive confondues) : le compteur ne doit donc
        # jamais être filtré par type_facture, sinon une proforma et une
        # définitive de la même année peuvent calculer le même numéro.
        if not self.numero:
            annee = timezone.now().year
            dernier = Facture_prestation.objects.filter(
                numero__startswith=f"{annee}_",
            ).count() + 1
            for _ in range(20):
                self.numero = f"{annee}_{dernier}/MESFPT/SG/BSB/DAF"
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    self.numero = None
                    dernier += 1
                    continue
            raise IntegrityError("Impossible de générer un numéro de facture unique après plusieurs tentatives.")

        super().save(*args, **kwargs)

    def montant_paye(self):
        return sum(p.montant for p in self.paiements.all())

    def reste_a_payer(self):
        return self.montant_total - self.montant_paye()

    def __str__(self):
        return self.numero

    class Meta:
        verbose_name = "Facture de prestation"
        verbose_name_plural = "Factures de prestation"
        permissions = [
            ("gerer_facturation", "Créer/gérer les factures de prestation"),
            ("valider_facture_prestation", "Valider une facture proforma en définitive"),
        ]


class LigneFacture_prestation(models.Model):

    facture=models.ForeignKey(
        Facture_prestation,
        on_delete=models.CASCADE,
        related_name="lignes"
    )

    prestation=models.ForeignKey(
        Prestation_prestation,
        on_delete=models.PROTECT
    )

    quantite=models.PositiveIntegerField(default=1)

    prix_unitaire=models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    montant=models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    def save(self, *args, **kwargs):
        self.montant = self.quantite * self.prix_unitaire
        super().save(*args, **kwargs)

    def montant_paye(self):
        return sum(l.montant for l in self.lignepaiement_prestation_set.all())

    def reste(self):
        return self.montant - self.montant_paye()

    def __str__(self):
        return f"{self.prestation} x{self.quantite}"


class Paiement_prestation(models.Model):

    MODE_PAIEMENT=[
        ("espece","Espèces"),
        ("mobile_money","Mobile Money"),
        ("virement","Virement"),
        ("cheque","Chèque"),
    ]

    facture=models.ForeignKey(
        Facture_prestation,
        on_delete=models.CASCADE,
        related_name="paiements"
    )

    numero_recu=models.CharField(
        max_length=50,
        unique=True
    )

    montant=models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    mode_paiement=models.CharField(
        max_length=20,
        choices=MODE_PAIEMENT
    )

    reference=models.CharField(
        max_length=255,
        blank=True
    )

    caissier=models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT
    )

    date_paiement=models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        from django.db import transaction, IntegrityError
        if not self.numero_recu:
            annee = timezone.now().year
            dernier = Paiement_prestation.objects.filter(
                numero_recu__startswith=f"REC-{annee}-"
            ).count() + 1
            for _ in range(20):
                self.numero_recu = f"REC-{annee}-{str(dernier).zfill(4)}"
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    self.numero_recu = None
                    dernier += 1
                    continue
            raise IntegrityError("Impossible de générer un numéro de reçu unique après plusieurs tentatives.")
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.numero_recu

    class Meta:
        verbose_name = "Paiement de prestation"
        verbose_name_plural = "Paiements de prestation"
        permissions = [
            ("encaisser_prestation", "Encaisser un paiement de prestation"),
        ]


class LignePaiement_prestation(models.Model):

    paiement=models.ForeignKey(
        Paiement_prestation,
        on_delete=models.CASCADE,
        related_name="lignes"
    )

    ligne_facture=models.ForeignKey(
        LigneFacture_prestation,
        on_delete=models.CASCADE
    )

    montant=models.DecimalField(
        max_digits=12,
        decimal_places=2
    )