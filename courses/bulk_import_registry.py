"""Déclaration des ImportSpec pour les modèles "simples" de l'app `courses`
(Phase 1 de l'import en masse Excel/CSV). Chaque spec s'appuie sur le
ModelForm déjà utilisé par la vue de création correspondante — voir le plan
d'implémentation pour le détail des vues/formulaires réutilisés."""

import secrets
import string
from datetime import datetime

from django.utils import timezone

from accounts.models import Utilisateur

from courses.models import (
    AnneeScolaire, CentreEtFiliere, CentreFormation, Cours, Direction_reg,
    Filiere, Frais, Membre, Module, Province, Region, TITRE_PROFESSIONNEL_CHOICE,
    TYPE_FORMATION_CHOICE, TypeFrais,
)
from courses.forms import (
    AgentForm, AnneeScolaireForm, CentreFormationForm, CoursForm,
    DirectionRegForm, FiliereForm, MembreEquipeImportForm, ModuleForm, TypeFraisForm,
    USER_TYPE_CHOICES,
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
    verbose_name="Année de formation",
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


# ── Agent (formateur, membre de l'administration, directeur inter-regional) ──
# Mot de passe genere automatiquement, jamais lu dans le fichier : un mot de
# passe vide appellerait set_unusable_password().

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


# ── Programmation (CentreEtFiliere) ──────────────────────────────────────────
# Mode manuel : une ligne touche trois modeles, Filiere (dedupliquee par nom),
# CentreEtFiliere et Frais (propre a chaque couple centre-metier).

def _parse_date_aware(value):
    """resolve_column(kind="date") renvoie une chaîne "AAAA-MM-JJ" ; les 3
    champs date de CentreEtFiliere sont des DateTimeField — on la convertit
    en datetime timezone-aware (minuit) pour éviter l'avertissement Django
    sur les datetimes naïfs (USE_TZ=True)."""
    if not value:
        return None
    naive = datetime.strptime(value, "%Y-%m-%d")
    return timezone.make_aware(naive)


def _programmation_validator(resolved):
    centre_id = resolved.get("centre")
    nom_filiere = (resolved.get("nom_filiere") or "").strip()
    errors = []
    if not centre_id:
        errors.append("Le centre est obligatoire.")
    if not nom_filiere:
        errors.append("Le métier est obligatoire.")
    if errors:
        return False, None, errors

    if CentreEtFiliere.objects.filter(centre_id=centre_id, filiere__nom_filiere__iexact=nom_filiere).exists():
        return False, None, [f"Cette formation « {nom_filiere} » existe déjà pour ce centre."]

    # Le fichier fait autorite : un metier deja present est mis a jour avec les
    # valeurs de la ligne.
    filiere = Filiere.objects.filter(nom_filiere__iexact=nom_filiere).first()
    filiere_fields = {
        "niveau_diplome": resolved.get("niveau_diplome") or None,
        "titre_professionnel": resolved.get("titre_professionnel") or None,
    }
    if filiere:
        changed = False
        for attr, val in filiere_fields.items():
            if val not in (None, "") and getattr(filiere, attr) != val:
                setattr(filiere, attr, val)
                changed = True
        if changed:
            filiere.save()
    else:
        filiere = Filiere.objects.create(nom_filiere=nom_filiere, is_active=True, **filiere_fields)

    annee_id = resolved.get("annee_prog")
    if not annee_id:
        derniere_annee = AnneeScolaire.objects.order_by("-date_creation").first()
        annee_id = derniere_annee.pk if derniere_annee else None

    duree_jours = resolved.get("duree_jours_override") or (resolved.get("duree_mois") or 0) * 30

    cef_kwargs = dict(
        centre_id=centre_id,
        filiere=filiere,
        type_formation=resolved.get("type_formation") or "initiale",
        is_active=True if resolved.get("is_active") is None else resolved["is_active"],
        annee_prog_id=annee_id,
        duree_jours=duree_jours or None,
        date_limite_inscription=_parse_date_aware(resolved.get("date_limite_inscription")),
    )
    date_lancement = _parse_date_aware(resolved.get("date_lancement"))
    if date_lancement:
        cef_kwargs["date_lancement"] = date_lancement
    formation = CentreEtFiliere.objects.create(**cef_kwargs)

    montant = resolved.get("montant_frais")
    if montant:
        type_frais = TypeFrais.objects.filter(libelle__iexact="Scolarité").first()
        if not type_frais:
            type_frais = TypeFrais.objects.create(libelle="Scolarité")
        Frais.objects.create(formation=formation, type_frais=type_frais, montant=montant)

    return True, formation, []


def _programmation_label_fn(obj):
    return f"{obj.filiere.nom_filiere} — {obj.centre.nom_centre}"


SPEC_PROGRAMMATION = ImportSpec(
    slug="programmation",
    verbose_name="Formation à lancer (centre × métier)",
    model=CentreEtFiliere,
    mode="manual",
    manual_validator=_programmation_validator,
    label_fn=_programmation_label_fn,
    columns=[
        ColumnSpec("Centre de formation", "centre", required=True, kind="fk_pk",
                    fk_model=CentreFormation, fk_lookup_field="nom_centre"),
        ColumnSpec("Métier", "nom_filiere", required=True, kind="text"),
        ColumnSpec("Conditions d'accès", "niveau_diplome", required=False, kind="text"),
        ColumnSpec("Titre professionnel", "titre_professionnel", required=False,
                    kind="choice_static", choices=TITRE_PROFESSIONNEL_CHOICE),
        ColumnSpec("Durée (mois)", "duree_mois", required=True, kind="int"),
        ColumnSpec("Durée (jours) — si formation courte, remplace la colonne mois",
                    "duree_jours_override", required=False, kind="int",
                    help_text="À utiliser pour une formation courte (ex: 15 ou 45 jours) ; prime sur la colonne Durée (mois)."),
        ColumnSpec("Type de formation", "type_formation", required=False,
                    kind="choice_static", choices=TYPE_FORMATION_CHOICE,
                    help_text="Laisser vide = Initiale."),
        ColumnSpec("Frais de formation (FCFA)", "montant_frais", required=False, kind="int",
                    help_text="Laisser vide si aucun frais n'est encore fixé pour cette formation."),
        ColumnSpec("Année de formation", "annee_prog", required=False, kind="fk_pk",
                    fk_model=AnneeScolaire, fk_lookup_field="libelle_anne",
                    help_text="Laisser vide = année de formation la plus récemment créée."),
        ColumnSpec("Date limite d'inscription (JJ/MM/AAAA)", "date_limite_inscription",
                    required=False, kind="date"),
        ColumnSpec("Date de lancement (JJ/MM/AAAA)", "date_lancement", required=False, kind="date"),
        ColumnSpec("Actif (Oui/Non)", "is_active", required=False, kind="bool",
                    help_text="Laisser vide = Oui (formation immédiatement ouverte aux inscriptions)."),
    ],
    intro=(
        "Une ligne = une formation (couple centre + métier). Si le métier "
        "existe déjà en base, ses conditions d'accès/titre professionnel "
        "sont mis à jour avec les valeurs de cette ligne (le fichier "
        "fait autorité). La durée et la date de lancement appartiennent à "
        "la formation (pas au métier) — la date de fin est calculée "
        "automatiquement à partir de la date de lancement et de la durée. "
        "Une formation déjà existante pour ce couple centre+métier est "
        "rejetée avec une erreur plutôt que dupliquée. Par défaut la "
        "formation créée est active (visible et ouverte aux inscriptions) "
        "— mettre « Non » dans la colonne Actif pour la créer désactivée."
    ),
    url_namespace="bsb_admin",
    template_url_name="programming_import_template",
    upload_url_name="programming_import",
    list_url_name="programming_list",
)


# ── Membre de l'equipe (page publique « A propos ») ──────────────────────────
# Le modele telecharge est pre-rempli avec les membres deja enregistres : on
# corrige et on complete un existant plutot que de tout ressaisir, et le format
# attendu se lit sur de vraies donnees. La photo reste hors import, un fichier
# ne se transportant pas dans une cellule — elle se depose ecran par ecran.
def _membres_existants():
    return [
        {
            'full_name': m.full_name,
            'position': m.position,
            'description': m.description,
            'order': m.order,
            'is_active': m.is_active,
        }
        for m in Membre.objects.all().order_by('order', 'full_name')
    ]


def _membre_existant(resolved):
    """Le nom complet fait office de cle : une ligne portant un nom deja
    enregistre met la fiche a jour au lieu d'echouer sur l'unicite. C'est ce
    qui rend le modele pre-rempli exploitable — on le renvoie corrige."""
    nom = (resolved.get('full_name') or '').strip()
    return Membre.objects.filter(full_name__iexact=nom).first() if nom else None


SPEC_MEMBRE_EQUIPE = ImportSpec(
    slug="membre_equipe",
    verbose_name="Membre de l'équipe",
    model=Membre,
    mode="form",
    form_class=MembreEquipeImportForm,
    columns=[
        ColumnSpec("Nom complet", "full_name", required=True, kind="text",
                   help_text="Doit être unique : un nom déjà présent fait échouer la ligne."),
        ColumnSpec("Fonction", "position", required=True, kind="text",
                   help_text="Intitulé affiché sous le nom sur la page « À propos »."),
        ColumnSpec("Description", "description", required=True, kind="text",
                   help_text="Obligatoire : ce texte accompagne le membre sur la page publique."),
        ColumnSpec("Ordre d'affichage", "order", required=False, kind="int",
                   help_text="Nombre entier croissant. À valeur égale, le classement se fait par date de création."),
        ColumnSpec("Actif", "is_active", required=False, kind="bool",
                   help_text="oui / non. Un membre inactif reste enregistré mais disparaît de la page publique."),
    ],
    prefill_fn=_membres_existants,
    exemples=[
        {'full_name': 'SANOU Boureima', 'position': 'Secrétaire général',
         'description': "Coordonne les services centraux du ministère.",
         'order': 1, 'is_active': True},
        {'full_name': 'OUEDRAOGO Awa', 'position': 'Directrice des études',
         'description': "Supervise les programmes de formation.",
         'order': 2, 'is_active': True},
        {'full_name': 'KABORE Issa', 'position': 'Ancien directeur',
         'description': "Fiche conservée, retirée de la page publique.",
         'order': 3, 'is_active': False},
    ],
    instance_lookup_fn=_membre_existant,
    sheet_name="Membres",
    intro="Une ligne par membre de l'administration affiché sur la page publique « À propos ».",
    url_namespace="bsb_admin",
    template_url_name="membre_import_template",
    upload_url_name="membre_import",
    list_url_name="equipe_list",
)
