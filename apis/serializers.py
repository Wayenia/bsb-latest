import re
from datetime import date

from rest_framework import serializers
from accounts.models import Utilisateur, Eleve


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
    nip = serializers.CharField(required=False, allow_blank=True, max_length=20)
    type_document = serializers.ChoiceField(choices=Eleve.TYPE_DOCUMENT_CHOICES, required=False, allow_blank=True)
    numero_document = serializers.CharField(required=False, allow_blank=True)
    date_etablissement_document = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = Utilisateur
        fields = [
            'username', 'email', 'nom', 'prenom', 'password', 'password_confirm',
            'adresse', 'tel', 'sexe', 'date_naissance', 'lieu_naissance',
            'nom_pere', 'prenom_pere', 'nom_mere', 'prenom_mere', 'nip',
            'type_document', 'numero_document', 'date_etablissement_document',
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})

        naissance = attrs.get('date_naissance')
        tel = attrs.get('tel') or ''
        if naissance:
            today = date.today()
            age = today.year - naissance.year - ((today.month, today.day) < (naissance.month, naissance.day))
            utilise_nip = age >= 18 and tel.startswith('+226')
            if utilise_nip:
                nip = attrs.get('nip', '').strip()
                if not nip:
                    raise serializers.ValidationError({"nip": "Le NIP est obligatoire à partir de 18 ans avec un numéro burkinabè (+226)."})
                if not re.fullmatch(r'\d{17}', nip):
                    raise serializers.ValidationError({"nip": "Le NIP doit contenir exactement 17 chiffres."})
            else:
                champs_requis = [
                    ('type_document', "Le type de document"),
                    ('numero_document', "Le numéro du document"),
                    ('date_etablissement_document', "La date d'établissement du document"),
                ]
                for field, label in champs_requis:
                    valeur = attrs.get(field)
                    if not valeur or (isinstance(valeur, str) and not valeur.strip()):
                        raise serializers.ValidationError({field: f"{label} est obligatoire."})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')

        user = Eleve(**validated_data)
        user.set_password(password)
        user.save()
        return user
