from django import forms

from .models import Actualite, AbonneNewsletter


class AbonnementForm(forms.Form):
    """Inscription à la newsletter. `site_web` est un piège à robots : le champ
    est masqué, un humain ne le remplit jamais."""

    email = forms.EmailField(
        max_length=254,
        error_messages={"invalid": "Cette adresse e-mail n'est pas valide.",
                        "required": "Veuillez saisir votre adresse e-mail."},
        widget=forms.EmailInput(attrs={"placeholder": "votre.adresse@exemple.bf", "autocomplete": "email"}),
    )
    site_web = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean(self):
        donnees = super().clean()
        if donnees.get("site_web"):
            raise forms.ValidationError("Requête invalide.")
        return donnees


class ActualiteForm(forms.ModelForm):
    class Meta:
        model = Actualite
        fields = ["titre", "chapeau", "contenu", "image", "statut", "date_publication"]
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "chapeau": forms.TextInput(attrs={"class": "form-control"}),
            "contenu": forms.Textarea(attrs={"class": "form-control", "rows": 12}),
            "statut": forms.Select(attrs={"class": "form-control"}),
            "date_publication": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"},
                                                    format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date_publication"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"]
        self.fields["date_publication"].required = False
