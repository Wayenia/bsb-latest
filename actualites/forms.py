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
    # Classe partagee par les champs texte/select/date : charte BSB (focus rouge),
    # reprise telle quelle sur chaque widget plutot que via un ancien ".form-control"
    # qui n'existe pas dans le CSS compile (les champs s'affichaient donc sans style).
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
            # Rendu en pilules dans le template (2 choix seulement) plutot qu'un
            # <select> depliant : le statut est la decision la plus importante du
            # formulaire, elle merite d'etre visible d'un coup d'oeil.
            "statut": forms.RadioSelect(),
            "date_publication": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "date_fin_publication": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nom, champ in self.fields.items():
            if nom == "image":
                # `accept` est un confort d'UI (filtre le selecteur de fichier),
                # pas un controle de securite : clean_image() ci-dessus est la
                # verification qui compte, cote serveur.
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

    # Django (ImageField) verifie deja que le fichier est structurellement une
    # image valide (Pillow ouvre et verifie le contenu, pas seulement le nom/
    # l'extension) : un .php renomme en .jpg est deja rejete en amont. Ici on
    # resserre en plus a une liste blanche de formats web courants et a une
    # taille raisonnable pour une vignette d'actualite - defense en profondeur,
    # pas un remplacement du controle Django.
    _IMAGE_TYPES_AUTORISES = {"image/jpeg", "image/png", "image/webp"}
    _IMAGE_TAILLE_MAX = 5 * 1024 * 1024  # 5 Mo

    def clean_image(self):
        image = self.cleaned_data.get("image")
        # `content_type` n'existe que sur un fichier fraichement televerse
        # (UploadedFile) : sur une modification sans nouveau fichier, `image`
        # est le fichier deja stocke et ne doit pas etre re-valide a chaque edit.
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
