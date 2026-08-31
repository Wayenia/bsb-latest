from django import forms

from .models import DestinataireRapport

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
