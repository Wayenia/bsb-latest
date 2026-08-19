from rest_framework import serializers
from accounts.models import Utilisateur, Eleve


def _valider_pdf(fichier):
    """Meme convention que le reste de l'app : extension ET signature
    binaire verifiees, pour empecher un fichier renomme en .pdf (vecteur XSS
    stocke contre le personnel qui ouvre ces documents)."""
    if not fichier.name.lower().endswith('.pdf'):
        raise serializers.ValidationError("Le fichier doit être un PDF (.pdf).")
    entete = fichier.read(5)
    fichier.seek(0)
    if entete != b'%PDF-':
        raise serializers.ValidationError("Le fichier n'est pas un PDF valide.")


# REGISTER
class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

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

        if attrs.get('a_handicap'):
            if not attrs.get('type_handicap'):
                raise serializers.ValidationError({"type_handicap": "Le type de handicap est obligatoire."})
            piece = attrs.get('piece_jointe_handicap')
            if not piece:
                raise serializers.ValidationError({"piece_jointe_handicap": "La pièce jointe est obligatoire."})
            _valider_pdf(piece)
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
