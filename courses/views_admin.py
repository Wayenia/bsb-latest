from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils.http import url_has_allowed_host_and_scheme
import qrcode
from django.db.models import Q, Sum, Count
from accounts.models import Utilisateur, Formateur, MembreAdministration
from .forms import AgentForm
from courses.models import TypeFrais, TrancheFrais
from courses.forms import TypeFraisForm, TrancheFraisFormSet
from django.utils import timezone
from .permissions import require_permission
from .models import (
    Direction_reg, Filiere, CentreFormation, Module, 
    Frais, Cours, Inscription, Paiement, CentreEtFiliere,PieceJointeInscription,
    DocumentEleve,AnneeScolaire,Dette
)
from .forms import (
    DirectionRegForm, FiliereForm, CentreFormationForm, ModuleForm,
    FraisForm, CoursForm, InscriptionForm, PaiementForm, PaiementAdminForm, CentreEtFiliereForm,
    PieceJointeFormSet,FraisFormSet,AnneeScolaireForm, EleveForm
)
from accounts.models import Eleve,Formateur
from .admin_filters import FormationFilter,FiliereFilter,SubscriptionFilter
from django.db.models import Sum
from .views import _get_scope


def _filiere_modules_map():
    """{filiere_id: [{id, nom_module}, ...]} pour filtrer côté client le select Module selon le métier choisi."""
    mapping = {}
    for filiere in Filiere.objects.filter(is_active=True).prefetch_related('modules'):
        mapping[filiere.id] = [
            {'id': m.id, 'nom': m.nom_module} for m in filiere.modules.all()
        ]
    return mapping


def _agent_in_scope(agent, centres_qs):
    """True si cet agent (Formateur ou MembreAdministration) appartient à l'un des centres du périmètre donné."""
    centre_ids = list(centres_qs.values_list("id", flat=True))
    membre = getattr(agent, 'membreadministration', None)
    if membre and membre.structure_id in centre_ids:
        return True
    formateur = getattr(agent, 'formateur', None)
    if formateur and formateur.centre_id in centre_ids:
        return True
    return False


# DASHBOARD
@require_permission('courses.voir_statistiques')
def admin_dashboard(request):
    stats = {
        'total_centers': CentreFormation.objects.count(),
        'total_fields': Filiere.objects.count(),
        'total_subscriptions': Inscription.objects.count(),
        'total_directions': Direction_reg.objects.count(),
        'total_students':Eleve.objects.count(),
        'total_teachers':Formateur.objects.count()
    }
    active_careers = (
        CentreEtFiliere.objects
        .filter(is_active=True)
        .select_related('centre', 'filiere', 'annee_prog')
        .prefetch_related('frais_set')
        .annotate(total_frais=Sum('frais__montant'))
        .order_by('-date_lancement')
    )
    context = {
        'active_careers': active_careers,
        'stats': stats,  # ← fusionné ici
    }
    return render(request, "admin/admin_dashboard/dashboard.html", context)


#  DIRECTION CRUD
@require_permission('courses.gerer_directions')
def direction_list(request):
    directions = Direction_reg.objects.all().order_by('-date_modification')

    search = request.GET.get('q', '').strip()
    if search:
        directions = directions.filter(nom_direction__icontains=search)

    paginator = Paginator(directions, 10)
    page = request.GET.get('page')
    directions = paginator.get_page(page)
    return render(request, 'admin/direction/direction_list.html', {'directions': directions, 'search': search})

@require_permission('courses.gerer_directions')
def direction_create(request):
    if request.method == 'POST':
        form = DirectionRegForm(request.POST)
        if form.is_valid():
            direction = form.save()
            messages.success(request, f'Direction "{direction.nom_direction}" créée avec succès!')
            return redirect('bsb_admin:direction_list')
    else:
        form = DirectionRegForm()
    return render(request, 'admin/direction/direction_form.html', {'form': form, 'action': 'Créer'})


@require_permission('courses.gerer_directions')
def direction_import_template(request):
    from .bulk_import_registry import SPEC_DIRECTION
    from .bulk_import.views_helpers import render_import_template
    return render_import_template(request, SPEC_DIRECTION)


@require_permission('courses.gerer_directions')
def direction_import(request):
    from .bulk_import_registry import SPEC_DIRECTION
    from .bulk_import.views_helpers import handle_import_upload
    return handle_import_upload(request, SPEC_DIRECTION)


@require_permission('courses.gerer_directions')
def direction_update(request, id):
    direction = get_object_or_404(Direction_reg, id=id)
    if request.method == 'POST':
        form = DirectionRegForm(request.POST, instance=direction)
        if form.is_valid():
            direction = form.save()
            messages.success(request, f'Direction "{direction.nom_direction}" modifiée avec succès!')
            return redirect('bsb_admin:direction_list')
    else:
        form = DirectionRegForm(instance=direction)
    return render(request, 'admin/direction/direction_form.html', {'form': form, 'action': 'Modifier', 'object': direction})

@require_permission('courses.gerer_directions')
def direction_delete(request, id):
    direction = get_object_or_404(Direction_reg, id=id)
    if request.method == 'POST':
        nom = direction.nom_direction
        direction.delete()
        messages.success(request, f'Direction "{nom}" supprimée avec succès!')
        return redirect('bsb_admin:direction_list')
    return render(request, 'admin/direction/direction_confirm_delete.html', {'object': direction})


# FIELD CRUD
@require_permission('courses.gerer_metiers')
def field_list(request):
    fields = Filiere.objects.all().order_by('-date_modification')
    f=FiliereFilter(request.GET,queryset=fields)
    paginator = Paginator(f.qs, 10)
    page = request.GET.get('page')
    fields = paginator.get_page(page)
    return render(request, 'admin/field/list.html', {'fields': fields,'filter':f})

@require_permission('courses.gerer_metiers')
def field_create(request):
    if request.method == 'POST':
        form = FiliereForm(request.POST)
        if form.is_valid():
            field = form.save()
            next_url=request.GET.get('next') or request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            messages.success(request, f'Filière "{field.nom_filiere}" créée avec succès!')
            return redirect('bsb_admin:field_list')
    else:
        form = FiliereForm()
    return render(request, 'admin/field/form.html', {'form': form, 'action': 'Créer'})

@require_permission('courses.gerer_metiers')
def field_update(request, id):
    field = get_object_or_404(Filiere, id=id)
    if request.method == 'POST':
        form = FiliereForm(request.POST, request.FILES, instance=field)
        if form.is_valid():
            field = form.save()
            from .views import _process_metier_modules
            _process_metier_modules(request, field, form)
            messages.success(request, f'Filière "{field.nom_filiere}" modifiée avec succès!')
            return redirect('bsb_admin:field_list')
    else:
        form = FiliereForm(instance=field)
    return render(request, 'member/filiere/metier_form.html', {'form': form, 'action': 'Modifier', 'object': field})

@require_permission('courses.gerer_metiers')
def field_delete(request, id):
    field = get_object_or_404(Filiere, id=id)
    if request.method == 'POST':
        nom = field.nom_filiere
        field.delete()
        messages.success(request, f'Filière "{nom}" supprimée avec succès!')
        return redirect('bsb_admin:field_list')
    return render(request, 'member/filiere/confirm_delete.html', {'object': field})


# CENTER CRUD
@require_permission('courses.gerer_centres')
def center_list(request):
    q = request.GET.get('q', '').strip()
    direction_id = request.GET.get('direction', '').strip()
    niveau = request.GET.get('niveau', '').strip()

    qs = (
        CentreFormation.objects
        .filter(pk__in=_get_scope(request.user)[0])
        .select_related('direction', 'province')
        .order_by('nom_centre')
    )

    if q:
        qs = qs.filter(
            Q(nom_centre__icontains=q) |
            Q(adresse__icontains=q) |
            Q(province__nom_province__icontains=q)  # ← adapter si le champ s'appelle autrement
        ).distinct()

    if direction_id and direction_id.isdigit():
        qs = qs.filter(direction_id=int(direction_id))

    if niveau and niveau.isdigit():
        qs = qs.filter(niveau_centre=int(niveau))
    else:
        niveau = ''

    try:
        page_number = int(request.GET.get('page', 1))
        if page_number < 1:
            page_number = 1
    except (ValueError, TypeError):
        page_number = 1

    paginator = Paginator(qs, 10)
    centers = paginator.get_page(page_number)

    directions = Direction_reg.objects.all().order_by('nom_direction')

    niveaux = (
        CentreFormation.objects
        .exclude(niveau_centre__isnull=True)
        .values_list('niveau_centre', flat=True)
        .distinct()
        .order_by('niveau_centre')
    )

    return render(request, 'admin/center/list.html', {
        'centers': centers,
        'q': q,
        'direction_id': direction_id,
        'niveau': niveau,
        'directions': directions,
        'niveaux': niveaux,
    })

@require_permission('courses.gerer_centres')
def center_create(request):
    direction_queryset = _get_scope(request.user)[1]
    if request.method == 'POST':
        form = CentreFormationForm(request.POST, direction_queryset=direction_queryset)
        if form.is_valid():
            center = form.save()
            next_url=request.GET.get('next') or request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            messages.success(request, f'Centre "{center.nom_centre}" créé avec succès!')
            return redirect('bsb_admin:center_list')
    else:
        form = CentreFormationForm(direction_queryset=direction_queryset)
    return render(request, 'admin/center/form.html', {'form': form, 'action': 'Créer'})


@require_permission('courses.gerer_centres')
def center_import_template(request):
    from .bulk_import_registry import SPEC_CENTRE
    from .bulk_import.views_helpers import render_import_template
    return render_import_template(request, SPEC_CENTRE)


@require_permission('courses.gerer_centres')
def center_import(request):
    from .bulk_import_registry import SPEC_CENTRE
    from .bulk_import.views_helpers import handle_import_upload
    return handle_import_upload(request, SPEC_CENTRE)


@require_permission('courses.gerer_centres')
def center_update(request, id):
    centres_qs, direction_queryset, _ = _get_scope(request.user)
    center = get_object_or_404(CentreFormation, id=id, pk__in=centres_qs)
    if request.method == 'POST':
        form = CentreFormationForm(request.POST, instance=center, direction_queryset=direction_queryset)
        if form.is_valid():
            center = form.save()
            messages.success(request, f'Centre "{center.nom_centre}" modifié avec succès!')
            return redirect('bsb_admin:center_list')
    else:
        form = CentreFormationForm(instance=center, direction_queryset=direction_queryset)
    return render(request, 'admin/center/form.html', {'form': form, 'action': 'Modifier', 'object': center})

@require_permission('courses.gerer_centres')
def center_delete(request, id):
    center = get_object_or_404(CentreFormation, id=id, pk__in=_get_scope(request.user)[0])
    if request.method == 'POST':
        nom = center.nom_centre
        center.delete()
        messages.success(request, f'Centre "{nom}" supprimé avec succès!')
        return redirect('bsb_admin:center_list')
    return render(request, 'admin/center/confirm_delete.html', {'object': center})


# MODULE CRUD
@require_permission('courses.gerer_modules')
def module_list(request):
    modules = Module.objects.prefetch_related('filieres').all().order_by('-date_creation')

    q = request.GET.get('q', '').strip()
    if q:
        modules = modules.filter(
            Q(nom_module__icontains=q) |
            Q(filieres__nom_filiere__icontains=q)
        ).distinct()

    paginator = Paginator(modules, 10)
    page = request.GET.get('page')
    modules = paginator.get_page(page)
    return render(request, 'admin/module/list.html', {'modules': modules, 'q': q})

@require_permission('courses.gerer_modules')
def module_create(request):
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save()
            messages.success(request, f'Module "{module.nom_module}" créé avec succès!')
            return redirect('bsb_admin:module_list')
    else:
        initial = {}
        filiere_id = request.GET.get('filiere')
        if filiere_id:
            initial['filieres'] = [filiere_id]
        form = ModuleForm(initial=initial)
    return render(request, 'admin/module/form.html', {'form': form, 'action': 'Créer'})


@require_permission('courses.gerer_modules')
def module_import_template(request):
    from .bulk_import_registry import SPEC_MODULE
    from .bulk_import.views_helpers import render_import_template
    return render_import_template(request, SPEC_MODULE)


@require_permission('courses.gerer_modules')
def module_import(request):
    from .bulk_import_registry import SPEC_MODULE
    from .bulk_import.views_helpers import handle_import_upload
    return handle_import_upload(request, SPEC_MODULE)


@require_permission('courses.gerer_modules')
def module_update(request, id):
    module = get_object_or_404(Module, id=id)
    if request.method == 'POST':
        form = ModuleForm(request.POST, instance=module)
        if form.is_valid():
            module = form.save()
            messages.success(request, f'Module "{module.nom_module}" modifié avec succès!')
            return redirect('bsb_admin:module_list')
    else:
        form = ModuleForm(instance=module)
    return render(request, 'admin/module/form.html', {'form': form, 'action': 'Modifier', 'object': module})

@require_permission('courses.gerer_modules')
def module_delete(request, id):
    module = get_object_or_404(Module, id=id)
    if request.method == 'POST':
        nom = module.nom_module
        module.delete()
        messages.success(request, f'Module "{nom}" supprimé avec succès!')
        return redirect('bsb_admin:module_list')
    return render(request, 'admin/module/confirm_delete.html', {'object': module})


# FEE CRUD
@require_permission('courses.gerer_frais')
def fees_list(request):
    fees = Frais.objects.select_related(
        'formation',
        'formation__centre',
        'formation__filiere',
        'type_frais'
    ).all().order_by('-date_creation')

    q = request.GET.get('q', '').strip()
    if q:
        fees = fees.filter(
            Q(formation__centre__nom_centre__icontains=q) |
            Q(formation__filiere__nom_filiere__icontains=q) |
            Q(type_frais__libelle__icontains=q)
        )

    paginator = Paginator(fees, 10)
    page = request.GET.get('page')
    fees = paginator.get_page(page)

    return render(request, 'admin/fees/list.html', {'fees': fees, 'q': q})

@require_permission('courses.gerer_frais')
def fees_create(request):
    if request.method == 'POST':
        form = FraisForm(request.POST)
        if form.is_valid():
            fees = form.save()
            messages.success(request, f'Frais "{fees.type_frais}" créé avec succès!')
            return redirect('bsb_admin:fees_list')
    else:
        form = FraisForm()
    return render(request, 'admin/fees/form.html', {'form': form, 'action': 'Créer'})

@require_permission('courses.gerer_frais')
def fees_update(request, id):
    fees = get_object_or_404(Frais, id=id)
    if request.method == 'POST':
        form = FraisForm(request.POST, instance=fees)
        if form.is_valid():
            fees = form.save()
            messages.success(request, f'Frais "{fees.type_frais}" modifié avec succès!')
            return redirect('bsb_admin:fees_list')
    else:
        form = FraisForm(instance=fees)
    return render(request, 'admin/fees/form.html', {'form': form, 'action': 'Modifier', 'object': fees})

@require_permission('courses.gerer_frais')
def fees_delete(request, id):
    fees = get_object_or_404(Frais, id=id)
    if request.method == 'POST':
        libelle = fees.type_frais
        fees.delete()
        messages.success(request, f'Frais "{libelle}" supprimé avec succès!')
        return redirect('bsb_admin:fees_list')
    return render(request, 'admin/fees/confirm_delete.html', {'object': fees})


# COURSE CRUD
@require_permission('courses.gerer_modules')
def course_list(request):
    course = Cours.objects.select_related('module', 'module__filiere').all().order_by('-date_creation')

    q = request.GET.get('q', '').strip()
    if q:
        course = course.filter(
            Q(libelle_cours__icontains=q) |
            Q(module__nom_module__icontains=q) |
            Q(module__filiere__nom_filiere__icontains=q)
        )

    paginator = Paginator(course, 10)
    page = request.GET.get('page')
    course = paginator.get_page(page)
    return render(request, 'admin/course/list.html', {'course': course, 'q': q})

@require_permission('courses.gerer_modules')
def course_create(request):
    if request.method == 'POST':
        form = CoursForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, f'Cours "{course.libelle_cours}" créé avec succès!')
            return redirect('bsb_admin:course_list')
    else:
        form = CoursForm()
    return render(request, 'admin/course/form.html', {'form': form, 'action': 'Créer'})


@require_permission('courses.gerer_modules')
def course_import_template(request):
    from .bulk_import_registry import SPEC_COURS
    from .bulk_import.views_helpers import render_import_template
    return render_import_template(request, SPEC_COURS)


@require_permission('courses.gerer_modules')
def course_import(request):
    from .bulk_import_registry import SPEC_COURS
    from .bulk_import.views_helpers import handle_import_upload
    return handle_import_upload(request, SPEC_COURS)


@require_permission('courses.gerer_modules')
def course_update(request, id):
    course = get_object_or_404(Cours, id=id)
    if request.method == 'POST':
        form = CoursForm(request.POST, instance=course)
        if form.is_valid():
            course = form.save()
            messages.success(request, f'Cours "{course.libelle_cours}" modifié avec succès!')
            return redirect('bsb_admin:course_list')
    else:
        form = CoursForm(instance=course)
    return render(request, 'admin/course/form.html', {'form': form, 'action': 'Modifier', 'object': course})

@require_permission('courses.gerer_modules')
def course_delete(request, id):
    course = get_object_or_404(Cours, id=id)
    if request.method == 'POST':
        libelle = course.libelle_cours
        course.delete()
        messages.success(request, f'Cours "{libelle}" supprimé avec succès!')
        return redirect('bsb_admin:course_list')
    return render(request, 'admin/course/confirm_delete.html', {'object': course})


# SUBSCRIPTION CRUD Faudra peut etre filter par année aussi cça sera bien pour les staistiques
@require_permission('courses.voir_inscriptions')
def subscription_list(request):
    subscriptions = Inscription.objects.select_related('eleve', 'formation')\
    .exclude(statut="en-cours")\
    .order_by('-date_inscription')
    centres_qs, _, scope = _get_scope(request.user)
    if scope != "global":
        centre_ids = list(centres_qs.values_list("id", flat=True))
        subscriptions = subscriptions.filter(formation__centre_id__in=centre_ids)
    # total_incrit_annee=Inscription.objects.filter(statut="valide").count()
    # total_valide=Inscription.objects.filter()
    f=SubscriptionFilter(request.GET,queryset=subscriptions)
    paginator = Paginator(f.qs, 10)
    page = request.GET.get('page')
    subscriptions = paginator.get_page(page)
    return render(request, 'admin/subscription/list.html', {'subscriptions': subscriptions, 'filter': f})

@require_permission('courses.valider_inscription')
def subscription_create(request):
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            inscription = form.save()
            messages.success(request, 'Inscription créée avec succès!')
            return redirect('bsb_admin:subscription_list')
    else:
        form = InscriptionForm()
    return render(request, 'admin/subscription/form.html', {'form': form, 'action': 'Créer'})


@require_permission('courses.valider_inscription')
def subscription_update(request, id):
    subscription = get_object_or_404(Inscription, id=id)
    if request.method == 'POST':
        form = InscriptionForm(request.POST, instance=subscription)
        if form.is_valid():
            subscription = form.save()
            messages.success(request, 'Inscription modifiée avec succès!')
            return redirect('bsb_admin:subscription_list')
    else:
        form = InscriptionForm(instance=subscription)
    return render(request, 'admin/subscription/form.html', {'form': form, 'action': 'Modifier', 'object': subscription})

@require_permission('courses.valider_inscription')
def subscription_delete(request, id):
    subscription = get_object_or_404(Inscription, id=id)
    if request.method == 'POST':
        subscription.delete()
        messages.success(request, 'Inscription supprimée avec succès!')
        return redirect('bsb_admin:subscription_list')
    return render(request, 'admin/subscription/confirm_delete.html', {'object': subscription})

#Detail d'insciption
# Ici je veux la liste des pièces jointes que l'elève à renseigner pour une inscription
@require_permission('courses.voir_inscriptions')
def subscription_detail(request,id):
    subscription=get_object_or_404(Inscription.objects.select_related('eleve','formation__centre'),id=id)
    centres_qs, _, scope = _get_scope(request.user)
    if scope != "global" and (not subscription.formation_id or not centres_qs.filter(pk=subscription.formation.centre_id).exists()):
        raise PermissionDenied("Vous n'avez pas accès à cette inscription.")
    eleve_docs=DocumentEleve.objects.select_related('piece_requise').filter(inscription=subscription)
    return render(request,'admin/subscription/inscription_detail.html',{'detail':subscription,'eleve_docs':eleve_docs})

#Permet de gére l'inscription en fait 
@require_permission('courses.valider_inscription')
def gerer_inscription(request,id):
     subscription=get_object_or_404(Inscription.objects.select_related('formation__centre','eleve'),id=id)
     centres_qs, _, scope = _get_scope(request.user)
     if scope != "global" and (not subscription.formation_id or not centres_qs.filter(pk=subscription.formation.centre_id).exists()):
         raise PermissionDenied("Vous n'avez pas accès à cette inscription.")
     if request.method == 'POST':
         action=request.POST.get('action') 
         if action == 'valide':
             subscription.statut='valide'
             subscription.date_validation=timezone.now()
             subscription.motif_rejet=None
             messages.success(request, "Inscription validée et dettes générées.")
         subscription.save()
     return redirect("bsb_admin:subscription_en_cours")

@require_permission('courses.rejeter_inscription')
def rejeter_inscription(request,id):
    subscription=get_object_or_404(Inscription.objects.select_related('formation__centre','eleve'),id=id)
    centres_qs, _, scope = _get_scope(request.user)
    if scope != "global" and (not subscription.formation_id or not centres_qs.filter(pk=subscription.formation.centre_id).exists()):
        raise PermissionDenied("Vous n'avez pas accès à cette inscription.")

    if request.method == 'POST':
        motif=request.POST.get('motif')
        if not motif:
            messages.error(request,"Veuillez renseigner le motif du rejet du dossier ")
            return redirect("bsb_admin:subscription_en_cours")
        
        subscription.statut = "rejete"
        subscription.motif_rejet = motif
        subscription.date_validation = timezone.now()
        subscription.save()
        messages.warning(request, "Inscription rejetée")
        return redirect("bsb_admin:subscription_en_cours")

    return render(request, "admin/subscription/rejeter_inscription.html", {"subscription": subscription})

#Fonction de récupération des insciptions qui ont non validés 
@require_permission('courses.voir_inscriptions')
def inscription__en_cours_view(request):
    subscriptions=Inscription.objects.filter(statut="en_cours").select_related('eleve','formation').order_by('-date_inscription')
    inscrit_non_valide_qs = Inscription.objects.filter(statut="en_cours")
    centres_qs, _, scope = _get_scope(request.user)
    if scope != "global":
        centre_ids = list(centres_qs.values_list("id", flat=True))
        subscriptions = subscriptions.filter(formation__centre_id__in=centre_ids)
        inscrit_non_valide_qs = inscrit_non_valide_qs.filter(formation__centre_id__in=centre_ids)

    recherche = request.GET.get('recherche', '').strip()
    if recherche:
        subscriptions = subscriptions.filter(
            Q(eleve__nom__icontains=recherche) |
            Q(eleve__prenom__icontains=recherche) |
            Q(eleve__matricule__icontains=recherche)
        )

    paginator=Paginator(subscriptions,10)
    page=request.GET.get('page')
    subscriptions = paginator.get_page(page)
    inscrit_non_valide=inscrit_non_valide_qs.count()
    return render(request,'admin/subscription/validate_inscription.html',{
        'subscriptions':subscriptions,
        'numbers':inscrit_non_valide,
        'recherche': recherche,
    })

# PAYMENT CRUD

@require_permission('courses.gerer_paiements')
def payment_list(request):
    # Une inscription = une ligne, on filtre celles qui ont au moins un paiement
    inscriptions = Inscription.objects.select_related(
        'eleve',
        'formation',
        'formation__centre',
        'formation__filiere',
        'annee_scolaire',
    ).prefetch_related(
        'dettes',
        'dettes__paiements',
        'dettes__frais_formation',
        'dettes__frais_formation__type_frais',
    ).filter(
        dettes__paiements__isnull=False
    ).distinct().order_by('-date_inscription')

    centres_qs, _, scope = _get_scope(request.user)
    if scope != "global":
        centre_ids = list(centres_qs.values_list("id", flat=True))
        inscriptions = inscriptions.filter(formation__centre_id__in=centre_ids)

    q = request.GET.get('q', '').strip()
    if q:
        inscriptions = inscriptions.filter(
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q) |
            Q(eleve__matricule__icontains=q) |
            Q(dettes__paiements__numero_quittance__icontains=q)
        ).distinct()

    paginator = Paginator(inscriptions, 10)
    page = request.GET.get('page')
    inscriptions_page = paginator.get_page(page)

    # Re-calcul après pagination (les objets sont déjà prefetch, pas de requêtes supplémentaires)
    for insc in inscriptions_page:
        insc.total_du   = sum(d.montant_total for d in insc.dettes.all())
        insc.total_paye = sum(
            p.montant_paiement
            for d in insc.dettes.all()
            for p in d.paiements.all()
        )
        insc.reste = insc.total_du - insc.total_paye

    return render(request, 'admin/payment/list.html', {'inscriptions': inscriptions_page, 'q': q})

@require_permission('courses.encaisser_paiement')
def payment_create(request):
    if request.method == 'POST':
        form = PaiementAdminForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.cree_par = request.user
            payment.save()
            messages.success(request, 'Paiement enregistré avec succès!')
            return redirect('bsb_admin:payment_list')
    else:
        form = PaiementAdminForm()
    return render(request, 'admin/payment/form.html', {'form': form, 'action': 'Créer'})


@require_permission('courses.encaisser_paiement')
def payment_update(request, id):
    payment = get_object_or_404(Paiement, id=id)
    if request.method == 'POST':
        form = PaiementAdminForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save()
            messages.success(request, 'Paiement modifié avec succès!')
            return redirect('bsb_admin:payment_list')
    else:
        form = PaiementAdminForm(instance=payment)
    return render(request, 'admin/payment/form.html', {'form': form, 'action': 'Modifier', 'object': payment})


@require_permission('courses.gerer_paiements')
def payment_delete(request, id):
    payment = get_object_or_404(Paiement, id=id)
    if request.method == 'POST':
        payment.delete()
        messages.success(request, 'Paiement supprimé avec succès!')
        return redirect('bsb_admin:payment_list')
    return render(request, 'admin/payment/confirm_delete.html', {'object': payment})

#CRUD PROGRAMMING

@require_permission('courses.gerer_programmations')
def programming_list(request):
    centres_qs, _, _ = _get_scope(request.user)
    programs=CentreEtFiliere.objects.filter(centre__in=centres_qs).select_related('centre','filiere').order_by('-date_creation')
    f=FormationFilter(request.GET,queryset=programs)
    paginator=Paginator(f.qs,10)
    page=request.GET.get('page')
    programs=paginator.get_page(page)
    return render(request,'admin/programming/list.html',{'programs':programs,'filter':f})

from .models import TypeFrais, PieceJointeInscription  # assure-toi des imports

@require_permission('courses.gerer_programmations')
def programming_create(request):
    if not AnneeScolaire.objects.exists():
        messages.warning(request, "Aucune année scolaire disponible. Veuillez en créer une d'abord.")
        return redirect('bsb_admin:annee_create')

    centres_qs, _, _ = _get_scope(request.user)

    if request.method == 'POST':
        form = CentreEtFiliereForm(request.POST, request.FILES, centre_queryset=centres_qs)
        frais_formset = FraisFormSet(request.POST, prefix='frais')
        piece_jointe_formset = PieceJointeFormSet(request.POST, prefix='piece')

        if form.is_valid() and frais_formset.is_valid() and piece_jointe_formset.is_valid():
            programming = form.save()
            frais_formset.instance = programming
            frais_formset.save()
            piece_jointe_formset.instance = programming
            piece_jointe_formset.save()
            messages.success(request, 'Programmation ajoutée avec succès')
            return redirect('bsb_admin:programming_list')
    else:
        form = CentreEtFiliereForm(centre_queryset=centres_qs)
        frais_formset = FraisFormSet(prefix='frais')
        piece_jointe_formset = PieceJointeFormSet(prefix='piece')

    return render(request, 'admin/programming/form.html', {
        'form': form,
        'frais_formset': frais_formset,
        'piece_jointe_formset': piece_jointe_formset,
        'action': 'Créer',
        # ↓ Les deux lignes ajoutées
        'type_frais_options': TypeFrais.objects.all(),
        'type_piece_options': PieceJointeInscription._meta.get_field('type_piece').choices,
    })


@require_permission('courses.gerer_programmations')
def update_pregramming(request, id):
    centres_qs, _, _ = _get_scope(request.user)
    program = get_object_or_404(CentreEtFiliere, id=id, centre__in=centres_qs)

    if request.method == 'POST':
        form = CentreEtFiliereForm(request.POST, request.FILES, instance=program, centre_queryset=centres_qs)
        frais_formset = FraisFormSet(request.POST, instance=program, prefix='frais')
        piece_jointe_formset = PieceJointeFormSet(request.POST, instance=program, prefix='piece')

        if form.is_valid() and frais_formset.is_valid() and piece_jointe_formset.is_valid():
            program = form.save()
            frais_formset.instance = program
            frais_formset.save()
            piece_jointe_formset.instance = program
            piece_jointe_formset.save()
            messages.success(request, 'Modification réussie avec succès')
            return redirect('bsb_admin:programming_list')
    else:
        form = CentreEtFiliereForm(instance=program, centre_queryset=centres_qs)
        frais_formset = FraisFormSet(instance=program, prefix='frais')
        piece_jointe_formset = PieceJointeFormSet(instance=program, prefix='piece')

    return render(request, 'admin/programming/form.html', {
        'action': 'Modifier',
        'form': form,
        'frais_formset': frais_formset,
        'piece_jointe_formset': piece_jointe_formset,
        # ↓ Les deux lignes ajoutées
        'type_frais_options': TypeFrais.objects.all(),
        'type_piece_options': PieceJointeInscription._meta.get_field('type_piece').choices,
    })
@require_permission('courses.gerer_programmations')
def programming_delete(request, id):
    centres_qs, _, _ = _get_scope(request.user)
    program = get_object_or_404(CentreEtFiliere, id=id, centre__in=centres_qs)
    if request.method == 'POST':
        program.delete()
        messages.success(request, 'Programme supprimé avec succès!')
        return redirect('bsb_admin:programming_list')
    return render(request, 'admin/programming/confirm_delete.html', {'object': program})

@require_permission('courses.gerer_annees')
def annee_create(request):
    if request.method == 'POST':
        form=AnneeScolaireForm(request.POST)
        if form.is_valid():
            annee=form.save()
            messages.success(request, 'Année enregistré avec succès!')
            return redirect('bsb_admin:annee_list')
    else:
        form = AnneeScolaireForm()
    return render(request, 'admin/annee_scolaire/form.html', {'form': form, 'action': 'Créer'})

#def annee_list(request):
#    return render(request,'admin/annee_scolaire/list.html')

ALL_AGENT_TYPES = [
    'formateur',
    'dir',
    'gestionnaire',
    'agent_comptable',
    'caissier',
    'deps',
    'admin',
    'daf',
    'membre',
]

TYPE_LABELS = [
    ('formateur',       'Formateur'),
    ('dir',             'Directeur inter-régional'),
    ('gestionnaire',    'Directeur de centre'),
    ('agent_comptable', 'Agent comptable'),
    ('caissier',        'Caissière / Caissier'),
    ('deps',            'Direction des Études, de la Planification et des Statistiques'),
    ('admin',           'Administrateur'),
    ('daf',             'Directeur Administratif et Financier'),
    ('membre',          "Membre de l'administration"),
]


@require_permission('accounts.gerer_agents')
def agent_list(request):
    q         = request.GET.get('q', '').strip()
    user_type = request.GET.get('type', '').strip()

    qs = Utilisateur.objects.filter(
        user_type__in=ALL_AGENT_TYPES
    ).order_by('nom', 'prenom')

    centres_qs, _, scope = _get_scope(request.user)
    if scope != "global":
        centre_ids = list(centres_qs.values_list("id", flat=True))
        qs = qs.filter(
            Q(membreadministration__structure_id__in=centre_ids) |
            Q(formateur__centre_id__in=centre_ids)
        )

    if q:
        qs = qs.filter(
            Q(nom__icontains=q)      |
            Q(prenom__icontains=q)   |
            Q(email__icontains=q)    |
            Q(username__icontains=q)
        )
    if user_type:
        qs = qs.filter(user_type=user_type)

    paginator = Paginator(qs, 10)
    agents    = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/rh/agent_list.html', {
        'agents':       agents,
        'q':            q,
        'user_type':    user_type,
        'type_choices': TYPE_LABELS,
    })


@require_permission('accounts.gerer_agents')

def agent_create(request):
    if request.method == 'POST':
        form = AgentForm(request.POST)
        if form.is_valid():

            username = form.cleaned_data.get("username")
            if Utilisateur.objects.filter(username=username).exists():
                messages.error(request, "Ce nom d'utilisateur est déjà utilisé.")
                return render(request, 'admin/rh/agent_form.html', {
                    'form': form,
                    'action': 'Créer',
                    'filiere_modules_json': _filiere_modules_map(),
                })

            agent = form.save()
            messages.success(request, f'Agent « {agent.nom} {agent.prenom} » créé avec succès !')
            return redirect('bsb_admin:agent_list')
    else:
        form = AgentForm()

    return render(request, 'admin/rh/agent_form.html', {
        'form': form,
        'action': 'Créer',
        'filiere_modules_json': _filiere_modules_map(),
    })


@require_permission('accounts.gerer_agents')
def agent_import_template(request):
    from .bulk_import_registry import SPEC_AGENT
    from .bulk_import.views_helpers import render_import_template
    return render_import_template(request, SPEC_AGENT)


@require_permission('accounts.gerer_agents')
def agent_import(request):
    from .bulk_import_registry import SPEC_AGENT
    from .bulk_import.views_helpers import handle_import_upload
    return handle_import_upload(request, SPEC_AGENT)


@require_permission('accounts.gerer_agents')
def agent_update(request, id):
    agent = get_object_or_404(Utilisateur, id=id, user_type__in=ALL_AGENT_TYPES)
    centres_qs, _, scope = _get_scope(request.user)
    if scope != "global" and not _agent_in_scope(agent, centres_qs):
        raise PermissionDenied("Vous n'avez pas accès à cet agent.")
    if request.method == 'POST':
        form = AgentForm(request.POST, instance=agent)
        if form.is_valid():
            agent = form.save()
            messages.success(request, f'Agent « {agent.nom} {agent.prenom} » modifié avec succès !')
            return redirect('bsb_admin:agent_list')
    else:
        form = AgentForm(instance=agent)
    return render(request, 'admin/rh/agent_form.html', {
        'form': form, 'action': 'Modifier',
        'filiere_modules_json': _filiere_modules_map(),
    })


@require_permission('accounts.gerer_agents')
def agent_delete(request, id):
    agent = get_object_or_404(Utilisateur, id=id, user_type__in=ALL_AGENT_TYPES)
    centres_qs, _, scope = _get_scope(request.user)
    if scope != "global" and not _agent_in_scope(agent, centres_qs):
        raise PermissionDenied("Vous n'avez pas accès à cet agent.")
    if request.method == 'POST':
        nom = f"{agent.nom} {agent.prenom}"
        agent.delete()
        messages.success(request, f'Agent « {nom} » supprimé avec succès !')
        return redirect('bsb_admin:agent_list')
    return render(request, 'admin/rh/agent_confirm_delete.html', {'object': agent})


# ─────────────────────────────────────────────
# GESTION DES APPRENANTS — modification complète (y compris mot de passe),
# distincte des écrans d'inscription : ici on corrige/complète le dossier
# d'un élève déjà existant (identité, contact, mot de passe oublié, etc.)
# ─────────────────────────────────────────────

@require_permission('accounts.gerer_eleves')
def eleve_list(request):
    recherche = request.GET.get('recherche', '').strip()

    qs = Eleve.objects.all().order_by('nom', 'prenom')
    if recherche:
        qs = qs.filter(
            Q(nom__icontains=recherche) |
            Q(prenom__icontains=recherche) |
            Q(numero_identifiant__icontains=recherche)
        )

    paginator = Paginator(qs, 10)
    eleves = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/eleve/list.html', {
        'eleves': eleves,
        'recherche': recherche,
    })


@require_permission('accounts.gerer_eleves')
def eleve_update(request, id):
    eleve = get_object_or_404(Eleve, id=id)
    if request.method == 'POST':
        form = EleveForm(request.POST, instance=eleve)
        if form.is_valid():
            eleve = form.save()
            messages.success(request, f'Apprenant « {eleve.nom} {eleve.prenom} » modifié avec succès !')
            return redirect('bsb_admin:eleve_list')
    else:
        form = EleveForm(instance=eleve)
    return render(request, 'admin/eleve/form.html', {'form': form, 'object': eleve})


# ─────────────────────────────────────────────
# GESTION DES PERMISSIONS — matrice rôle × action
# ─────────────────────────────────────────────

# Permissions métier affichées dans la matrice (codename, libellé, app_label).
# Volontairement une liste courte et curatée — pas les permissions Django
# auto-générées (add/change/delete/view en anglais) qui n'ont aucun sens
# pour un utilisateur non technique.
MATRIX_PERMISSIONS = [
    ('gerer_regions', "Créer/modifier/supprimer une région ou province", 'courses'),
    ('gerer_directions', "Créer/modifier/supprimer une direction inter-régionale", 'courses'),
    ('gerer_centres', "Créer/modifier/supprimer un centre de formation", 'courses'),
    ('gerer_metiers', "Créer/modifier/supprimer un métier", 'courses'),
    ('gerer_programmations', "Gérer les associations centre-métier", 'courses'),
    ('gerer_modules', "Gérer les modules et cours", 'courses'),
    ('gerer_frais', "Gérer les frais et types de frais", 'courses'),
    ('gerer_annees', "Gérer les années scolaires", 'courses'),
    ('gerer_agents', "Gérer les comptes utilisateurs", 'accounts'),
    ('gerer_eleves', "Gérer les comptes apprenants", 'accounts'),
    ('gerer_permissions', "Gérer les permissions", 'accounts'),
    ('voir_inscriptions', "Voir les candidatures", 'courses'),
    ('valider_inscription', "Valider une candidature", 'courses'),
    ('rejeter_inscription', "Rejeter une candidature", 'courses'),
    ('encaisser_paiement', "Encaisser un paiement", 'courses'),
    ('gerer_paiements', "Modifier/supprimer un paiement", 'courses'),
    ('rechercher_tous_centres', "Rechercher un apprenant dans tous les centres (paiements)", 'courses'),
    ('telecharger_pieces', "Télécharger les pièces jointes des candidats", 'courses'),
    ('voir_statistiques', "Voir les statistiques", 'courses'),
    ('gerer_statistiques_reelles', "Gérer les statistiques réelles (saisie manuelle)", 'courses'),
    ('exporter_donnees', "Exporter des données (CSV/Excel/PDF)", 'courses'),
    ('gerer_facturation', "Créer/gérer les factures de prestation", 'accounts'),
    ('valider_facture_prestation', "Valider une facture proforma en définitive", 'accounts'),
    ('encaisser_prestation', "Encaisser un paiement de prestation", 'accounts'),
]
MATRIX_CODENAMES = [codename for codename, _, _ in MATRIX_PERMISSIONS]

# Ordre d'affichage des colonnes (rôle = groupe Django), aligné sur
# accounts.Utilisateur.ROLE_GROUPS.
MATRIX_ROLES = [
    'Admin', 'Directeur Général', 'Directeur Inter-régional', 'DEPS',
    'Directeur de Centre', 'Caissier', 'Agent Comptable', 'Formateur',
    'Membre Administration', 'DAF',
]


@require_permission('accounts.gerer_permissions')
def permissions_matrix_view(request):
    from django.contrib.auth.models import Permission, Group

    groups = [Group.objects.get_or_create(name=name)[0] for name in MATRIX_ROLES]

    if request.method == 'POST':
        checked = {}  # group_id -> set(perm_id)
        for pair in request.POST.getlist('cell'):
            perm_id_str, group_id_str = pair.split(':')
            checked.setdefault(int(group_id_str), set()).add(int(perm_id_str))

        matrix_perms = Permission.objects.filter(codename__in=MATRIX_CODENAMES)
        for group in groups:
            perm_ids = checked.get(group.id, set())
            kept = list(group.permissions.exclude(codename__in=MATRIX_CODENAMES))
            newly_checked = list(matrix_perms.filter(id__in=perm_ids))
            group.permissions.set(kept + newly_checked)

        messages.success(request, "Permissions mises à jour avec succès !")
        return redirect('bsb_admin:permissions_matrix')

    permissions = list(
        Permission.objects.filter(codename__in=MATRIX_CODENAMES)
    )
    # garder l'ordre métier défini ci-dessus plutôt que l'ordre alphabétique de la BD
    perm_by_codename = {p.codename: p for p in permissions}
    ordered_permissions = [perm_by_codename[c] for c, _, _ in MATRIX_PERMISSIONS if c in perm_by_codename]

    group_perm_ids = {
        group.id: set(group.permissions.filter(codename__in=MATRIX_CODENAMES).values_list('id', flat=True))
        for group in groups
    }

    rows = []
    for perm in ordered_permissions:
        rows.append({
            'perm': perm,
            'cells': [(group, perm.id in group_perm_ids[group.id]) for group in groups],
        })

    context = {
        'roles': groups,
        'rows': rows,
    }
    return render(request, 'admin/permissions/matrix.html', context)


@require_permission('accounts.gerer_agents')
def agent_toggle_active(request, id):
    agent = get_object_or_404(Utilisateur, id=id, user_type__in=ALL_AGENT_TYPES)
    centres_qs, _, scope = _get_scope(request.user)
    if scope != "global" and not _agent_in_scope(agent, centres_qs):
        raise PermissionDenied("Vous n'avez pas accès à cet agent.")
    if request.method == 'POST':
        agent.is_active = not agent.is_active
        agent.save(update_fields=['is_active'])
        etat = "réactivé" if agent.is_active else "suspendu"
        messages.success(request, f'Compte de « {agent.nom} {agent.prenom} » {etat} avec succès !')
    return redirect('bsb_admin:agent_list')


# ─────────────────────────────────────────────
# À ajouter dans les imports en haut de views_admin.py
# ─────────────────────────────────────────────
# from .models import (..., TypeFrais, ...)
# from .forms  import (..., TypeFraisForm, AnneeScolaireForm)


# ─────────────────────────────────────────────
# TYPE DE FRAIS CRUD
# ─────────────────────────────────────────────

@require_permission('courses.gerer_frais')
def type_frais_list(request):
    types = TypeFrais.objects.annotate(nb_tranches=Count('tranches')).order_by('libelle')

    q = request.GET.get('q', '').strip()
    if q:
        types = types.filter(libelle__icontains=q)

    paginator = Paginator(types, 10)
    page = request.GET.get('page')
    types = paginator.get_page(page)
    return render(request, 'admin/fees/type_frais_list.html', {'types': types, 'q': q})


@require_permission('courses.gerer_frais')
def type_frais_create(request):
    if request.method == 'POST':
        form = TypeFraisForm(request.POST)
        if form.is_valid():
            t = form.save()
            messages.success(request, f'Type de frais "{t.libelle}" créé avec succès!')
            return redirect('bsb_admin:type_frais_list')
    else:
        form = TypeFraisForm()
    return render(request, 'admin/fees/type_frais_form.html', {'form': form, 'action': 'Créer'})


@require_permission('courses.gerer_frais')
def type_frais_import_template(request):
    from .bulk_import_registry import SPEC_TYPE_FRAIS
    from .bulk_import.views_helpers import render_import_template
    return render_import_template(request, SPEC_TYPE_FRAIS)


@require_permission('courses.gerer_frais')
def type_frais_import(request):
    from .bulk_import_registry import SPEC_TYPE_FRAIS
    from .bulk_import.views_helpers import handle_import_upload
    return handle_import_upload(request, SPEC_TYPE_FRAIS)


@require_permission('courses.gerer_frais')
def type_frais_update(request, id):
    t = get_object_or_404(TypeFrais, id=id)
    if request.method == 'POST':
        form = TypeFraisForm(request.POST, instance=t)
        if form.is_valid():
            t = form.save()
            messages.success(request, f'Type de frais "{t.libelle}" modifié avec succès!')
            return redirect('bsb_admin:type_frais_list')
    else:
        form = TypeFraisForm(instance=t)
    return render(request, 'admin/fees/type_frais_form.html', {'form': form, 'action': 'Modifier', 'object': t})


@require_permission('courses.gerer_frais')
def type_frais_delete(request, id):
    t = get_object_or_404(TypeFrais, id=id)
    if request.method == 'POST':
        libelle = t.libelle
        t.delete()
        messages.success(request, f'Type de frais "{libelle}" supprimé avec succès!')
        return redirect('bsb_admin:type_frais_list')
    return render(request, 'admin/fees/type_frais_confirm_delete.html', {'object': t})


@require_permission('courses.gerer_frais')
def type_frais_tranches(request, id):
    """
    Gère toutes les tranches d'un type de frais sur une seule page (ajout,
    modification, suppression) : la somme des pourcentages doit faire 100%
    et une seule tranche peut être primordiale, donc elles se valident
    ensemble plutôt qu'une par une.
    """
    type_frais = get_object_or_404(TypeFrais, id=id)
    if request.method == 'POST':
        formset = TrancheFraisFormSet(request.POST, instance=type_frais)
        if formset.is_valid():
            formset.save()
            messages.success(request, f'Tranches de "{type_frais.libelle}" mises à jour avec succès!')
            return redirect('bsb_admin:type_frais_list')
    else:
        formset = TrancheFraisFormSet(instance=type_frais)
    return render(request, 'admin/fees/type_frais_tranches.html', {
        'type_frais': type_frais,
        'formset': formset,
    })


# ─────────────────────────────────────────────
# ANNÉE SCOLAIRE CRUD  (remplace les 2 vues existantes)
# ─────────────────────────────────────────────

@require_permission('courses.gerer_annees')
def annee_list(request):
    annees = AnneeScolaire.objects.all().order_by('-libelle_anne')

    q = request.GET.get('q', '').strip()
    if q:
        annees = annees.filter(libelle_anne__icontains=q)

    paginator = Paginator(annees, 10)
    page = request.GET.get('page')
    annees = paginator.get_page(page)
    return render(request, 'admin/annee/annee_list.html', {'annees': annees, 'q': q})


@require_permission('courses.gerer_annees')
def annee_create(request):
    if request.method == 'POST':
        form = AnneeScolaireForm(request.POST)
        if form.is_valid():
            annee = form.save()
            messages.success(request, f'Année "{annee.libelle_anne}" enregistrée avec succès!')
            return redirect('bsb_admin:annee_list')
    else:
        form = AnneeScolaireForm()
    return render(request, 'admin/annee/annee_scolaire_form.html', {'form': form, 'action': 'Créer'})


@require_permission('courses.gerer_annees')
def annee_import_template(request):
    from .bulk_import_registry import SPEC_ANNEE
    from .bulk_import.views_helpers import render_import_template
    return render_import_template(request, SPEC_ANNEE)


@require_permission('courses.gerer_annees')
def annee_import(request):
    from .bulk_import_registry import SPEC_ANNEE
    from .bulk_import.views_helpers import handle_import_upload
    return handle_import_upload(request, SPEC_ANNEE)


@require_permission('courses.gerer_annees')
def annee_update(request, id):
    annee = get_object_or_404(AnneeScolaire, id=id)
    if request.method == 'POST':
        form = AnneeScolaireForm(request.POST, instance=annee)
        if form.is_valid():
            annee = form.save()
            messages.success(request, f'Année "{annee.libelle_anne}" modifiée avec succès!')
            return redirect('bsb_admin:annee_list')
    else:
        form = AnneeScolaireForm(instance=annee)
    return render(request, 'admin/annee/annee_scolaire_form.html', {'form': form, 'action': 'Modifier', 'object': annee})


@require_permission('courses.gerer_annees')
def annee_delete(request, id):
    annee = get_object_or_404(AnneeScolaire, id=id)
    if request.method == 'POST':
        libelle = annee.libelle_anne
        annee.delete()
        messages.success(request, f'Année "{libelle}" supprimée avec succès!')
        return redirect('bsb_admin:annee_list')
    return render(request, 'admin/annee/annee_confirm_delete.html', {'object': annee})