"""Déclaration des ImportSpec pour les modèles "simples" de l'app `accounts`
(module Facturation) — Phase 1 de l'import en masse Excel/CSV."""

from courses.bulk_import.specs import ColumnSpec, ImportSpec

from .forms import ClientPrestationForm, PrestationQuickForm
from .models import Client_prestation, Prestation_prestation

# ─── Prestation_prestation ──────────────────────────────────────────────

SPEC_PRESTATION = ImportSpec(
    slug="prestation",
    verbose_name="Prestation",
    model=Prestation_prestation,
    form_class=PrestationQuickForm,
    columns=[
        ColumnSpec("Libellé de la prestation", "libelle", required=True, kind="text"),
        ColumnSpec("Description", "description", required=False, kind="text"),
        ColumnSpec("Prix unitaire (FCFA)", "prix_unitaire", required=True, kind="decimal"),
    ],
    url_namespace="accounts",
    template_url_name="prestation_import_template",
    upload_url_name="prestation_import",
    list_url_name="prestation_list",
)


# ─── Client_prestation ──────────────────────────────────────────────────

SPEC_CLIENT = ImportSpec(
    slug="client",
    verbose_name="Client (facturation)",
    model=Client_prestation,
    form_class=ClientPrestationForm,
    columns=[
        ColumnSpec("Type de client", "type_client", required=True, kind="choice_static",
                    choices=Client_prestation.TYPE_CLIENT),
        ColumnSpec("Nom", "nom", required=False, kind="text",
                    help_text="Obligatoire si Type de client = personne."),
        ColumnSpec("Prénom", "prenom", required=False, kind="text",
                    help_text="Obligatoire si Type de client = personne."),
        ColumnSpec("Téléphone", "telephone", required=False, kind="text",
                    help_text="Obligatoire si Type de client = personne."),
        ColumnSpec("Adresse", "adresse", required=False, kind="text",
                    help_text="Toujours obligatoire."),
        ColumnSpec("Type de pièce", "type_piece", required=False, kind="choice_static",
                    choices=Client_prestation.TYPE_PIECE,
                    help_text="Obligatoire si Type de client = personne."),
        ColumnSpec("Numéro de pièce", "numero_piece", required=False, kind="text",
                    help_text="Obligatoire si Type de client = personne."),
        ColumnSpec("Raison sociale", "raison_sociale", required=False, kind="text",
                    help_text="Obligatoire si Type de client = entreprise/autre."),
        ColumnSpec("IFU", "ifu", required=False, kind="text",
                    help_text="Obligatoire si Type de client = entreprise/autre."),
        ColumnSpec("Statut juridique", "statut", required=False, kind="text",
                    help_text="Obligatoire si Type de client = entreprise/autre."),
        ColumnSpec("Date de création (JJ/MM/AAAA)", "date_creation", required=False, kind="date",
                    help_text="Obligatoire si Type de client = entreprise/autre."),
    ],
    intro=(
        "Les champs obligatoires diffèrent selon le Type de client : pour "
        "une personne physique, Nom/Prénom/Type de pièce/Numéro de pièce/"
        "Téléphone/Adresse sont requis ; pour une entreprise ou un autre "
        "type, Adresse/IFU/Raison sociale/Statut/Date de création sont requis."
    ),
    url_namespace="accounts",
    template_url_name="client_import_template",
    upload_url_name="client_import",
    list_url_name="client_list",
)
