from rest_framework import serializers
from accounts.models import Utilisateur, Eleve


TAILLE_MAX_UPLOAD = 5 * 1024 * 1024  # 5 Mo, aligne sur client_max_body_size de nginx

def _valider_fichier_upload(fichier):
    """Meme convention que le reste de l'app : extension ET signature
    binaire verifiees (empeche un fichier renomme, ex. .html en .pdf —
    vecteur XSS stocke contre le personnel qui ouvre ces documents), taille
    max 5 Mo. Formats acceptes : PDF, JPEG, JPG, PNG."""
    if fichier.size > TAILLE_MAX_UPLOAD:
        raise serializers.ValidationError("Le fichier dépasse la taille maximale de 5 Mo.")

    nom = fichier.name.lower()
    entete = fichier.read(8)
    fichier.seek(0)

    if nom.endswith('.pdf'):
        if entete[:5] != b'%PDF-':
            raise serializers.ValidationError("Le fichier n'est pas un PDF valide.")
    elif nom.endswith('.jpg') or nom.endswith('.jpeg'):
        if entete[:3] != b'\xff\xd8\xff':
            raise serializers.ValidationError("Le fichier n'est pas une image JPEG valide.")
    elif nom.endswith('.png'):
        if entete[:8] != b'\x89PNG\r\n\x1a\n':
            raise serializers.ValidationError("Le fichier n'est pas une image PNG valide.")
    else:
        raise serializers.ValidationError("Formats acceptés : JPEG, JPG, PNG, PDF uniquement.")


# REGISTER
class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    # Declare explicitement (sans validateur d'unicite automatique) : la
    # contrainte unique porte uniquement sur les adresses reellement saisies,
    # verifiee a la main dans validate() — sinon deux comptes laissant ce
    # champ vide se bloqueraient l'un l'autre (chaine vide != NULL en base,
    # mais deux chaines vides sont identiques pour la contrainte unique).
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    lieu_naissance = serializers.CharField(required=True, allow_blank=False)
    adresse = serializers.CharField(required=False, allow_blank=True)

    nom_pere = serializers.CharField(required=True, allow_blank=False)
    prenom_pere = serializers.CharField(required=True, allow_blank=False)
    nom_mere = serializers.CharField(required=True, allow_blank=False)
    prenom_mere = serializers.CharField(required=True, allow_blank=False)
    type_document = serializers.ChoiceField(choices=Eleve.TYPE_DOCUMENT_CHOICES, required=True)
    numero_document = serializers.CharField(required=True, allow_blank=False)
    date_etablissement_document = serializers.DateField(required=True)

    a_handicap = serializers.BooleanField(required=False, default=False)
    type_handicap = serializers.ChoiceField(choices=Eleve.TYPE_HANDICAP_CHOICES, required=False, allow_blank=True)
    piece_jointe_handicap = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Utilisateur
        fields = [
            'username', 'email', 'nom', 'prenom', 'password', 'password_confirm',
            'adresse', 'tel', 'sexe', 'date_naissance', 'lieu_naissance',
            'nom_pere', 'prenom_pere', 'nom_mere', 'prenom_mere',
            'type_document', 'numero_document', 'date_etablissement_document',
            'a_handicap', 'type_handicap', 'piece_jointe_handicap',
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})

        email = (attrs.get('email') or '').strip()
        if email:
            if Utilisateur.objects.filter(email=email).exists():
                raise serializers.ValidationError({"email": "Cette adresse email est déjà utilisée."})
            attrs['email'] = email
        else:
            attrs['email'] = None

        if attrs.get('a_handicap'):
            if not attrs.get('type_handicap'):
                raise serializers.ValidationError({"type_handicap": "Le type de handicap est obligatoire."})
            piece = attrs.get('piece_jointe_handicap')
            if not piece:
                raise serializers.ValidationError({"piece_jointe_handicap": "La pièce jointe est obligatoire."})
            _valider_fichier_upload(piece)
        else:
            attrs['type_handicap'] = None
            attrs['piece_jointe_handicap'] = None

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')

        user = Eleve(**validated_data)
        user.set_password(password)
        user.save()
        return user
