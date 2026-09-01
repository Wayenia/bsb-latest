from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.urls import reverse
from apis.serializers import UserRegisterSerializer


# REGISTER
def user_register(request):
    if request.method == 'POST':
        data = request.POST.copy()
        data.update(request.FILES)
        serializer = UserRegisterSerializer(data=data)

        if serializer.is_valid():
            try:
                user = serializer.save()
                login(request, user)
                messages.success(
                    request,
                    f"Bienvenue {user.prenom} {user.nom} ! Votre compte a été créé avec succès. "
                    "Consultez dès maintenant nos métiers de formation disponibles."
                )
                return redirect('courses:student_dashboard')

            except Exception as e:
                messages.error(request, f"Une erreur est survenue lors de la création du compte: {str(e)}")
                context = {
                    'errors': {'general': [str(e)]},
                    'form_data': request.POST
                }
                return render(request, 'accounts/register.html', context)

        context = {
            'errors': serializer.errors,
            'form_data': request.POST
        }
        return render(request, 'accounts/register.html', context)

    return render(request, 'accounts/register.html')

# LOGIN
import logging

from . import appareil, otp, ratelimit

logger = logging.getLogger('django.security')


def _est_apprenant(user):
    """Seul l'apprenant se connecte en une étape. Tout compte du personnel
    (rôle explicite, ou droit staff/superuser) passe par la vérification
    e-mail, même si son `user_type` est resté à la valeur par défaut."""
    return user.user_type == 'eleve' and not user.is_staff and not user.is_superuser


def _est_compte_admin(user):
    """Compte a privileges d'administration technique. Piloté par une permission
    (les superutilisateurs l'ont d'office, les comptes « admin » via leur groupe),
    donc délégable a tout compte depuis RH -> Permissions (README 9.2)."""
    return user.has_perm('accounts.acces_administration_technique')


def _passe_partout(user):
    """Le DG peut se connecter par les deux portes, publique comme dédiée."""
    return user.user_type == 'dg'


def _verifier_acces_admin_ip(request):
    """Filtre optionnel par adresse : hors des plages ADMIN_LOGIN_IPS, la page
    d'administration est introuvable (404), et non refusée — un sondeur ne peut
    pas même confirmer son existence. Liste vide = aucun filtrage."""
    import ipaddress
    from django.conf import settings
    from django.http import Http404
    reseaux = getattr(settings, 'ADMIN_LOGIN_IPS', []) or []
    if not reseaux:
        return
    brut = ratelimit.adresse_client(request)
    try:
        adresse = ipaddress.ip_address(brut)
    except ValueError:
        raise Http404
    for cidr in reseaux:
        try:
            if adresse in ipaddress.ip_network(cidr, strict=False):
                return
        except ValueError:
            continue
    raise Http404


def user_login(request):
    from .models import Utilisateur

    # ── Déjà connecté → tableau de bord ───────────────────────────────────
    if request.user.is_authenticated:
        return redirect('courses:redirect_to_dashboard')

    # Repartir de zéro depuis la page « code » (lien « utiliser un autre compte »).
    if request.GET.get('reset'):
        otp.annuler(request)

    if request.method == 'POST':
        identifiant = request.POST.get('identifiant', '').strip()
        password = request.POST.get('password', '')

        if not identifiant or not password:
            messages.error(request, "Veuillez renseigner tous les champs.")
            return render(request, 'accounts/login.html', {'identifiant': identifiant})

        par_email = '@' in identifiant
        if par_email:
            compte = Utilisateur.objects.filter(email__iexact=identifiant).first()
            msg_incorrect = "Email ou mot de passe incorrect."
        else:
            compte = Utilisateur.objects.filter(username=identifiant).first()
            msg_incorrect = "Nom d'utilisateur ou mot de passe incorrect."

        # Verrou anti-force brute par compte (le verrou par IP est posé en amont
        # par LimitationConnexionMiddleware).
        if compte is not None and ratelimit.est_verrouille(request, compte.username):
            messages.error(request, "Trop de tentatives de connexion. Réessayez dans quelques minutes.")
            return render(request, 'accounts/login.html', {'identifiant': identifiant})

        user = None
        if compte is not None:
            user = authenticate(request, username=compte.username, password=password)
        else:
            # Exécute quand même le hachage : sans cela, un e-mail inconnu
            # répondrait nettement plus vite qu'un mot de passe faux, ce qui
            # permettrait d'énumérer les comptes existants au chronomètre.
            authenticate(request, username='', password=password)

        if user is None:
            messages.error(request, msg_incorrect)
            return render(request, 'accounts/login.html', {'identifiant': identifiant})

        if not user.is_active:
            messages.error(request, "Votre compte est désactivé. Contactez l'administrateur.")
            return render(request, 'accounts/login.html', {'identifiant': identifiant})

        # ── Compte d'administration technique : porte publique fermée ─────
        # Le DG fait exception (il passe partout). Message générique : la page
        # ne révèle pas qu'un compte est à privilèges, ni qu'il existe.
        if _est_compte_admin(user) and not _passe_partout(user):
            logger.warning("Connexion admin refusee sur la page publique : %s (%s)",
                           user.username, ratelimit.adresse_client(request))
            messages.error(request, msg_incorrect)
            return render(request, 'accounts/login.html', {'identifiant': identifiant})

        # ── Apprenant : connexion directe ────────────────────────────────
        if _est_apprenant(user):
            login(request, user)
            messages.success(request, f"Bienvenue {user.prenom} {user.nom} !")
            return redirect('courses:redirect_to_dashboard')

        # ── Personnel : appareil deja reconnu, le code n'est pas redemande ──
        # L'agent qui travaille depuis son poste habituel n'a plus a saisir de
        # code a chaque connexion ; tout autre appareil reste barre par le code.
        if appareil.est_reconnu(request, user):
            login(request, user)
            messages.success(request, f"Bienvenue {user.prenom} {user.nom} !")
            return redirect('courses:redirect_to_dashboard')

        # ── Personnel : envoi d'un code de vérification par e-mail ───────
        if not user.email:
            messages.error(request, "Aucune adresse e-mail n'est associée à ce compte. Contactez l'administrateur.")
            return render(request, 'accounts/login.html', {'identifiant': identifiant})

        try:
            otp.envoyer_code(request, user, premier_envoi=True)
        except Exception:
            otp.annuler(request)
            logger.exception("Echec d'envoi du code OTP a %s", user.email)
            messages.error(request, "Impossible d'envoyer le code de connexion pour le moment. Réessayez plus tard.")
            return render(request, 'accounts/login.html', {'identifiant': identifiant})

        return redirect('accounts:login_otp')

    return render(request, 'accounts/login.html')


def admin_login(request):
    """Porte d'entrée dédiée aux comptes d'administration technique.

    Chemin issu du .env (jamais du dépôt), non lié depuis le site. La page
    n'authentifie que les comptes à privilèges (et le DG, qui passe partout) ;
    tout autre compte est refusé par un message générique. Le code e-mail (2FA)
    est exigé à chaque connexion, sans dispense d'appareil.
    """
    from .models import Utilisateur

    _verifier_acces_admin_ip(request)

    if request.user.is_authenticated:
        return redirect('courses:redirect_to_dashboard')

    if request.GET.get('reset'):
        otp.annuler(request)

    if request.method == 'POST':
        identifiant = request.POST.get('identifiant', '').strip()
        password = request.POST.get('password', '')

        if not identifiant or not password:
            messages.error(request, "Veuillez renseigner tous les champs.")
            return render(request, 'accounts/admin_login.html', {'identifiant': identifiant})

        if '@' in identifiant:
            compte = Utilisateur.objects.filter(email__iexact=identifiant).first()
        else:
            compte = Utilisateur.objects.filter(username=identifiant).first()
        msg_incorrect = "Identifiants incorrects."

        if compte is not None and ratelimit.est_verrouille(request, compte.username):
            messages.error(request, "Trop de tentatives de connexion. Réessayez dans quelques minutes.")
            return render(request, 'accounts/admin_login.html', {'identifiant': identifiant})

        user = None
        if compte is not None:
            user = authenticate(request, username=compte.username, password=password)
        else:
            authenticate(request, username='', password=password)

        if user is None or not user.is_active:
            messages.error(request, msg_incorrect)
            return render(request, 'accounts/admin_login.html', {'identifiant': identifiant})

        # Réservé aux comptes à privilèges et au DG. Refus générique sinon :
        # la page ne dit pas si le compte existe ni s'il est admin.
        if not (_est_compte_admin(user) or _passe_partout(user)):
            logger.warning("Acces admin refuse (compte non habilite) : %s (%s)",
                           user.username, ratelimit.adresse_client(request))
            messages.error(request, msg_incorrect)
            return render(request, 'accounts/admin_login.html', {'identifiant': identifiant})

        if not user.email:
            messages.error(request, "Aucune adresse e-mail n'est associée à ce compte. Contactez l'administrateur.")
            return render(request, 'accounts/admin_login.html', {'identifiant': identifiant})

        try:
            otp.envoyer_code(request, user, premier_envoi=True, admin=True)
        except Exception:
            otp.annuler(request)
            logger.exception("Echec d'envoi du code OTP (admin) a %s", user.email)
            messages.error(request, "Impossible d'envoyer le code de connexion pour le moment. Réessayez plus tard.")
            return render(request, 'accounts/admin_login.html', {'identifiant': identifiant})

        return redirect('accounts:login_otp')

    return render(request, 'accounts/admin_login.html')


def _masquer_email(email):
    if not email or '@' not in email:
        return email or ''
    local, domaine = email.split('@', 1)
    if len(local) <= 2:
        local_masque = local[0] + '•'
    else:
        local_masque = local[0] + '•' * (len(local) - 2) + local[-1]
    return f"{local_masque}@{domaine}"


def _contexte_otp(request):
    donnees = otp.etat(request)
    return {
        'email_masque': _masquer_email(donnees['email']) if donnees else '',
        'secondes_restantes': otp.secondes_restantes(donnees) if donnees else 0,
        'delai_renvoi': otp.DELAI_RENVOI,
    }


def login_otp(request):
    """Deuxième étape : saisie du code à 4 chiffres reçu par e-mail."""
    from .models import Utilisateur

    if request.user.is_authenticated:
        return redirect('courses:redirect_to_dashboard')

    donnees = otp.etat(request)
    if not donnees:
        messages.error(request, "Session expirée. Veuillez vous reconnecter.")
        return redirect('accounts:login')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        if not code:
            code = ''.join(request.POST.get(f'code_{i}', '') for i in range(4))

        # L'identifiant du compte et le mode admin sont lus maintenant : en cas
        # de succès, otp.verifier() purge l'entrée de session.
        user_id = donnees['user_id']
        mode_admin = donnees.get('admin', False)
        ok, erreur = otp.verifier(request, code)

        if ok:
            user = Utilisateur.objects.filter(pk=user_id, is_active=True).first()
            if user is None:
                messages.error(request, "Compte introuvable. Reconnectez-vous.")
                return redirect('accounts:login')
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            messages.success(request, f"Bienvenue {user.prenom} {user.nom} !")
            # Le titulaire est averti : c'est la seule alerte qui lui parvienne
            # directement, sans attendre un rapport periodique.
            appareil.avertir(user, request)
            reponse = redirect('courses:redirect_to_dashboard')
            # Espace d'administration : jamais de dispense d'appareil, le code
            # est redemande a chaque connexion. Les autres profils gardent la
            # reconnaissance d'appareil pendant trente jours.
            if mode_admin:
                return reponse
            return appareil.marquer_reconnu(reponse, user)

        messages.error(request, erreur)
        if not otp.etat(request):
            return redirect('accounts:login')

    return render(request, 'accounts/otp.html', _contexte_otp(request))


def login_otp_resend(request):
    from .models import Utilisateur

    if request.method != 'POST':
        return redirect('accounts:login_otp')

    donnees = otp.etat(request)
    if not donnees:
        messages.error(request, "Session expirée. Veuillez vous reconnecter.")
        return redirect('accounts:login')

    ok, erreur = otp.peut_renvoyer(donnees)
    if not ok:
        messages.error(request, erreur)
        return redirect('accounts:login_otp')

    user = Utilisateur.objects.filter(pk=donnees['user_id'], is_active=True).first()
    if user is None:
        otp.annuler(request)
        messages.error(request, "Compte introuvable. Reconnectez-vous.")
        return redirect('accounts:login')

    try:
        otp.envoyer_code(request, user, premier_envoi=False)
    except Exception:
        logger.exception("Echec de renvoi du code OTP a %s", user.email)
        messages.error(request, "Impossible d'envoyer le code pour le moment. Réessayez plus tard.")
        return redirect('accounts:login_otp')

    messages.success(request, "Un nouveau code vous a été envoyé.")
    return redirect('accounts:login_otp')


# LOGOUT
def user_logout(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('accounts:login')


# ─── Profil (self-service, tous rôles) ─────────────────────────────────────

@login_required
def mon_compte(request):
    from .models import Eleve

    if request.user.user_type == 'eleve':
        profil = get_object_or_404(Eleve, pk=request.user.pk)
    else:
        profil = request.user

    return render(request, 'accounts/mon_compte.html', {'profil': profil})


@login_required
def mon_profil(request):
    from .models import Eleve
    from .forms import ProfilForm, ProfilEleveForm

    if request.user.user_type == 'eleve':
        instance = get_object_or_404(Eleve, pk=request.user.pk)
        form_class = ProfilEleveForm
    else:
        instance = request.user
        form_class = ProfilForm

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Vos informations ont été mises à jour avec succès.")
            return redirect('accounts:mon_compte')
        messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = form_class(instance=instance)

    return render(request, 'accounts/profil.html', {'form': form})


@login_required
def changer_mot_de_passe(request):
    champ_classes = (
        'w-full px-4 py-3 border border-gray-300 rounded-lg '
        'focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all'
    )

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Sans ceci, changer son propre mot de passe déconnecte l'utilisateur
            # (le hash de session ne correspond plus au nouveau mot de passe).
            update_session_auth_hash(request, user)
            messages.success(request, "Votre mot de passe a été modifié avec succès.")
            return redirect('accounts:mon_compte')
        messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = PasswordChangeForm(request.user)

    for field in form.fields.values():
        field.widget.attrs.setdefault('class', champ_classes)

    return render(request, 'accounts/changer_mot_de_passe.html', {'form': form})


############### MODULE FACTURATION ET PRESTATION (DAF) #############

from decimal import Decimal, InvalidOperation

import base64
import os

from django.conf import settings
from django.db.models import Q, ProtectedError
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
import weasyprint

from courses.permissions import require_permission, require_role

from .models import (
    Client_prestation, Prestation_prestation, Facture_prestation,
    LigneFacture_prestation, Paiement_prestation, LignePaiement_prestation,
)
from .forms import (
    ClientPrestationForm, PrestationQuickForm, PrestationForm, FactureForm,
    LigneFactureFormSet, PaiementPrestationForm,
)
from .utils import montant_en_lettres


def _user_centre_direction(user):
    """Résout le centre / la direction régionale rattachés à l'utilisateur
    connecté, quel que soit son rôle (DAF, membre de l'administration,
    directeur inter-régional...). Retourne (centre, direction) — l'un des
    deux, ou les deux, peuvent être None (ex. admin/DG sans rattachement)."""
    from .models import DAF, MembreAdministration, DirecteurInterRegional

    centre = None
    direction = None

    daf = DAF.objects.filter(pk=user.pk).first()
    if daf and daf.structure:
        centre = daf.structure

    if not centre:
        membre = MembreAdministration.objects.filter(pk=user.pk).first()
        if membre:
            centre = membre.structure
            direction = membre.direction

    if not direction:
        dir_obj = DirecteurInterRegional.objects.filter(pk=user.pk).first()
        if dir_obj:
            direction = dir_obj.direction

    if not direction and centre:
        direction = centre.direction

    return centre, direction


def _facturation_header_lines(user=None):
    """En-tête officiel des documents du module Facturation (factures, reçus).

    Si l'utilisateur connecté est rattaché à une direction régionale et/ou un
    centre, l'en-tête se termine par ces informations (comme pour les autres
    documents officiels de l'application) ; à défaut (ex. admin/DG sans
    rattachement), la ligne générique "DIRECTION DE L'ADMINISTRATION ET DES
    FINANCES" est utilisée.
    """
    left = [
        "MINISTÈRE DE L'ENSEIGNEMENT SECONDAIRE",
        "ET DE LA FORMATION PROFESSIONNELLE ET TECHNIQUE",
        "**********",
        "SECRETARIAT GENERAL",
        "**********",
        "BURKINA SUUDU BAWDE",
        "**********",
        "DIRECTION GENERALE",
    ]

    centre, direction = _user_centre_direction(user) if user is not None else (None, None)

    if not centre and not direction:
        left += ["**********", "DIRECTION DE L'ADMINISTRATION", "ET DES FINANCES"]
    else:
        if direction:
            left += ["**********", direction.nom_direction.upper()]
        if centre:
            left += ["**********", centre.nom_centre.upper()]

    right = [
        "Burkina Faso",
        "la patrie ou la mort, nous vaincrons",
    ]
    return left, right


_FAVICON_DATA_URI_CACHE = None


def _pdf_logo_data_uri():
    """Logo encodé en base64, à insérer directement dans le HTML des PDF
    weasyprint (`<img src="{{ favicon_data_uri }}">`). Nécessaire car
    `weasyprint.HTML(string=...)` ne peut pas résoudre une URL `{% static %}`
    en environnement conteneurisé — on évite tout aller-retour réseau ou
    résolution de fichier au moment du rendu."""
    global _FAVICON_DATA_URI_CACHE
    if _FAVICON_DATA_URI_CACHE is None:
        favicon_path = os.path.join(settings.BASE_DIR, 'static/images/favicon.png')
        with open(favicon_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('ascii')
        _FAVICON_DATA_URI_CACHE = f"data:image/png;base64,{encoded}"
    return _FAVICON_DATA_URI_CACHE


# ─── Tableau de bord DAF ────────────────────────────────────────────────────

@require_role('daf')
def daf_dashboard(request):
    return render(request, 'accounts/facturation/daf_dashboard.html')


# ─── Recherche client existant (téléphone / IFU) ───────────────────────────

@require_permission('accounts.gerer_facturation')
def client_lookup(request):
    tel = request.GET.get('tel', '').strip()
    ifu = request.GET.get('ifu', '').strip()

    client = None
    if tel:
        client = Client_prestation.objects.filter(type_client='personne', telephone=tel).first()
    elif ifu:
        client = Client_prestation.objects.exclude(type_client='personne').filter(ifu=ifu).first()

    if not client:
        return JsonResponse({'found': False})

    return JsonResponse({
        'found': True,
        'id': client.id,
        'type_client': client.type_client,
        'nom': client.nom,
        'prenom': client.prenom,
        'telephone': client.telephone,
        'adresse': client.adresse,
        'type_piece': client.type_piece,
        'numero_piece': client.numero_piece,
        'raison_sociale': client.raison_sociale,
        'ifu': client.ifu,
        'statut': client.statut,
        'date_creation': client.date_creation.isoformat() if client.date_creation else '',
    })


# ─── Création rapide d'une prestation (catalogue) ──────────────────────────

@require_permission('accounts.gerer_facturation')
def prestation_quick_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': "Méthode non autorisée."}, status=405)

    form = PrestationQuickForm(request.POST)
    if form.is_valid():
        prestation = form.save()
        return JsonResponse({
            'id': prestation.id,
            'libelle': prestation.libelle,
            'prix_unitaire': str(prestation.prix_unitaire),
        })
    return JsonResponse({'errors': form.errors}, status=400)


# ─── Catalogue des prestations (hors formulaire de facture) ────────────────

@require_permission('accounts.gerer_facturation')
def prestation_list(request):
    prestations = Prestation_prestation.objects.order_by('libelle')

    q = request.GET.get('q', '').strip()
    if q:
        prestations = prestations.filter(libelle__icontains=q)

    paginator = Paginator(prestations, 10)
    page = request.GET.get('page')
    prestations = paginator.get_page(page)

    return render(request, 'accounts/facturation/prestation_list.html', {
        'prestations': prestations,
        'q': q,
    })


@require_permission('accounts.gerer_facturation')
def prestation_create(request):
    if request.method == 'POST':
        form = PrestationQuickForm(request.POST)
        if form.is_valid():
            prestation = form.save()
            messages.success(request, f"Prestation « {prestation.libelle} » créée avec succès.")
            return redirect('accounts:prestation_list')
        messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = PrestationQuickForm()

    return render(request, 'accounts/facturation/prestation_form.html', {'form': form})


@require_permission('accounts.gerer_facturation')
def prestation_update(request, id):
    prestation = get_object_or_404(Prestation_prestation, id=id)

    if request.method == 'POST':
        form = PrestationForm(request.POST, instance=prestation)
        if form.is_valid():
            form.save()
            messages.success(request, f"Prestation « {prestation.libelle} » modifiée avec succès.")
            return redirect('accounts:prestation_list')
        messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = PrestationForm(instance=prestation)

    return render(request, 'accounts/facturation/prestation_form.html', {
        'form': form,
        'prestation': prestation,
        'editing': True,
    })


@require_permission('accounts.gerer_facturation')
def prestation_delete(request, id):
    prestation = get_object_or_404(Prestation_prestation, id=id)

    if request.method != 'POST':
        return redirect('accounts:prestation_list')

    libelle = prestation.libelle
    try:
        prestation.delete()
        messages.success(request, f"Prestation « {libelle} » supprimée.")
    except ProtectedError:
        messages.error(
            request,
            f"Impossible de supprimer « {libelle} » : elle est utilisée dans une ou plusieurs "
            "factures. Vous pouvez la désactiver depuis le formulaire de modification."
        )
    return redirect('accounts:prestation_list')


@require_permission('accounts.gerer_facturation')
def prestation_import_template(request):
    from courses.bulk_import.views_helpers import render_import_template
    from .bulk_import_registry import SPEC_PRESTATION
    return render_import_template(request, SPEC_PRESTATION)


@require_permission('accounts.gerer_facturation')
def prestation_import(request):
    from courses.bulk_import.views_helpers import handle_import_upload
    from .bulk_import_registry import SPEC_PRESTATION
    return handle_import_upload(request, SPEC_PRESTATION)


# ─── Catalogue des clients (facturation) ────────────────────────────────────

@require_permission('accounts.gerer_facturation')
def client_list(request):
    clients = Client_prestation.objects.order_by('nom', 'raison_sociale')

    q = request.GET.get('q', '').strip()
    if q:
        clients = clients.filter(
            Q(nom__icontains=q) | Q(prenom__icontains=q) |
            Q(raison_sociale__icontains=q) | Q(telephone__icontains=q) |
            Q(ifu__icontains=q)
        )

    paginator = Paginator(clients, 10)
    clients_page = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/facturation/client_list.html', {
        'clients': clients_page,
        'q': q,
    })


@require_permission('accounts.gerer_facturation')
def client_import_template(request):
    from courses.bulk_import.views_helpers import render_import_template
    from .bulk_import_registry import SPEC_CLIENT
    return render_import_template(request, SPEC_CLIENT)


@require_permission('accounts.gerer_facturation')
def client_import(request):
    from courses.bulk_import.views_helpers import handle_import_upload
    from .bulk_import_registry import SPEC_CLIENT
    return handle_import_upload(request, SPEC_CLIENT)


# ─── Création d'une facture (proforma ou définitive) ───────────────────────

@require_permission('accounts.gerer_facturation')
def facture_create(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action not in ('proforma', 'definitive'):
            messages.error(request, "Action invalide.")
            return redirect('accounts:facture_create')

        client_id = request.POST.get('client_id') or None
        client_instance = get_object_or_404(Client_prestation, pk=client_id) if client_id else None

        client_form = ClientPrestationForm(request.POST, instance=client_instance)
        facture_form = FactureForm(request.POST)
        formset = LigneFactureFormSet(request.POST, instance=Facture_prestation())

        lignes_valides = formset.is_valid() and any(
            f.cleaned_data and not f.cleaned_data.get('DELETE')
            for f in formset.forms if f.cleaned_data
        )

        if client_form.is_valid() and facture_form.is_valid() and lignes_valides:
            client = client_form.save()

            facture = facture_form.save(commit=False)
            facture.client = client
            facture.type_facture = action
            facture.cree_par = request.user
            facture.montant_total = 0
            facture.save()

            formset.instance = facture
            formset.save()

            facture.montant_total = sum(l.montant for l in facture.lignes.all())
            facture.save(update_fields=['montant_total'])

            messages.success(request, f"Facture {facture.numero} créée avec succès.")
            # Formulaire rafraichi, PDF declenche en telechargement par le
            # script de facture_form.html.
            return redirect(f"{reverse('accounts:facture_create')}?facture={facture.id}")

        # Messages d'erreur précis (champ par champ) plutôt qu'un message générique.
        erreurs = []
        for field, field_errors in client_form.errors.items():
            label = client_form.fields[field].label if field in client_form.fields else field
            erreurs.extend(f"{label} : {e}" for e in field_errors)
        for field, field_errors in facture_form.errors.items():
            label = facture_form.fields[field].label if field in facture_form.fields else field
            erreurs.extend(f"{label} : {e}" for e in field_errors)
        if not formset.is_valid():
            erreurs.append("Une ou plusieurs lignes de prestation contiennent une erreur (prestation, quantité ou coût unitaire manquant/invalide).")
        elif not lignes_valides:
            erreurs.append("Ajoutez au moins une ligne de prestation.")

        if erreurs:
            messages.error(request, "Veuillez corriger : " + " ; ".join(erreurs))
        else:
            messages.error(request, "Une erreur est survenue lors de la création de la facture. Veuillez réessayer.")
    else:
        client_form = ClientPrestationForm()
        facture_form = FactureForm()
        formset = LigneFactureFormSet(instance=Facture_prestation())

    prestations = Prestation_prestation.objects.filter(actif=True).order_by('libelle')
    return render(request, 'accounts/facturation/facture_form.html', {
        'client_form': client_form,
        'facture_form': facture_form,
        'formset': formset,
        'prestations': prestations,
        'prestations_json': [
            {'id': p.id, 'libelle': p.libelle, 'prix_unitaire': str(p.prix_unitaire)}
            for p in prestations
        ],
    })


# ─── Liste des factures proforma (modifiables) ─────────────────────────────

@require_permission('accounts.gerer_facturation')
def facture_proforma_list(request):
    factures = Facture_prestation.objects.select_related('client').filter(
        type_facture='proforma'
    ).order_by('-date_creation')

    q = request.GET.get('q', '').strip()
    if q:
        factures = factures.filter(
            Q(numero__icontains=q) |
            Q(client__nom__icontains=q) |
            Q(client__prenom__icontains=q) |
            Q(client__raison_sociale__icontains=q)
        )

    paginator = Paginator(factures, 10)
    page = request.GET.get('page')
    factures = paginator.get_page(page)

    return render(request, 'accounts/facturation/facture_proforma_list.html', {
        'factures': factures,
        'q': q,
    })


# ─── Modification d'une facture proforma ───────────────────────────────────

@require_permission('accounts.gerer_facturation')
def facture_proforma_update(request, id):
    facture = get_object_or_404(Facture_prestation, id=id, type_facture='proforma')

    if request.method == 'POST':
        client_form = ClientPrestationForm(request.POST, instance=facture.client)
        facture_form = FactureForm(request.POST, instance=facture)
        formset = LigneFactureFormSet(request.POST, instance=facture)

        lignes_valides = formset.is_valid() and any(
            f.cleaned_data and not f.cleaned_data.get('DELETE')
            for f in formset.forms if f.cleaned_data
        )

        if client_form.is_valid() and facture_form.is_valid() and lignes_valides:
            client = client_form.save()

            facture = facture_form.save(commit=False)
            facture.client = client
            facture.save()

            formset.save()

            facture.montant_total = sum(l.montant for l in facture.lignes.all())
            facture.save(update_fields=['montant_total'])

            messages.success(request, f"Facture {facture.numero} modifiée avec succès.")
            return redirect('accounts:facture_proforma_list')

        erreurs = []
        for field, field_errors in client_form.errors.items():
            label = client_form.fields[field].label if field in client_form.fields else field
            erreurs.extend(f"{label} : {e}" for e in field_errors)
        for field, field_errors in facture_form.errors.items():
            label = facture_form.fields[field].label if field in facture_form.fields else field
            erreurs.extend(f"{label} : {e}" for e in field_errors)
        if not formset.is_valid():
            erreurs.append("Une ou plusieurs lignes de prestation contiennent une erreur (prestation, quantité ou coût unitaire manquant/invalide).")
        elif not lignes_valides:
            erreurs.append("Ajoutez au moins une ligne de prestation.")

        if erreurs:
            messages.error(request, "Veuillez corriger : " + " ; ".join(erreurs))
        else:
            messages.error(request, "Une erreur est survenue lors de la modification de la facture. Veuillez réessayer.")
    else:
        client_form = ClientPrestationForm(instance=facture.client)
        facture_form = FactureForm(instance=facture)
        formset = LigneFactureFormSet(instance=facture)

    prestations = Prestation_prestation.objects.filter(actif=True).order_by('libelle')
    return render(request, 'accounts/facturation/facture_form.html', {
        'client_form': client_form,
        'facture_form': facture_form,
        'formset': formset,
        'prestations': prestations,
        'prestations_json': [
            {'id': p.id, 'libelle': p.libelle, 'prix_unitaire': str(p.prix_unitaire)}
            for p in prestations
        ],
        'facture': facture,
        'editing': True,
    })


# ─── Suppression d'une facture proforma ────────────────────────────────────

@require_permission('accounts.gerer_facturation')
def facture_proforma_delete(request, id):
    facture = get_object_or_404(Facture_prestation, id=id, type_facture='proforma')

    if request.method != 'POST':
        return redirect('accounts:facture_proforma_list')

    numero = facture.numero
    facture.delete()
    messages.success(request, f"Facture proforma {numero} supprimée.")
    return redirect('accounts:facture_proforma_list')


# ─── PDF de la facture ──────────────────────────────────────────────────────

@require_permission('accounts.gerer_facturation', 'accounts.encaisser_prestation')
def facture_pdf(request, id):
    facture = get_object_or_404(
        Facture_prestation.objects.select_related('client', 'cree_par').prefetch_related('lignes__prestation'),
        id=id
    )
    header_left, header_right = _facturation_header_lines(request.user)
    html_string = render_to_string('accounts/facturation/facture_pdf.html', {
        'facture': facture,
        'lignes': facture.lignes.all(),
        'montant_lettres': montant_en_lettres(facture.montant_total),
        'header_left': header_left,
        'header_right': header_right,
        'favicon_data_uri': _pdf_logo_data_uri(),
    })
    pdf_file = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    # "attachment" : déclenché automatiquement en téléchargement (création de
    # facture, page facture_detail) sans quitter/naviguer hors de la page.
    response['Content-Disposition'] = f'attachment; filename="{facture.numero.replace("/", "-")}.pdf"'
    return response


# ─── Validation proforma -> définitive ──────────────────────────────────────

@require_permission('accounts.valider_facture_prestation')
def facture_valider(request, id):
    facture = get_object_or_404(Facture_prestation, id=id)

    if request.method != 'POST':
        return redirect('accounts:facture_detail', id=id)

    if facture.type_facture == 'definitive':
        messages.warning(request, "Cette facture est déjà définitive.")
        return redirect('accounts:facture_detail', id=id)

    facture.type_facture = 'definitive'
    facture.numero = None
    facture.date_validation = timezone.now()
    facture.save()

    messages.success(request, f"Facture validée — nouveau numéro : {facture.numero}.")
    return redirect('accounts:facture_detail', id=id)


# ─── Liste des factures (Encaissement/Prestation) ──────────────────────────

@require_permission('accounts.gerer_facturation', 'accounts.encaisser_prestation')
def facture_list(request):
    factures = Facture_prestation.objects.select_related('client').order_by('-date_creation')

    statut = request.GET.get('statut', '').strip()
    if statut in ('proforma', 'definitive'):
        factures = factures.filter(type_facture=statut)

    q = request.GET.get('q', '').strip()
    if q:
        factures = factures.filter(
            Q(numero__icontains=q) |
            Q(client__nom__icontains=q) |
            Q(client__prenom__icontains=q) |
            Q(client__raison_sociale__icontains=q)
        )

    paginator = Paginator(factures, 10)
    page = request.GET.get('page')
    factures = paginator.get_page(page)

    return render(request, 'accounts/facturation/facture_list.html', {
        'factures': factures,
        'q': q,
        'statut': statut,
    })


# ─── Détail d'une facture + modale d'encaissement ──────────────────────────

@require_permission('accounts.gerer_facturation', 'accounts.encaisser_prestation')
def facture_detail(request, id):
    facture = get_object_or_404(
        Facture_prestation.objects.select_related('client').prefetch_related('lignes__prestation', 'paiements'),
        id=id
    )
    return render(request, 'accounts/facturation/facture_detail.html', {
        'facture': facture,
        'lignes': facture.lignes.all(),
        'paiements': facture.paiements.order_by('-date_paiement'),
        'paiement_form': PaiementPrestationForm(),
    })


# ─── Encaissement (par ligne ou total) ──────────────────────────────────────

@require_permission('accounts.encaisser_prestation')
def prestation_encaisser(request, id):
    facture = get_object_or_404(Facture_prestation.objects.prefetch_related('lignes'), id=id)

    if request.method != 'POST':
        return redirect('accounts:facture_detail', id=id)

    if facture.type_facture != 'definitive':
        messages.error(request, "Seules les factures définitives peuvent être encaissées.")
        return redirect('accounts:facture_detail', id=id)

    mode_encaissement = request.POST.get('mode_encaissement', 'total')
    mode_paiement = request.POST.get('mode_paiement', '')
    reference = request.POST.get('reference', '').strip()

    if mode_paiement not in dict(Paiement_prestation.MODE_PAIEMENT):
        messages.error(request, "Mode de paiement invalide.")
        return redirect('accounts:facture_detail', id=id)

    montant_str = request.POST.get('montant_paiement', '').strip()
    try:
        montant = Decimal(montant_str)
    except (InvalidOperation, TypeError):
        messages.error(request, "Montant invalide.")
        return redirect('accounts:facture_detail', id=id)

    # Aucun montant négatif (ni nul) n'est accepté, quel que soit le mode.
    if montant <= 0:
        messages.error(request, "Le montant doit être supérieur à 0.")
        return redirect('accounts:facture_detail', id=id)

    repartition = {}

    if mode_encaissement == 'ligne':
        ligne_id = request.POST.get('ligne_id')
        ligne = facture.lignes.filter(id=ligne_id).first()
        if not ligne:
            messages.error(request, "Ligne de facture introuvable.")
            return redirect('accounts:facture_detail', id=id)
        if montant > ligne.reste():
            messages.error(request, f"Le montant saisi pour « {ligne.prestation} » dépasse le reste dû sur cette ligne ({ligne.reste()} FCFA).")
            return redirect('accounts:facture_detail', id=id)
        repartition[ligne.id] = montant

    else:
        # Encaissement du montant total : doit correspondre exactement au
        # reste dû de la facture, ni plus ni moins.
        reste_facture = facture.reste_a_payer()
        if montant != reste_facture:
            messages.error(
                request,
                f"L'encaissement du montant total doit correspondre exactement au reste dû de la facture ({reste_facture} FCFA)."
            )
            return redirect('accounts:facture_detail', id=id)

        restant = montant
        for ligne in facture.lignes.all():
            if restant <= 0:
                break
            reste_ligne = ligne.reste()
            if reste_ligne <= 0:
                continue
            part = min(reste_ligne, restant)
            repartition[ligne.id] = part
            restant -= part

    montant_total_verse = sum(repartition.values())
    if montant_total_verse <= 0:
        messages.error(request, "Veuillez saisir un montant supérieur à 0.")
        return redirect('accounts:facture_detail', id=id)

    paiement = Paiement_prestation(
        facture=facture,
        montant=montant_total_verse,
        mode_paiement=mode_paiement,
        reference=reference,
        caissier=request.user,
    )
    paiement.save()

    lignes_by_id = {l.id: l for l in facture.lignes.all()}
    for ligne_id, part in repartition.items():
        LignePaiement_prestation.objects.create(
            paiement=paiement, ligne_facture=lignes_by_id[ligne_id], montant=part,
        )

    messages.success(request, f"Paiement de {montant_total_verse} FCFA encaissé — reçu {paiement.numero_recu}.")
    # Facture a jour, recu declenche en telechargement par le script de
    # facture_detail.html, qui lit ce parametre.
    return redirect(f"{reverse('accounts:facture_detail', kwargs={'id': id})}?recu={paiement.id}")


# ─── Reçu de paiement (PDF) ─────────────────────────────────────────────────

@require_permission('accounts.encaisser_prestation')
def prestation_recu_pdf(request, id):
    paiement = get_object_or_404(
        Paiement_prestation.objects.select_related('facture__client', 'caissier'), id=id
    )
    header_left, header_right = _facturation_header_lines(request.user)
    html_string = render_to_string('accounts/facturation/recu_pdf.html', {
        'paiement': paiement,
        'facture': paiement.facture,
        'header_left': header_left,
        'header_right': header_right,
        'favicon_data_uri': _pdf_logo_data_uri(),
    })
    pdf_file = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    # attachment : telechargement declenche sans quitter facture_detail.html.
    response['Content-Disposition'] = f'attachment; filename="recu_{paiement.numero_recu}.pdf"'
    return response


# ─── Historique des encaissements ──────────────────────────────────────────

@require_permission('accounts.encaisser_prestation')
def prestation_historique(request):
    paiements = Paiement_prestation.objects.select_related('facture__client', 'caissier').order_by('-date_paiement')

    q = request.GET.get('q', '').strip()
    if q:
        paiements = paiements.filter(
            Q(numero_recu__icontains=q) |
            Q(facture__numero__icontains=q) |
            Q(facture__client__nom__icontains=q) |
            Q(facture__client__raison_sociale__icontains=q)
        )

    paginator = Paginator(paiements, 10)
    page = request.GET.get('page')
    paiements = paginator.get_page(page)

    return render(request, 'accounts/facturation/historique.html', {
        'paiements': paiements,
        'q': q,
    })