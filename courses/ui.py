"""Bascule entre l'interface refondue et l'interface d'origine.

Toute refonte d'ecran conserve son gabarit d'origine sous le meme nom suffixe
`_classique`. Le reglage BO_UI decide lequel est rendu, si bien qu'un retour en
arriere ne demande ni modification de code ni redeploiement du depot : une
commande suffit (./bascule_ui.sh classique).

Un ecran qui n'a pas de variante classique est rendu tel quel : la bascule ne
peut donc jamais provoquer d'erreur de gabarit introuvable.
"""
from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loader import get_template


def gabarit(chemin):
    """Nom du gabarit a rendre, selon le reglage en vigueur."""
    if getattr(settings, 'BO_UI', 'nouveau') != 'classique':
        return chemin
    variante = chemin[:-len('.html')] + '_classique.html' if chemin.endswith('.html') else chemin
    try:
        get_template(variante)
    except TemplateDoesNotExist:
        return chemin
    return variante
