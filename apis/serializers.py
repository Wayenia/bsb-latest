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

    class Meta:
        model = Utilisateur
        fields = [
            'username', 'email', 'nom', 'prenom', 'password', 'password_confirm',
            'adresse', 'tel', 'sexe', 'date_naissance', 'lieu_naissance',
            'nom_pere', 'prenom_pere', 'nom_mere', 'prenom_mere', 'nip',
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})

        naissance = attrs.get('date_naissance')
        if naissance:
            today = date.today()
            age = today.year - naissance.year - ((today.month, today.day) < (naissance.month, naissance.day))
            nip = attrs.get('nip', '').strip()
            if age >= 18 and not nip:
                raise serializers.ValidationError({"nip": "Le NIP est obligatoire à partir de 18 ans."})
            if nip and not re.fullmatch(r'\d{17}', nip):
                raise serializers.ValidationError({"nip": "Le NIP doit contenir exactement 17 chiffres."})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')

        user = Eleve(**validated_data)
        user.set_password(password)
        user.save()
        return user
