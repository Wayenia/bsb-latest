"""Déclarations réutilisables pour l'import Excel/CSV en masse.

Un `ImportSpec` décrit un modèle importable : ses colonnes attendues, et
comment chaque ligne doit être validée/enregistrée. Deux modes :

- mode="form" (le cas courant) : chaque ligne est passée à un ModelForm déjà
  existant dans le projet (`form_class`), exactement comme si elle avait été
  soumise via le formulaire web — la logique métier n'est jamais dupliquée.
- mode="manual" : pour les rares vues qui valident le POST à la main plutôt
  que via un ModelForm (ex. Region/Province) ; `manual_validator(resolved)`
  doit reproduire fidèlement les mêmes règles que la vue existante et
  retourner (ok, objet_ou_None, liste_erreurs).
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class ColumnSpec:
    header: str
    field_name: str
    required: bool = True
    # text | int | decimal | bool | date | choice_static |
    # fk_pk | fk_pk_multi | fk_name_value | fk_name_value_multi
    kind: str = "text"
    choices: Optional[list] = None
    fk_model: Optional[type] = None
    fk_lookup_field: str = "nom"
    separator: str = ","
    help_text: str = ""


@dataclass
class ImportSpec:
    slug: str
    verbose_name: str
    model: type
    columns: list
    mode: str = "form"
    form_class: Optional[type] = None
    manual_validator: Optional[Callable[[dict], tuple]] = None
    pre_validate_hook: Optional[Callable[[dict], None]] = None
    # (obj, resolved) -> dict | None — le dict est attaché à RowSuccess.extra
    post_save_hook: Optional[Callable[[Any, dict], Optional[dict]]] = None
    label_fn: Optional[Callable[[Any], str]] = None
    sheet_name: str = "Import"
    intro: str = ""
    # Retourne une liste de dicts {field_name: valeur} ecrits sous les en-tetes
    # du modele telecharge. Sert a livrer un fichier deja rempli des donnees
    # existantes, que l'on corrige plutot que de tout ressaisir.
    prefill_fn: Optional[Callable[[], list]] = None
    # (resolved) -> instance existante | None. Fourni, une ligne qui designe un
    # enregistrement deja present le met a jour au lieu d'echouer sur une
    # contrainte d'unicite. Indispensable des lors que le modele telecharge est
    # pre-rempli : on renvoie le fichier corrige, pas un fichier vierge.
    instance_lookup_fn: Optional[Callable[[dict], Any]] = None

    # Résolution des URLs pour les liens générés par les templates génériques
    # (bouton "Télécharger le modèle", "Retour à la liste"...).
    url_namespace: str = ""
    template_url_name: str = ""
    upload_url_name: str = ""
    list_url_name: str = ""
