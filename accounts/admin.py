from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Eleve, Formateur, Utilisateur, MembreAdministration

@admin.register(Utilisateur)
class EleveAdmin(admin.ModelAdmin):
    list_display = ["username", "nom", "prenom", "is_staff" , "is_active"]


@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    list_display = ["username", "matricule", "nom", "prenom", "is_active"]

@admin.register(Formateur)
class FormateurAdmin(admin.ModelAdmin):
    list_display = ["username", "matricule", "nom", "prenom", "is_active"]
    
@admin.register(MembreAdministration)
class MembreAdmin(UserAdmin):
        model = MembreAdministration
        list_display = ["username", "matricule", "nom", "prenom", "is_active"]
        
        add_fieldsets = (
            (None, {
                'classes': ('wide',),
                'fields': ('username', 'email', 'password1', 'password2', 'user_type', 'matricule', 'nom', 'prenom', 'adresse', 'tel', 'sexe', 'date_naissance', 'structure', 'direction','emploi','categorie'),
            }),
        )   

