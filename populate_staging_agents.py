"""Comptes de test du STAGING : 1 admin technique (superuser) + 1 agent par role,
chacun avec la ligne de profil que son role exige (MTI) et rattache a une
structure reelle. Sans cette ligne, redirect_to_dashboard() appelle
_bounce_to_login() qui deconnecte aussitot le compte.

Lancement (depuis la racine, stack staging demarre) :

    docker exec -i suudu_backend_staging python manage.py shell < populate_staging_agents.py

Idempotent : relançable sans creer de doublon. Ne cree jamais rien en prod
(garde-fou : refuse de tourner hors d'un environnement .env.staging, sauf
STAGING_AGENTS_FORCE=1).

Variables d'environnement optionnelles :
    STAGING_ADMIN_PWD   (defaut « StagingAdmin#2026 »)
    STAGING_AGENT_PWD   (defaut « StagingAgent#2026 »)
"""
import datetime
import os
import sys

from django.conf import settings
from django.contrib.auth.models import Group, Permission

from accounts.models import (Utilisateur, Formateur, MembreAdministration,
                             DirecteurInterRegional)
from courses.models import CentreFormation, Direction_reg, Filiere

# ── Garde-fou anti-prod ────────────────────────────────────────────────────
_env_file = os.environ.get("ENV_FILE", "")
if not _env_file.endswith(".staging") and os.environ.get("STAGING_AGENTS_FORCE") != "1":
    sys.exit("REFUS : ENV_FILE n'est pas un .env.staging. "
             "Forcer avec STAGING_AGENTS_FORCE=1 si vous savez ce que vous faites.")

MDP_ADMIN = os.environ.get("STAGING_ADMIN_PWD", "StagingAdmin#2026")
MDP_AGENT = os.environ.get("STAGING_AGENT_PWD", "StagingAgent#2026")
AUJ = datetime.date.today()

centre = CentreFormation.objects.order_by("id").first()
direction = Direction_reg.objects.order_by("id").first()
filiere = Filiere.objects.order_by("id").first()
if not centre or not direction:
    sys.exit("REFUS : base staging sans centre ni direction. "
             "Lancez d'abord ./.bascules/staging.sh seed (ou refresh).")

print("=" * 78)
print("  COMPTES DE TEST STAGING — BURKINA SUUDU BAWDE")
print("=" * 78)
print("  centre    :", centre)
print("  direction :", direction)
print("  filiere   :", filiere)

# Toute la matrice role x action (permissions « metier », hors add/change/delete auto).
MATRIX = [
    'gerer_regions', 'gerer_directions', 'gerer_centres', 'gerer_metiers',
    'gerer_programmations', 'gerer_modules', 'gerer_frais', 'gerer_annees',
    'gerer_equipe', 'gerer_agents', 'gerer_eleves', 'gerer_permissions',
    'acces_administration_technique', 'voir_historique_connexion',
    'voir_inscriptions', 'valider_inscription',
    'valider_inscription_reconversion', 'rejeter_inscription',
    'encaisser_paiement', 'gerer_paiements', 'rechercher_tous_centres',
    'telecharger_pieces', 'voir_statistiques', 'gerer_statistiques_reelles',
    'exporter_donnees', 'gerer_facturation', 'valider_facture_prestation',
    'encaisser_prestation',
]

# user_type -> permissions accordees au GROUPE du role ("ALL" = toute la matrice)
PERMS = {
    "admin": "ALL",
    "dg": "ALL",
    "dir": ["voir_inscriptions", "voir_statistiques", "exporter_donnees", "rechercher_tous_centres"],
    "deps": ["voir_statistiques", "gerer_statistiques_reelles", "exporter_donnees", "voir_inscriptions"],
    "gestionnaire": ["voir_inscriptions", "valider_inscription", "valider_inscription_reconversion",
                     "rejeter_inscription", "telecharger_pieces", "voir_statistiques"],
    "caissier": ["encaisser_paiement", "voir_inscriptions", "rechercher_tous_centres"],
    "agent_comptable": ["gerer_paiements", "encaisser_paiement", "exporter_donnees",
                        "gerer_facturation", "valider_facture_prestation", "encaisser_prestation"],
    "formateur": ["voir_statistiques"],
    "membre": ["gerer_agents", "gerer_eleves", "voir_historique_connexion"],
    "daf": ["gerer_facturation", "valider_facture_prestation", "encaisser_prestation",
            "exporter_donnees", "voir_statistiques"],
}


def applique_permissions(utype):
    """Ajoute les permissions du role a son groupe Django (auto-cree par save())."""
    group = Group.objects.get(name=Utilisateur.ROLE_GROUPS[utype])
    codes = MATRIX if PERMS.get(utype) == "ALL" else PERMS.get(utype, [])
    if codes:
        group.permissions.add(*Permission.objects.filter(codename__in=codes))
    return len(codes)


def finalise(u, mot_de_passe):
    u.is_staff = True
    u.is_superuser = getattr(u, "is_superuser", False)
    u.is_active = True
    u.set_password(mot_de_passe)
    u.save()  # save() rattache l'utilisateur au groupe ROLE_GROUPS[user_type]


def recree(username):
    """Supprime la ligne existante (et sa ligne fille MTI) pour repartir propre."""
    ancien = Utilisateur.objects.filter(username=username).first()
    if ancien:
        ancien.delete()


# ── 1. Admin technique (superuser -> acces /staging-bsb garanti) ───────────
print("\n[1] Admin technique")
recree("admin_staging")
admin = Utilisateur(username="admin_staging", nom="ADMIN", prenom="Staging",
                    email="admin_staging@staging.local", adresse="Ouagadougou",
                    user_type="admin")
admin.is_superuser = True
finalise(admin, MDP_ADMIN)
applique_permissions("admin")
Group.objects.get(name="Directeur Général").permissions.add(
    *Permission.objects.filter(codename="acces_administration_technique"))
print(f"    admin_staging / {MDP_ADMIN}  (superuser)")

# ── 2. Un agent par role ─────────────────────────────────────────────────
print("\n[2] Un agent par role")
lignes = []

# 2a. Roles sans ligne de profil dediee (Utilisateur simple)
for utype in ("admin", "dg", "deps", "membre", "daf"):
    uname = f"agent_{utype}"
    recree(uname)
    u = Utilisateur(username=uname, nom=utype.upper(), prenom="Agent",
                    email=f"{uname}@staging.local", adresse="Ouagadougou", user_type=utype)
    if utype in ("admin",):
        u.is_superuser = True
    finalise(u, MDP_AGENT)
    n = applique_permissions(utype)
    lignes.append((uname, Utilisateur.ROLE_GROUPS[utype], n, "Utilisateur"))

# 2b. dir -> DirecteurInterRegional + direction
recree("agent_dir")
u = DirecteurInterRegional(username="agent_dir", nom="DIR", prenom="Agent",
                           email="agent_dir@staging.local", adresse="Ouagadougou",
                           direction=direction)
finalise(u, MDP_AGENT)  # save() force user_type="dir"
n = applique_permissions("dir")
lignes.append(("agent_dir", "Directeur Inter-régional", n, f"DirInterReg -> {direction}"))

# 2c. gestionnaire / caissier / agent_comptable -> MembreAdministration + centre
for utype, emploi in (("gestionnaire", "Directeur de centre"),
                      ("caissier", "Caissier"),
                      ("agent_comptable", "Agent comptable")):
    uname = f"agent_{utype}"
    recree(uname)
    u = MembreAdministration(username=uname, nom=utype.upper(), prenom="Agent",
                             email=f"{uname}@staging.local", adresse="Ouagadougou",
                             user_type=utype, structure=centre,
                             emploi=emploi, categorie="Test")
    finalise(u, MDP_AGENT)
    n = applique_permissions(utype)
    lignes.append((uname, Utilisateur.ROLE_GROUPS[utype], n, f"Membre -> {centre}"))

# 2d. formateur -> Formateur + centre + filiere
recree("agent_formateur")
u = Formateur(username="agent_formateur", nom="FORMATEUR", prenom="Agent",
              email="agent_formateur@staging.local", adresse="Ouagadougou",
              user_type="formateur", centre=centre, filiere=filiere,
              emploi="Formateur", specialite="Test", date_integration=AUJ)
finalise(u, MDP_AGENT)
n = applique_permissions("formateur")
lignes.append(("agent_formateur", "Formateur", n, f"Formateur -> {centre}"))

# ── 3. Recapitulatif ─────────────────────────────────────────────────────
print("\n" + "=" * 78)
print(f"  {'username':22} {'groupe (role)':26} perms  profil")
print("  " + "-" * 74)
for uname, gname, nb, profil in lignes:
    print(f"  {uname:22} {gname:26} {nb:>4}  {profil}")
print("  " + "-" * 74)
print(f"  mot de passe admin  : {MDP_ADMIN}")
print(f"  mot de passe agents : {MDP_AGENT}")
print(f"  comptes en base     : {Utilisateur.objects.count()}")
print("=" * 78)
print("  Connexion agents : /accounts/login   |   Admin technique : /staging-bsb")
print("  OTP : selon EMAIL_BACKEND — en mode console, lire le code dans")
print("        docker logs -f suudu_backend_staging")
print("=" * 78)
