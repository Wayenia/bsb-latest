"""Déclaration des ImportSpec pour les modèles "simples" de l'app `courses`
(Phase 1 de l'import en masse Excel/CSV). Chaque spec s'appuie sur le
ModelForm déjà utilisé par la vue de création correspondante — voir le plan
d'implémentation pour le détail des vues/formulaires réutilisés."""

import secrets
import string

from accounts.models import Utilisateur

from courses.models import (
    AnneeScolaire, CentreFormation, Cours, Direction_reg, Filiere, Module,
    Province, Region, TITRE_PROFESSIONNEL_CHOICE, TypeFrais,
)
from courses.forms import (
    AgentForm, AnneeScolaireForm, CentreFormationForm, CoursForm,
    DirectionRegForm, FiliereForm, ModuleForm, TypeFraisForm, USER_TYPE_CHOICES,
)

from .bulk_import.specs import ColumnSpec, ImportSpec


# ─── Region (mode manuel — pas de ModelForm, réplique region_create) ───────

def _region_validator(resolved):
    nom = (resolved.get("nom_region") or "").strip()
    chef_lieu = (resolved.get("chef_lieu") or "").strip()
    errors = []
    if not nom:
        errors.append("Le nom de la région est obligatoire.")
    elif Region.objects.filter(nom_region__iexact=nom).exists():
        errors.append("Une région avec ce nom existe déjà.")
    if not chef_lieu:
        errors.append("Le chef-lieu est obligatoire.")
    if errors:
        return False, None, errors
    region = Region.objects.create(nom_region=nom, chef_lieu=chef_lieu)
    return True, region, []


SPEC_REGION = ImportSpec(
    slug="region",
    verbose_name="Région",
    model=Region,
    mode="manual",
    manual_validator=_region_validator,
    columns=[
        ColumnSpec("Nom de la région", "nom_region", required=True, kind="text"),
        ColumnSpec("Chef-lieu", "chef_lieu", required=True, kind="text"),
    ],
    url_namespace="bsb_admin",
    template_url_name="region_import_template",
    upload_url_name="region_import",
    list_url_name="region_list",
)


# ─── Province (mode manuel — réplique province_create) ─────────────────────

def _province_validator(resolved):
    nom = (resolved.get("nom_province") or "").strip()
    chef_lieu = (resolved.get("chef_lieu") or "").strip()
    region_id = resolved.get("region")
    errors = []
    if not nom:
        errors.append("Le nom de la province est obligatoire.")
    elif Province.objects.filter(nom_province__iexact=nom).exists():
        errors.append("Une province avec ce nom existe déjà.")
    if not chef_lieu:
        errors.append("Le chef-lieu est obligatoire.")
    if not region_id:
        errors.append("La région est obligatoire.")
    if errors:
        return False, None, errors
    province = Province.objects.create(nom_province=nom, chef_lieu=chef_lieu, region_id=region_id)
    return True, province, []


SPEC_PROVINCE = ImportSpec(
    slug="province",
    verbose_name="Province",
    model=Province,
    mode="manual",
    manual_validator=_province_validator,
    columns=[
        ColumnSpec("Nom de la province", "nom_province", required=True, kind="text"),
        ColumnSpec("Chef-lieu", "chef_lieu", required=True, kind="text"),
        ColumnSpec("Région", "region", required=True, kind="fk_pk",
                    fk_model=Region, fk_lookup_field="nom_region"),
    ],
    url_namespace="bsb_admin",
    template_url_name="province_import_template",
    upload_url_name="province_import",
    list_url_name="region_list",
)


# ─── TypeFrais ───────────────────────────────────────────────────────────

SPEC_TYPE_FRAIS = ImportSpec(
    slug="type_frais",
    verbose_name="Type de frais",
    model=TypeFrais,
    form_class=TypeFraisForm,
    columns=[
        ColumnSpec("Libellé", "libelle", required=True, kind="text"),
    ],
    url_namespace="bsb_admin",
    template_url_name="type_frais_import_template",
    upload_url_name="type_frais_import",
    list_url_name="type_frais_list",
)


# ─── AnneeScolaire ───────────────────────────────────────────────────────

SPEC_ANNEE = ImportSpec(
    slug="annee",
    verbose_name="Année scolaire",
    model=AnneeScolaire,
    form_class=AnneeScolaireForm,
    columns=[
        ColumnSpec("Libellé (AAAA-AAAA)", "libelle_anne", required=True, kind="text",
                    help_text="Format AAAA-AAAA, années consécutives (ex: 2025-2026)."),
    ],
    url_namespace="bsb_admin",
    template_url_name="annee_import_template",
    upload_url_name="annee_import",
    list_url_name="annee_list",
)


# ─── Filiere (métier) — colonnes simples uniquement, sans gestion modules ──

SPEC_FILIERE = ImportSpec(
    slug="filiere",
    verbose_name="Métier (filière)",
    model=Filiere,
    form_class=FiliereForm,
    columns=[
        ColumnSpec("Nom du métier", "nom_filiere", required=True, kind="text"),
        ColumnSpec("Titre professionnel", "titre_professionnel", required=False,
                    kind="choice_static", choices=TITRE_PROFESSIONNEL_CHOICE),
        ColumnSpec("Conditions d'accès", "niveau_diplome", required=False, kind="text"),
        ColumnSpec("Texte défilant", "texte_defilante", required=False, kind="text"),
        ColumnSpec("Actif (Oui/Non)", "is_active", required=False, kind="bool",
                    help_text="Laisser vide = Non."),
    ],
    intro=(
        "L'association des modules existants et la création de nouveaux "
        "modules à la volée ne sont pas gérées par cet import — utilisez le "
        "formulaire de création du métier pour cela."
    ),
    url_namespace="bsb_admin",
    template_url_name="field_import_template",
    upload_url_name="field_import",
    list_url_name="field_list",
)


# ─── Direction_reg ──────────────────────────────────────────────────────

SPEC_DIRECTION = ImportSpec(
    slug="direction",
    verbose_name="Direction inter-régionale",
    model=Direction_reg,
    form_class=DirectionRegForm,
    columns=[
        ColumnSpec("Nom de la direction", "nom_direction", required=True, kind="text"),
        ColumnSpec("Chef-lieu", "chef_lieu", required=True, kind="fk_name_value",
                    fk_model=Region, fk_lookup_field="chef_lieu"),
        ColumnSpec("Régions couvertes", "regions", required=True, kind="fk_name_value_multi",
                    fk_model=Region, fk_lookup_field="nom_region", separator=",",
                    help_text="Noms de régions séparés par une virgule."),
    ],
    intro=(
        "Le chef-lieu doit appartenir à l'une des régions couvertes listées "
        "sur la même ligne. Le champ Directeur (optionnel) n'est pas géré "
        "par cet import."
    ),
    url_namespace="bsb_admin",
    template_url_name="direction_import_template",
    upload_url_name="direction_import",
    list_url_name="direction_list",
)


# ─── Module ─────────────────────────────────────────────────────────────

SPEC_MODULE = ImportSpec(
    slug="module",
    verbose_name="Module",
    model=Module,
    form_class=ModuleForm,
    columns=[
        ColumnSpec("Nom du module", "nom_module", required=True, kind="text"),
        ColumnSpec("Volume horaire (heures)", "volume_h_cours", required=True, kind="int"),
        ColumnSpec("Métiers", "filieres", required=False, kind="fk_pk_multi",
                    fk_model=Filiere, fk_lookup_field="nom_filiere", separator=",",
                    help_text="Noms de métiers séparés par une virgule."),
    ],
    url_namespace="bsb_admin",
    template_url_name="module_import_template",
    upload_url_name="module_import",
    list_url_name="module_list",
)


# ─── Cours ──────────────────────────────────────────────────────────────

SPEC_COURS = ImportSpec(
    slug="cours",
    verbose_name="Cours",
    model=Cours,
    form_class=CoursForm,
    columns=[
        ColumnSpec("Module", "module", required=True, kind="fk_pk",
                    fk_model=Module, fk_lookup_field="nom_module"),
        ColumnSpec("Libellé du cours", "libelle_cours", required=True, kind="text"),
        ColumnSpec("Volume horaire", "volume_h_cours", required=True, kind="text",
                    help_text="Ex: 20h"),
    ],
    url_namespace="bsb_admin",
    template_url_name="course_import_template",
    upload_url_name="course_import",
    list_url_name="course_list",
)


# ─── CentreFormation ────────────────────────────────────────────────────

SPEC_CENTRE = ImportSpec(
    slug="centre",
    verbose_name="Centre de formation",
    model=CentreFormation,
    form_class=CentreFormationForm,
    columns=[
        ColumnSpec("Nom du centre", "nom_centre", required=True, kind="text"),
        ColumnSpec("Code du centre", "code_centre", required=False, kind="text"),
        ColumnSpec("Direction", "direction", required=False, kind="fk_pk",
                    fk_model=Direction_reg, fk_lookup_field="nom_direction"),
        ColumnSpec("Province", "province", required=False, kind="fk_pk",
                    fk_model=Province, fk_lookup_field="nom_province"),
        ColumnSpec("Niveau du centre", "niveau_centre", required=False, kind="int"),
        ColumnSpec("Adresse", "adresse", required=False, kind="text"),
        ColumnSpec("Téléphone", "tel", required=False, kind="text"),
    ],
    url_namespace="bsb_admin",
    template_url_name="center_import_template",
    upload_url_name="center_import",
    list_url_name="center_list",
)


# ─── Agent (Formateur / MembreAdministration / DirecteurInterRegional) ───
# Mot de passe généré automatiquement (jamais dans le fichier Excel) — voir
# AgentForm.save() : un mot de passe vide sur un compte neuf appelle
# set_unusable_password(), il faut donc toujours en injecter un.

_ROLE_CHOICES_IMPORT = [c for c in USER_TYPE_CHOICES if c[0]]


def _generer_mot_de_passe():
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(10))


def _agent_pre_validate_hook(resolved):
    resolved["password"] = _generer_mot_de_passe()


def _agent_post_save_hook(obj, resolved):
    # Le mot de passe généré (avant hachage par AgentForm.save()) est repris
    # tel quel ici pour être affiché une seule fois dans le rapport.
    return {
        "username": resolved.get("username"),
        "password": resolved.get("password"),
    }


def _agent_label_fn(obj):
    return f"{obj.nom} {obj.prenom} ({obj.get_user_type_display()})"


SPEC_AGENT = ImportSpec(
    slug="agent",
    verbose_name="Agent (Formateur / Membre administration / Directeur inter-régional)",
    model=Utilisateur,
    form_class=AgentForm,
    pre_validate_hook=_agent_pre_validate_hook,
    post_save_hook=_agent_post_save_hook,
    label_fn=_agent_label_fn,
    columns=[
        ColumnSpec("Nom", "nom", required=True, kind="text"),
        ColumnSpec("Prénom(s)", "prenom", required=True, kind="text"),
        ColumnSpec("Nom d'utilisateur", "username", required=True, kind="text"),
        ColumnSpec("Email", "email", required=True, kind="text"),
        ColumnSpec("Téléphone", "tel", required=False, kind="text"),
        ColumnSpec("Sexe (m/f)", "sexe", required=False, kind="choice_static",
                    choices=[("m", "Masculin"), ("f", "Féminin")]),
        ColumnSpec("Date de naissance (JJ/MM/AAAA)", "date_naissance", required=False, kind="date"),
        ColumnSpec("Adresse", "adresse", required=False, kind="text"),
        ColumnSpec("Rôle", "user_type", required=True, kind="choice_static",
                    choices=_ROLE_CHOICES_IMPORT),
        ColumnSpec("Centre (si Formateur)", "centre_formateur", required=False, kind="fk_pk",
                    fk_model=CentreFormation, fk_lookup_field="nom_centre"),
        ColumnSpec("Date d'intégration (si Formateur, JJ/MM/AAAA)", "date_integration_formateur",
                    required=False, kind="date"),
        ColumnSpec("Métier dispensé (si Formateur)", "filiere", required=False, kind="fk_pk",
                    fk_model=Filiere, fk_lookup_field="nom_filiere"),
        ColumnSpec("Module dispensé (si Formateur)", "module", required=False, kind="fk_pk",
                    fk_model=Module, fk_lookup_field="nom_module"),
        ColumnSpec("Direction inter-régionale (si Directeur)", "direction_interreg",
                    required=False, kind="fk_pk", fk_model=Direction_reg, fk_lookup_field="nom_direction"),
        ColumnSpec("Centre rattaché (si Directeur de centre/Comptable/Caissier)", "centre_role",
                    required=False, kind="fk_pk", fk_model=CentreFormation, fk_lookup_field="nom_centre"),
        ColumnSpec("Centre administré (si Administrateur ou DAF, optionnel)", "centre_admin",
                    required=False, kind="fk_pk", fk_model=CentreFormation, fk_lookup_field="nom_centre"),
        ColumnSpec("Fonction / emploi (si Membre de l'administration)", "emploi_libre",
                    required=False, kind="text",
                    help_text="Obligatoire si Rôle = Membre de l'administration (fonction libre)."),
    ],
    intro=(
        "Le mot de passe est généré automatiquement pour chaque compte créé "
        "(il n'y a pas de colonne mot de passe) et affiché une seule fois "
        "dans le rapport d'import — transmettez-le immédiatement à l'agent. "
        "Selon le Rôle choisi, seules certaines colonnes sont obligatoires "
        "(ex: Centre + Date d'intégration pour un Formateur, Direction "
        "inter-régionale pour un Directeur, Centre rattaché pour un "
        "Directeur de centre/Agent comptable/Caissier)."
    ),
    url_namespace="bsb_admin",
    template_url_name="agent_import_template",
    upload_url_name="agent_import",
    list_url_name="agent_list",
)
