import django_filters
from django.db.models import Q
from .models import TITRE_PROFESSIONNEL_CHOICE, CentreFormation,Filiere,CentreEtFiliere,Inscription
from django.forms.widgets import TextInput,Select


class FormationFilter(django_filters.FilterSet):
    centre=django_filters.ModelChoiceFilter(
        queryset=CentreFormation.objects.all(),
        label="Centre de formation",
        empty_label="---Tous les centres---",
        widget=Select(attrs={
            'class': 'block w-full py-2 px-3 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-bsb-gold focus:border-bsb-gold',
            'data-autosubmit': 'true'
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
        widget=TextInput(attrs={
            'class': 'block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-bsb-gold focus:border-bsb-gold',
            'placeholder': 'Rechercher une filière...',
        })
    )
    titre_professionnel = django_filters.ChoiceFilter(
        field_name='titre_professionnel',
        choices=TITRE_PROFESSIONNEL_CHOICE,
        empty_label="---Tous les titres---",
        widget=Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-bsb-gold focus:border-bsb-gold',
            'data-autosubmit': 'true'
        })
    )

    class Meta:
        model = Filiere
        fields = ['recherche', 'titre_professionnel']

class SubscriptionFilter(django_filters.FilterSet):
    recherche = django_filters.CharFilter(
        label="Recherche",
        method='filter_recherche',
        widget=TextInput(attrs={
            'class': 'block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-bsb-gold focus:border-bsb-gold',
            'placeholder': 'Nom, prénom ou matricule...',
        })
    )
    formation=django_filters.ModelChoiceFilter(
        queryset=CentreEtFiliere.objects.all(),
        label="Centre de formation",
        empty_label="---Centre---",
        widget=Select(attrs={
            'class': 'block w-full py-2 px-3 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-bsb-gold focus:border-bsb-gold',
            'data-autosubmit': 'true'
        })
    )
    statut = django_filters.ChoiceFilter(
        choices=Inscription.STATUT_CHOICE,
        empty_label="---Tous les statuts---",
        widget=Select(attrs={
            'class': 'block w-full py-2 px-3 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-bsb-gold focus:border-bsb-gold',
            'data-autosubmit': 'true'
        })
    )

    def filter_recherche(self, queryset, name, value):
        return queryset.filter(
            Q(eleve__nom__icontains=value) |
            Q(eleve__prenom__icontains=value) |
            Q(eleve__matricule__icontains=value)
        )

    class Meta:
        model=Inscription
        fields=['recherche', 'formation', 'statut']