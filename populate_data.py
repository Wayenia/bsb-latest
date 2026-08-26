"""
=============================================================================
Script de population de la base de données BSB (Burkina Suudu Bawdè)
=============================================================================
Utilisation :
    python manage.py shell < populate_data.py

    OU via Django shell :
    exec(open('populate_data.py').read())

Ce script crée :
    1. Un compte administrateur (superuser)
    2. Les 17 régions et 47 provinces du Burkina Faso (découpage 2025)
    3. Les 3 Directions Inter-Régionales et les centres de formation
       professionnelle recensés (source : METIERS_YUPAAN_2025-2026)
    4. Les métiers de formation (filières) recensés, avec leur titre
       professionnel et leurs conditions d'accès
    5. Les 51 utilisateurs réels de la plateforme (source :
       HABILITATIONS EXPLOITATION_YUPAAN_V2.xlsx) : direction générale,
       directions inter-régionales, DAF, directeurs de centre, personnel
       du siège — voir ÉTAPE 6 pour le détail des anomalies du fichier
       source et la façon dont elles ont été résolues.

Volontairement absent de ce script :
    - Le lien centre ↔ métier (CentreEtFiliere) : il se fait à l'écran
      "Programmation", pas au peuplement initial.
    - La durée de formation par métier : elle est fixée lors de la
      programmation (elle dépend du centre, pas du métier en soi).
    - Les frais de formation : idem, liés à la programmation.
    - Toute donnée de démonstration (élèves, formateurs, inscriptions,
      paiements fictifs) : ce script ne prépare que les données réelles
      nécessaires au démarrage de la plateforme.

Prérequis :
    - Migrations appliquées : python manage.py migrate
    - AUTH_USER_MODEL = 'accounts.Utilisateur' (config/settings.py)

Mise à jour (communiqué de recrutement FI 2026-2027) :
    - Région "YAAGDA" renommée en "YAADGA" (orthographe officielle,
      chef-lieu Ouahigouya) — impacte REGIONS_DATA, PROVINCES_DATA et
      DIRECTIONS_DATA (Direction Inter-Régionale N°3).
    - Direction Inter-Régionale N°3 : chef-lieu corrigé en "Ouahigouya"
      (au lieu de "Ziniaré").
    - 2 nouveaux centres (Bagré, Ouargaye) et 10 nouveaux métiers ajoutés.
    - ATTENTION : ce script utilise get_or_create() par nom exact. Si une
      base de données a déjà été peuplée AVANT cette mise à jour, les
      renommages ci-dessus (région YAAGDA, chef-lieu de la Direction N°3)
      ne modifient PAS les lignes déjà existantes — un nouveau lancement
      créera des lignes supplémentaires au lieu de corriger les anciennes.
      Il faudra corriger/supprimer manuellement les anciennes entrées
      ("YAAGDA", chef-lieu "Ziniaré" pour la Direction N°3) via l'admin.
=============================================================================
"""

from django.contrib.auth.hashers import make_password
from datetime import date

from accounts.models import (
    Utilisateur, MembreAdministration, DirecteurInterRegional, DAF,
)
from courses.models import Region, Province, Direction_reg, Filiere, CentreFormation

print("=" * 80)
print("   POPULATION DE LA BASE DE DONNÉES — BURKINA SUUDU BAWDÈ (BSB)")
print("=" * 80)


def log(label, created, identifier=""):
    status = "✓ Créé  " if created else "→ Existe"
    print(f"   {status} | {label}: {identifier}")


# == ÉTAPE 1 — COMPTE ADMINISTRATEUR ===========================================
print("\n[1/6] Création du compte administrateur...")

admin_obj, admin_created = Utilisateur.objects.get_or_create(
    username="admin",
    defaults={
        "nom": "ADMINISTRATEUR",
        "prenom": "Système",
        "email": "admin@bsb.bf",
        "tel": "+226 70 00 00 00",
        "adresse": "Ouagadougou",
        "sexe": "m",
        "date_naissance": date(1990, 1, 1),
        "user_type": "admin",
        "password": make_password("Admin@2024"),
        "is_staff": True,
        "is_superuser": True,
        "is_active": True,
    }
)
log("Admin", admin_created, admin_obj.username)


# == ÉTAPE 2 — RÉGIONS ET PROVINCES (découpage 2025 — 17 régions / 47 provinces) ===
print("\n[2/6] Création des régions et provinces...")

# (code région tel qu'utilisé dans le fichier des métiers, chef-lieu de région)
REGIONS_DATA = [
    ("SOUROU",      "Tougan"),
    ("BANKUI",      "Dédougou"),
    ("GUIRIKO",     "Bobo-Dioulasso"),
    ("TANNOUNYAN",  "Banfora"),
    ("DJORO",       "Gaoua"),
    ("YAADGA",      "Ouahigouya"),
    ("NANDO",       "Koudougou"),
    ("SOUM",        "Djibo"),
    ("KUILSE",      "Kaya"),
    ("OUBRI",       "Ziniaré"),
    ("KADIOGO",     "Ouagadougou"),
    ("NAZINON",     "Manga"),
    ("NAKAMBE",     "Tenkodogo"),
    ("LIPTAKO",     "Dori"),
    ("GOULMOU",     "Fada N'Gourma"),
    ("TAPOA",       "Diapaga"),
    ("SIRBA",       "Bogandé"),
]

# (nom de la province, code région, chef-lieu de province)
PROVINCES_DATA = [
    ("Kossi", "SOUROU", "Nouna"),
    ("Nayala", "SOUROU", "Toma"),
    ("Sourou", "SOUROU", "Tougan"),
    ("Mouhoun", "BANKUI", "Dédougou"),
    ("Balé", "BANKUI", "Boromo"),
    ("Bamwa", "BANKUI", "Solenzo"),
    ("Houet", "GUIRIKO", "Bobo-Dioulasso"),
    ("Kénédougou", "GUIRIKO", "Orodara"),
    ("Tuy", "GUIRIKO", "Houndé"),
    ("Comoé", "TANNOUNYAN", "Banfora"),
    ("Léraba", "TANNOUNYAN", "Sindou"),
    ("Bougouriba", "DJORO", "Diébougou"),
    ("Ioba", "DJORO", "Dano"),
    ("Noumbiel", "DJORO", "Batié"),
    ("Poni", "DJORO", "Gaoua"),
    ("Loroum", "YAADGA", "Titao"),
    ("Passoré", "YAADGA", "Yako"),
    ("Yatenga", "YAADGA", "Ouahigouya"),
    ("Zondoma", "YAADGA", "Gourcy"),
    ("Boulkiemdé", "NANDO", "Koudougou"),
    ("Sanguié", "NANDO", "Réo"),
    ("Sissili", "NANDO", "Léo"),
    ("Ziro", "NANDO", "Sapouy"),
    ("Djelgodji", "SOUM", "Djibo"),
    ("Karo-Peli", "SOUM", "Arbinda"),
    ("Bam", "KUILSE", "Kongoussi"),
    ("Namentenga", "KUILSE", "Boulsa"),
    ("Sandbondtenga", "KUILSE", "Kaya"),
    ("Bassitenga", "OUBRI", "Ziniaré"),
    ("Ganzourgou", "OUBRI", "Zorgho"),
    ("Kourwéogo", "OUBRI", "Boussé"),
    ("Kadiogo", "KADIOGO", "Ouagadougou"),
    ("Bazèga", "NAZINON", "Kombissiri"),
    ("Nahouri", "NAZINON", "Pô"),
    ("Zoundwéogo", "NAZINON", "Manga"),
    ("Boulgou", "NAKAMBE", "Tenkodogo"),
    ("Koulpelogo", "NAKAMBE", "Ouargaye"),
    ("Kourittenga", "NAKAMBE", "Koupèla"),
    ("Oudalan", "LIPTAKO", "Gorm-Gorom"),
    ("Séno", "LIPTAKO", "Dori"),
    ("Yagha", "LIPTAKO", "Sebba"),
    ("Gourma", "GOULMOU", "Fada N'Gourma"),
    ("Kompienga", "GOULMOU", "Pama"),
    ("Dyamongou", "TAPOA", "Kantchari"),
    ("Gobnangou", "TAPOA", "Diapaga"),
    ("Gnagna", "SIRBA", "Bogandé"),
    ("Komondjari", "SIRBA", "Gayéri"),
]

regions = {}
for code, chef_lieu in REGIONS_DATA:
    obj, created = Region.objects.get_or_create(
        nom_region=code,
        defaults={"chef_lieu": chef_lieu}
    )
    regions[code] = obj
    log("Région", created, code)

provinces = {}
province_count = 0
for nom_province, region_code, chef_lieu in PROVINCES_DATA:
    obj, created = Province.objects.get_or_create(
        nom_province=nom_province,
        defaults={"region": regions[region_code], "chef_lieu": chef_lieu}
    )
    provinces[nom_province] = obj
    if created:
        province_count += 1
print(f"   ✓ {len(regions)} régions | {province_count} nouvelles provinces (total {Province.objects.count()})")


# == ÉTAPE 3 — DIRECTIONS INTER-RÉGIONALES =====================================
print("\n[3/6] Création des directions inter-régionales...")

# chef_lieu : ville de la region chef-lieu, telle que communiquee par le MESFPT.
DIRECTIONS_DATA = [
    ("Direction Inter-Régionale N°1", "Kadiogo, Nakambé, Nazinon, Goulmou, Nando", "Ouagadougou"),
    ("Direction Inter-Régionale N°2", "Guiriko, Bankui, Djoro, Tannounyan, Sourou", "Bobo-Dioulasso"),
    ("Direction Inter-Régionale N°3", "Oubri, Yaadga, Kuilse, Liptako", "Ouahigouya"),
]

directions = {}
for nom, region_label, chef_lieu in DIRECTIONS_DATA:
    obj, created = Direction_reg.objects.get_or_create(
        nom_direction=nom,
        defaults={"region": region_label, "chef_lieu": chef_lieu}
    )
    directions[nom] = obj
    log("Direction", created, nom)


# == ÉTAPE 4 — CENTRES DE FORMATION PROFESSIONNELLE ============================
print("\n[4/6] Création des centres de formation...")

# (nom, direction, province). Niveau, adresse et ville sont absents du fichier
# source : a completer via l'ecran d'administration des centres.
CENTRES_DATA = [
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Direction Inter-Régionale N°1", "Kadiogo"),
    ("Centre de formation professionnelle de Cissin (Ouagadougou)", "Direction Inter-Régionale N°1", "Kadiogo"),
    ("Centre Provincial de Formation Professionnelle de Koupéla", "Direction Inter-Régionale N°1", "Kourittenga"),
    ("Centre Provincial de Formation Professionnelle de Pô", "Direction Inter-Régionale N°1", "Nahouri"),
    ("Centre Provincial de Formation Professionnelle de Saponé", "Direction Inter-Régionale N°1", "Bazèga"),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Direction Inter-Régionale N°1", "Gourma"),
    ("Centre Régional de Formation Professionnelle de Koudougou", "Direction Inter-Régionale N°1", "Boulkiemdé"),
    ("Centre Régional de Formation Professionnelle de Manga", "Direction Inter-Régionale N°1", "Zoundwéogo"),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Direction Inter-Régionale N°1", "Kadiogo"),
    ("Centre Régional de Formation Professionnelle de Tenkodogo", "Direction Inter-Régionale N°1", "Boulgou"),
    ("Centre Provincial de Formation Professionnelle de Bagré", "Direction Inter-Régionale N°1", "Boulgou"),
    ("Centre Provincial de Formation Professionnelle de Ouargaye", "Direction Inter-Régionale N°1", "Koulpelogo"),

    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Direction Inter-Régionale N°2", "Houet"),
    ("Centre Provincial de Formation Professionnelle de Boromo", "Direction Inter-Régionale N°2", "Balé"),
    ("Centre Provincial de Formation Professionnelle de Dano", "Direction Inter-Régionale N°2", "Ioba"),
    ("Centre Provincial de Formation Professionnelle de Diébougou", "Direction Inter-Régionale N°2", "Bougouriba"),
    ("Centre Provincial de Formation Professionnelle de Sindou", "Direction Inter-Régionale N°2", "Léraba"),
    ("Centre Provincial de Formation Professionnelle de Toma", "Direction Inter-Régionale N°2", "Nayala"),
    ("Centre Provincial de Formation Professionnelle de Tougan", "Direction Inter-Régionale N°2", "Sourou"),
    ("Centre Régional de Formation Professionnelle de Banfora", "Direction Inter-Régionale N°2", "Comoé"),
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Direction Inter-Régionale N°2", "Houet"),
    ("Centre Régional de Formation Professionnelle de Dédougou", "Direction Inter-Régionale N°2", "Mouhoun"),
    ("Centre Régional de Formation Professionnelle de Gaoua", "Direction Inter-Régionale N°2", "Poni"),

    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Direction Inter-Régionale N°3", "Ganzourgou"),
    ("Centre Provincial de Formation Professionnelle de Gourcy", "Direction Inter-Régionale N°3", "Zondoma"),
    ("Centre Régional de Formation Professionnelle de Dori", "Direction Inter-Régionale N°3", "Séno"),
    ("Centre Régional de Formation Professionnelle de Kaya", "Direction Inter-Régionale N°3", "Sandbondtenga"),
    ("Centre Régional de Formation Professionnelle de Ouahigouya", "Direction Inter-Régionale N°3", "Yatenga"),
    ("Centre Régional de Formation Professionnelle de Ziniaré", "Direction Inter-Régionale N°3", "Ganzourgou"),
]

centres = {}
centre_count = 0
for nom_centre, direction_nom, province_nom in CENTRES_DATA:
    obj, created = CentreFormation.objects.get_or_create(
        nom_centre=nom_centre,
        defaults={
            "direction": directions[direction_nom],
            "province": provinces[province_nom],
        }
    )
    # IMPORTANT : conserver chaque centre dans le dictionnaire
    centres[nom_centre] = obj
    
    if created:
        centre_count += 1
print(f"   ✓ {centre_count} nouveaux centres (total {CentreFormation.objects.count()})")


# == ÉTAPE 5 — MÉTIERS DE FORMATION (FILIÈRES) =================================
print("\n[5/6] Création des métiers de formation...")

# (nom, titre professionnel, conditions d'acces). La duree depend du centre et
# se fixe a la programmation.
METIERS_DATA = [
    ("Plombier polyvalent", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Maintenancier des équipements et systèmes informatiques", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Maintenancier automobile", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Electronicien automobile", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Styliste-modéliste", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Maintenancier des équipements d'impression et de reprographie", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Electricien du bâtiment", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Monteur /dépanneur en climatisation individuelle", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Couturier homme", "CQP", "Niveau CM2 au moins"),
    ("Menuisier bois", "CQP", "Niveau CM2 au moins"),
    ("Tailleur", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Constructeur métallique", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Maçon polyvalent", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Aide-électricien", "CQP", "Niveau CM2 au moins"),
    ("Mécanicien automobile", "CQP", "Niveau CM2 au moins"),
    ("Plombier", "CQP", "Niveau CM2 au moins"),
    ("Mécanicien des machines agricoles", "CQP", "Niveau CM2 au moins"),
    ("Menuisier Métallique", "CQP", "Niveau CM2 au moins"),
    ("Couturier dame", "CQP", "Niveau CM2 au moins"),
    ("Maçon", "CQP", "Niveau CM2 au moins"),
    ("Mécanicien de vélomoteurs et Motocycles", "CQP", "Niveau CM2 au moins"),
    ("Coiffeur dame", "CQP", "Niveau CM2 au moins"),
    ("Installateur de système solaire photovoltaïque", "BPT", "Niveau de la classe de 1ère, ou être titulaire du BQP ou du BEP dans la filière ou le corps de métier + 3 ans d'expérience professionnelle prouvé (attestation, certificat de travail)"),
    ("Monteur/dépanneur en climatisation centralisée", "BPT", "Niveau de la classe de 1ère, ou être titulaire du BQP ou du BEP dans la filière ou le corps de métier + 3 ans d'expérience professionnelle prouvé (attestation, certificat de travail)"),
    ("Opérateur de machines-outils", "BPT", "Niveau de la classe de 1ère, ou être titulaire du BQP ou du BEP dans la filière ou le corps de métier + 3 ans d'expérience professionnelle prouvé (attestation, certificat de travail)"),
    ("Technicien de ligne télécom", "BPT", "Niveau de la classe de 1ère, ou être titulaire du BQP ou du BEP dans la filière ou le corps de métier + 3 ans d'expérience professionnelle prouvé (attestation, certificat de travail)"),
    ("Développeur d’applications web", "BPT", "Niveau de la classe de 1ère, ou être titulaire du BQP ou du BEP dans la filière ou le corps de métier + 3 ans d'expérience professionnelle prouvé (attestation, certificat de travail)"),
    ("Technicien en maintenance et réseau informatique", "BPT", "Niveau de la classe de 1ère, BEP ou être titulaire du BQP dans la filière ou le corps de métier + 3 ans d'expérience professionnelle prouvé (attestation, certificat de travail)"),
    ("Electromécanicien", "BPT", "Niveau de la classe de 1ère, BEP ou être titulaire du BQP dans la filière ou le corps de métier + 3 ans d'expérience professionnelle prouvé (attestation, certificat de travail)"),
    ("Dessinateur industriel", "BPTS", "Être titulaire d'un Baccalauréat technologique ou du BPT dans la filière ou le corps de métiers + 3 ans d'expérience prouvée."),
    ("Administrateur de réseaux informatiques", "BPTS", "Être titulaire d'un Baccalauréat technologique ou du BPT dans la filière ou le corps de métiers + 3 ans d'expérience prouvée."),
    ("Mécatronicien", "BPTS", "Être titulaire d'un Baccalauréat technologique ou du BPT dans la filière ou le corps de métiers + 3 ans d'expérience prouvée."),
    ("Domoticien", "BPTS", "Niveau terminale au moins ou avoir le BPT d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Mécanicien d’usine", "BPTS", "Être titulaire d'un Baccalauréat technologique ou du BPT dans la filière ou le corps de métiers + 3 ans d'expérience prouvée."),
    ("Maintenancier des équipements industriels de production et de surveillance", "BPTS", "Être titulaire d'un Baccalauréat technologique ou du BPT dans la filière ou le corps de métiers + 3 ans d'expérience prouvée."),
    ("Spécialiste réseaux télécoms", "BPTS", "Être titulaire d'un Baccalauréat technologique ou du BPT dans la filière ou le corps de métiers + 3 ans d'expérience prouvée."),
    ("Câbleur industriel", "BQP", "Niveau 3ème au moins, CQP ou être titulaire du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Menuisier aluminium", "CQP", "Niveau CM2 au moins"),
    ("Menuisier agenceur", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Tourneur/fraiseur", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Electronicien des installations domestique et tertiaire", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Boulanger", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Chef de chantier", "BPT", "Niveau de la classe de 1ère, ou être titulaire du BQP ou du BEP dans la filière ou le corps de métier + 3 ans d'expérience professionnelle prouvé (attestation, certificat de travail)"),
    ("Métreur-vérificateur", "BPT", "Niveau de la classe de 1ère, ou être titulaire du BQP ou du BEP dans la filière ou le corps de métier + 3 ans d'expérience professionnelle prouvé (attestation, certificat de travail)"),
    ("Technicien de maintenance automobile", "BPT", "Niveau de la classe de 1ère, ou être titulaire du BQP ou du BEP dans la filière ou le corps de métier + 3 ans d'expérience professionnelle prouvé (attestation, certificat de travail)"),
    ("Electronicien de maintenance", "BPT", "Niveau de la classe de 1ère, ou être titulaire du BQP ou du BEP dans la filière ou le corps de métier + 3 ans d'expérience professionnelle prouvé (attestation, certificat de travail)"),
    ("Pâtissier", "BPT", "Niveau de la classe de 1ère, ou être titulaire du BQP ou du BEP dans la filière ou le corps de métier + 3 ans d'expérience professionnelle prouvé (attestation, certificat de travail)"),

    # Ajoutes depuis le communique de recrutement FI 2026-2027.
    ("Esthéticien", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Sérigraphie sur textile", "CQP", "Niveau CM2 au moins"),
    ("Monteur /dépanneur en climatisation industrielle", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Maintenancier en froid domestique et commercial", "CQP", "Niveau CM2 au moins"),
    ("Câbleur des installations domestiques et industrielles", "BPT", "Niveau de la classe de 1ère, ou être titulaire du BQP ou du BEP dans la filière ou le corps de métier + 3 ans d'expérience professionnelle prouvé (attestation, certificat de travail)"),
    ("Décorateur/staffer", "CQP", "Niveau CM2 au moins"),
    ("Peintre bâtiment", "CQP", "Niveau CM2 au moins"),
    ("Installateur de systèmes électroniques", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Réparateur de climatisation automobile", "BQP", "Niveau 3ème au moins ou être titulaire du CQP ou du CAP d'un métier de la même filière + 3 ans d'expérience professionnelle"),
    ("Carreleur", "CQP", "Niveau CM2 au moins"),
]

metier_count = 0
for nom_filiere, titre_professionnel, conditions_acces in METIERS_DATA:
    obj, created = Filiere.objects.get_or_create(
        nom_filiere=nom_filiere,
        defaults={
            "titre_professionnel": titre_professionnel,
            "niveau_diplome": conditions_acces,
            "is_active": True,
        }
    )
    if created:
        metier_count += 1
print(f"   ✓ {metier_count} nouveaux métiers (total {Filiere.objects.count()})")


# == ÉTAPE 6 — UTILISATEURS DE LA PLATEFORME (HABILITATIONS EXPLOITATION YUPAAN) ===
print("\n[6/6] Création des utilisateurs de la plateforme...")

# Source : HABILITATIONS EXPLOITATION_YUPAAN_V2.xlsx, 51 comptes transcrits a la
# main. Le username (Prenom.NOM) tranche nom et prenom, le fichier melangeant les
# deux ordres. Anomalies du fichier source et regles retenues : README 9.
#
# `sexe` n'est fourni par aucune ligne du fichier source : valeur par defaut du
# modele pour tout le monde, a corriger par chaque titulaire via Mon profil.

# (nom, prénom, username, email, mot de passe par défaut)
DG_DATA = ("Pale", "Kèrabouro", "Kèrabouro.PALE", "keraple@gmail.com", "YupaanBSB@DG")

# (nom, prénom, username, email, mot de passe par défaut, direction)
DIR_DATA = [
    ("Millogo", "Evariste", "Evariste.MILLOGO", "millogoevariste@yahoo.fr", "YupaanBSB@DIR1", "Direction Inter-Régionale N°1"),
    ("Millogo", "Bakary", "Bakary.MILLOGO", "bakmillogos@gmail.com", "YupaanBSB@DIR2", "Direction Inter-Régionale N°2"),
    ("Sawadogo", "Hamidou", "Hamidou.SAWADOGO", "canpinka@gmail.com", "YupaanBSB@DIR3", "Direction Inter-Régionale N°3"),
]

# (nom, prénom, username, email, mot de passe par défaut)
DAF_DATA = ("Tiemtore", "Abdoul Aziz", "AbdoulAziz.TIEMTORE", "tientoreaziz100@gmail.com", "YupaanBSB@DAF")

# 29 directeurs de centre, en correspondance 1:1 avec les cles de CENTRES_DATA,
# etablie par l'acronyme du fichier source.
CENTRE_DIRECTEURS_DATA = [
    ("Batienon/Rouamba", "Jeanne Fleur", "JeanneFleure.ROUAMBA", "jeannebatienon@gmail.com", "YupaanBSB@DC1",
     "Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)"),
    ("Sori/Parkouda W.", "Yvonne Pélagie", "YvonnePélagie.PARKOUDA", "soriyvonne232@gmail.com", "YupaanBSB@DC2",
     "Centre de formation professionnelle de Cissin (Ouagadougou)"),
    ("Traore", "Nessan", "Nessan.TRAORE", "tnessan@yahoo.com", "YupaanBSB@DC3",
     "Centre Provincial de Formation Professionnelle de Diébougou"),
    ("Boundane", "Marius", "Marius.BOUNDANE", "mariusboundane24@gmail.com", "YupaanBSB@DC4",
     "Centre Régional de Formation Professionnelle de Dédougou"),
    ("Kabore W. Cesaire", "Cyriack", "Cyriack.KABORE", "cyriacking12@gmail.com", "YupaanBSB@DC5",
     "Centre Provincial de Formation Professionnelle de Boromo"),
    # Username avec un "Y" en double (COULIBALYY) : conservé tel quel — c'est
    # un identifiant de connexion, pas un nom à corriger.
    ("Coulibaly", "Blahima", "Blahima.COULIBALYY", "coulibalyblahima@yahoo.fr", "YupaanBSB@DC6",
     "Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)"),
    ("Diapa", "Gané", "Gané.DIAPA", "ganediapa4@gmail.com", "YupaanBSB@DC7",
     "Centre Régional de Formation Professionnelle de Bobo-Dioulasso"),
    ("Soudre", "Ismaël", "Ismaël.SOUDRE", "soudreismael13@gmail.com", "YupaanBSB@DC8",
     "Centre Régional de Formation Professionnelle de Manga"),
    ("Oboulbiga", "Donald", "Donald.OBOULBIGA", "yerdioboulbiga@gmail.com", "YupaanBSB@DC9",
     "Centre Régional de Formation Professionnelle de Kaya"),
    ("Konate", "Brahima", "Brahima.KONATE", "konatemecarurale@gmail.com", "YupaanBSB@DC10",
     "Centre Provincial de Formation Professionnelle de Koupéla"),
    ("Nignan", "Nikénédoua", "Nikénédoua.NIGNAN", "nignannsoum@gmail.com", "YupaanBSB@DC11",
     "Centre Provincial de Formation Professionnelle de Pô"),
    ("Traore", "Karim", "Karim.TRAORE", "sheylatraore@gmail.com", "YupaanBSB@DC12",
     "Centre Régional de Formation Professionnelle de Tenkodogo"),
    ("Ouedraogo", "Abdoulaye", "Abdoulaye.OUEDRAOGO", "yandabry@gmail.com", "YupaanBSB@DC13",
     "Centre Régional de Formation Professionnelle de Ouagadougou"),
    ("Konkobo", "Frédéric", "Frédéric.KONKOBO", "konkobofrederic8@gmail.com", "YupaanBSB@DC14",
     "Centre Régional de Formation Professionnelle de Ziniaré"),
    ("Bayala", "Richard", "Richard.BAYALA", "bayalabaptiste@gmail.com", "YupaanBSB@DC15",
     "Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)"),
    ("Bembamba", "Cédric P. Rodolphe", "Cedric.BEMBAMBA", "bembamce@gmail.com", "YupaanBSB@DC16",
     "Centre Provincial de Formation Professionnelle de Tougan"),
    ("Longo", "Kader Siméon", "SimeonKader.LONGO", "simeonleader882@gmail.com", "YupaanBSB@DC17",
     "Centre Provincial de Formation Professionnelle de Gourcy"),
    ("Sanogo", "Moussa", "Moussa.SANOGO", "mosessanogo18@gmail.com", "YupaanBSB@DC18",
     "Centre Provincial de Formation Professionnelle de Sindou"),
    ("Sanou", "Toukolo", "Toukolo.SANOU", "touksanou@gmail.com", "YupaanBSB@DC19",
     "Centre Régional de Formation Professionnelle de Ouahigouya"),
    ("Sombie", "Oumar", "Oumar.SOMBIE", "oum256@yahoo.fr", "YupaanBSB@DC20",
     "Centre Provincial de Formation Professionnelle de Dano"),
    ("Sana", "Boureima", "Boureima.SANA", "boureimasana89@gmail.com", "YupaanBSB@DC21",
     "Centre Régional de Formation Professionnelle de Dori"),
    ("Bouda", "Jonas", "Jonas.BOUDA", "boudajoe@yahoo.fr", "YupaanBSB@DC22",
     "Centre Provincial de Formation Professionnelle de Saponé"),
    ("Thiombiano", "Amitandi Jacques", "Jacques.THIOMBIANO", "jthiombiano@gmail.com", "YupaanBSB@DC23",
     "Centre Régional de Formation Professionnelle de Fada N'Gourma"),
    # Emails Ymien/Kere : voir note d'anomalies ci-dessus.
    ("Ymien", "Wassa", "Ymien.WASSA", "wassa.ymien@gmail.com", "YupaanBSB@DC24",
     "Centre Régional de Formation Professionnelle de Gaoua"),
    ("Kere", "Saidou", "Kere.SAIDOU", "kere.saidou@bsb.bf", "YupaanBSB@DC25",
     "Centre Régional de Formation Professionnelle de Banfora"),
    ("Ouedraogo", "Souleymane", "Souleymane.OUEDRAOGO", "salomo_seni@yahoo.fr", "YupaanBSB@DC26",
     "Centre Régional de Formation Professionnelle de Koudougou"),
    ("Bougoum", "Noaga", "Noaga.BOUGOUM", "bougoumnoaga@gmail.com", "YupaanBSB@DC27",
     "Centre Provincial de Formation Professionnelle de Bagré"),
    ("Tonde", "Gérard", "Gérard.TONDE", "gerard.tonde@yahoo.fr", "YupaanBSB@DC28",
     "Centre Provincial de Formation Professionnelle de Ouargaye"),
    ("Sanou", "Alfred", "Alfred.SANOU", "alfredsanou76@gmail.com", "YupaanBSB@DC29",
     "Centre Provincial de Formation Professionnelle de Toma"),
]

# (nom, prénom, username, email, mot de passe par défaut, clé dans `centres`)
CAISSIERS_CENTRE_DATA = [
    ("Sawadogo", "Sandrine", "Sandrine.SAWADOGO", "sandrinesasadogo@gmail.com", "YupaanBSB@CAISSE1",
     "Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)"),
]

# Personnel du siege, sans rattachement : le DESP prend le role deps, le reste
# la voie generique membre.
MEMBRES_SIEGE_DATA = [
    ("Bako/Zaghre", "Edwige", "Edwige.ZAGHRE", "zghred@gmail.com", "YupaanBSB@SG",
     "Secrétaire Générale (SG)", "membre"),
    ("Ba", "Boubakar", "Boubakar.BA", "bboubakarba@gmail.com", "YupaanBSB@DCIFP",
     "Directeur du Centre d'Ingénierie et de Formation des Personnels (DCIFP)", "membre"),
    ("Balma S.", "Basile", "Basile.BALMA", "sbasilebalma@gmail.com", "YupaanBSB@DESP",
     "Direction des Études, de la Planification et des Statistiques", "deps"),
    ("Ouedraogo", "Pierre", "Pierre.OUEDRAOGO", "ouedpier@gmail.com", "YupaanBSB@DIOP",
     "Directeur de l'Information et de l'Orientation Professionnelle (DIOP)", "membre"),
    ("Kabre", "Boukaré", "Boukaré.KABRE", "boukarek220@gmail.com", "YupaanBSB@DRH",
     "Directeur des Ressources Humaines (DRH)", "membre"),
    ("Zongo", "Idrissa", "Idrissa.ZONGO", "dris20zongo@yahoo.com", "YupaanBSB@PCRP",
     "Personne Responsable de la Commande Publique (PRCP)", "membre"),
    ("Dera", "Issouf", "Issouf.DERA", "issoudera@gmail.com", "YupaanBSB@CI",
     "Contrôleur Interne (CI)", "membre"),
    ("Oubda", "Issaka", "Issaka.OUBDA", "oubdaissaka33@gmail.com", "YupaanBSB@TP",
     "Trésorier Principal", "membre"),
    ("Doundoulougou", "Evariste", "Evariste.DOUNDOULOUGOU", "dondoulgoucevariste@gmail.com", "YupaanBSB@DCMEF",
     "Directeur du Contrôle des Marchés et des Engagements Financiers (DCMEF)", "membre"),
    ("Zongo", "Arsène", "Arsène.ZONGO", "zongoarse@gmail.com", "YupaanBSB@CE1",
     "Chargé d'Études (CE)", "membre"),
    # Username avec un "/" (KIMA/HOUNSINOU) : conservé tel quel, comme dans
    # le fichier source — identifiant de connexion, pas un champ affiché.
    ("Kima/Hounsinou", "Denise", "Denise.KIMA/HOUNSINOU", "denisehounsinou1@gmail.com", "YupaanBSB@SECOOP",
     "Chef de Service de la Coopération (SECOOP)", "membre"),
    ("Kafando", "Wendkouni", "Wendkouni.KAFANDO", "kafwends30@gmail.com", "YupaanBSB@SCRP",
     "Chef de service de la Communication et des Relations Publiques (SCRP)", "membre"),
    ("Soulama S.", "Irène", "Irène.SOULAMA", "souiresa@yahoo.fr", "YupaanBSB@CE2",
     "Chargée d'Études (CE)", "membre"),
    ("Kalmogo Koudaogo", "Alexis", "Alexis.KALMOGO", "kalmogokalexis@gmail.com", "YupaanBSB@SDA",
     "Chef de Service de la Documentation et des Archives (SDA)", "membre"),
    ("Kabore", "Marcel", "Marcel.KABORE", "machelo957@gmail.com", "YupaanBSB@RA1",
     "Régisseur/Caissier", "membre"),
    ("Ouedraogo", "Salam", "Salam.OUEDRAOGO", "salam.ouedraogo@bsb.bf", "YupaanBSB@DICAPPSTT",
     "DCAPPS-TT", "membre"),
]

# --- DG : aucun sous-modèle requis (rôle seul, cf. AgentForm.save()) -------
nom, prenom, username, email, mdp = DG_DATA
obj, created = Utilisateur.objects.get_or_create(
    username=username,
    defaults={
        "nom": nom.upper(), "prenom": prenom, "email": email, "sexe": "m",
        "user_type": "dg", "password": make_password(mdp), "is_active": True,
    }
)
log("Directeur Général", created, username)

# --- Directeurs Inter-Régionaux --------------------------------------------
for nom, prenom, username, email, mdp, direction_nom in DIR_DATA:
    obj, created = DirecteurInterRegional.objects.get_or_create(
        username=username,
        defaults={
            "nom": nom.upper(), "prenom": prenom, "email": email, "sexe": "m",
            "password": make_password(mdp), "is_active": True,
            "direction": directions[direction_nom],
        }
    )
    log("Directeur Inter-Régional", created, username)

# --- DAF ---------------------------------------------------------------
nom, prenom, username, email, mdp = DAF_DATA
obj, created = DAF.objects.get_or_create(
    username=username,
    defaults={
        "nom": nom.upper(), "prenom": prenom, "email": email, "sexe": "m",
        "password": make_password(mdp), "is_active": True,
    }
)
log("DAF", created, username)

# --- Directeurs de Centre ------------------------------------------------
for nom, prenom, username, email, mdp, centre_nom in CENTRE_DIRECTEURS_DATA:
    obj, created = MembreAdministration.objects.get_or_create(
        username=username,
        defaults={
            "nom": nom.upper(), "prenom": prenom, "email": email, "sexe": "m",
            "password": make_password(mdp), "is_active": True,
            "user_type": "gestionnaire",
            "structure": centres[centre_nom], "direction": None,
            "emploi": "Directeur de centre", "categorie": "Directeur de centre",
        }
    )
    log("Directeur de Centre", created, username)

# --- Caissiers de centre ---------------------------------------------------
for nom, prenom, username, email, mdp, centre_nom in CAISSIERS_CENTRE_DATA:
    obj, created = MembreAdministration.objects.get_or_create(
        username=username,
        defaults={
            "nom": nom.upper(), "prenom": prenom, "email": email, "sexe": "m",
            "password": make_password(mdp), "is_active": True,
            "user_type": "caissier",
            "structure": centres[centre_nom], "direction": None,
            "emploi": "Caissière/Caissier", "categorie": "Caissière/Caissier",
        }
    )
    log("Caissier(ère) de centre", created, username)

# --- Personnel du siège (DEPS + fonctions libres 'membre') -----------------
for nom, prenom, username, email, mdp, emploi, user_type in MEMBRES_SIEGE_DATA:
    obj, created = MembreAdministration.objects.get_or_create(
        username=username,
        defaults={
            "nom": nom.upper(), "prenom": prenom, "email": email, "sexe": "m",
            "password": make_password(mdp), "is_active": True,
            "user_type": user_type,
            "structure": None, "direction": None,
            "emploi": emploi, "categorie": emploi,
        }
    )
    log("Membre de l'administration", created, username)

utilisateurs_plateforme_count = (
    1 + len(DIR_DATA) + 1 + len(CENTRE_DIRECTEURS_DATA)
    + len(CAISSIERS_CENTRE_DATA) + len(MEMBRES_SIEGE_DATA)
)
print(f"   ✓ {utilisateurs_plateforme_count} utilisateurs de la plateforme traités "
      f"(total {Utilisateur.objects.count()} comptes)")


# == RÉSUMÉ FINAL ==============================================================
print("\n" + "=" * 80)
print("   RÉSUMÉ DE LA POPULATION")
print("=" * 80)

summary = [
    ("Régions",                       Region.objects.count()),
    ("Provinces",                     Province.objects.count()),
    ("Directions inter-régionales",   Direction_reg.objects.count()),
    ("Centres de formation",          CentreFormation.objects.count()),
    ("Métiers de formation",          Filiere.objects.count()),
    ("Utilisateurs (tous rôles)",     Utilisateur.objects.count()),
]

for label, count in summary:
    bar = "█" * min(count, 40)
    print(f"   {label:<38} {count:>4}  {bar}")

print("=" * 80)
print("✅  POPULATION TERMINÉE AVEC SUCCÈS !")
print("=" * 80)
print()
print("   Compte administrateur :")
print("   ┌─────────────────────────┬─────────────────────┬──────────────────┐")
print("   │ Rôle                    │ username            │ password         │")
print("   ├─────────────────────────┼─────────────────────┼──────────────────┤")
print("   │ Super Admin             │ admin               │ Admin@2024       │")
print("   └─────────────────────────┴─────────────────────┴──────────────────┘")
print("=" * 80)
