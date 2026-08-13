from datetime import date

from django import forms
from django.forms import inlineformset_factory

from .models import (
    Client_prestation, Prestation_prestation, Facture_prestation,
    LigneFacture_prestation, Utilisateur, Eleve,
)


def max_date_naissance():
    """Dernier jour de l'année précédente : empêche de choisir une date de
    naissance dans l'année en cours."""
    return date(date.today().year - 1, 12, 31)

# ─── Base ───────────────────────────────────────────────────────────────────
# Palette du module Facturation : rouge vif / jaune or uniquement.

_BASE_CLASSES = (
    'w-full px-4 py-3 border border-gray-300 rounded-lg '
    'focus:ring-2 focus:ring-red-600 focus:border-transparent transition-all'
)


class BaseFacturationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    'class', 'w-5 h-5 text-red-600 border-gray-300 rounded focus:ring-red-600'
                )
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault('class', _BASE_CLASSES)
                field.widget.attrs.setdefault('rows', 3)
            else:
                field.widget.attrs.setdefault('class', _BASE_CLASSES)


# ─── Client ─────────────────────────────────────────────────────────────────

class ClientPrestationForm(BaseFacturationForm):
    class Meta:
        model = Client_prestation
        fields = [
            'type_client', 'nom', 'prenom', 'telephone', 'adresse',
            'type_piece', 'numero_piece',
            'raison_sociale', 'ifu', 'statut', 'date_creation',
        ]
        labels = {
            'type_client': 'Type de client',
            'nom': 'Nom',
            'prenom': 'Prénom',
            'telephone': 'Téléphone',
            'adresse': 'Adresse',
            'type_piece': 'Type de pièce',
            'numero_piece': 'Numéro de pièce',
            'raison_sociale': 'Raison sociale',
            'ifu': 'IFU',
            'statut': 'Statut juridique',
            'date_creation': 'Date de création',
        }
        widgets = {
            'date_creation': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('nom', 'prenom', 'telephone', 'type_piece', 'numero_piece',
                     'raison_sociale', 'ifu', 'statut', 'date_creation'):
            self.fields[name].required = False

    def clean(self):
        cleaned_data = super().clean()
        type_client = cleaned_data.get('type_client')

        if type_client == 'personne':
            requis = ['nom', 'prenom', 'type_piece', 'numero_piece', 'telephone', 'adresse']
        else:
            requis = ['adresse', 'ifu', 'raison_sociale', 'statut', 'date_creation']

        for champ in requis:
            if not cleaned_data.get(champ):
                self.add_error(champ, "Ce champ est obligatoire.")

        return cleaned_data


class PrestationQuickForm(BaseFacturationForm):
    class Meta:
        model = Prestation_prestation
        fields = ['libelle', 'description', 'prix_unitaire']
        labels = {
            'libelle': 'Libellé de la prestation',
            'description': 'Description',
            'prix_unitaire': 'Prix unitaire (FCFA)',
        }
        widgets = {
            'prix_unitaire': forms.NumberInput(attrs={'min': '0', 'step': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False


# ─── Facture ────────────────────────────────────────────────────────────────

class FactureForm(BaseFacturationForm):
    class Meta:
        model = Facture_prestation
        fields = ['objet']
        labels = {'objet': 'Objet de la facture'}
        widgets = {
            'objet': forms.TextInput(attrs={'placeholder': "Ex : Frais de formation de dix-huit (18) apprenants"}),
        }


LigneFactureFormSet = inlineformset_factory(
    Facture_prestation,
    LigneFacture_prestation,
    fields=['prestation', 'quantite', 'prix_unitaire'],
    extra=1,
    can_delete=True,
    widgets={
        'prestation': forms.Select(attrs={'class': _BASE_CLASSES}),
        'quantite': forms.NumberInput(attrs={'class': _BASE_CLASSES, 'min': '1', 'value': '1'}),
        'prix_unitaire': forms.NumberInput(attrs={'class': _BASE_CLASSES, 'min': '0', 'step': '1'}),
    },
)


# ─── Encaissement ───────────────────────────────────────────────────────────

class PaiementPrestationForm(forms.Form):
    montant_paiement = forms.DecimalField(
        label='Montant (FCFA)', min_value=0, max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': _BASE_CLASSES, 'min': '0', 'step': '1'})
    )
    mode_paiement = forms.ChoiceField(
        label='Mode de paiement',
        choices=[],  # peuplé dans __init__ depuis le modèle
        widget=forms.Select(attrs={'class': _BASE_CLASSES})
    )
    reference = forms.CharField(
        label='Référence (optionnel)', required=False,
        widget=forms.TextInput(attrs={'class': _BASE_CLASSES})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Paiement_prestation
        self.fields['mode_paiement'].choices = Paiement_prestation.MODE_PAIEMENT


# ─── Profil (self-service, tous rôles) ─────────────────────────────────────
# Champs verrouillés (non modifiables ici) : username, matricule,
# numero_identifiant, user_type, permissions/groupes — ce ne sont pas des
# "infos personnelles" mais des identifiants/droits gérés par l'administration.

class ProfilForm(forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = ['nom', 'prenom', 'sexe', 'date_naissance', 'tel', 'adresse', 'email']
        labels = {
            'nom': 'Nom de famille',
            'prenom': 'Prénom',
            'sexe': 'Sexe',
            'date_naissance': 'Date de naissance',
            'tel': 'Téléphone',
            'adresse': 'Adresse',
            'email': 'Adresse email',
        }
        widgets = {
            'nom': forms.TextInput(attrs={'class': _BASE_CLASSES}),
            'prenom': forms.TextInput(attrs={'class': _BASE_CLASSES}),
            'sexe': forms.Select(attrs={'class': _BASE_CLASSES}),
            'date_naissance': forms.DateInput(attrs={'class': _BASE_CLASSES, 'type': 'date'}, format='%Y-%m-%d'),
            'tel': forms.TextInput(attrs={'class': _BASE_CLASSES + ' phone-intl', 'placeholder': '70 00 00 00'}),
            'adresse': forms.TextInput(attrs={'class': _BASE_CLASSES}),
            'email': forms.EmailInput(attrs={'class': _BASE_CLASSES}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_naissance'].widget.attrs['max'] = max_date_naissance().isoformat()

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

    def clean_date_naissance(self):
        naissance = self.cleaned_data.get('date_naissance')
        if naissance and naissance > max_date_naissance():
            raise forms.ValidationError("La date de naissance ne peut pas être dans l'année en cours.")
        return naissance


class ProfilEleveForm(ProfilForm):
    class Meta(ProfilForm.Meta):
        model = Eleve
        fields = ProfilForm.Meta.fields + ['lieu_naissance']
        labels = {**ProfilForm.Meta.labels, 'lieu_naissance': 'Lieu de naissance'}
        widgets = {
            **ProfilForm.Meta.widgets,
            'lieu_naissance': forms.TextInput(attrs={'class': _BASE_CLASSES}),
        }
