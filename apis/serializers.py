from rest_framework import serializers
from accounts.models import Utilisateur, Eleve


# REGISTER
class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    lieu_naissance = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = Utilisateur
        fields = [
            'username', 'email', 'nom', 'prenom', 'password', 'password_confirm',
            'adresse', 'tel', 'sexe', 'date_naissance', 'lieu_naissance',
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')

        user = Eleve(**validated_data)
        user.set_password(password)
        user.save()
        return user