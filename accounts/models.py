from django.utils import timezone
import random
import string

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, FileExtensionValidator

# Garde-fou serveur au format E.164 ; le nombre de chiffres par pays est valide
# cote client par intl-tel-input.
phone_validator = RegexValidator(
    regex=r'^\+[1-9]\d{6,14}$',
    message="Le numéro doit être au format international avec l'indicatif du pays (ex : +226 70 00 00 00)."
)

# COMMON MODEL
class Utilisateur(AbstractUser):
    SEXE_CHOICE = [
        ("m", "Masculin"),
        ("f", "Féminin")
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
    email = models.EmailField(verbose_name="Adresse email", unique=True, blank=True, null=True)
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

    # user_type -> groupe Django, applique a chaque save() d'ou qu'il vienne.
    # 'eleve' est absent : les eleves ne portent aucune permission.
    ROLE_GROUPS = {
        'admin': 'Admin',
        'dg': 'Directeur Général',
        'dir': 'Directeur Inter-régional',
        'deps': 'DESP',
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
    TYPE_DOCUMENT_CHOICES = [
        ("extrait_naissance", "Extrait de naissance"),
        ("jugement_supletif", "Jugement supplétif"),
    ]

    TYPE_HANDICAP_CHOICES = [
        ("moteur", "Handicap moteur"),
        ("sensoriel_visuel", "Handicap sensoriel — Visuel"),
        ("sensoriel_auditif", "Handicap sensoriel — Auditif"),
        ("maladie_epilepsie", "Maladie invalidante — Épilepsie"),
        ("maladie_asthme", "Maladie invalidante — Asthme"),
        ("autre", "Autres maladies"),
    ]

    NIVEAU_SCOLAIRE_CHOICES = [
        ("cp1", "CP1"),
        ("cp2", "CP2"),
        ("ce1", "CE1"),
        ("ce2", "CE2"),
        ("cm1", "CM1"),
        ("cm2", "CM2"),
        ("6e", "6ème"),
        ("5e", "5ème"),
        ("4e", "4ème"),
        ("3e", "3ème"),
        ("2nde", "2nde"),
        ("1ere", "1ère"),
        ("terminale", "Terminale"),
        ("licence", "Licence"),
        ("maitrise", "Maîtrise"),
    ]

    lieu_naissance = models.CharField(max_length=225, verbose_name="Lieu de naissance")

    nom_pere = models.CharField(max_length=150, verbose_name="Nom du père")
    prenom_pere = models.CharField(max_length=150, verbose_name="Prénom du père")
    nom_mere = models.CharField(max_length=150, verbose_name="Nom de la mère")
    prenom_mere = models.CharField(max_length=150, verbose_name="Prénom de la mère")
    nip = models.CharField(
        max_length=20, blank=True, null=True,
        verbose_name="NIP (Numéro d'Identification Personnel)",
        help_text="Champ historique, non utilisé pour les nouvelles inscriptions."
    )
    type_document = models.CharField(
        max_length=20, choices=TYPE_DOCUMENT_CHOICES, blank=True, null=True,
        verbose_name="Type de document d'identité",
    )
    numero_document = models.CharField(max_length=100, blank=True, null=True, verbose_name="Numéro du document")
    date_etablissement_document = models.DateField(blank=True, null=True, verbose_name="Date d'établissement du document")

    a_handicap = models.BooleanField(default=False, verbose_name="En situation de handicap")
    type_handicap = models.CharField(
        max_length=30, choices=TYPE_HANDICAP_CHOICES, blank=True, null=True,
        verbose_name="Type de handicap",
    )
    piece_jointe_handicap = models.FileField(
        upload_to='eleves/handicap/', blank=True, null=True,
        verbose_name="Pièce jointe (Attestation/Certificat d'indigence)",
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])],
    )

    numero_identifiant = models.CharField(
        # 200 : la concatenation (numero de document + type + dates + lieu de
        # naissance) peut depasser 50 caracteres avec des lieux longs.
        max_length=200,
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
        choices=NIVEAU_SCOLAIRE_CHOICES,
        verbose_name="Niveau scolaire"
    )

    def generate_identifiant(self):
        """L'identifiant de l'apprenant est une concaténation déterministe de
        son document d'identité (numéro + type + date d'établissement) et de
        sa date/lieu de naissance."""
        parties = [
            self.numero_document, self.type_document,
            self.date_etablissement_document.strftime('%Y%m%d') if self.date_etablissement_document else '',
            self.date_naissance.strftime('%Y%m%d') if self.date_naissance else '',
            self.lieu_naissance,
        ]
        brut = ''.join(p or '' for p in parties)
        return ''.join(brut.upper().split())

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
            if Eleve.objects.filter(numero_identifiant=identifiant).exclude(pk=self.pk).exists():
                raise ValidationError(
                    "Un apprenant avec les mêmes informations d'identification "
                    "(NIP, ou nom/prénom/parents/lieu et date de naissance) existe déjà."
                )
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

        # Numero regenere des qu'il est remis a vide (validation proforma vers
        # definitive). Le compteur n'est jamais filtre par type_facture : numero
        # est unique sur toute la table (README 9).
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
        choices=MODE_PAIEMENT,
        default="espece"
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


class HistoriqueConnexion(models.Model):
    """Journal des connexions/déconnexions — un enregistrement par événement,
    créé par les signaux Django user_logged_in/user_logged_out (voir
    accounts/signals.py)."""

    TYPE_EVENEMENT_CHOICES = [
        ("connexion", "Connexion"),
        ("deconnexion", "Déconnexion"),
    ]

    utilisateur = models.ForeignKey(
        Utilisateur, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="historique_connexions", verbose_name="Utilisateur"
    )
    # Conservés tels quels au moment de l'événement : le journal reste lisible
    # même si le compte est ensuite supprimé (utilisateur devient alors NULL).
    username = models.CharField(max_length=150, blank=True, verbose_name="Nom d'utilisateur")
    nom_complet = models.CharField(max_length=250, blank=True, verbose_name="Nom complet")
    est_apprenant = models.BooleanField(default=False, verbose_name="Apprenant")
    type_evenement = models.CharField(max_length=20, choices=TYPE_EVENEMENT_CHOICES, verbose_name="Événement")
    date_evenement = models.DateTimeField(default=timezone.now, verbose_name="Date et heure")
    centre = models.ForeignKey(
        'courses.CentreFormation', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Centre"
    )
    adresse_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")

    class Meta:
        verbose_name = "Historique de connexion"
        verbose_name_plural = "Historique des connexions"
        ordering = ["-date_evenement"]
        permissions = [
            ("voir_historique_connexion", "Voir l'historique des connexions"),
        ]

    def __str__(self):
        return f"{self.username} — {self.get_type_evenement_display()} — {self.date_evenement:%d/%m/%Y %H:%M}"