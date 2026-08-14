from django.contrib import admin

from .models import AbonneNewsletter, Actualite


@admin.register(Actualite)
class ActualiteAdmin(admin.ModelAdmin):
    list_display = ('titre', 'statut', 'date_publication', 'abonnes_notifies', 'auteur')
    list_filter = ('statut', 'abonnes_notifies')
    search_fields = ('titre', 'chapeau', 'contenu')
    readonly_fields = ('slug', 'abonnes_notifies', 'date_creation', 'date_modification')


@admin.register(AbonneNewsletter)
class AbonneNewsletterAdmin(admin.ModelAdmin):
    list_display = ('email', 'actif', 'date_inscription', 'date_desinscription')
    list_filter = ('actif',)
    search_fields = ('email',)
    readonly_fields = ('token', 'date_inscription', 'date_desinscription')
