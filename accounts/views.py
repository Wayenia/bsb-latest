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
        serializer = UserRegisterSerializer(data=request.POST)

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
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.shortcuts import render, redirect
def user_login(request):

    # ── Déjà connecté → rediriger directement ────────────────────────────
    if request.user.is_authenticated:
        return redirect('courses:redirect_to_dashboard')  # ← une seule ligne, ta vue gère tout

    # ── Pas encore connecté ───────────────────────────────────────────────
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            messages.error(request, "Veuillez renseigner tous les champs.")
            return render(request, 'accounts/login.html', {'username': username})

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
            return render(request, 'accounts/login.html', {'username': username})

        if not user.is_active:
            messages.error(request, "Votre compte est désactivé. Contactez l'administrateur.")
            return render(request, 'accounts/login.html', {'username': username})

        # Authentification réussie
        login(request, user)
        messages.success(request, f"Bienvenue {user.prenom} {user.nom} !")

        return redirect('courses:redirect_to_dashboard')  # ← ta vue gère tout

    return render(request, 'accounts/login.html')

# LOGOUT
def user_logout(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('accounts:login')


# ─── Profil (self-service, tous rôles) ─────────────────────────────────────

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
        form = form_class(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Vos informations ont été mises à jour avec succès.")
            return redirect('accounts:mon_profil')
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
            return redirect('accounts:mon_profil')
        messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = PasswordChangeForm(request.user)

    for field in form.fields.values():
        field.widget.attrs.setdefault('class', champ_classes)

    return render(request, 'accounts/changer_mot_de_passe.html', {'form': form})


# HELPER
# def _redirect_to_dashboard(user, request):  # ← ajouter request
#     if user.user_type == 'eleve':
#         return redirect('courses:student_dashboard')
    
#     elif user.user_type == 'formateur':
#         return redirect('courses:teacher_dashboard')
    
#     elif user.user_type == 'admin':
#         return redirect('bsb_admin:admin_dashboard')
    
#     elif user.user_type == 'membre':
#         try:
#             membre = user.membreadministration
#             if membre.structure:
#                 return redirect('courses:member_dashboard', centre_id=membre.structure_id)
#             else:
#                 return redirect('courses:member_dashboard_direction', direction_id=membre.direction_id)
#         except Exception:
#             messages.error(request, "Profil membre introuvable.")  # ← request ajouté
#             return redirect('accounts:login')
    
#     else:
#         if user.is_superuser:
#             return redirect('bsb_admin:admin_dashboard')
#         return redirect('accounts:login')


############### MODULE FACTURATION ET PRESTATION (DAF) #############

from decimal import Decimal, InvalidOperation

import base64
import os

from django.conf import settings
from django.db.models import Q
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
    ClientPrestationForm, PrestationQuickForm, FactureForm,
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
            # Retour sur le formulaire de création (page rafraîchie, prête pour
            # une nouvelle facture) avec le PDF déclenché automatiquement en
            # téléchargement (voir le script de facture_form.html).
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
    # Retour sur la page de la facture (état à jour : reste dû, historique des
    # paiements) avec le reçu déclenché automatiquement en téléchargement
    # (voir le script de facture_detail.html qui lit ce paramètre).
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
    # "attachment" : déclenché automatiquement en téléchargement depuis
    # facture_detail.html sans quitter/naviguer hors de la page (voir le
    # script qui pointe window.location vers cette URL après un encaissement).
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