from django import forms

from .models import Actualite, AbonneNewsletter, Annonce


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
    # Reprise sur chaque widget : « .form-control » n'existe pas dans le CSS
    # compile, les champs s'affichaient donc sans style.
    _INPUT_CLASSES = ("w-full px-4 py-3 border border-gray-300 rounded-lg "
                       "focus:outline-none focus:ring-2 focus:ring-bsb-primary "
                       "focus:border-bsb-primary transition-colors")

    class Meta:
        model = Actualite
        fields = ["titre", "chapeau", "contenu", "image", "statut", "date_publication", "date_fin_publication"]
        widgets = {
            "titre": forms.TextInput(attrs={
                "placeholder": "Ex. : Ouverture des inscriptions pour la session 2026"}),
            "chapeau": forms.TextInput(attrs={
                "placeholder": "Résumé accrocheur, affiché dans la liste et l'e-mail (300 caractères max)",
                "maxlength": 300}),
            "contenu": forms.Textarea(attrs={"rows": 12, "placeholder": "Rédigez le corps de l'actualité..."}),
            # Rendu en pilules : le statut est la decision principale du
            # formulaire et doit rester visible d'un coup d'oeil.
            "statut": forms.RadioSelect(),
            "date_publication": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "date_fin_publication": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nom, champ in self.fields.items():
            if nom == "image":
                # Confort d'UI seulement : clean_image() est le controle reel.
                champ.widget.attrs.setdefault("accept", "image/jpeg,image/png,image/webp")
                champ.widget.attrs.setdefault(
                    "class",
                    "block w-full text-sm text-gray-600 cursor-pointer file:mr-4 file:py-2.5 file:px-5 "
                    "file:rounded-full file:border-0 file:text-sm file:font-bold file:bg-bsb-cream "
                    "file:text-bsb-dark hover:file:bg-bsb-primary hover:file:text-white file:transition-colors")
            elif nom == "statut":
                # "peer" + input masque : le template stylise le choix coche via
                # un selecteur CSS peer-checked sur le <label> associe, sans JS.
                champ.widget.attrs.setdefault("class", "peer sr-only")
            else:
                champ.widget.attrs.setdefault("class", self._INPUT_CLASSES)
        for nom_date in ("date_publication", "date_fin_publication"):
            self.fields[nom_date].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"]
            self.fields[nom_date].required = False

    # Defense en profondeur : ImageField valide deja le contenu du fichier, on
    # resserre ici sur une liste blanche de formats et une taille de vignette.
    _IMAGE_TYPES_AUTORISES = {"image/jpeg", "image/png", "image/webp"}
    _IMAGE_TAILLE_MAX = 5 * 1024 * 1024  # 5 Mo

    def clean_image(self):
        image = self.cleaned_data.get("image")
        # content_type n'existe que sur un fichier fraichement televerse : sans
        # nouveau fichier, l'image stockee n'a pas a etre revalidee.
        type_mime = getattr(image, "content_type", None)
        if image and type_mime:
            if type_mime not in self._IMAGE_TYPES_AUTORISES:
                raise forms.ValidationError(
                    "Format d'image non accepté : utilisez un fichier JPEG, PNG ou WebP.")
            if image.size > self._IMAGE_TAILLE_MAX:
                raise forms.ValidationError("L'image dépasse la taille maximale autorisée (5 Mo).")
        return image

    def clean(self):
        donnees = super().clean()
        debut, fin = donnees.get("date_publication"), donnees.get("date_fin_publication")
        if debut and fin and fin <= debut:
            self.add_error("date_fin_publication", "La fin de publication doit être postérieure à la date de publication.")
        return donnees


class AnnonceForm(forms.ModelForm):
    """Annonce du bandeau défilant : texte court, lien optionnel, fenêtre d'affichage."""
    _INPUT = ("w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none "
              "focus:ring-2 focus:ring-bsb-primary focus:border-bsb-primary transition-colors")

    class Meta:
        model = Annonce
        fields = ["texte", "lien", "libelle_lien", "ordre", "date_debut", "date_fin", "actif"]
        widgets = {
            "texte": forms.TextInput(attrs={"placeholder": "Ex. : Les inscriptions 2026 sont ouvertes.", "maxlength": 200}),
            "lien": forms.TextInput(attrs={"placeholder": "https://… ou /chemin/interne (optionnel)"}),
            "libelle_lien": forms.TextInput(attrs={"placeholder": "En savoir plus", "maxlength": 60}),
            "ordre": forms.NumberInput(attrs={"min": 0}),
            "date_debut": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "date_fin": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nom, champ in self.fields.items():
            if nom == "actif":
                continue
            champ.widget.attrs.setdefault("class", self._INPUT)
        for nom_date in ("date_debut", "date_fin"):
            self.fields[nom_date].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"]
            self.fields[nom_date].required = False
        self.fields["lien"].required = False
        self.fields["libelle_lien"].required = False

    def clean_lien(self):
        # Strictement un lien : URL http(s) ou chemin interne commençant par « / ».
        lien = (self.cleaned_data.get("lien") or "").strip()
        if lien and not (lien.startswith(("http://", "https://")) or lien.startswith("/")):
            raise forms.ValidationError(
                "Saisissez un lien valide : une adresse commençant par http:// ou https://, "
                "ou un chemin interne commençant par « / ».")
        return lien

    def clean(self):
        donnees = super().clean()
        debut, fin = donnees.get("date_debut"), donnees.get("date_fin")
        if debut and fin and fin <= debut:
            self.add_error("date_fin", "L'expiration doit être postérieure au début d'affichage.")
        return donnees
