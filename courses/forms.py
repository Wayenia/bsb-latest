from datetime import date

from django import forms
from .models import (
    TITRE_PROFESSIONNEL_CHOICE, Direction_reg, Filiere, CentreFormation, Module,
    Frais, Cours, Inscription, Paiement, CentreEtFiliere,PieceJointeInscription,TypeFrais,
    AnneeScolaire, TrancheFrais, Region
)
from django.forms import inlineformset_factory


def max_date_naissance():
    """Dernier jour de l'année précédente : empêche de choisir une date de
    naissance dans l'année en cours (personne ne s'inscrit l'année de sa
    naissance)."""
    return date(date.today().year - 1, 12, 31)


############### BASE FORM / COMMON FORM #############
class BaseModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            base_classes = 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all'

            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = base_classes + ' min-h-[120px]'
                field.widget.attrs['rows'] = 4
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = base_classes + ' cursor-pointer'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
            elif isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs['class'] = base_classes + ' min-h-[150px]'
            else:
                field.widget.attrs['class'] = base_classes
            
            if field.required:
                field.widget.attrs['required'] = 'required'


############### STUDENT LEVEL #############

# PRSONAL INFO
class PersonalInfoForm(forms.Form):
    SEXE_CHOICES = [
        ('M', 'Masculin'), 
        ('F', 'Féminin')
        ]

    nom = forms.CharField(
        label='Nom de famille',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Ex: OUEDRAOGO'
        })
    )
    prenom = forms.CharField(
        label='Prénom(s)',
        max_length=225,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Ex: Tipoko'
        })
    )
    sexe = forms.ChoiceField(
        label='Sexe',
        choices=SEXE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        })
    )
    email = forms.EmailField(
        label='Adresse email',
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'monmail@email.com'
        })
    )
    tel = forms.CharField(
        label='Téléphone',
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 phone-intl',
            'placeholder': 'Ex: 70 00 00 00'
        })
    )
    date_naissance = forms.DateField(
        label='Date de naissance',
        required=True,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }, format='%Y-%m-%d')
    )
    lieu_naissance = forms.CharField(
        label='Lieu de naissance',
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Ex: Ouagadougou'
        })    
    )

    nom_personne = forms.CharField(
        label='Nom de la Personne',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class':'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder':'Ex: SAWADOGO'
        })
    )

    prenom_personne=forms.CharField(
        label='Prénom de la personne',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class':'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder':'EX: Moussa'
        })
    )
    fonction=forms.CharField(
        label='Fonction de la Personne',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class':'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder':'EX: Informaticien'
        })
    )

    contact=forms.CharField(
        label='Contact de la Personne',
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class':'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 phone-intl',
            'placeholder':'65 08 57 40'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_naissance'].widget.attrs['max'] = max_date_naissance().isoformat()

    def clean_date_naissance(self):
        naissance = self.cleaned_data.get('date_naissance')
        if naissance and naissance > max_date_naissance():
            raise forms.ValidationError("La date de naissance ne peut pas être dans l'année en cours.")
        return naissance


# SUBSCRIPTION
class InscriptionForm(BaseModelForm):
    centre = forms.ModelChoiceField(
        queryset=CentreFormation.objects.all(),
        label='Centre de formation',
        required=True,
        widget=forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'})
    )
    filiere = forms.ModelChoiceField(
        queryset=Filiere.objects.all(),
        label='Métier',
        required=True,
        widget=forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'})
    )

    class Meta:
        model = Inscription
        fields = ['eleve', 'annee_scolaire', 'statut']
        labels = {
            'eleve': 'Élève',
            'annee_scolaire': 'Année scolaire',
            'statut': 'Statut'
        }
        widgets = {
            'annee_scolaire': forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pré-remplir centre et filière si une instance existe
        instance = kwargs.get('instance')
        if instance and instance.formation:
            self.fields['centre'].initial = instance.formation.centre
            self.fields['filiere'].initial = instance.formation.filiere
            self.fields['annee_scolaire'].initial = instance.annee_scolaire

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        centre = self.cleaned_data.get('centre')
        filiere = self.cleaned_data.get('filiere')
        annee_scolaire = self.cleaned_data.get('annee_scolaire')
        
        if centre and filiere:
            formation, created = CentreEtFiliere.objects.get_or_create(
                centre=centre,
                filiere=filiere
            )
            instance.formation = formation
        instance.annee_scolaire = annee_scolaire
        
        if commit:
            instance.save()
        return instance

# PAYMENT
class PaiementForm(BaseModelForm):#
    class Meta:
         model = Paiement
         fields = [ 'montant_paiement', 'mode_paiement', 'motif_derogation', 'piece_jointe_derogation']
         labels = {
             'montant_paiement': 'Montant (FCFA)',
             'mode_paiement': 'Mode de paiement',
             'motif_derogation': 'Motif de la dérogation',
             'piece_jointe_derogation': 'Pièce jointe justificative',
         }
         widgets = {
             'montant_paiement': forms.NumberInput(attrs={'placeholder': '50000', 'min': '0', 'step': '1000'}),
            'mode_paiement':forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'motif_derogation': forms.Textarea(attrs={'rows': 2, 'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'}),
         }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['motif_derogation'].required = False
        self.fields['piece_jointe_derogation'].required = False


# PAYMENT (formulaire admin, création/modification manuelle d'un paiement)
class PaiementAdminForm(BaseModelForm):
    class Meta:
        model = Paiement
        fields = ['dette', 'tranche', 'tranche_frais', 'montant_paiement', 'mode_paiement', 'numero_quittance']
        labels = {
            'dette': 'Dette liée',
            'tranche': 'Numéro de tranche',
            'tranche_frais': 'Tranche de frais soldée',
            'montant_paiement': 'Montant (FCFA)',
            'mode_paiement': 'Mode de paiement',
            'numero_quittance': 'Numéro de quittance',
        }
        widgets = {
            'dette': forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'tranche': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500', 'min': '1'}),
            'tranche_frais': forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'montant_paiement': forms.NumberInput(attrs={'placeholder': '50000', 'min': '0', 'step': '1000'}),
            'mode_paiement': forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'numero_quittance': forms.TextInput(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['dette'].required = False
        self.fields['dette'].empty_label = 'Aucune (paiement libre)'
        self.fields['tranche_frais'].required = False
        self.fields['tranche_frais'].empty_label = 'Aucune'
        self.fields['numero_quittance'].required = False


############### ADMIN LEVEL #############

# DIRECTION
class RegionAwareSelect(forms.Select):
    """Select dont chaque <option> porte un attribut data-region, pour permettre
    au JS de ne proposer que les chefs-lieux des régions sélectionnées."""
    def __init__(self, region_map=None, *args, **kwargs):
        self.region_map = region_map or {}
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        region_name = self.region_map.get(value)
        if region_name:
            option['attrs']['data-region'] = region_name
        return option


class DirectionRegForm(BaseModelForm):
    regions = forms.MultipleChoiceField(
        label='Régions couvertes',
        required=True,
        widget=forms.SelectMultiple(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 min-h-[120px]'
        }),
    )

    class Meta:
        model = Direction_reg
        fields = ['nom_direction', 'chef_lieu', 'directeur']
        labels = {
            'nom_direction': 'Nom de la direction',
            'chef_lieu': 'Chef-lieu',
            'directeur': 'Directeur',
        }
        widgets = {
            'nom_direction': forms.TextInput(attrs={'placeholder': 'Ex: Direction régionale du centre'}),
        }

    field_order = ['nom_direction', 'regions', 'chef_lieu', 'directeur']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        regions_qs = list(Region.objects.order_by('nom_region'))

        self.fields['regions'].choices = [(r.nom_region, r.nom_region) for r in regions_qs]

        region_map = {r.chef_lieu: r.nom_region for r in regions_qs}
        self.fields['chef_lieu'] = forms.ChoiceField(
            label='Chef-lieu',
            required=True,
            choices=[('', 'Sélectionner une région d’abord')] + [
                (r.chef_lieu, f"{r.chef_lieu} ({r.nom_region})") for r in regions_qs
            ],
            widget=RegionAwareSelect(
                region_map=region_map,
                attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'}
            ),
        )

        self.fields['directeur'].required = False
        self.fields['directeur'].empty_label = 'Aucun'

        instance = kwargs.get('instance')
        if instance and instance.pk and instance.region:
            self.fields['regions'].initial = [r.strip() for r in instance.region.split(',') if r.strip()]

    def clean(self):
        cleaned_data = super().clean()
        regions = cleaned_data.get('regions') or []
        chef_lieu = cleaned_data.get('chef_lieu')
        if regions and chef_lieu:
            valid_chef_lieux = set(Region.objects.filter(nom_region__in=regions).values_list('chef_lieu', flat=True))
            if chef_lieu not in valid_chef_lieux:
                self.add_error('chef_lieu', "Le chef-lieu doit appartenir à l'une des régions sélectionnées.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.region = ', '.join(self.cleaned_data.get('regions', []))
        if commit:
            instance.save()
        return instance

# FIELD
class FiliereForm(BaseModelForm):
    modules_existants = forms.ModelMultipleChoiceField(
        queryset=Module.objects.all().order_by('nom_module'),
        required=False,
        label="Modules existants à associer",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Filiere
        fields = ['nom_filiere', 'titre_professionnel', 'niveau_diplome', 'texte_defilante', 'is_active', 'curricula']
        labels = {
            'nom_filiere': 'Nom du métier',
            'titre_professionnel': 'Titre professionnel',

            'niveau_diplome': "Conditions d'accès",
            'texte_defilante': 'Texte défilant (optionnel)',
            'is_active': 'Rendre actif',
            'curricula': 'Curricula (optionnel)',
        }
        widgets = {
            'nom_filiere': forms.TextInput(attrs={
                'placeholder': 'Ex : Mécanique, Soudure, Maçonnerie',
                'class': 'w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-600 focus:border-transparent transition',
            }),
            'titre_professionnel': forms.Select(attrs={
                'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-600 focus:border-transparent transition',
            }),

            'niveau_diplome': forms.Textarea(attrs={
                'placeholder': 'Ex : BEPC ou équivalent, BAC minimum, Ouvert sans condition de diplôme...',
                'rows': 3,
                'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-600 focus:border-transparent transition resize-none',
            }),
            'texte_defilante': forms.Textarea(attrs={
                'placeholder': 'Ex : Nouvelle session ouverte, places limitées ! (affiché dans le carrousel de la page d\'accueil)',
                'rows': 2,
                'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-600 focus:border-transparent transition resize-none',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-red-600 border-gray-300 rounded',
            }),
            'curricula': forms.FileInput(attrs={
                'class': 'block text-xs text-gray-500 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-red-50 file:text-red-700 hover:file:bg-red-100',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['modules_existants'].initial = self.instance.modules.values_list('pk', flat=True)
        # BaseModelForm applique une classe de <select> aux CheckboxSelectMultiple
        # (sous-classe de SelectMultiple) : on la remplace par un style de case à cocher.
        self.fields['modules_existants'].widget.attrs['class'] = 'h-4 w-4 text-red-600 border-gray-300 rounded'


# ── Filtre Django-filter pour la liste ────────────────────────────────────────
# Ajoutez cette classe dans votre fichier filters.py

import django_filters

class FiliereFilter(django_filters.FilterSet):
    recherche = django_filters.CharFilter(
        field_name='nom_filiere',
        lookup_expr='icontains',
        label='Recherche',
    )
    titre_professionnel = django_filters.ChoiceFilter(
        choices=[('', 'Tous')] + list(TITRE_PROFESSIONNEL_CHOICE),
        label='Titre professionnel',
        empty_label=None,
    )
    is_active = django_filters.BooleanFilter(
        label='Disponible',
        widget=forms.Select(choices=[('', 'Tous'), ('true', 'Actif'), ('false', 'Inactif')]),
    )

    class Meta:
        model = Filiere
        fields = ['recherche', 'titre_professionnel', 'is_active']

# CENTER
# courses/forms/center_form.py  (ou dans courses/forms.py)

from django import forms
from courses.models import CentreFormation, Province  # ← ajouter Province

class CentreFormationForm(forms.ModelForm):
    class Meta:
        model = CentreFormation
        fields = [
            'nom_centre',
            'code_centre',
            'direction',
            'province',      # ← ajouté
            'niveau_centre', # ← optionnel
            'adresse',       # ← optionnel
            'tel',
            # ville supprimé, parent supprimé, filieres supprimé
        ]
        widgets = {
            'nom_centre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Centre de Ouagadougou'
            }),
            'code_centre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : OUAGA1'
            }),
            'direction': forms.Select(attrs={'class': 'form-control'}),
            'province': forms.Select(attrs={'class': 'form-control'}),  # ← ajouté
            'niveau_centre': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : 1'
            }),
            'adresse': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Secteur 12, Avenue Kwame Nkrumah'
            }),
            'tel': forms.TextInput(attrs={
                'class': 'form-control phone-intl',
                'placeholder': 'Ex : 25 00 00 00'
            }),
        }
        labels = {
            'nom_centre': 'Nom du centre',
            'code_centre': 'Code du centre',
            'direction': 'Direction du centre',
            'province': 'Province',              # ← ajouté
            'niveau_centre': 'Niveau du centre (optionnel)',
            'adresse': 'Adresse / Localisation (optionnel)',
            'tel': 'Téléphone',
        }

    def __init__(self, *args, direction_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tel'].required = False
        self.fields['niveau_centre'].required = False  # ← optionnel
        self.fields['adresse'].required = False         # ← optionnel
        self.fields['province'].required = False        # ← optionnel selon le modèle
        # Portée (ex: un Directeur Inter-régional ne doit pouvoir rattacher
        # un centre qu'à sa propre direction) — non restreint par défaut.
        if direction_queryset is not None:
            self.fields['direction'].queryset = direction_queryset

    def clean_niveau_centre(self):
        value = self.cleaned_data.get("niveau_centre")
        if value in ["", None]:
            return None
        return value
# MODULE
class ModuleForm(BaseModelForm):
    class Meta:
        model = Module
        fields = ['filieres', 'nom_module', 'volume_h_cours']
        labels = {
            'filieres': 'Métiers',
            'nom_module': 'Nom du module',
            'volume_h_cours': 'Volume horaire (heures)'
        }
        widgets = {
            'filieres': forms.SelectMultiple(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 min-h-[140px]'}),
            'nom_module': forms.TextInput(attrs={'placeholder': 'Ex: Introduction à la mécanique'}),
            'volume_h_cours': forms.NumberInput(attrs={'placeholder': '60', 'min': '1'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['filieres'].required = False


 #TypeFrais
class TypeFraisForm(forms.ModelForm):
    class Meta:
        model = TypeFrais
        fields = ['libelle']
        widgets = {
            'libelle':forms.TextInput(attrs={'placeholder': 'Ex: Notions de base en mécanique'})
        }
    
# FEE
class FraisForm(BaseModelForm):
    class Meta:
        model = Frais
        fields = ['formation', 'type_frais', 'montant']
        labels = {
            'formation': 'Formation (centre / métier)',
            'montant': 'Montant (FCFA)'
        }
        widgets = {
            'formation':forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'type_frais':forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'montant': forms.NumberInput(attrs={'placeholder': '50000', 'min': '0', 'step': '1000'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type_frais'].empty_label='Sélectionner un type de frais'
        self.fields['formation'].empty_label='Sélectionner une formation'


# COURSE
class CoursForm(BaseModelForm):
    class Meta:
        model = Cours
        fields = ['module', 'libelle_cours', 'volume_h_cours']
        labels = {
            'module': 'Module',
            'libelle_cours': 'Libellé du cours',
            'volume_h_cours': 'Volume horaire (heures)'
        }
        widgets = {
            'module':forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'}),
            'libelle_cours': forms.TextInput(attrs={'placeholder': 'Ex: Notions de base en mécanique'}),
            'volume_h_cours': forms.TextInput(attrs={'placeholder': 'Ex: 20h'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['module'].empty_label='Sélectionner un module'
# CENTER-FIELD JUNCTION
class CentreEtFiliereForm(BaseModelForm):
    class Meta:
        model = CentreEtFiliere
        fields = ['centre', 'type_formation', 'filiere', 'is_active', 'communique', 'annee_prog', 'date_lancement', 'duree_jours', 'date_limite_inscription']
        labels = {
            'centre': 'Centre de formation',
            'type_formation': 'Type de formation',
            'filiere': 'Métier',           # ← "filière" → "Métier"
            'is_active': 'Actif',
            'communique': 'Communiqué',
            'annee_prog': 'Année de programmation',
            'date_lancement': 'Date de lancement',
            'duree_jours': 'Durée (en jours)',
            'date_limite_inscription': "Date limite d'inscription",
        }
        widgets = {
            'centre': forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all cursor-pointer'}),
            'type_formation': forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all cursor-pointer'}),
            'filiere': forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all cursor-pointer'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'sr-only peer'}),
            'communique': forms.FileInput(attrs={
                'class': 'block text-xs text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-medium file:bg-yellow-50 file:text-yellow-700 hover:file:bg-yellow-100 cursor-pointer'
            }),
            'annee_prog': forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all cursor-pointer'}),
            'date_lancement': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all'},
                format='%Y-%m-%dT%H:%M'
            ),
            'duree_jours': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all',
                'min': 1, 'placeholder': 'Ex : 15, 45, 270',
            }),
            'date_limite_inscription': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all'},
                format='%Y-%m-%dT%H:%M'
            ),
        }

    def __init__(self, *args, centre_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['centre'].empty_label = "Sélectionnez un centre"
        self.fields['type_formation'].empty_label = "Sélectionnez un type de formation"
        self.fields['filiere'].empty_label = "Sélectionnez un métier"
        self.fields['annee_prog'].empty_label = "Sélectionnez une année"
        # Portée (ex: un Directeur Inter-régional ne doit programmer que dans
        # les centres de sa propre direction) — non restreint par défaut.
        if centre_queryset is not None:
            self.fields['centre'].queryset = centre_queryset
        # Date de lancement, durée et date limite d'inscription sont OBLIGATOIRES
        self.fields['duree_jours'].required = True
        if self.instance and self.instance.pk:
            if self.instance.date_lancement:
                self.initial['date_lancement'] = self.instance.date_lancement.strftime('%Y-%m-%dT%H:%M')
            if self.instance.date_limite_inscription:
                self.initial['date_limite_inscription'] = self.instance.date_limite_inscription.strftime('%Y-%m-%dT%H:%M')
        else:
            # Nouvelle programmation : présélectionner l'année scolaire la plus
            # récemment créée plutôt que de forcer un choix manuel à chaque fois.
            derniere_annee = AnneeScolaire.objects.order_by('-date_creation').first()
            if derniere_annee:
                self.initial['annee_prog'] = derniere_annee.pk

class PieceJointeForm(forms.ModelForm):
    class Meta:
        model = PieceJointeInscription
        fields = ['libelle_piece', 'type_piece', 'est_requis']
        widgets = {
            'libelle_piece': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
                'placeholder': 'Ex: Copie CNI'
            }),
            'type_piece': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500',
            }),
            'est_requis': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded text-yellow-600',
            }),
        }

#Formset pour frais
# Formset pour frais
FraisFormSet = inlineformset_factory(
    CentreEtFiliere,
    Frais,
    form=FraisForm,
    extra=0,        # Pas de ligne vide au départ (le JS en ajoute)
    min_num=0,
    validate_min=False,
    can_delete=True
)

# Formset pour pièce jointe
PieceJointeFormSet = inlineformset_factory(
    CentreEtFiliere,
    PieceJointeInscription,
    form=PieceJointeForm,
    extra=0,
    min_num=0,
    validate_min=False,
    can_delete=True
)

from accounts.models import Utilisateur, Formateur, MembreAdministration, DirecteurInterRegional, DAF, Eleve
from django.utils import timezone

# ─── Constantes alignées sur USER_TYPE du modèle Utilisateur ─────────────────

USER_TYPE_CHOICES = [
    ('',                '-- Choisir un rôle --'),
    ('formateur',       'Formateur'),
    ('dir',             'Directeur inter-régional'),
    ('gestionnaire',    'Directeur de centre'),
    ('agent_comptable', 'Agent comptable'),
    ('caissier',        'Caissière / Caissier'),
    ('deps',            'Direction des Études, de la Planification et des Statistiques'),
    ('admin',           'Administrateur'),
    ('dg',              'Directeur Général'),
    ('daf',             'Directeur Administratif et Financier'),
    ('membre',          "Membre de l'administration (fonction libre)"),
]

# Rôles stockés dans MembreAdministration avec un centre (structure)
ROLES_CENTRE = {'gestionnaire', 'agent_comptable', 'caissier'}

# Emploi automatique par rôle (pour MembreAdministration)
EMPLOI_MAP = {
    'gestionnaire':    'Directeur de centre',
    'agent_comptable': 'Agent Comptable',
    'caissier':        'Caissière / Caissier',
    'deps':            'Direction des Études, de la Planification et des Statistiques',
}


# ─── Formulaire ───────────────────────────────────────────────────────────────

class AgentForm(forms.ModelForm):

    password = forms.CharField(
        label='Mot de passe',
        required=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Laisser vide pour ne pas modifier'
        })
    )

    # ── Champs Formateur ──────────────────────────────────────────────────────
    centre_formateur = forms.ModelChoiceField(
        queryset=CentreFormation.objects.all(),
        label='Centre de formation',
        required=False,
        empty_label="Sélectionnez un centre"
    )
    date_integration_formateur = forms.DateField(
        label="Date d'intégration",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
    )
    filiere = forms.ModelChoiceField(
        queryset=Filiere.objects.filter(is_active=True),
        label='Métier dispensé',
        required=False,
        empty_label="Sélectionnez un métier"
    )
    module = forms.ModelChoiceField(
        queryset=Module.objects.all(),
        label='Module dispensé',
        required=False,
        empty_label="Sélectionnez d'abord un métier"
    )

    # ── Champs Directeur inter-régional (modèle DirecteurInterRegional) ───────
    direction_interreg = forms.ModelChoiceField(
        queryset=Direction_reg.objects.all(),
        label='Direction inter-régionale',
        required=False,
        empty_label="Sélectionnez une direction"
    )

    # ── Champ Centre pour gestionnaire / comptable / caissier ─────────────────
    centre_role = forms.ModelChoiceField(
        queryset=CentreFormation.objects.all(),
        label='Centre rattaché',
        required=False,
        empty_label="Sélectionnez un centre"
    )

    # ── Champ Centre Admin (optionnel, réutilisé par 'admin' et 'daf') ────────
    centre_admin = forms.ModelChoiceField(
        queryset=CentreFormation.objects.all(),
        label='Centre administré',
        required=False,
        empty_label="Sélectionnez un centre (optionnel)"
    )

    # ── Champ fonction libre pour 'membre' (Membre de l'administration) ──────
    emploi_libre = forms.CharField(
        label='Fonction / emploi',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': "Ex: Secrétaire Générale (SG)"})
    )

    class Meta:
        model = Utilisateur
        fields = [
            'nom', 'prenom', 'username', 'email',
            'tel', 'sexe', 'date_naissance', 'adresse', 'user_type'
        ]
        labels = {
            'nom':            'Nom de famille',
            'prenom':         'Prénom(s)',
            'username':       "Nom d'utilisateur",
            'email':          'Adresse email',
            'tel':            'Téléphone',
            'sexe':           'Sexe',
            'date_naissance': 'Date de naissance',
            'adresse':        'Adresse',
            'user_type':      "Rôle de l'agent",
        }
        widgets = {
            'nom':            forms.TextInput(attrs={'placeholder': 'Ex: OUEDRAOGO'}),
            'prenom':         forms.TextInput(attrs={'placeholder': 'Ex: Moussa'}),
            'username':       forms.TextInput(attrs={'placeholder': 'Ex: moussa.ouedraogo'}),
            'email':          forms.EmailInput(attrs={'placeholder': 'Ex: moussa@bsb.bf'}),
            'tel':            forms.TextInput(attrs={'placeholder': 'Ex: 70 00 00 00'}),
            'sexe':           forms.Select(),
            'date_naissance': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'adresse':        forms.TextInput(attrs={'placeholder': 'Ex: Secteur 12, Ouagadougou'}),
            'user_type':      forms.Select(choices=USER_TYPE_CHOICES),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base = (
            'w-full px-4 py-3 border border-gray-300 rounded-lg '
            'focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all'
        )
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    'class',
                    'w-5 h-5 text-yellow-600 border-gray-300 rounded focus:ring-yellow-500'
                )
            elif isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs.setdefault('class', base + ' min-h-[140px]')
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', base + ' cursor-pointer')
            else:
                field.widget.attrs.setdefault('class', base)

        # Champs identité optionnels
        self.fields['tel'].widget.attrs['class'] = (
            self.fields['tel'].widget.attrs.get('class', '') + ' phone-intl'
        ).strip()
        self.fields['tel'].required = False
        self.fields['date_naissance'].required = False
        self.fields['date_naissance'].widget.attrs['max'] = max_date_naissance().isoformat()
        self.fields['adresse'].required = False

        # ── Préremplissage en mode modification ───────────────────────────────
        instance = self.instance
        if instance and instance.pk:
            utype = instance.user_type

            if utype == 'formateur':
                try:
                    f = Formateur.objects.get(pk=instance.pk)
                    self.fields['centre_formateur'].initial = f.centre_id
                    self.fields['date_integration_formateur'].initial = f.date_integration
                    self.fields['filiere'].initial = f.filiere_id
                    self.fields['module'].initial = f.module_id
                except Formateur.DoesNotExist:
                    pass

            elif utype == 'dir':
                try:
                    d = DirecteurInterRegional.objects.get(pk=instance.pk)
                    self.fields['direction_interreg'].initial = d.direction_id
                except DirecteurInterRegional.DoesNotExist:
                    pass

            elif utype in ROLES_CENTRE:
                try:
                    m = MembreAdministration.objects.get(pk=instance.pk)
                    self.fields['centre_role'].initial = m.structure_id
                except MembreAdministration.DoesNotExist:
                    pass

            elif utype == 'admin':
                try:
                    m = MembreAdministration.objects.get(pk=instance.pk)
                    self.fields['centre_admin'].initial = m.structure_id
                except MembreAdministration.DoesNotExist:
                    pass

            # deps : rien à préremplir (rôle seul)

        # Le choix du module est restreint aux modules du métier sélectionné.
        # La valeur postée (si le formulaire est soumis) prime sur celle de
        # l'instance, sinon la sélection précédente serait perdue au premier
        # changement de métier (rejet en validation d'un module valide).
        if self.is_bound:
            filiere_id_for_modules = self.data.get('filiere') or None
        else:
            filiere_id_for_modules = self.fields['filiere'].initial
        if filiere_id_for_modules:
            self.fields['module'].queryset = Module.objects.filter(filieres=filiere_id_for_modules)
        else:
            self.fields['module'].queryset = Module.objects.none()

    # ── Validations ───────────────────────────────────────────────────────────

    def clean_date_naissance(self):
        naissance = self.cleaned_data.get('date_naissance')
        if naissance and naissance > max_date_naissance():
            raise forms.ValidationError("La date de naissance ne peut pas être dans l'année en cours.")
        return naissance

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError("Le nom d'utilisateur est obligatoire.")
        qs = Utilisateur.objects.filter(username=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError("L'adresse email est obligatoire.")
        qs = Utilisateur.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        return email

    def clean(self):
        cleaned = super().clean()
        utype = cleaned.get('user_type')

        if utype == 'formateur':
            if not cleaned.get('centre_formateur'):
                self.add_error('centre_formateur', "Le centre de formation est requis.")
            if not cleaned.get('date_integration_formateur'):
                self.add_error('date_integration_formateur', "La date d'intégration est requise.")

        elif utype == 'dir':
            if not cleaned.get('direction_interreg'):
                self.add_error('direction_interreg', "La direction inter-régionale est requise.")

        elif utype in ROLES_CENTRE:
            if not cleaned.get('centre_role'):
                self.add_error('centre_role', "Le centre rattaché est requis.")

        elif utype == 'membre':
            if not cleaned.get('emploi_libre'):
                self.add_error('emploi_libre', "La fonction / emploi est requis.")

        # deps, admin et daf : aucune validation supplémentaire (centre_admin optionnel)

        return cleaned

    # ── Sauvegarde ────────────────────────────────────────────────────────────

    def save(self, commit=True):
        instance = super().save(commit=False)

        password = self.cleaned_data.get('password')
        if password:
            instance.set_password(password)
        elif not instance.pk:
            instance.set_unusable_password()

        instance.user_type = self.cleaned_data.get('user_type')

        if commit:
            instance.save()

        utype = instance.user_type

        # Champs communs pour les sous-modèles (multi-table inheritance)
        base_ptr = {'utilisateur_ptr_id': instance.pk}
        base_fields = {
            'nom':       instance.nom,
            'prenom':    instance.prenom,
            'username':  instance.username,
            'email':     instance.email,
            'password':  instance.password,
            'user_type': utype,
        }

        if utype == 'formateur':
            Formateur.objects.update_or_create(
                **base_ptr,
                defaults={
                    **base_fields,
                    'centre':           self.cleaned_data.get('centre_formateur'),
                    'emploi':           'Formateur',
                    'specialite':       '',
                    'date_integration': (
                        self.cleaned_data.get('date_integration_formateur')
                        or timezone.now().date()
                    ),
                    'filiere':          self.cleaned_data.get('filiere'),
                    'module':           self.cleaned_data.get('module'),
                }
            )

        elif utype == 'dir':
            DirecteurInterRegional.objects.update_or_create(
                **base_ptr,
                defaults={
                    **base_fields,
                    'direction': self.cleaned_data.get('direction_interreg'),
                }
            )

        elif utype in ROLES_CENTRE:
            MembreAdministration.objects.update_or_create(
                **base_ptr,
                defaults={
                    **base_fields,
                    'structure': self.cleaned_data.get('centre_role'),
                    'direction': None,
                    'emploi':    EMPLOI_MAP[utype],
                    'categorie': EMPLOI_MAP[utype],
                }
            )

        elif utype == 'deps':
            # deps : aucun centre ni direction requis
            MembreAdministration.objects.update_or_create(
                **base_ptr,
                defaults={
                    **base_fields,
                    'structure': None,
                    'direction': None,
                    'emploi':    EMPLOI_MAP['deps'],
                    'categorie': EMPLOI_MAP['deps'],
                }
            )

        elif utype == 'admin':
            centre_admin = self.cleaned_data.get('centre_admin')
            if centre_admin:
                MembreAdministration.objects.update_or_create(
                    **base_ptr,
                    defaults={
                        **base_fields,
                        'structure': centre_admin,
                        'direction': None,
                        'emploi':    'Administrateur',
                        'categorie': 'Admin',
                    }
                )

        elif utype == 'daf':
            # centre_admin réutilisé ici comme structure de rattachement du DAF
            # (optionnelle sur le modèle DAF, comme pour 'admin').
            DAF.objects.update_or_create(
                **base_ptr,
                defaults={
                    **base_fields,
                    'structure': self.cleaned_data.get('centre_admin'),
                }
            )

        elif utype == 'membre':
            emploi_libre = self.cleaned_data.get('emploi_libre')
            MembreAdministration.objects.update_or_create(
                **base_ptr,
                defaults={
                    **base_fields,
                    'structure': None,
                    'direction': None,
                    'emploi':    emploi_libre,
                    'categorie': emploi_libre,
                }
            )

        # dg : Directeur Général — aucun sous-modèle requis, le rôle seul suffit
        # (il obtient toutes les permissions comme l'admin, voir accounts.Utilisateur.ROLE_GROUPS)

        return instance


# ─── Gestion des apprenants (écran DSI/admin — accounts.gerer_eleves) ────────
# Édition complète d'un compte élève, y compris le mot de passe — distinct de
# ProfilEleveForm (self-service, accounts/forms.py) qui verrouille
# username/matricule/numero_identifiant : ici c'est un tiers habilité qui
# corrige/complète le dossier, donc l'accès est plus large (même pattern que
# AgentForm : champ password optionnel, "laisser vide pour ne pas modifier").
class EleveForm(forms.ModelForm):

    password = forms.CharField(
        label='Mot de passe',
        required=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Laisser vide pour ne pas modifier'
        })
    )

    class Meta:
        model = Eleve
        fields = [
            'nom', 'prenom', 'username', 'email', 'tel', 'sexe', 'date_naissance',
            'adresse', 'lieu_naissance', 'nationalite', 'niveau_scolaire',
        ]
        labels = {
            'nom':             'Nom de famille',
            'prenom':          'Prénom(s)',
            'username':        "Nom d'utilisateur",
            'email':           'Adresse email',
            'tel':             'Téléphone',
            'sexe':            'Sexe',
            'date_naissance':  'Date de naissance',
            'adresse':         'Adresse',
            'lieu_naissance':  'Lieu de naissance',
            'nationalite':     'Nationalité',
            'niveau_scolaire': 'Niveau scolaire',
        }
        widgets = {
            'nom':             forms.TextInput(attrs={'placeholder': 'Ex: OUEDRAOGO'}),
            'prenom':          forms.TextInput(attrs={'placeholder': 'Ex: Moussa'}),
            'username':        forms.TextInput(attrs={'placeholder': 'Ex: moussa.ouedraogo'}),
            'email':           forms.EmailInput(attrs={'placeholder': 'Ex: moussa@exemple.com'}),
            'tel':             forms.TextInput(attrs={'placeholder': 'Ex: 70 00 00 00'}),
            'sexe':            forms.Select(),
            'date_naissance':  forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'adresse':         forms.TextInput(attrs={'placeholder': 'Ex: Secteur 12, Ouagadougou'}),
            'lieu_naissance':  forms.TextInput(attrs={'placeholder': 'Ex: Ouagadougou'}),
            'nationalite':     forms.TextInput(attrs={'placeholder': 'Ex: Burkinabè'}),
            'niveau_scolaire': forms.TextInput(attrs={'placeholder': 'Ex: Classe de 3ème'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base = (
            'w-full px-4 py-3 border border-gray-300 rounded-lg '
            'focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all'
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', base)
        self.fields['tel'].widget.attrs['class'] = base + ' phone-intl'
        self.fields['tel'].required = False
        self.fields['adresse'].required = False
        self.fields['date_naissance'].required = False
        self.fields['date_naissance'].widget.attrs['max'] = max_date_naissance().isoformat()
        self.fields['nationalite'].required = False
        self.fields['niveau_scolaire'].required = False

    def clean_date_naissance(self):
        naissance = self.cleaned_data.get('date_naissance')
        if naissance and naissance > max_date_naissance():
            raise forms.ValidationError("La date de naissance ne peut pas être dans l'année en cours.")
        return naissance

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError("Le nom d'utilisateur est obligatoire.")
        qs = Utilisateur.objects.filter(username=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError("L'adresse email est obligatoire.")
        qs = Utilisateur.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        return email

    def save(self, commit=True):
        eleve = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            eleve.set_password(password)
        if commit:
            eleve.save()
        return eleve


# À ajouter dans forms.py
# (AnneeScolaireForm existe déjà, seulement TypeFraisForm est nouveau)

from django import forms
from .models import AnneeScolaire
import re

class AnneeScolaireForm(forms.ModelForm):
    class Meta:
        model = AnneeScolaire
        fields = ['libelle_anne']
        widgets = {
            'libelle_anne': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400',
                'placeholder': 'Ex : 2025-2026',
            })
        }
        labels = {
            'libelle_anne': "Libellé de l'année scolaire",
        }

    def clean_libelle_anne(self):
        libelle = self.cleaned_data.get('libelle_anne', '').strip()

        # Format AAAA-AAAA obligatoire
        if not re.match(r'^\d{4}-\d{4}$', libelle):
            raise forms.ValidationError("Le format doit être AAAA-AAAA (ex : 2025-2026).")

        # Les deux années doivent être consécutives
        annee1, annee2 = int(libelle[:4]), int(libelle[5:])
        if annee2 != annee1 + 1:
            raise forms.ValidationError("Les deux années doivent être consécutives (ex : 2025-2026).")

        # Doublon — exclure l'instance en cours si modification
        qs = AnneeScolaire.objects.filter(libelle_anne__iexact=libelle)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"L'année « {libelle} » existe déjà.")

        return libelle
    
class TypeFraisForm(forms.ModelForm):
    class Meta:
        model = TypeFrais
        fields = ['libelle']
        widgets = {
            'libelle': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400',
                'placeholder': 'Ex : Frais de scolarité, Frais d\'inscription...',
            })
        }

    def clean_libelle(self):
        libelle = self.cleaned_data.get('libelle', '').strip()

        qs = TypeFrais.objects.filter(libelle__iexact=libelle)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Le type « {libelle} » existe déjà.")

        return libelle


# ─── TRANCHES D'UN TYPE DE FRAIS ──────────────────────────────────────────────
class TrancheFraisForm(forms.ModelForm):
    class Meta:
        model = TrancheFrais
        fields = ['libelle', 'ordre', 'pourcentage', 'est_primordiale']
        widgets = {
            'libelle': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400',
                'placeholder': 'Ex : Tranche 1',
            }),
            'ordre': forms.NumberInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400',
                'min': 1,
            }),
            'pourcentage': forms.NumberInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400',
                'min': 0, 'max': 100, 'step': '0.01',
            }),
            'est_primordiale': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded text-indigo-600',
            }),
        }


class BaseTrancheFraisFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        total_pourcentage = 0
        nb_primordiales = 0
        nb_lignes = 0

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            data = form.cleaned_data
            if not data or data.get('DELETE'):
                continue
            nb_lignes += 1
            total_pourcentage += float(data.get('pourcentage') or 0)
            if data.get('est_primordiale'):
                nb_primordiales += 1

        if nb_primordiales > 1:
            raise forms.ValidationError("Une seule tranche peut être marquée comme primordiale.")

        if nb_lignes > 0 and round(total_pourcentage, 2) != 100:
            raise forms.ValidationError(
                f"La somme des pourcentages des tranches doit être exactement 100% (actuellement {total_pourcentage:g}%)."
            )


TrancheFraisFormSet = inlineformset_factory(
    TypeFrais,
    TrancheFrais,
    form=TrancheFraisForm,
    formset=BaseTrancheFraisFormSet,
    extra=1,
    can_delete=True,
)