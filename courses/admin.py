from django.contrib import admin
from django.utils.html import format_html

from .models import DG, Direction_reg, CentreFormation, Filiere, CentreEtFiliere, Membre, Module, Frais, Cours, Inscription, Paiement, PieceJointeInscription,DocumentEleve,AnneeScolaire


###### ADMIN LEVEL  ######

# DIRECTION
@admin.register(Direction_reg)
class Direction_regAdmin(admin.ModelAdmin):
    list_display = ["nom_direction", "chef_lieu", "region", "directeur"]

# CENTER
@admin.register(CentreFormation)
class CentreFormationAdmin(admin.ModelAdmin):
    list_display = ["direction", "niveau_centre", "nom_centre", "adresse", "ville"]
    #filter_horizontal = ["filieres"]

# FIELD
@admin.register(Filiere)
class FiliereAdmin(admin.ModelAdmin):
    list_display = ["nom_filiere", "nom_diplome", "niveau_diplome", "is_active"]

# CENTER-FIELD JONCTION
@admin.register(CentreEtFiliere)
class CentreEtFiliereAdmin(admin.ModelAdmin):
    list_display = ["centre", "filiere", "duree_display", "is_active", "communique"]

@admin.register(DocumentEleve)
class DocumentEleveAdmin(admin.ModelAdmin):
    list_display=["inscription","piece_requise","piece"]
# MODULE
@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ["nom_module", "get_filieres", "volume_h_cours"]
    filter_horizontal = ["filieres"]

    def get_filieres(self, obj):
        return ", ".join(f.nom_filiere for f in obj.filieres.all())
    get_filieres.short_description = "Métiers"

# FEE
@admin.register(Frais)
class FraisAdmin(admin.ModelAdmin):
    list_display = [ "filiere", "montant","centre","type_frais"]
    
    def centre(self,obj):
        return obj.formation.centre
    def filiere(self,obj):
        return obj.formation.filiere
    

# COURSE
@admin.register(Cours)
class CoursAdmin(admin.ModelAdmin):
    list_display = ["module", "libelle_cours", "volume_h_cours"]

    search_fields = ["module__nom_module", "libelle_cours"]
    list_filter = ["module__filieres__nom_filiere"]

# SUBSCRIPTION
@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ["formation", "eleve", "date_inscription", "annee_scolaire", "statut"]
    list_filter = ["statut", "annee_scolaire"]
    search_fields = ["eleve__utilisateur__nom", "eleve__utilisateur__prenom", "formation__centre__nom_centre", "formation__filiere__nom_filiere"]
    
    
#Anneescolaire
@admin.register(AnneeScolaire)
class AnneeScolaireAdmin(admin.ModelAdmin):
    list_display = ["libelle_anne"]
    list_filter = ["libelle_anne"]
    search_fields = ["libelle_anne"]

#PAYMENT
@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
     list_display = ["dette", "montant_paiement", "date_paiement", "mode_paiement", "tranche"]
     list_filter = [ "mode_paiement", "date_paiement"]
     search_fields = ["inscription__eleve__utilisateur__nom", "inscription__eleve__utilisateur__prenom", "inscription__formation__centre__nom_centre", "inscription__formation__filiere__nom_filiere"]

# DOCUMENT
@admin.register(PieceJointeInscription)
class PieceJointeInscriptionAdmin(admin.ModelAdmin):
    list_display = ["formation", "libelle_piece", "type_piece"] 
    list_filter = ["type_piece"]
    search_fields = ["formation__filiere__nom_filiere", "formation__centre__nom_centre", "libelle_piece"]    


###### ABOUT LEVEL  ######

# DG
@admin.register(DG)
class DGAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'position', 'photo_preview', 'is_active', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['full_name', 'position']
    readonly_fields = ['photo_preview_large', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('full_name', 'position', 'is_active')
        }),
        ('Photo', {
            'fields': ('photo', 'photo_preview_large')
        }),
        ('Messages', {
            'fields': ('message', 'commitment'),
            'description': 'Le message principal et l\'engagement du DG'
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 50%;" />',
                obj.photo.url
            )
        return "Pas de photo"
    photo_preview.short_description = "Aperçu"

    def photo_preview_large(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 300px; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" />',
                obj.photo.url
            )
        return "Aucune photo téléchargée"
    photo_preview_large.short_description = "Aperçu de la photo"

    def has_add_permission(self, request):
        # Allow adding only if no active DG exists
        if DG.objects.filter(is_active=True).exists():
            return False
        return super().has_add_permission(request)

# MEMBER
@admin.register(Membre)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'position', 'photo_preview', 'order', 'is_active', 'updated_at']
    list_filter = ['is_active', 'position', 'created_at']
    search_fields = ['full_name', 'position', 'description']
    list_editable = ['order', 'is_active']
    readonly_fields = ['photo_preview_large', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informations Principales', {
            'fields': ('full_name', 'position', 'order', 'is_active')
        }),
        ('Photo', {
            'fields': ('photo', 'photo_preview_large')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 50%;" />',
                obj.photo.url
            )
        return "Pas de photo"
    photo_preview.short_description = "Aperçu"

    def photo_preview_large(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 300px; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" />',
                obj.photo.url
            )
        return "Aucune photo téléchargée"
    photo_preview_large.short_description = "Aperçu de la photo"
    
    