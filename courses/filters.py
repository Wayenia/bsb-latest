from .models import TITRE_PROFESSIONNEL_CHOICE, CentreEtFiliere,Filiere,CentreFormation
import django_filters
from django.forms.widgets import Select,TextInput

class CentreFormationFilter(django_filters.FilterSet):
    centre=django_filters.ModelChoiceFilter(
        queryset=CentreFormation.objects.all(),
        label="Centre de formation",
        empty_label="---Tous les centres---",
        widget=Select(attrs={
            'class': 'block w-full py-2 px-3 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-bsb-gold focus:border-bsb-gold',
            'onchange': 'this.form.submit()'
        })
    )

    formation=django_filters.CharFilter(
        field_name='filiere__nom_filiere',
        lookup_expr='icontains',
        widget=TextInput(attrs={
            'class': 'block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-bsb-gold focus:border-bsb-gold',
            'placeholder': 'Rechercher une formation...',
        })
    )

    class Meta:
        model=CentreEtFiliere
        fields=['centre']

class FiliereFilter(django_filters.FilterSet):
    recherche = django_filters.CharFilter(
        field_name='nom_filiere',
        lookup_expr='icontains',
        label='Recherche',
    )
    titre_professionnel = django_filters.ChoiceFilter(
        choices=[('', 'Tous les titres')] + list(TITRE_PROFESSIONNEL_CHOICE),
        label='Titre professionnel',
        empty_label=None,
    )
    is_active = django_filters.ChoiceFilter(
        choices=[('', 'Tous'), ('true', 'Actif'), ('false', 'Inactif')],
        label='Disponible',
        empty_label=None,
        method='filter_is_active',
    )

    def filter_is_active(self, queryset, name, value):
        if value == 'true':
            return queryset.filter(is_active=True)
        if value == 'false':
            return queryset.filter(is_active=False)
        return queryset  # valeur vide → retourne tout

    class Meta:
        model  = Filiere
        fields = ['recherche', 'titre_professionnel', 'is_active']



