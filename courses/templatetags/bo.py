"""Filtres de presentation du back-office.

Les noms de classes sont ecrits ici en toutes lettres : `tailwind.config.js`
inclut `./**/*.py` dans son balayage, elles sont donc bien compilees. Une
classe construite par concatenation dans un gabarit
(`bo-badge-{{ variable }}`) ne le serait pas — le scanner ne cherche que des
litteraux.
"""
from django import template

register = template.Library()

# Familles de roles. Le decoupage suit l'organisation reelle, pas l'esthetique :
# un agent se repere d'abord a son rattachement.
_FAMILLE_ROLE = {
    'admin': 'direction', 'dg': 'direction', 'dir': 'direction',
    'deps': 'national', 'agent_comptable': 'national', 'daf': 'national',
    'gestionnaire': 'centre', 'caissier': 'centre', 'membre': 'centre',
    'formateur': 'pedagogie',
}

_BADGE = {
    'direction': 'bo-badge-danger',
    'national': 'bo-badge-info',
    'centre': 'bo-badge-warning',
    'pedagogie': 'bo-badge-success',
}

_PASTILLE = {
    'direction': 'bg-red-600',
    'national': 'bg-blue-600',
    'centre': 'bg-amber-600',
    'pedagogie': 'bg-green-600',
}


@register.filter
def badge_role(user_type):
    """Classe de pastille d'etat correspondant a la famille du role."""
    return _BADGE.get(_FAMILLE_ROLE.get(user_type), 'bo-badge-neutral')


@register.filter
def pastille_role(user_type):
    """Classe de fond de l'initiale, accordee au badge du meme agent."""
    return _PASTILLE.get(_FAMILLE_ROLE.get(user_type), 'bg-gray-500')
