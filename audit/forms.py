from django import forms

from .models import DestinataireRapport, ReglageDiffusion

_CLASSES = "bo-input"


class DestinataireRapportForm(forms.ModelForm):
    class Meta:
        model = DestinataireRapport
        fields = ['email', 'nom', 'fonction', 'actif']
        widgets = {
            'email': forms.EmailInput(attrs={'class': _CLASSES, 'placeholder': 'nom@exemple.org'}),
            'nom': forms.TextInput(attrs={'class': _CLASSES}),
            'fonction': forms.TextInput(attrs={'class': _CLASSES}),
        }

    def clean_email(self):
        return (self.cleaned_data.get('email') or '').strip().lower()


class ReglageDiffusionForm(forms.ModelForm):
    """Reglage par clics : listes deroulantes, aucun terme technique."""
    HEURES = [(h, f"{h:02d} h") for h in range(24)]
    JOURS_SEMAINE = [
        (0, 'Lundi'), (1, 'Mardi'), (2, 'Mercredi'), (3, 'Jeudi'),
        (4, 'Vendredi'), (5, 'Samedi'), (6, 'Dimanche'),
    ]
    JOURS_MOIS = [(j, f"le {j}") for j in range(1, 29)]

    class Meta:
        model = ReglageDiffusion
        fields = ['frequence', 'jour_semaine', 'jour_mois', 'heure']
        widgets = {
            'frequence': forms.RadioSelect(),
            'jour_semaine': forms.Select(attrs={'class': 'bo-select'}),
            'jour_mois': forms.Select(attrs={'class': 'bo-select'}),
            'heure': forms.Select(attrs={'class': 'bo-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['heure'].widget.choices = self.HEURES
        self.fields['jour_semaine'].widget.choices = self.JOURS_SEMAINE
        self.fields['jour_mois'].widget.choices = self.JOURS_MOIS
        self.fields['jour_semaine'].label = "Chaque"
        self.fields['jour_mois'].label = "Chaque mois"
        self.fields['heure'].label = "À"
