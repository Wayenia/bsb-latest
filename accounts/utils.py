"""Utilitaires pour le module Facturation et Prestation."""

_UNITES = [
    "", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
    "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize",
    "dix-sept", "dix-huit", "dix-neuf",
]

_DIZAINES = [
    "", "", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante",
    "quatre-vingt", "quatre-vingt",
]


def _deux_chiffres(n):
    """Convertit un nombre de 0 à 99 en lettres françaises."""
    if n < 20:
        return _UNITES[n]

    dizaine, unite = divmod(n, 10)

    if dizaine in (7, 9):
        # soixante-dix (70-79) / quatre-vingt-dix (90-99)
        dizaine -= 1
        unite += 10

    mot = _DIZAINES[dizaine]
    if unite == 0:
        # "quatre-vingts" prend un s au pluriel quand rien ne suit
        return mot + "s" if dizaine == 8 else mot
    if unite == 1 and dizaine not in (8,):
        return f"{mot} et un"
    return f"{mot}-{_UNITES[unite]}"


def _trois_chiffres(n):
    """Convertit un nombre de 0 à 999 en lettres françaises."""
    centaine, reste = divmod(n, 100)
    parties = []
    if centaine:
        if centaine == 1:
            parties.append("cent")
        else:
            parties.append(f"{_UNITES[centaine]} cent" + ("s" if reste == 0 else ""))
    if reste:
        parties.append(_deux_chiffres(reste))
    return " ".join(parties)


def montant_en_lettres(montant):
    """Convertit un montant entier (FCFA) en toutes lettres françaises.

    Ex. 292965000 -> "deux cent quatre-vingt-douze millions neuf cent
    soixante-cinq mille".
    """
    montant = int(round(montant))

    if montant == 0:
        return "zéro"

    negatif = montant < 0
    montant = abs(montant)

    tranches = [
        (1_000_000_000_000, "billion", "billions"),
        (1_000_000_000, "milliard", "milliards"),
        (1_000_000, "million", "millions"),
        (1_000, "mille", "mille"),
    ]

    parties = []
    reste = montant
    for valeur, singulier, pluriel in tranches:
        if reste >= valeur:
            nombre_tranche, reste = divmod(reste, valeur)
            if valeur == 1_000 and nombre_tranche == 1:
                parties.append("mille")
            else:
                mot_nombre = _trois_chiffres(nombre_tranche)
                mot_unite = singulier if nombre_tranche == 1 else pluriel
                parties.append(f"{mot_nombre} {mot_unite}")

    if reste:
        parties.append(_trois_chiffres(reste))

    resultat = " ".join(parties)
    return f"moins {resultat}" if negatif else resultat
