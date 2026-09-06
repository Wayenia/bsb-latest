"""
=============================================================================
Script de population de la base de données BSB (Burkina Suudu Bawdè)
=============================================================================
Utilisation (méthode recommandée) :
    python manage.py shell -c "exec(open('populate_data.py', encoding='utf-8').read())"

    (« python manage.py shell < populate_data.py » ne fonctionne pas de façon
    fiable : le REPL de Python découpe mal les gros littéraux multi-lignes.)

Ce script crée :
    1. Un compte administrateur (superuser)
    2. Les 17 régions et 47 provinces du Burkina Faso (découpage 2025)
    3. Les 3 Directions Inter-Régionales et les centres de formation
       professionnelle recensés (source : METIERS_YUPAAN_2025-2026)
    4. Les métiers de formation (filières) recensés, avec leur titre
       professionnel et leurs conditions d'accès
    5. Les programmations 2026-2027 (CentreEtFiliere) :
       - formations de type « Formation » (source :
         exemple_formations_2026-2027 vérifié.xlsx, feuille « Import »),
         avec « Frais de dossier » (2 000) + « Frais de formation »
         (montant du fichier, tranches 75 % primordiale / 25 %) et
         3 pièces requises ;
       - packs de reconversion (PRDSU, source : PRDSU.2026_PACKS.docx) :
         métiers + modules, frais « Reconversion » (40 000), 1 pièce
         requise, durée 90 jours.
       Toutes ces programmations partagent l'année « 2026-2027 » et la
       date limite d'inscription du 10 octobre 2026.
    6. Les 51 utilisateurs réels de la plateforme (source :
       HABILITATIONS EXPLOITATION_YUPAAN_V2.xlsx) : direction générale,
       directions inter-régionales, DAF, directeurs de centre, personnel
       du siège — voir ÉTAPE 7 pour le détail des anomalies du fichier
       source et la façon dont elles ont été résolues.

Volontairement absent de ce script :
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
    - Périmètre des directions inter-régionales écrit avec le code exact des
      régions (majuscules), et les 2 centres de Ziniaré rattachés à la
      province "Bassitenga" (au lieu de "Ganzourgou").
    - Les étapes 3 (directions) et 4 (centres) CORRIGENT désormais une ligne
      déjà existante dont le périmètre / la province / le chef-lieu ne
      correspond plus (relancer le script suffit). Les autres étapes restent
      en get_or_create par nom exact : une région/un métier renommé crée une
      ligne en doublon plutôt que de corriger l'ancienne — à nettoyer via
      l'admin le cas échéant.
=============================================================================
"""

import os
from django.contrib.auth.hashers import make_password
from datetime import date

from accounts.models import (
    Utilisateur, MembreAdministration, DirecteurInterRegional, DAF,
)
from courses.models import Region, Province, Direction_reg, Filiere, CentreFormation

# POPULATE_COMPTES=0 -> peuple UNIQUEMENT la structure (régions, provinces,
# directions, centres, métiers), sans créer aucun compte (ni admin ni agents).
CREER_COMPTES = os.environ.get('POPULATE_COMPTES', '1') != '0'

print("=" * 80)
print("   POPULATION DE LA BASE DE DONNÉES — BURKINA SUUDU BAWDÈ (BSB)")
print("=" * 80)


def log(label, created, identifier=""):
    status = "✓ Créé  " if created else "→ Existe"
    print(f"   {status} | {label}: {identifier}")


# == ÉTAPE 1 — COMPTE ADMINISTRATEUR ===========================================
if CREER_COMPTES:
    print("\n[1/7] Création du compte administrateur...")
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
else:
    print("\n[1/7] Compte administrateur ignoré (POPULATE_COMPTES=0).")


# == ÉTAPE 2 — RÉGIONS ET PROVINCES (découpage 2025 — 17 régions / 47 provinces) ===
print("\n[2/7] Création des régions et provinces...")

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
print("\n[3/7] Création des directions inter-régionales...")

# (nom, régions couvertes, chef-lieu). Les régions sont écrites avec le code
# EXACT de REGIONS_DATA (majuscules) : `_direction_regions()` (courses/views.py)
# fait `Region.objects.filter(nom_region__in=direction.region.split(','))` — un
# libellé qui ne correspond pas au nom exact d'une région casse le périmètre du
# directeur inter-régional (statistiques, listes).
DIRECTIONS_DATA = [
    ("Direction Inter-Régionale N°1", "KADIOGO, NAKAMBE, NAZINON, GOULMOU, NANDO", "Ouagadougou"),
    ("Direction Inter-Régionale N°2", "GUIRIKO, BANKUI, DJORO, TANNOUNYAN, SOUROU", "Bobo-Dioulasso"),
    ("Direction Inter-Régionale N°3", "OUBRI, YAADGA, LIPTAKO, KUILSE", "Ouahigouya"),
]

directions = {}
for nom, region_label, chef_lieu in DIRECTIONS_DATA:
    obj, created = Direction_reg.objects.get_or_create(
        nom_direction=nom,
        defaults={"region": region_label, "chef_lieu": chef_lieu}
    )
    # Corrige une direction déjà présente avec un périmètre/chef-lieu erroné
    # (get_or_create n'applique `defaults` qu'à la création).
    maj = []
    if obj.region != region_label:
        obj.region = region_label
        maj.append("region")
    if obj.chef_lieu != chef_lieu:
        obj.chef_lieu = chef_lieu
        maj.append("chef_lieu")
    if maj:
        obj.save(update_fields=maj)
    directions[nom] = obj
    log("Direction", created, nom + ("" if created else f" (corrigé: {', '.join(maj)})" if maj else ""))


# == ÉTAPE 4 — CENTRES DE FORMATION PROFESSIONNELLE ============================
print("\n[4/7] Création des centres de formation...")

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

    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Direction Inter-Régionale N°3", "Bassitenga"),
    ("Centre Provincial de Formation Professionnelle de Gourcy", "Direction Inter-Régionale N°3", "Zondoma"),
    ("Centre Régional de Formation Professionnelle de Dori", "Direction Inter-Régionale N°3", "Séno"),
    ("Centre Régional de Formation Professionnelle de Kaya", "Direction Inter-Régionale N°3", "Sandbondtenga"),
    ("Centre Régional de Formation Professionnelle de Ouahigouya", "Direction Inter-Régionale N°3", "Yatenga"),
    ("Centre Régional de Formation Professionnelle de Ziniaré", "Direction Inter-Régionale N°3", "Bassitenga"),
]

centres = {}
centre_count = 0
centre_corrige = 0
for nom_centre, direction_nom, province_nom in CENTRES_DATA:
    obj, created = CentreFormation.objects.get_or_create(
        nom_centre=nom_centre,
        defaults={
            "direction": directions[direction_nom],
            "province": provinces[province_nom],
        }
    )
    # Corrige un centre déjà présent mal rattaché (ex. Ziniaré rattaché par
    # erreur à la province « Ganzourgou »/chef-lieu Zorgho au lieu de
    # « Bassitenga »/chef-lieu Ziniaré) — la province détermine la ville
    # affichée aux apprenants pour la Reconversion.
    maj = []
    if obj.direction_id != directions[direction_nom].id:
        obj.direction = directions[direction_nom]
        maj.append("direction")
    if obj.province_id != provinces[province_nom].id:
        obj.province = provinces[province_nom]
        maj.append("province")
    if maj:
        obj.save(update_fields=maj)
        centre_corrige += 1

    # IMPORTANT : conserver chaque centre dans le dictionnaire
    centres[nom_centre] = obj

    if created:
        centre_count += 1
print(f"   ✓ {centre_count} nouveaux centres, {centre_corrige} corrigés "
      f"(total {CentreFormation.objects.count()})")


# == ÉTAPE 5 — MÉTIERS DE FORMATION (FILIÈRES) =================================
print("\n[5/7] Création des métiers de formation...")

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




# == ÉTAPE 6 — PROGRAMMATIONS 2026-2027 (formations + packs de reconversion) =====
# Source : « exemple_formations_2026-2027 vérifié.xlsx » (feuille « Import ») pour
# les formations de type de programme « Formation », et « PRDSU.2026_PACKS.docx »
# pour les packs de reconversion (PRDSU). Les noms de centres de l'Excel sont
# ramenés aux noms officiels ci-dessus (retrait des sigles « (CPFP) »/« (CRFP) »).
print("\n[6/7] Programmations, frais et packs (campagne 2026-2027)...")

from datetime import datetime
from django.utils import timezone
from courses.models import (
    AnneeScolaire, CentreEtFiliere, Frais, TypeFrais, TrancheFrais,
    PieceJointeInscription, Module,
)

ANNEE_LIBELLE = "2026-2027"
DATE_LIMITE_2026 = timezone.make_aware(datetime(2026, 10, 10, 23, 59))

# Conditions d'accès communes à TOUTES les formations de type « Formation »
# (communiqué de recrutement FI 2026-2027) — elles remplacent les conditions
# par métier.
CONDITIONS_FORMATION = (
    "- avoir seize (16) ans au moins à la date du début effectif des cours ;\n"
    "- avoir vingt-deux (22) ans au plus pour les postulants à l'internat ;\n"
    "- être de bonne moralité ;\n"
    "- être apte à suivre la formation."
)
# Conditions d'accès des packs de reconversion (PRDSU).
CONDITIONS_PACK = (
    "- être titulaire d'un diplôme universitaire ou d'un BAC datant d'au moins 03 ans ;\n"
    "- s'acquitter d'une contribution de quarante mille (40 000) FCFA ;\n"
    "- être disponible durant la période de formation."
)
TEXTE_DEFILANT_PACK = "Programme de reconversion des diplômés du système universitaire (PRDSU)"

MONTANT_FRAIS_DOSSIER = 2000
MONTANT_PACK = 40000

# Documents requis (libellé, type de pièce) — voir PieceJointeInscription.TYPE_PIECE
DOCS_FORMATION = [
    ("Extrait d'acte de naissance", "type_4"),
    ("Photocopie du diplôme, titre de qualification ou attestation de niveau requis", "type_5"),
    ("Photo d'identité récente", "type_4"),
]
DOC_PACK = ("Diplôme universitaire ou BAC", "type_5")

FORMATIONS_2026_2027 = [
    # (centre, métier, titre professionnel, durée en mois, montant « Frais de formation »)

    # --- Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO) (13) ---
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Plombier polyvalent", "BQP", 9, 250000),
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Maintenancier des équipements et systèmes informatiques", "BQP", 9, 250000),
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Boulanger", "BQP", 9, 250000),
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Pâtissier", "BPT", 10, 350000),
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Esthéticien", "BQP", 9, 250000),
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Technicien de maintenance automobile", "BPT", 10, 350000),
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Sérigraphie sur textile", "CQP", 8, 100000),
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Maintenancier automobile", "BQP", 9, 250000),
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Electronicien automobile", "BPT", 9, 250000),
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Modéliste", "BQP", 9, 250000),
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Maintenancier des équipements d'impression et de reprographie", "BQP", 9, 250000),
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Electricien bâtiment", "BQP", 9, 250000),
    ("Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)", "Monteur /dépanneur en climatisation individuelle", "BQP", 9, 250000),

    # --- Centre de formation professionnelle de Cissin (Ouagadougou) (7) ---
    ("Centre de formation professionnelle de Cissin (Ouagadougou)", "Couturier homme", "CQP", 8, 100000),
    ("Centre de formation professionnelle de Cissin (Ouagadougou)", "Couturier dame", "CQP", 8, 60000),
    ("Centre de formation professionnelle de Cissin (Ouagadougou)", "Aide-électricien", "CQP", 8, 60000),
    ("Centre de formation professionnelle de Cissin (Ouagadougou)", "Menuisier métallique", "CQP", 8, 100000),
    ("Centre de formation professionnelle de Cissin (Ouagadougou)", "Menuisier bois", "CQP", 8, 100000),
    ("Centre de formation professionnelle de Cissin (Ouagadougou)", "Constructeur métallique", "BQP", 9, 275000),
    ("Centre de formation professionnelle de Cissin (Ouagadougou)", "Maçon polyvalent", "BQP", 9, 250000),

    # --- Centre Provincial de Formation Professionnelle de Koupéla (3) ---
    ("Centre Provincial de Formation Professionnelle de Koupéla", "Aide-électricien", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Koupéla", "Couturier dame", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Koupéla", "Réparateur de véhicules automobiles", "CQP", 8, 35000),

    # --- Centre Provincial de Formation Professionnelle de Pô (4) ---
    ("Centre Provincial de Formation Professionnelle de Pô", "Plombier", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Pô", "Réparateur de véhicules automobiles", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Pô", "Mécanicien des machines agricoles", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Pô", "Aide-électricien", "CQP", 8, 35000),

    # --- Centre Provincial de Formation Professionnelle de Saponé (3) ---
    ("Centre Provincial de Formation Professionnelle de Saponé", "Menuisier métallique", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Saponé", "Aide-électricien", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Saponé", "Couturier dame", "CQP", 8, 35000),

    # --- Centre Provincial de Formation Professionnelle de Bagré (1) ---
    ("Centre Provincial de Formation Professionnelle de Bagré", "Mécanicien des machines agricoles", "CQP", 8, 35000),

    # --- Centre Régional de Formation Professionnelle de Fada N'Gourma (14) ---
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Maçon", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Plombier", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Menuisier métallique", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Réparateur de véhicules automobiles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Mécanicien de vélomoteurs et motocycles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Maintenancier en froid domestique et commercial", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Couturier dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Aide-électricien", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Maintenancier des équipements et systèmes informatiques", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Electricien bâtiment", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Constructeur métallique", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Maçon polyvalent", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Plombier polyvalent", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Fada N'Gourma", "Maintenancier automobile", "BQP", 9, 115000),

    # --- Centre Régional de Formation Professionnelle de Koudougou (12) ---
    ("Centre Régional de Formation Professionnelle de Koudougou", "Plombier", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Koudougou", "Menuisier métallique", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Koudougou", "Aide-électricien", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Koudougou", "Electricien bâtiment", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Koudougou", "Maintenancier des équipements et systèmes informatiques", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Koudougou", "Plombier polyvalent", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Koudougou", "Technicien en réseaux et maintenance informatiques", "BPT", 10, 350000),
    ("Centre Régional de Formation Professionnelle de Koudougou", "Boulanger", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Koudougou", "Constructeur Métallique", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Koudougou", "Installateur de système solaire photovoltaïque", "BPT", 10, 350000),
    ("Centre Régional de Formation Professionnelle de Koudougou", "Câbleur industriel", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Koudougou", "Maintenancier des équipements d'impression et de reprographie", "BQP", 9, 115000),

    # --- Centre Régional de Formation Professionnelle de Manga (7) ---
    ("Centre Régional de Formation Professionnelle de Manga", "Menuisier métallique", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Manga", "Réparateur de véhicules automobiles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Manga", "Constructeur métallique", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Manga", "Mécanicien de vélomoteurs et motocycles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Manga", "Couturier dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Manga", "Electricien bâtiment", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Manga", "Aide-électricien", "CQP", 8, 60000),

    # --- Centre Régional de Formation Professionnelle de Ouagadougou (19) ---
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Plombier", "CQP", 8, 100000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Menuisier métallique", "CQP", 8, 100000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Décorateur-staffeur", "CQP", 8, 100000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Mécanicien de vélomoteurs et motocycles", "CQP", 8, 75000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Menuisier bois", "CQP", 8, 100000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Réparateur de véhicules automobiles", "CQP", 8, 100000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Couturier dame", "CQP", 8, 100000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Aide-électricien", "CQP", 8, 100000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Maçon", "CQP", 8, 75000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Peintre bâtiment", "CQP", 8, 100000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Maintenancier en froid domestique et commercial", "CQP", 8, 100000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Monteur /dépanneur en climatisation individuelle", "BQP", 9, 250000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Maintenancier des équipements et systèmes informatiques", "BQP", 9, 250000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Maintenancier automobile", "BQP", 9, 250000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Constructeur métallique", "BQP", 9, 275000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Maintenancier des équipements d'impression et de reprographie", "BQP", 9, 250000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Electricien bâtiment", "BQP", 9, 250000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Maçon polyvalent", "BQP", 9, 250000),
    ("Centre Régional de Formation Professionnelle de Ouagadougou", "Métreur-vérificateur", "BPT", 10, 350000),

    # --- Centre Régional de Formation Professionnelle de Tenkodogo (11) ---
    ("Centre Régional de Formation Professionnelle de Tenkodogo", "Maçon", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Tenkodogo", "Menuisier métallique", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Tenkodogo", "Réparateur de véhicules automobiles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Tenkodogo", "Couturier dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Tenkodogo", "Coiffeur dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Tenkodogo", "Mécanicien de vélomoteurs et motocycles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Tenkodogo", "Plombier", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Tenkodogo", "Aide-électricien", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Tenkodogo", "Maintenancier automobile", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Tenkodogo", "Modéliste", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Tenkodogo", "Electricien bâtiment", "BQP", 9, 115000),

    # --- Centre Provincial de Formation Professionnelle de Ouargaye (2) ---
    ("Centre Provincial de Formation Professionnelle de Ouargaye", "Maçon", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Ouargaye", "Tisserand", "CQP", 8, 35000),

    # --- Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B) (14) ---
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Installateur de système solaire photovoltaïque", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Monteur /dépanneur en climatisation centralisée", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Opérateur de machines-outils", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Technicien de ligne télécom", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Développeur d’applications web", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Technicien en réseaux et maintenance informatiques", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Electromécanicien", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Dessinateur industriel", "BPTS", 11, 400000),
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Administrateur de réseaux informatiques", "BPTS", 11, 400000),
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Mécatronicien", "BPTS", 11, 400000),
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Domoticien", "BPTS", 11, 400000),
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Mécanicien d’usine", "BPTS", 11, 400000),
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Maintenancier des équipements industriels de production et de surveillance", "BPTS", 11, 400000),
    ("Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)", "Spécialiste réseaux télécoms", "BPTS", 11, 400000),

    # --- Centre Provincial de Formation Professionnelle de Boromo (2) ---
    ("Centre Provincial de Formation Professionnelle de Boromo", "Réparateur de véhicules automobiles", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Boromo", "Couturier dame", "CQP", 8, 35000),

    # --- Centre Provincial de Formation Professionnelle de Dano (4) ---
    ("Centre Provincial de Formation Professionnelle de Dano", "Mécanicien de vélomoteurs et motocycles", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Dano", "Couturier dame", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Dano", "Aide-électricien", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Dano", "Menuisier métallique", "CQP", 8, 35000),

    # --- Centre Provincial de Formation Professionnelle de Diébougou (5) ---
    ("Centre Provincial de Formation Professionnelle de Diébougou", "Mécanicien de vélomoteurs et Motocycles", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Diébougou", "Couturier dame", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Diébougou", "Aide-électricien", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Diébougou", "Coiffeur dame", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Diébougou", "Tisserand", "CQP", 8, 35000),

    # --- Centre Provincial de Formation Professionnelle de Sindou (4) ---
    ("Centre Provincial de Formation Professionnelle de Sindou", "Menuisier métallique", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Sindou", "Couturier dame", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Sindou", "Aide-électricien", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Sindou", "Maçon", "CQP", 8, 35000),

    # --- Centre Provincial de Formation Professionnelle de Toma (2) ---
    ("Centre Provincial de Formation Professionnelle de Toma", "Mécanicien de vélomoteurs et motocycles", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Toma", "Aide-électricien", "CQP", 8, 35000),

    # --- Centre Provincial de Formation Professionnelle de Tougan (2) ---
    ("Centre Provincial de Formation Professionnelle de Tougan", "Menuisier bois", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Tougan", "Couturier dame", "CQP", 8, 35000),

    # --- Centre Régional de Formation Professionnelle de Banfora (8) ---
    ("Centre Régional de Formation Professionnelle de Banfora", "Menuisier bois", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Banfora", "Réparateur de véhicules automobiles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Banfora", "Mécanicien de vélomoteurs et motocycles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Banfora", "Couturier dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Banfora", "Aide-électricien", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Banfora", "Câbleur industriel", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Banfora", "Maintenancier automobile", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Banfora", "Modéliste", "BQP", 9, 115000),

    # --- Centre Régional de Formation Professionnelle de Bobo-Dioulasso (13) ---
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Plombier", "CQP", 8, 100000),
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Menuisier métallique", "CQP", 8, 100000),
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Menuisier bois", "CQP", 8, 100000),
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Réparateur de véhicules automobiles", "CQP", 8, 100000),
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Menuisier en aluminium", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Maçon", "CQP", 8, 75000),
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Mécanicien de vélomoteurs et Motocycles", "CQP", 8, 75000),
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Aide-électricien", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Couturier-dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Constructeur métallique", "BQP", 9, 250000),
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Plombier polyvalent", "BQP", 9, 250000),
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Maintenancier des véhicules automobiles", "BQP", 9, 250000),
    ("Centre Régional de Formation Professionnelle de Bobo-Dioulasso", "Electricien bâtiment", "BQP", 9, 250000),

    # --- Centre Régional de Formation Professionnelle de Dédougou (8) ---
    ("Centre Régional de Formation Professionnelle de Dédougou", "Maçon", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Dédougou", "Plombier", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Dédougou", "Menuisier métallique", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Dédougou", "Couturier dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Dédougou", "Aide-électricien", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Dédougou", "Réparateur de véhicules automobiles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Dédougou", "Maintenancier automobile", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Dédougou", "Constructeur métallique", "BQP", 9, 115000),

    # --- Centre Régional de Formation Professionnelle de Gaoua (8) ---
    ("Centre Régional de Formation Professionnelle de Gaoua", "Menuisier métallique", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Gaoua", "Menuisier en aluminium", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Gaoua", "Menuisier bois", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Gaoua", "Mécanicien de vélomoteurs et Motocycles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Gaoua", "Coiffeur dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Gaoua", "Couturier dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Gaoua", "Aide-électricien", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Gaoua", "Maintenancier des équipements et systèmes informatiques", "BQP", 9, 115000),

    # --- Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z) (26) ---
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Menuisier agenceur", "BQP", 9, 250000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Electricien bâtiment", "BQP", 9, 250000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Maintenancier automobile", "BQP", 9, 250000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Maçon polyvalent", "BQP", 9, 250000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Constructeur métallique", "BQP", 9, 250000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Tourneur/fraiseur", "BQP", 9, 250000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Maintenancier des équipements et systèmes informatiques", "BQP", 9, 250000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Electronicien d'installation", "BQP", 9, 250000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Câbleur industriel", "BQP", 9, 250000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Monteur /dépanneur des équipements de froid domestique, commercial et climatisation individuelle", "BQP", 9, 250000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Boulanger", "BQP", 9, 250000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Chef de chantier", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Réparateur de climatisation automobile", "BQP", 9, 250000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Décorateur-staffeur", "CQP", 8, 100000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Peintre bâtiment", "CQP", 8, 100000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Carreleur", "CQP", 8, 100000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Menuisier en aluminium", "CQP", 8, 100000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Métreur-vérificateur", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Technicien de maintenance automobile", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Opérateur de machines-outils", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Electromécanicien", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Installateur de système solaire photovoltaïque", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Electronicien de maintenance", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Monteur /dépanneur des équipements de froid industrielle et climatisation centralisée", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Technicien en réseaux et maintenance informatiques", "BPT", 10, 350000),
    ("Centre de Formation Professionnelle de Référence de Ziniaré (CFPR-Z)", "Pâtissier", "BPT", 10, 350000),

    # --- Centre Provincial de Formation Professionnelle de Gourcy (3) ---
    ("Centre Provincial de Formation Professionnelle de Gourcy", "Maçon", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Gourcy", "Couturier dame", "CQP", 8, 35000),
    ("Centre Provincial de Formation Professionnelle de Gourcy", "Mécanicien de vélomoteurs et motocycles", "CQP", 8, 35000),

    # --- Centre Régional de Formation Professionnelle de Dori (8) ---
    ("Centre Régional de Formation Professionnelle de Dori", "Maçon", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Dori", "Menuisier métallique", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Dori", "Coiffeur dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Dori", "Couturier dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Dori", "Aide-électricien", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Dori", "Menuisier bois", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Dori", "Mécanicien de vélomoteurs et motocycles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Dori", "Réparateur de véhicules automobiles", "CQP", 8, 60000),

    # --- Centre Régional de Formation Professionnelle de Kaya (9) ---
    ("Centre Régional de Formation Professionnelle de Kaya", "Menuisier métallique", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Kaya", "Menuisier bois", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Kaya", "Mécanicien de vélomoteurs et motocycles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Kaya", "Tailleur", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Kaya", "Coiffeur dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Kaya", "Couturier dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Kaya", "Mécanicien de véhicules automobile", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Kaya", "Aide-électricien", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Kaya", "Electricien bâtiment", "BQP", 9, 150000),

    # --- Centre Régional de Formation Professionnelle de Ouahigouya (9) ---
    ("Centre Régional de Formation Professionnelle de Ouahigouya", "Couturier dame", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Ouahigouya", "Maçon", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Ouahigouya", "Réparateur des véhicules automobiles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Ouahigouya", "Aide-électricien", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Ouahigouya", "Mécanicien de vélomoteurs et motocycles", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Ouahigouya", "Menuisier bois", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Ouahigouya", "Electricien bâtiment", "BQP", 9, 150000),
    ("Centre Régional de Formation Professionnelle de Ouahigouya", "Tailleur", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Ouahigouya", "Maintenancier des véhicules automobiles", "BQP", 9, 115000),

    # --- Centre Régional de Formation Professionnelle de Ziniaré (5) ---
    ("Centre Régional de Formation Professionnelle de Ziniaré", "Plombier", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Ziniaré", "Tailleur", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Ziniaré", "Electricien bâtiment", "BQP", 9, 115000),
    ("Centre Régional de Formation Professionnelle de Ziniaré", "Aide-électricien", "CQP", 8, 60000),
    ("Centre Régional de Formation Professionnelle de Ziniaré", "Couturier dame", "CQP", 8, 60000),
]
PACKS_2026_2027 = [
    # (nom du pack (métier), [modules], [centres où le pack est déployé])

    (
        "PACK 1 — Aviculteur polyvalent",
        [
            "Confection de couveuses manuelle et automatique",
            "Fabrication d'aliments pour volailles",
            "Élevage de volaille",
            "Rôtisserie",
            "Fumage",
            "Cuisine-Restauration",
            "Marketing digital",
            "Civisme Patriotisme-Entrepreneuriat",
        ],
        [
            "Centre Régional de Formation Professionnelle de Banfora",
            "Centre Régional de Formation Professionnelle de Dédougou",
            "Centre Régional de Formation Professionnelle de Fada N'Gourma",
            "Centre Régional de Formation Professionnelle de Kaya",
            "Centre Régional de Formation Professionnelle de Koudougou",
            "Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)",
            "Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)",
        ],
    ),

    (
        "PACK 2 — Pisciculteur polyvalent",
        [
            "Fabrication d'aliments pour poissons",
            "Pisciculture",
            "Fumage/séchage de poissons",
            "Restauration",
            "Maraîchage",
            "Marketing digital",
            "Civisme Patriotisme-Entrepreneuriat",
        ],
        [
            "Centre Régional de Formation Professionnelle de Tenkodogo",
            "Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)",
            "Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)",
        ],
    ),

    (
        "PACK 3 — Maintenancier des terminaux TIC et sécurité électronique",
        [
            "Réparation de téléphones portables (smartphones, tablettes)",
            "Technique d'installation, de réparation et d'entretien de système de vidéo surveillance",
            "Technique d'installation de système de visioconférence",
            "Technique d'installation de sonorisation",
            "Marketing digital",
            "Civisme Patriotisme-Entrepreneuriat",
        ],
        [
            "Centre Régional de Formation Professionnelle de Banfora",
            "Centre Régional de Formation Professionnelle de Dori",
            "Centre Régional de Formation Professionnelle de Kaya",
            "Centre Régional de Formation Professionnelle de Koudougou",
            "Centre Régional de Formation Professionnelle de Ouahigouya",
            "Centre Régional de Formation Professionnelle de Tenkodogo",
            "Centre Régional de Formation Professionnelle de Ziniaré",
            "Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)",
            "Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)",
        ],
    ),

    (
        "PACK 4 — Entrepreneur en communication digitale",
        [
            "Infographie (graphisme, calligraphie, photographie, sérigraphie)",
            "Intelligence artificielle",
            "Marketing digital",
            "Civisme Patriotisme-Entrepreneuriat",
        ],
        [
            "Centre Régional de Formation Professionnelle de Koudougou",
            "Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)",
            "Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)",
        ],
    ),

    (
        "PACK 5 — Entrepreneur en arts culinaires",
        [
            "Restauration (mets locaux, riz au soumbala poulet/poisson, mets occidentaux)",
            "Fumage/séchage de poulet/poisson",
            "Production de jus (gingembre, pain de singe, bissap, tamarin, mangue, cocktail de jus, etc.)",
            "Marketing digital",
            "Civisme Patriotisme-Entrepreneuriat",
        ],
        [
            "Centre Régional de Formation Professionnelle de Dédougou",
            "Centre Régional de Formation Professionnelle de Gaoua",
            "Centre Régional de Formation Professionnelle de Manga",
            "Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)",
            "Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)",
        ],
    ),

    (
        "PACK 6 — Référent digital",
        [
            "Médiation numérique",
            "Contenu multimédia et montage vidéo",
            "Communication et prospection via des outils en ligne",
            "Marketing digital",
            "Civisme Patriotisme-Entrepreneuriat",
        ],
        [
            "Centre de Formation Professionnelle Industriel de Bobo-Dioulasso (CFPI-B)",
            "Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)",
        ],
    ),

    (
        "PACK 7 — Artisan boulanger et pâtissier polyvalent",
        [
            "Pâtisserie",
            "Production du pain local",
            "Production des beignets locaux (maassa, Bourmassa, samsa)",
            "Marketing digital",
            "Civisme Patriotisme-Entrepreneuriat",
        ],
        [
            "Centre Régional de Formation Professionnelle de Banfora",
            "Centre Régional de Formation Professionnelle de Gaoua",
            "Centre Régional de Formation Professionnelle de Manga",
            "Centre Régional de Formation Professionnelle de Ziniaré",
        ],
    ),

    (
        "PACK 8 — Transformateur polyvalent de tubercules (manioc, igname, pomme de terre, patate)",
        [
            "Transformation de tubercules (Foutou, atiéké, placali, dèguè de patate douce, etc.)",
            "Conservation et conditionnement des produits à base de tubercules",
            "Gestion d’un atelier de transformation",
            "Marketing digital",
            "Civisme Patriotisme-Entrepreneuriat",
        ],
        [
            "Centre Régional de Formation Professionnelle de Koudougou",
            "Centre d’Evaluation et de Formation Professionnelle de Ouagadougou (CEFPO)",
        ],
    ),
]


# --- Année de programmation --------------------------------------------------
annee_2026, _ = AnneeScolaire.objects.get_or_create(libelle_anne=ANNEE_LIBELLE)

# --- Types de frais --------------------------------------------------------
tf_dossier, _ = TypeFrais.objects.get_or_create(
    libelle="Frais de dossier", defaults={"est_frais_de_dossier": True})
if not tf_dossier.est_frais_de_dossier:
    tf_dossier.est_frais_de_dossier = True
    tf_dossier.save(update_fields=["est_frais_de_dossier"])

tf_formation, _ = TypeFrais.objects.get_or_create(
    libelle="Frais de formation", defaults={"est_frais_de_dossier": False})
TrancheFrais.objects.get_or_create(
    type_frais=tf_formation, ordre=1,
    defaults={"libelle": "Tranche 1", "pourcentage": 75, "est_primordiale": True})
TrancheFrais.objects.get_or_create(
    type_frais=tf_formation, ordre=2,
    defaults={"libelle": "Tranche 2", "pourcentage": 25, "est_primordiale": False})

tf_reconversion, _ = TypeFrais.objects.get_or_create(
    libelle="Reconversion", defaults={"est_frais_de_dossier": False})

log("Type de frais", True, "Frais de dossier / Frais de formation (75/25) / Reconversion")


def _get_centre(nom):
    return centres.get(nom) or CentreFormation.objects.filter(nom_centre=nom).first()


def _set_frais(programmation, type_frais, montant):
    obj, created = Frais.objects.get_or_create(
        formation=programmation, type_frais=type_frais, defaults={"montant": montant})
    if not created and obj.montant != montant:
        obj.montant = montant
        obj.save(update_fields=["montant"])


def _set_piece(programmation, libelle, type_piece):
    PieceJointeInscription.objects.get_or_create(
        formation=programmation, libelle_piece=libelle,
        defaults={"type_piece": type_piece, "est_requis": True})


# Recherche de filière insensible à la casse / aux espaces : on évite de
# dupliquer un métier déjà présent sous une casse légèrement différente.
_filieres_par_cle = {}
for _f in Filiere.objects.all():
    _filieres_par_cle.setdefault(" ".join(_f.nom_filiere.lower().split()), _f)


def _filiere_formation(nom, titre):
    cle = " ".join(nom.lower().split())
    obj = _filieres_par_cle.get(cle)
    if obj is None:
        obj = Filiere.objects.create(
            nom_filiere=nom, titre_professionnel=titre or None,
            niveau_diplome=CONDITIONS_FORMATION, is_active=True)
        _filieres_par_cle[cle] = obj
        return obj
    maj = []
    if titre and obj.titre_professionnel != titre:
        obj.titre_professionnel = titre
        maj.append("titre_professionnel")
    if obj.niveau_diplome != CONDITIONS_FORMATION:
        obj.niveau_diplome = CONDITIONS_FORMATION
        maj.append("niveau_diplome")
    if not obj.is_active:
        obj.is_active = True
        maj.append("is_active")
    if maj:
        obj.save(update_fields=maj)
    return obj


# --- Formations (type de programme « Formation ») --------------------------
nb_formations = 0
centres_manquants = set()
for centre_nom, metier, titre, duree_mois, montant in FORMATIONS_2026_2027:
    centre = _get_centre(centre_nom)
    if centre is None:
        centres_manquants.add(centre_nom)
        continue
    filiere = _filiere_formation(metier, titre)
    prog, created = CentreEtFiliere.objects.get_or_create(
        centre=centre, filiere=filiere,
        defaults={
            "type_formation": "initiale",
            "type_programme": "formation",
            "annee_prog": annee_2026,
            "duree_jours": (duree_mois or 0) * 30 or None,
            "date_limite_inscription": DATE_LIMITE_2026,
            "is_active": True,
        },
    )
    if not created:
        prog.type_formation = "initiale"
        prog.type_programme = "formation"
        prog.annee_prog = annee_2026
        prog.date_limite_inscription = DATE_LIMITE_2026
        prog.is_active = True
        if duree_mois:
            prog.duree_jours = duree_mois * 30
        prog.save()
    _set_frais(prog, tf_dossier, MONTANT_FRAIS_DOSSIER)
    if montant:
        _set_frais(prog, tf_formation, montant)
    for libelle, type_piece in DOCS_FORMATION:
        _set_piece(prog, libelle, type_piece)
    nb_formations += 1

print("   OK " + str(nb_formations) + " programmations Formation "
      "(frais de dossier + frais de formation, 3 pieces requises)")

# --- Packs de reconversion (PRDSU) ---------------------------------------
nb_packs_prog = 0
for nom_pack, modules, centres_pack in PACKS_2026_2027:
    filiere_pack, _ = Filiere.objects.get_or_create(
        nom_filiere=nom_pack,
        defaults={
            "titre_professionnel": "CQP",
            "niveau_diplome": CONDITIONS_PACK,
            "texte_defilante": TEXTE_DEFILANT_PACK,
            "is_active": True,
        },
    )
    Filiere.objects.filter(pk=filiere_pack.pk).update(
        titre_professionnel="CQP", niveau_diplome=CONDITIONS_PACK,
        texte_defilante=TEXTE_DEFILANT_PACK, is_active=True)

    for libelle_module in modules:
        module = (Module.objects.filter(nom_module=libelle_module).first()
                  or Module.objects.create(nom_module=libelle_module, volume_h_cours=0))
        module.filieres.add(filiere_pack)

    for centre_nom in centres_pack:
        centre = _get_centre(centre_nom)
        if centre is None:
            centres_manquants.add(centre_nom)
            continue
        prog, created = CentreEtFiliere.objects.get_or_create(
            centre=centre, filiere=filiere_pack,
            defaults={
                "type_formation": "modulaire_qualifiante",
                "type_programme": "reconversion",
                "annee_prog": annee_2026,
                "duree_jours": 90,
                "date_limite_inscription": DATE_LIMITE_2026,
                "is_active": True,
            },
        )
        if not created:
            prog.type_formation = "modulaire_qualifiante"
            prog.type_programme = "reconversion"
            prog.annee_prog = annee_2026
            prog.duree_jours = 90
            prog.date_limite_inscription = DATE_LIMITE_2026
            prog.is_active = True
            prog.save()
        _set_frais(prog, tf_reconversion, MONTANT_PACK)
        _set_piece(prog, DOC_PACK[0], DOC_PACK[1])
        nb_packs_prog += 1

print("   OK " + str(len(PACKS_2026_2027)) + " packs (metiers + modules) - "
      + str(nb_packs_prog) + " programmations Reconversion")

if centres_manquants:
    print("   ATTENTION centres introuvables (programmations ignorees) : "
          + ", ".join(sorted(centres_manquants)))


# == ÉTAPE 7 — UTILISATEURS DE LA PLATEFORME (HABILITATIONS EXPLOITATION YUPAAN) ===
print("\n[7/7] Création des utilisateurs de la plateforme...")

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

# Structure seule : si POPULATE_COMPTES=0, listes vidées -> aucun compte créé.
if not CREER_COMPTES:
    print("   Comptes de la plateforme ignorés (structure seule).")
    DG_DATA = DAF_DATA = None
    DIR_DATA = CENTRE_DIRECTEURS_DATA = CAISSIERS_CENTRE_DATA = MEMBRES_SIEGE_DATA = []

# --- DG : aucun sous-modèle requis (rôle seul, cf. AgentForm.save()) -------
if DG_DATA:
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
if DAF_DATA:
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

if CREER_COMPTES:
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
    ("Modules",                       Module.objects.count()),
    ("Programmations (formations)",   CentreEtFiliere.objects.count()),
    ("  dont Reconversion",           CentreEtFiliere.objects.filter(type_programme="reconversion").count()),
    ("Types de frais",                TypeFrais.objects.count()),
    ("Lignes de frais",               Frais.objects.count()),
    ("Utilisateurs (tous rôles)",     Utilisateur.objects.count()),
]

for label, count in summary:
    bar = "█" * min(count, 40)
    print(f"   {label:<38} {count:>4}  {bar}")

print("=" * 80)
print("✅  POPULATION TERMINÉE AVEC SUCCÈS !")
print("=" * 80)
if CREER_COMPTES:
    print()
    print("   Compte administrateur :")
    print("   ┌─────────────────────────┬─────────────────────┬──────────────────┐")
    print("   │ Rôle                    │ username            │ password         │")
    print("   ├─────────────────────────┼─────────────────────┼──────────────────┤")
    print("   │ Super Admin             │ admin               │ Admin@2024       │")
    print("   └─────────────────────────┴─────────────────────┴──────────────────┘")
    print("=" * 80)
