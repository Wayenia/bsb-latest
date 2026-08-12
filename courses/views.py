from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.decorators import method_decorator
from django.contrib.auth import logout
from django.core.paginator import Paginator
from django.core.files.storage import FileSystemStorage
from django.db.models import Sum
import qrcode
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.cell.cell import MergedCell
from courses.forms import PersonalInfoForm,PaiementForm
from .models import (CentreEtFiliere, Filiere, Inscription, PieceJointeInscription
    ,DocumentEleve,Paiement,Dette,CentreFormation,AnneeScolaire,Module
    )
from .forms import FiliereForm
from .filters import CentreFormationFilter, FiliereFilter
from .permissions import require_permission, require_role
from django.core.exceptions import PermissionDenied
from accounts.models import Eleve
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Prefetch
import weasyprint
from django.db.models import Sum
import io
import os
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from django.conf import settings



############### STUDENT LEVEL #############

# SUBSCRIBE SELECTION : annee scolaire -> centre -> metier
def subscribe_selection_view(request):
    annees = AnneeScolaire.objects.all()
    centres = CentreFormation.objects.all()
    selected_annee_id = request.GET.get('annee') or ''
    selected_centre_id = request.GET.get('centre') or ''

    careers = []
    if selected_annee_id and selected_centre_id:
        careers = (
            CentreEtFiliere.objects
            .filter(
                is_active=True,
                annee_prog_id=selected_annee_id,
                centre_id=selected_centre_id,
            )
            .filter(Q(date_limite_inscription__isnull=True) | Q(date_limite_inscription__gte=timezone.now()))
            .select_related('filiere')
            .prefetch_related('frais_set')
            .annotate(total_frais=Sum('frais__montant'))
        )

    careers_data = [
        {
            'id': career.id,
            'nom_filiere': career.filiere.nom_filiere,
            'duree': career.duree_display,
            'niveau_diplome': career.filiere.niveau_diplome or '',
            'titre_professionnel': career.filiere.get_titre_professionnel_display() if career.filiere.titre_professionnel else '',
            'total_frais': career.total_frais or 0,
            'communique_url': career.communique.url if career.communique else '',
            'date_limite': career.date_limite_inscription.strftime('%d/%m/%Y à %H:%M') if career.date_limite_inscription else '',
        }
        for career in careers
    ]

    context = {
        'annees': annees,
        'centres': centres,
        'selected_annee_id': selected_annee_id,
        'selected_centre_id': selected_centre_id,
        'careers': careers,
        'careers_data': careers_data,
    }
    return render(request, 'student/subscription/subscribe_selection.html', context)

# AVAILABLE CAREERS
# @login_required
def available_career_view(request):
    # already_subscribed = Inscription.objects.filter(eleve=request.user).values_list('formation', flat=True)
    # available_career = CentreEtFiliere.objects.filter(is_active=True).exclude(id__in=already_subscribed).select_related('centre', 'filiere').order_by('filiere__nom_filiere')
    available_career = (
        CentreEtFiliere.objects.filter(is_active=True)
        .filter(Q(date_limite_inscription__isnull=True) | Q(date_limite_inscription__gte=timezone.now()))
        .prefetch_related('frais_set').annotate(total_frais=Sum('frais__montant'))
        .select_related('centre', 'filiere').order_by('-date_creation')
    )
    #Ici on doit récupéré le id de la formtion lié a fil et centre pour l'affecter le frais   

    f=CentreFormationFilter(request.GET,queryset=available_career)
    paginator=Paginator(f.qs,10)
    page=request.GET.get('page')
    available_career=paginator.get_page(page)

    # Recherche libre d'un métier + téléchargement de son curricula,
    # accessible sans connexion et indépendamment des offres de formation actives.
    curricula_q = request.GET.get('curricula_q', '').strip()
    if curricula_q:
        curricula_results = Filiere.objects.filter(
            is_active=True, nom_filiere__icontains=curricula_q
        ).order_by('nom_filiere')
    else:
        curricula_results = Filiere.objects.none()

    context = {
        'available_career': available_career,
        'filter': f,
        'curricula_q': curricula_q,
        'curricula_results': curricula_results,
    }
    return render(request, 'student/subscription/available_career.html', context)

# GET CAREER BY ID

@login_required
def get_career_by_id(request, id):
    selected_career = get_object_or_404(CentreEtFiliere, id=id)
    context = {'selected_career': selected_career}
    return render(request, 'student/subscription/personal_info.html', context)

# DOCUMENTS
@login_required
def documents_view(request):
    career_id = request.session.get('career_id')
    if not career_id:
        messages.warning(request, "Choisissez d'abord une formation.")
        return redirect('courses:available_career')
    career = get_object_or_404(CentreEtFiliere, id=career_id, is_active=True)
    required_doc = PieceJointeInscription.objects.filter(formation=career)

    if request.method == 'POST':
        fs = FileSystemStorage()
        uploaded_files = {}
        errors = []

        for doc in required_doc:
            if doc.est_requis and doc.libelle_piece not in request.FILES:
                errors.append(f'Le document « {doc.libelle_piece} » est obligatoire.')

        # Seuls des PDF sont acceptés pour les documents envoyés par l'élève :
        # extension ET signature binaire (%PDF-) verifiees, pour empecher un
        # fichier .html/.svg renomme en .pdf (vecteur XSS stocke contre le
        # personnel qui ouvre ces documents via "Visualiser").
        for doc in required_doc:
            if doc.libelle_piece in request.FILES:
                requested_file = request.FILES[doc.libelle_piece]
                if not requested_file.name.lower().endswith('.pdf'):
                    errors.append(f'« {doc.libelle_piece} » doit être un fichier PDF (.pdf).')
                    continue
                header = requested_file.read(5)
                requested_file.seek(0)
                if header != b'%PDF-':
                    errors.append(f'« {doc.libelle_piece} » n\'est pas un fichier PDF valide.')

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            # Save each to disk, store path in session
            for doc in required_doc:
                if doc.libelle_piece in request.FILES:
                    requested_file = request.FILES[doc.libelle_piece]
                    file_name_saved = fs.save(f'student/pieces/{requested_file.name}', requested_file)
                    uploaded_files[doc.libelle_piece] = {
                        'url':fs.url(file_name_saved),
                        'path':file_name_saved
                    }

            # Save to session
            request.session['career_id'] = career_id
            request.session['uploaded_files'] = uploaded_files
            return redirect('courses:recap')
    context = {'career': career, 'required_doc': required_doc,}
    print(f'=== CAREER : {career} ======')
    return render(request, 'student/subscription/documents.html', context)

# PERSONAL INFO
@login_required
@login_required
def personal_info_view(request, career_id):
    request.session['career_id'] = career_id
    try:
        eleve = request.user.eleve
    except Eleve.DoesNotExist:
        messages.error(request, "Votre profil élève est introuvable.")
        return redirect("courses:home")  # ou une autre page appropriée

    #eleve = request.user.eleve

    # Réinscription après rejet : on mémorise l'inscription rejetée d'origine en session
    # (elle ne survit pas forcément dans l'URL après le POST) et on préremplit le formulaire
    # avec les informations qu'elle contenait.
    from_rejected_param = request.GET.get('from_rejected')
    if from_rejected_param:
        request.session['from_rejected_id'] = from_rejected_param
    from_rejected_id = request.session.get('from_rejected_id')

    rejected_inscription = None
    if from_rejected_id:
        rejected_inscription = Inscription.objects.filter(
            id=from_rejected_id, eleve=eleve, statut='rejete'
        ).first()

    initial = {
        'nom': eleve.nom,
        'prenom': eleve.prenom,
        'email': eleve.email,
        'tel': eleve.tel or '',
        'date_naissance': eleve.date_naissance or '',
        'lieu_naissance': eleve.lieu_naissance or '',
    }
    if rejected_inscription:
        initial.update({
            'nom_personne': rejected_inscription.personne_contact_nom or '',
            'prenom_personne': rejected_inscription.personne_contact_prenom or '',
            'fonction': rejected_inscription.personne_contact_fonction or '',
            'contact': rejected_inscription.personne_contact_tel or '',
        })

    form = PersonalInfoForm(request.POST or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        # Mettre à jour l'élève avec les nouvelles infos
        eleve.nom = form.cleaned_data['nom']
        eleve.prenom = form.cleaned_data['prenom']
        eleve.sexe = form.cleaned_data['sexe'].lower()  # 'M' → 'm'
        eleve.email = form.cleaned_data['email']
        eleve.tel = form.cleaned_data.get('tel', '')
        eleve.date_naissance = form.cleaned_data.get('date_naissance')
        eleve.lieu_naissance = form.cleaned_data.get('lieu_naissance', '')
        eleve.save()

        request.session['student_data'] = {
            'nom': eleve.nom,
            'prenom': eleve.prenom,
            'sexe': eleve.sexe,
            'email': eleve.email,
            'tel': eleve.tel,
            'date_naissance': str(eleve.date_naissance or ''),
            'lieu_naissance': eleve.lieu_naissance,
            'nom_personne': form.cleaned_data.get('nom_personne', ''),
            'prenom_personne': form.cleaned_data.get('prenom_personne', ''),
            'fonction': form.cleaned_data.get('fonction', ''),
            'contact': form.cleaned_data.get('contact', ''),
        }
        return redirect('courses:documents')

    context = {'form': form, 'career_id': career_id}
    return render(request, 'student/subscription/personal_info.html', context)
# RECAP
@login_required
def recap_view(request):
    career_id = request.session.get('career_id')
    student_data = request.session.get('student_data')
    uploaded_files = request.session.get('uploaded_files', {})
   

    if not career_id or not student_data:
        messages.warning(request, 'Votre session a expiré. Recommencez svp.')
        return redirect('courses:available_career')

    career = get_object_or_404(CentreEtFiliere, id=career_id)

    if request.method == 'POST': # double safety
        if Inscription.objects.filter(
            eleve=request.user.eleve,
            formation=career
            ).exclude(statut='rejete').exists():
            messages.error(request, 'Vous avez déjà déposé une demande d\'inscription pour cette formation.')
            return redirect('courses:my_subscriptions')

        from_rejected_id = request.session.get('from_rejected_id')
        rejected_inscription = None
        if from_rejected_id:
            rejected_inscription = Inscription.objects.filter(
                id=from_rejected_id, eleve=request.user.eleve, statut='rejete'
            ).first()

        # Create inscription
        inscription=Inscription.objects.create(
            eleve=request.user.eleve,
            formation=career,
            statut='en_cours',
            annee_scolaire=career.annee_prog,  # ← récupérée depuis la formation
            personne_contact_nom=student_data.get('nom_personne', ''),
            personne_contact_prenom=student_data.get('prenom_personne', ''),
            personne_contact_fonction=student_data.get('fonction', ''),
            personne_contact_tel=student_data.get('contact', ''),
            id_inscription_rejeter=rejected_inscription,
        )
        for libelle,fic in uploaded_files.items():
            try:

                docs=PieceJointeInscription.objects.get(
                    formation=career,
                    libelle_piece=libelle
                )
                doc=DocumentEleve(
                    inscription=inscription,
                    piece_requise=docs,
                )
                doc.piece.name=fic['path']
                doc.save()
            except PieceJointeInscription.DoesNotExist:
             continue

        # finally clear session data
        for key in ['career_id', 'student_data', 'uploaded_files', 'from_rejected_id']:
            request.session.pop(key, None)

        messages.success(request, 'Votre dossier a été soumis avec succès !')
        return redirect('courses:my_subscriptions')
    context = {
        'career': career,
        'student': student_data,
        'uploaded_files': uploaded_files,
    }
    return render(request, 'student/subscription/recap.html', context)

#Ici on affiche d'abord les frais à payer avec action
@login_required
def liste_dettes(request,id):
    inscription=get_object_or_404(Inscription,id=id)
    eleve = getattr(request.user, 'eleve', None)
    if inscription.eleve_id != getattr(eleve, 'pk', None) and not (request.user.is_superuser or request.user.has_perm('courses.voir_inscriptions')):
        raise PermissionDenied("Vous ne pouvez consulter que vos propres dettes.")
    dettes=Dette.objects.filter(inscription=inscription).select_related('inscription','frais_formation__type_frais').prefetch_related('frais_formation__type_frais__tranches','paiements')
    total = dettes.count()
    soldees = dettes.filter(etat_dette='soldé').count()
    non_soldees = dettes.filter(etat_dette='non_soldé').count()

    return render(request,'student/subscription/dette.html',context={'inscription':inscription,'dettes':dettes,'total': total,
        'soldees': soldees,
        'non_soldees': non_soldees,
        })

#Page informative affichée à l'apprenant à la place du formulaire de paiement
@login_required
def paiement_info_centre(request):
    return render(request, 'student/paiement/info_centre.html')


#Ici cest si cliques sur payé en fait
@login_required
def effectuer_paiment(request, id):
    dette = get_object_or_404(Dette, id=id)
    eleve = getattr(request.user, 'eleve', None)
    is_self = dette.inscription.eleve_id == getattr(eleve, 'pk', None)
    if not is_self and not (request.user.is_superuser or request.user.has_perm('courses.encaisser_paiement')):
        raise PermissionDenied("Vous ne pouvez régler que vos propres dettes.")

    # Paiement en ligne désactivé pour les apprenants : ils doivent se rendre
    # au centre BSB le plus proche. Le circuit de paiement lui-même n'est pas
    # touché — cette redirection ne s'applique qu'à l'élève réglant sa propre
    # dette (is_self) ; le personnel autorisé (encaisser_paiement) continue
    # d'utiliser cette vue normalement, rien ci-dessous n'est modifié pour eux.
    if is_self:
        return redirect('courses:paiement_info_centre')

    if dette.reste_a_payer() <= 0:
        messages.warning(request, "Cette dette est déjà soldée.")
        return redirect('courses:liste_dettes', id=dette.inscription.id)

    # Ordre de paiement : la tranche primordiale d'une autre dette de la même
    # inscription doit être intégralement réglée avant celle-ci.
    dette_bloquante, tranche_bloquante = dette.inscription.dette_et_tranche_bloquantes()
    if dette_bloquante and dette_bloquante.id != dette.id:
        messages.error(
            request,
            f"Vous devez d'abord régler entièrement la tranche « {tranche_bloquante.libelle} » "
            f"de « {dette_bloquante.frais_formation.type_frais} » avant de pouvoir payer ceci."
        )
        return redirect('courses:liste_dettes', id=dette.inscription.id)

    tranche_cible = dette.tranche_a_payer()
    montant_cible = dette.montant_a_payer()
    tranche_suivante = dette.paiements.count() + 1

    if request.method == 'POST':
        form = PaiementForm(request.POST, request.FILES)
        if form.is_valid():
            paiement = form.save(commit=False)
            paiement.dette = dette
            paiement.tranche = tranche_suivante
            paiement.tranche_frais = tranche_cible

            # Le numéro de quittance est généré automatiquement à l'enregistrement
            # (voir Paiement.save()), avec nouvelle tentative en cas de collision.

            # L'élève doit régler exactement le montant dû (tranche ou dette
            # entière) ; les autres rôles (caisse, admin, gestionnaire...)
            # peuvent régler un montant partiel.
            if is_self and paiement.montant_paiement != montant_cible:
                messages.error(request, f"Vous devez régler exactement le montant dû ({montant_cible} FCFA).")
                return render(request, 'student/paiement/form.html', {
                    'form': form, 'dette': dette, 'tranche_cible': tranche_cible, 'montant_cible': montant_cible,
                })
            if paiement.montant_paiement <= 0 or paiement.montant_paiement > montant_cible:
                messages.error(request, f"Le montant saisi dépasse le montant dû ({montant_cible} FCFA).")
                return render(request, 'student/paiement/form.html', {
                    'form': form, 'dette': dette, 'tranche_cible': tranche_cible, 'montant_cible': montant_cible,
                })

            # Sous-paiement d'une tranche primordiale par un caissier/staff : motif +
            # pièce jointe obligatoires avant de pouvoir valider le paiement.
            if not is_self and tranche_cible and tranche_cible.est_primordiale and paiement.montant_paiement < montant_cible:
                motif = request.POST.get('motif_derogation', '').strip()
                piece_jointe = request.FILES.get('piece_jointe_derogation')
                if not motif or not piece_jointe:
                    messages.error(
                        request,
                        "Un motif et une pièce jointe justificative sont obligatoires pour valider un "
                        "règlement inférieur au montant dû de la tranche primordiale."
                    )
                    return render(request, 'student/paiement/form.html', {
                        'form': form, 'dette': dette, 'tranche_cible': tranche_cible, 'montant_cible': montant_cible,
                    })
                paiement.motif_derogation = motif
                paiement.piece_jointe_derogation = piece_jointe

            paiement.cree_par = request.user
            paiement.save()

            if dette.reste_a_payer() <= 0:
                dette.etat_dette = "soldé"
                dette.save()

            messages.success(request, f'Paiement de {paiement.montant_paiement} FCFA enregistré.')
            return redirect('courses:mes_paiements')
    else:
        form = PaiementForm(initial={'tranche': tranche_suivante, 'montant_paiement': montant_cible})

    return render(request, 'student/paiement/form.html', {
        'form': form,
        'dette': dette,
        'tranche_cible': tranche_cible,
        'montant_cible': montant_cible,
    })

#Afficher tous les paiemnents de l'élève conneecté en fait c'est mieux on a pas beoin des dettes on affiche tout
def liste_paiement(request):
    paiements=Paiement.objects.filter(dette__inscription__eleve=request.user.eleve).select_related('dette','dette__inscription','dette__inscription__eleve').order_by('-date_paiement')
    paginator=Paginator(paiements,10)
    page=request.GET.get('page')
    paiements=paginator.get_page(page)
    return render(request, 'student/paiement/mes_paiements.html', {
        'paiements': paiements,
    })
              
# ─────────────────────────────────────────────
# EN-TÊTE OFFICIEL PARTAGÉ POUR LES PDF GÉNÉRÉS
# ─────────────────────────────────────────────
def _pdf_header_lines(centre=None, direction=None):
    """Retourne (lignes_gauche, lignes_droite) de l'en-tête officiel.

    `direction` (Direction_reg) et `centre` (CentreFormation) sont optionnels :
    si absents, l'en-tête s'arrête à "Direction Générale" (cas d'un rapport
    non circonscrit à une direction/un centre précis).
    """
    left = [
        "MINISTÈRE DE L'ENSEIGNEMENT SECONDAIRE",
        "ET DE LA FORMATION PROFESSIONNELLE ET TECHNIQUE",
        "**********",
        "BURKINA SUUDU BAWDE",
        "**********",
        "DIRECTION GENERALE",
    ]
    resolved_direction = direction or (centre.direction if centre else None)
    if resolved_direction:
        left.append("**********")
        left.append(resolved_direction.nom_direction.upper())
    if centre:
        left.append("**********")
        left.append(centre.nom_centre.upper())

    right = ["BURKINA FASO", "**********", "la patrie ou la mort,", "nous vaincrons"]
    return left, right

# ─────────────────────────────────────────────
# ELEVE — Télécharger la quittance PDF
# ─────────────────────────────────────────────
def telecharger_quittance(request, id):
    
    paiement = get_object_or_404(
        Paiement.objects.filter(dette__inscription__eleve=request.user.eleve).select_related(
            'dette__inscription__formation',
            'dette__inscription__eleve',
            'dette__inscription__annee_scolaire',
        ),
        id=id
    )

    if paiement.dette.inscription.eleve != request.user.eleve:
         messages.error(request, "Action non autorisée.")
         return redirect('courses:mes_paiements')

    centre = paiement.dette.inscription.formation.centre
    header_left, header_right = _pdf_header_lines(centre)
    html_string = render_to_string('student/paiement/quittance_pdf.html', {
         'paiement': paiement,
         'eleve':paiement.dette.inscription.eleve,
         'annee_scolaire':paiement.dette.inscription.annee_scolaire,
         'dette':paiement.dette,
         'centre':centre,
         'filiere':paiement.dette.inscription.formation.filiere,
         'frais':paiement.dette.frais_formation,
         'type_de_frais':paiement.dette.frais_formation.type_frais.libelle,
         'montant_frais':paiement.dette.frais_formation.montant,
         'inscription':paiement.dette.inscription,
         'quittance_numero':paiement.numero_quittance,
         'header_left': header_left,
         'header_right': header_right,
     })
    pdf_file = weasyprint.HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="quittance_{paiement.numero_quittance}.pdf"'
    return response


# ─────────────────────────────────────────────
# RÉCÉPISSÉ DE DEMANDE D'INSCRIPTION (dépôt ou validation, sans paiement)
# ─────────────────────────────────────────────
@login_required
def telecharger_recepisse(request, id):
    inscription = get_object_or_404(
        Inscription.objects.select_related(
            'eleve', 'formation__centre', 'formation__filiere', 'annee_scolaire'
        ),
        id=id
    )

    if inscription.eleve != request.user.eleve:
        messages.error(request, "Action non autorisée.")
        return redirect('courses:my_subscriptions')

    centre = inscription.formation.centre
    header_left, header_right = _pdf_header_lines(centre)

    if inscription.statut == 'valide':
        titre_document = "Récépissé de validation"
    elif inscription.statut == 'rejete':
        titre_document = "Récépissé de demande d'inscription"
    else:
        titre_document = "Récépissé de dépôt de demande"

    html_string = render_to_string('student/subscription/recepisse_pdf.html', {
        'inscription': inscription,
        'eleve': inscription.eleve,
        'annee_scolaire': inscription.annee_scolaire,
        'centre': centre,
        'filiere': inscription.formation.filiere,
        'numero_dossier': f"DOSS-{inscription.id:06d}",
        'titre_document': titre_document,
        'header_left': header_left,
        'header_right': header_right,
    })
    pdf_file = weasyprint.HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="recepisse_{inscription.id}.pdf"'
    return response


def download_quittance(request,id):
    paiement = get_object_or_404(
        Paiement.objects.select_related(
            'dette__inscription__eleve',
            'dette__inscription__formation',
            'dette__inscription__annee_scolaire',
        ),
        id=id,
        dette__inscription__eleve=request.user.eleve
    )
    dette=paiement.dette
    inscription=paiement.dette.inscription
    eleve=inscription.eleve
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A5)
    width, height = A5
    favicon_path = os.path.join(settings.BASE_DIR, 'static/images/favicon.png')
    header_left, header_right = _pdf_header_lines(inscription.formation.centre)
    line_h = 0.28*cm
    y_left = height - 0.6*cm
    p.setFont("Helvetica-Bold", 5.5)
    for line in header_left:
        p.drawString(0.6*cm, y_left, line)
        y_left -= line_h
    y_right = height - 0.6*cm
    for line in header_right:
        p.drawRightString(width-0.6*cm, y_right, line)
        y_right -= line_h
    p.drawImage(ImageReader(favicon_path), x=width/2-0.9*cm, y=height-2.2*cm, width=1.8*cm, height=1.8*cm, preserveAspectRatio=True, mask='auto')
    #  TITRE
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width/2, height-3.8*cm, "QUITTANCE DE PAIEMENT")
    p.setFont("Helvetica", 9)
    p.drawCentredString(width/2, height-4.4*cm, "Burkina Suudu Bawde")
    # LIGNE SEPARATRICE
    y = height - 5.2*cm
    p.setLineWidth(0.8)
    p.line(1.5*cm, y, width-1.5*cm, y)
    # FONCTION HELPER 
    def ligne(label, valeur, y_pos):
        p.setFont("Helvetica-Bold", 10)
        p.drawString(1.5*cm, y_pos, label)
        p.setFont("Helvetica", 10)
        p.drawString(7*cm, y_pos, str(valeur))
        return y_pos - 0.5*cm  # <-- était 0.7*cm (chevauchait le QR code plus bas)
    #  INFOS QUITTANCE 
    y -= 0.5*cm
    y = ligne("Numéro de quittance :", paiement.numero_quittance, y)
    y = ligne("Date de paiement :", paiement.date_paiement.strftime("%d/%m/%Y à %H:%M"), y)
    y -= 0.3*cm
    p.setLineWidth(0.3)
    p.setDash(3, 3)
    p.line(1.5*cm, y, width-1.5*cm, y)
    p.setDash()
    y -= 0.5*cm
    # INFOS APPRENANT 
    y = ligne("Apprenant :", f"{eleve.nom} {eleve.prenom}", y)
    y = ligne("Centre de Formation :", str(inscription.formation.centre), y)
    y=ligne("Métier :" ,str(inscription.formation.filiere),y)
    y = ligne("Année scolaire :", str(inscription.annee_scolaire), y)
    y -= 0.3*cm
    p.setDash(3, 3)
    p.line(1.5*cm, y, width-1.5*cm, y)
    p.setDash()
    y -= 0.5*cm
    # ── DETAILS PAIEMENT ───────────────────────────────────
    y = ligne("Type de frais :", str(dette.frais_formation.type_frais.libelle), y)
    y = ligne("Tranche :", f"Tranche {paiement.tranche}", y)
    y = ligne("Mode de paiement :", paiement.get_mode_paiement_display(), y)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(1.5*cm, y, "Montant payé :")
    p.drawString(7*cm, y, f"{paiement.montant_paiement:,.0f} FCFA")
    y -= 0.7*cm
    y -= 0.3*cm
    p.setDash(3, 3)
    p.line(1.5*cm, y, width-1.5*cm, y)
    p.setDash()
    y -= 0.5*cm
    # ── RECAP DETTE ────────────────────────────────────────
    y = ligne("Total dû :",      f"{dette.montant_total:,.0f} FCFA", y)
    y = ligne("Total payé :",    f"{dette.montant_paye():,.0f} FCFA", y)
    y = ligne("Reste à payer :", f"{dette.reste_a_payer():,.0f} FCFA", y)
    y = ligne("État de la dette :", dette.get_etat_dette_display(), y)

    # ── QR CODE ────────────────────────────────────────────
    qr_data = (
        f"Quittance : {paiement.numero_quittance}\n"
        f"Date : {paiement.date_paiement.strftime('%d/%m/%Y à %H:%M')}\n"
        f"Apprenant : {eleve.nom} {eleve.prenom}\n"
        f"Centre : {inscription.formation.centre}\n"
        f"Métier : {inscription.formation.filiere}\n"
        f"Année scolaire : {inscription.annee_scolaire}\n"
        f"Type de frais : {dette.frais_formation.type_frais.libelle}\n"
        f"Tranche : {paiement.tranche}\n"
        f"Mode de paiement : {paiement.get_mode_paiement_display()}\n"
        f"Montant payé : {paiement.montant_paiement:,.0f} FCFA\n"
        f"Total dû : {dette.montant_total:,.0f} FCFA\n"
        f"Total payé : {dette.montant_paye():,.0f} FCFA\n"
        f"Reste à payer : {dette.reste_a_payer():,.0f} FCFA\n"
        f"État : {dette.get_etat_dette_display()}"
    )
    import qrcode
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    qr_size = 3*cm
    qr_x = (width - qr_size) / 2  # centré horizontalement
    qr_y = 1.8*cm
    p.drawImage(ImageReader(qr_buffer), x=qr_x, y=qr_y, width=qr_size, height=qr_size)
    p.setFont("Helvetica-Oblique", 7)
    p.setFillColor(colors.grey)
    p.drawCentredString(width/2, 1.6*cm, "Scannez pour vérifier")

    #  PIED DE PAGE 
    p.setFont("Helvetica-Oblique", 8)
    p.setFillColor(colors.grey)
    p.drawCentredString(width/2, 1*cm, f"BSB-DSI          généré sur YU-PAAN le : {timezone.now().strftime('%d/%m/%Y à %H:%M')}")
    p.showPage()
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="quittance_{paiement.numero_quittance}.pdf"'
    return response
# STUDENT DASHBOARD
@login_required
def student_dashboard(request):
    already_subscribed = Inscription.objects.filter(eleve=request.user.eleve).values_list('formation', flat=True)
    available_career_count = CentreEtFiliere.objects.filter(is_active=True).exclude(id__in=already_subscribed).count()
    active_careers = (
        CentreEtFiliere.objects
        .filter(is_active=True)
        .select_related('centre', 'filiere', 'annee_prog')
        .prefetch_related('frais_set')
        .annotate(total_frais=Sum('frais__montant'))
        .order_by('-date_lancement')
    )
    context = {
        'my_subscriptions': Inscription.objects.filter(eleve=request.user.eleve).count(),
        'available_career_count': available_career_count,
        'active_careers': active_careers,
    }
    return render(request, 'student/dashboard/dashboard.html', context)

# MY SUBSCRIPTIONS
@login_required
def my_subscriptions(request):
    subscriptions = Inscription.objects.filter(eleve=request.user.eleve).select_related('formation__centre', 'formation__filiere').order_by('-date_inscription')
    # Inscriptions rejetées pour lesquelles une réinscription (non re-rejetée) existe déjà :
    # leur bouton "Se réinscrire" doit être désactivé.
    deja_reinscrites_ids = set(
        Inscription.objects.filter(
            eleve=request.user.eleve,
            id_inscription_rejeter__isnull=False,
        ).exclude(statut='rejete').values_list('id_inscription_rejeter_id', flat=True)
    )

    paginator = Paginator(subscriptions, 10)
    page = request.GET.get('page')
    subscriptions = paginator.get_page(page)

    context = {'subscriptions': subscriptions, 'deja_reinscrites_ids': deja_reinscrites_ids}
    return render(request, 'student/dashboard/my_subscriptions.html', context)

@login_required
def api(request):
    return render(request,'student/paiement/quittance_pdf.html')

###############CENTRE USER PANEL #############


@login_required
@login_required
def member_dashboard(request):
    user = request.user
    utype = user.user_type

    active_careers = (
        CentreEtFiliere.objects
        .filter(is_active=True)
        .select_related('centre', 'filiere', 'annee_prog')
        .prefetch_related('frais_set')
        .annotate(total_frais=Sum('frais__montant'))
        .order_by('-date_lancement')
    )

    # ── deps/membre (personnel du siège, sans centre) → accès global en
    # lecture ; ce que chacun peut FAIRE reste gouverné par ses permissions ─
    if utype in ['deps', 'admin', 'dg', 'membre'] or user.is_superuser:
        stats = {
            'total_inscriptions': Inscription.objects.count(),
            'filieres': Filiere.objects.distinct().count(),
            'etudiants': Eleve.objects.distinct().count(),
        }
        return render(request, 'member/member_dashboard/dashboard.html', {
            'active_careers': active_careers,
            'stats': stats,
            'membre': None,
            'centre': None,
            'centres_visibles': CentreFormation.objects.all(),
            'centres_visibles_ids': list(CentreFormation.objects.values_list('id', flat=True)),
        })

    # ── dir → toute sa direction (tous ses centres), pas de membreadministration
    if utype == 'dir':
        try:
            dir_obj = DirecteurInterRegional.objects.get(pk=user.pk)
        except DirecteurInterRegional.DoesNotExist:
            messages.error(request, "Accès refusé.")
            return redirect('accounts:login')

        direction = dir_obj.direction
        if not direction:
            messages.error(request, "Accès refusé : aucune direction associée à votre profil.")
            return redirect('accounts:login')

        centres_visibles = CentreFormation.objects.filter(direction=direction)
        stats = {
            'total_inscriptions': Inscription.objects.filter(formation__centre__direction=direction).count(),
            'filieres': Filiere.objects.filter(centreetfiliere__centre__direction=direction).distinct().count(),
            'etudiants': Eleve.objects.filter(inscription__formation__centre__direction=direction).distinct().count(),
        }
        return render(request, 'member/member_dashboard/dashboard.html', {
            'active_careers': active_careers.filter(centre__direction=direction),
            'stats': stats,
            'membre': None,
            'centre': None,
            'direction': direction,
            'centres_visibles': centres_visibles,
            'centres_visibles_ids': list(centres_visibles.values_list('id', flat=True)),
        })

    # ── tous les autres → ont forcément un membreadministration ───────────
    try:
        membre = request.user.membreadministration
    except Exception:
        messages.error(request, "Accès refusé.")
        return redirect('accounts:login')

    if not membre.structure:
        messages.error(request, "Accès refusé : vous n'êtes pas membre d'un centre.")
        return redirect('accounts:login')

    structure = membre.structure
    stats = {
        'total_inscriptions': Inscription.objects.filter(formation__centre=structure).count(),
        'filieres': Filiere.objects.filter(centreetfiliere__centre=structure).distinct().count(),
        'etudiants': Eleve.objects.filter(inscription__formation__centre=structure).distinct().count(),
    }
    centres_visibles = membre.get_centres_visibles()
    centres_visibles_ids = [c.id for c in centres_visibles]

    return render(request, 'member/member_dashboard/dashboard.html', {
        'centre': structure,
        'membre': membre,
        'stats': stats,
        'centres_visibles': centres_visibles,
        'centres_visibles_ids': centres_visibles_ids,
        'active_careers': active_careers,
    })


#La liste de tous les inscriptions du cenrte
@require_permission('courses.voir_inscriptions')
def member_inscriptions_list(request):
    #centre=get_object_or_404(CentreFormation,id=id)
    from django.db.models import Q
    member=request.user
    membre = getattr(member, 'membreadministration', None)
    centre = membre.structure if membre else None
    inscriptions=Inscription.objects.select_related('eleve','formation__filiere').filter(formation__centre=centre)

    recherche = request.GET.get('recherche', '').strip()
    if recherche:
        inscriptions = inscriptions.filter(
            Q(eleve__nom__icontains=recherche) |
            Q(eleve__prenom__icontains=recherche) |
            Q(eleve__matricule__icontains=recherche)
        )

    paginator=Paginator(inscriptions,10)
    page=request.GET.get('page')
    inscriptions=paginator.get_page(page)

    context={
        'subscriptions':inscriptions,
        'centre':centre,
        'recherche': recherche,
    }
    return render(request,'member/inscriptions/list.html',context)


##La list des isncriptions en cours du centre
@require_permission('courses.voir_inscriptions')
def member_inscription_en_cours(request):
    #centre=get_object_or_404(CentreFormation,id=id)
    from django.db.models import Q
    member=request.user
    membre = getattr(member, 'membreadministration', None)
    centre = membre.structure if membre else None
    inscriptions=Inscription.objects.select_related('eleve','formation__filiere').filter(formation__centre=centre,statut='en_cours').order_by('-date_inscription')

    recherche = request.GET.get('recherche', '').strip()
    if recherche:
        inscriptions = inscriptions.filter(
            Q(eleve__nom__icontains=recherche) |
            Q(eleve__prenom__icontains=recherche) |
            Q(eleve__matricule__icontains=recherche)
        )

    paginator=Paginator(inscriptions,10)
    page=request.GET.get('page')
    inscriptions=paginator.get_page(page)

    non_valide=Inscription.objects.filter(formation__centre=centre,statut='en_cours').count()

    context={
        'subscriptions':inscriptions,
        'number':non_valide,
        'recherche': recherche,
    }
    return render(request,'member/inscriptions/valide_inscription.html',context)


##Valider une inscription du dentre en cours en fait Ici c'est bo en fait on a pas besoin de
@require_permission('courses.voir_inscriptions')
def member_inscription_detail(request,id):
    membre = getattr(request.user, 'membreadministration', None)
    centre = membre.structure if membre else None
    inscription=get_object_or_404(Inscription,id=id,formation__centre=centre)
    eleve_docs=DocumentEleve.objects.select_related('piece_requise').filter(inscription=inscription)
    return render(request,'member/inscriptions/inscription_detail.html',{'detail':inscription,'eleve_docs':eleve_docs})

@require_permission('courses.valider_inscription')
def gerer_inscription(request,id):
     membre = getattr(request.user, 'membreadministration', None)
     centre = membre.structure if membre else None
     subscription=get_object_or_404(Inscription,id=id,formation__centre=centre)
     if request.method == 'POST':
         action=request.POST.get('action') 
         if action == 'valide':
             subscription.statut='valide'
             subscription.date_validation=timezone.now()
             subscription.motif_rejet=None
             messages.success(request, "Inscription validée et dettes générées.")
         subscription.save()
     return redirect("courses:valide_inscription")

@require_permission('courses.rejeter_inscription')
def rejeter_inscription(request,id):
    membre = getattr(request.user, 'membreadministration', None)
    centre = membre.structure if membre else None
    subscription=get_object_or_404(Inscription,id=id,formation__centre=centre)

    if request.method == 'POST':
        motif=request.POST.get('motif')
        if not motif:
            messages.error(request,"Veuillez renseigner le motif du rejet du dossier ")
            return redirect("courses:valide_inscription")

        subscription.statut = "rejete"
        subscription.motif_rejet = motif
        subscription.date_validation = timezone.now()
        subscription.save()
        messages.warning(request, "Inscription rejetée")
        return redirect("courses:valide_inscription")

    return render(request, "member/inscriptions/rejeter_inscription.html", {"subscription": subscription})

@require_permission('courses.encaisser_paiement', 'courses.gerer_paiements')
def paiement_list(request):
    """
    Par défaut : inscriptions du centre du membre connecté dont le reste à
    payer est strictement positif. Avec une recherche (nom, prénom,
    identifiant, téléphone), la recherche porte sur tous les centres, pour
    pouvoir encaisser le paiement de n'importe quel apprenant.
    """
    q = request.GET.get('q', '').strip()
    membre = getattr(request.user, 'membreadministration', None)
    centre = membre.structure if membre else None
    peut_rechercher_tous_centres = (
        request.user.is_superuser or
        request.user.has_perm('courses.rechercher_tous_centres')
    )
    if q and not peut_rechercher_tous_centres:
        q = ''

    base_qs = Inscription.objects.select_related(
        'eleve',
        'formation__filiere',
        'formation__centre',
        'annee_scolaire',
    ).prefetch_related(
        'dettes',
        'dettes__paiements',
        'dettes__frais_formation',
        'dettes__frais_formation__type_frais',
    )

    if q:
        inscriptions_qs = base_qs.filter(
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q) |
            Q(eleve__numero_identifiant__icontains=q) |
            Q(eleve__tel__icontains=q) |
            Q(eleve__matricule__icontains=q) |
            Q(dettes__paiements__numero_quittance__icontains=q)
        ).distinct().order_by('-date_inscription')
    else:
        inscriptions_qs = base_qs.filter(formation__centre=centre).order_by('-date_inscription')

    # Le reste à payer est calculé à partir des dettes/paiements déjà préchargés :
    # filtrer en Python plutôt qu'avec une agrégation SQL fragile sur deux
    # niveaux de relations (dettes -> paiements).
    inscriptions_avec_reste = []
    for insc in inscriptions_qs:
        insc.total_du = sum(d.montant_total for d in insc.dettes.all())
        insc.total_paye = sum(
            p.montant_paiement
            for d in insc.dettes.all()
            for p in d.paiements.all()
        )
        insc.reste = insc.total_du - insc.total_paye
        if insc.reste > 0:
            inscriptions_avec_reste.append(insc)

    paginator = Paginator(inscriptions_avec_reste, 10)
    page = request.GET.get('page')
    inscriptions = paginator.get_page(page)

    return render(request, 'member/paiement/list.html', {
        'inscriptions': inscriptions,
        'q': q,
        'centre': centre,
        'peut_rechercher_tous_centres': peut_rechercher_tous_centres,
    })


@require_permission('courses.encaisser_paiement', 'courses.gerer_paiements')
def paiement_historique(request):
    """Historique de tous les paiements du centre du membre connecté."""
    membre = getattr(request.user, 'membreadministration', None)
    centre = membre.structure if membre else None

    paiements = Paiement.objects.select_related(
        'dette__inscription__eleve',
        'dette__inscription__formation__filiere',
        'dette__frais_formation__type_frais',
        'cree_par',
    ).filter(
        dette__inscription__formation__centre=centre
    ).order_by('-date_paiement')

    q = request.GET.get('q', '').strip()
    if q:
        paiements = paiements.filter(
            Q(dette__inscription__eleve__nom__icontains=q) |
            Q(dette__inscription__eleve__prenom__icontains=q) |
            Q(dette__inscription__eleve__matricule__icontains=q) |
            Q(numero_quittance__icontains=q)
        )

    paginator = Paginator(paiements, 10)
    page = request.GET.get('page')
    paiements = paginator.get_page(page)

    return render(request, 'member/paiement/historique.html', {
        'paiements': paiements,
        'centre': centre,
        'q': q,
    })

############### TEACHER LEVEL #############

# TEACHER DASHBOARD
@login_required
@login_required
def teacher_dashboard(request):
    return redirect('courses:formateur_dashboard')

@login_required
def member_dashboard_direction(request, id):
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
    }
    return render(request, "teacher/dashboard/dashboard.html", context)




# ─────────────────────────────────────────────────────────────────────────────
#  CRÉER UN MÉTIER  (anciennement create_fees)
# ─────────────────────────────────────────────────────────────────────────────
def _process_metier_modules(request, filiere, form):
    """
    Associe à ce métier les modules existants cochés dans le formulaire, plus
    les nouveaux modules créés à la volée (champs new_module_nom[]/new_module_volume[]).
    """
    module_ids = list(form.cleaned_data.get('modules_existants').values_list('id', flat=True))
    noms = request.POST.getlist('new_module_nom')
    volumes = request.POST.getlist('new_module_volume')
    for nom, volume in zip(noms, volumes):
        nom = nom.strip()
        if not nom:
            continue
        try:
            vol = int(volume)
        except (TypeError, ValueError):
            vol = 0
        module = Module.objects.create(nom_module=nom, volume_h_cours=vol)
        module_ids.append(module.id)
    filiere.modules.set(module_ids)


@require_permission('courses.gerer_metiers')
def create_metier(request):
    """Crée un nouveau métier (Filiere)."""
    if request.method == 'POST':
        form = FiliereForm(request.POST, request.FILES)
        if form.is_valid():
            metier = form.save()
            _process_metier_modules(request, metier, form)
            messages.success(request, f'Métier « {metier.nom_filiere} » créé avec succès !')
            return redirect('courses:member_field_list')
    else:
        form = FiliereForm()

    return render(request, 'member/filiere/metier_form.html', {
        'form': form,
        'action': 'Créer',
    })


@require_permission('courses.gerer_metiers')
def field_import_template(request):
    from .bulk_import_registry import SPEC_FILIERE
    from .bulk_import.views_helpers import render_import_template
    return render_import_template(request, SPEC_FILIERE)


@require_permission('courses.gerer_metiers')
def field_import(request):
    from .bulk_import_registry import SPEC_FILIERE
    from .bulk_import.views_helpers import handle_import_upload
    return handle_import_upload(request, SPEC_FILIERE)


# ─────────────────────────────────────────────────────────────────────────────
#  LISTE DES MÉTIERS D'UN CENTRE  (anciennement member_filiere_list)
# ─────────────────────────────────────────────────────────────────────────────
@require_permission('courses.gerer_metiers')
def member_metier_list(request):
    from django.db.models import Count
    metiers = Filiere.objects.annotate(nb_modules=Count('modules', distinct=True)).prefetch_related('modules').order_by('nom_filiere')
    f = FiliereFilter(request.GET, queryset=metiers)

    paginator = Paginator(f.qs, 10)
    metiers_page = paginator.get_page(request.GET.get('page'))

    context = {
        'filieres': metiers_page,
        'filter': f,
    }
    return render(request, 'member/filiere/metier_list.html', context)
        

@require_permission('courses.gerer_metiers')
def metier_delete(request, id):
    field = get_object_or_404(Filiere, id=id)
    if request.method == 'POST':
        nom = field.nom_filiere
        field.delete()
        messages.success(request, f'Métier "{nom}" supprimé avec succès !')
        return redirect('bsb_admin:field_list')
    return render(request, 'member/filiere/confirm_delete.html', {'object': field})
############### THIRD PAGES LEVEL #############

#  HOME
def home(request):
    from .models import CentreEtFiliere
    careers_qs = (
        CentreEtFiliere.objects
        .filter(is_active=True)
        .filter(Q(date_limite_inscription__isnull=True) | Q(date_limite_inscription__gte=timezone.now()))
        .select_related('centre', 'filiere', 'annee_prog')
        .order_by('-date_lancement')
    )
    seen_filieres = set()
    active_careers = []
    for career in careers_qs:
        if career.filiere_id in seen_filieres:
            continue
        seen_filieres.add(career.filiere_id)
        active_careers.append(career)
    return render(request, "third_pages/home.html", {'active_careers': active_careers})

# ABOUT
def about_view(request):
    from .models import DG, Membre
    context = {
        'dg': DG.objects.filter(is_active=True).first(),
        'members': Membre.objects.filter(is_active=True).order_by('order'),
        }
    return render(request, 'third_pages/about.html', context)



############### HELPER METHOD #############

def _bounce_to_login(request, error_message):
    """
    Déconnecte l'utilisateur avant de le renvoyer vers la connexion.
    Indispensable ici : `accounts:login` renvoie tout utilisateur déjà
    authentifié directement vers `redirect_to_dashboard` — sans cette
    déconnexion préalable, un profil incomplet/non reconnu créerait une
    boucle de redirection infinie (login → dashboard → login → ...).
    """
    logout(request)
    messages.error(request, error_message)
    return redirect('accounts:login')


@login_required
def redirect_to_dashboard(request):
    user = request.user

    # Superuser → accès total
    if user.is_superuser:
        return redirect('bsb_admin:admin_dashboard')

    utype = user.user_type

    # ── Admin / Directeur Général → même tableau de bord ───────────────────
    if utype in ('admin', 'dg'):
        return redirect('bsb_admin:admin_dashboard')

    # ── Deps, agent_comptable et membre (personnel du siège, sans centre ni
    # direction de rattachement) → member_dashboard (accès global en lecture,
    # ce que chacun peut y FAIRE reste gouverné par ses permissions) ────────
    if utype in ['deps', 'agent_comptable', 'membre']:
        return redirect('courses:member_dashboard')

    # ── Directeur inter-régional → member_dashboard (vue direction entière) ─
    if utype == 'dir':
        try:
            dir_obj = DirecteurInterRegional.objects.get(pk=user.pk)
            if dir_obj.direction:
                return redirect('courses:member_dashboard')
            return _bounce_to_login(request, "Aucune direction associée à votre profil. Contactez l'administrateur.")
        except DirecteurInterRegional.DoesNotExist:
            return _bounce_to_login(request, "Profil directeur introuvable. Contactez l'administrateur.")

    # ── Formateur ──────────────────────────────────────────────────────────
    if utype == 'formateur':
        try:
            _ = user.formateur
            return redirect('courses:formateur_dashboard')
        except Exception:
            return _bounce_to_login(request, "Profil formateur introuvable. Contactez l'administrateur.")

    # ── Gestionnaire / Caissier (ont toujours une structure) ───────────────
    if utype in ['gestionnaire', 'caissier']:
        try:
            membre = user.membreadministration
            if membre.structure is not None:
                return redirect('courses:member_dashboard')
            elif membre.direction is not None:
                return redirect('courses:member_dashboard_direction', id=membre.direction.id)
            return _bounce_to_login(request, "Aucune structure ni direction associée. Contactez l'administrateur.")
        except Exception:
            return _bounce_to_login(request, "Profil membre introuvable. Contactez l'administrateur.")

    # ── Élève ──────────────────────────────────────────────────────────────
    if utype == 'eleve':
        try:
            _ = user.eleve
            return redirect('courses:student_dashboard')
        except Exception:
            return _bounce_to_login(request, "Profil élève introuvable. Contactez l'administrateur.")

    # ── DAF (Directeur Administratif et Financier) — module Facturation ────
    if utype == 'daf':
        return redirect('accounts:daf_dashboard')

    # ── Fallback ───────────────────────────────────────────────────────────
    return _bounce_to_login(request, f"Type d'utilisateur non reconnu : {utype}. Contactez l'administrateur.")

#statistiques
############### STATISTIQUES & PAIEMENT MEMBRE ###############

"""
courses/views/statistiques_view.py
Logique d'accès par rôle :
  - admin | dg | agent_comptable | deps  → tout voir
  - dir                                  → sa direction + ses centres
  - gestionnaire | caissier              → son centre uniquement
"""

from django.db.models import Count, Sum, Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from .models import (
    CentreFormation, Direction_reg, Filiere, AnneeScolaire,
    Inscription, Dette, Paiement, CentreEtFiliere, Frais,
)
from accounts.models import Eleve, DirecteurInterRegional, MembreAdministration

import csv, io, json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors as rl_colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


# ─── Helpers ──────────────────────────────────────────────────────────────────

ROUGE  = "#C0392B"
OR     = "#D4A017"
GRIS   = "#6B7280"

def _get_scope(user):
    """
    Retourne (centres_qs, directions_qs, scope_label)
    selon le rôle de l'utilisateur connecté.
    """
    # Un superuser créé via `createsuperuser` ne demande pas user_type
    # et laisse donc la valeur par défaut "eleve" il faut donc le capter ici
    if user.is_superuser:
        return (
            CentreFormation.objects.all(),
            Direction_reg.objects.all(),
            "global",
        )

    utype = user.user_type

    # Niveau 1 : accès total
    if utype in ("admin", "dg", "agent_comptable", "deps"):
        return (
            CentreFormation.objects.all(),
            Direction_reg.objects.all(),
            "global",
        )

    # Directeur Inter-régional : toujours limité à sa propre direction
    # (un directeur ayant besoin d'une portée globale doit être promu vers un
    # rôle qui l'a par défaut — admin/dg/deps — plutôt que via un booléen caché)
    if utype == "dir":
        try:
            dir_obj = DirecteurInterRegional.objects.get(pk=user.pk)
            centres = CentreFormation.objects.filter(direction=dir_obj.direction)
            directions = Direction_reg.objects.filter(pk=dir_obj.direction_id)
            return centres, directions, "direction"
        except DirecteurInterRegional.DoesNotExist:
            pass

    # Gestionnaire / Caissier → son centre uniquement
    if utype in ("gestionnaire", "caissier"):
        try:
            membre = MembreAdministration.objects.get(pk=user.pk)
            if membre.structure:
                centres = CentreFormation.objects.filter(pk=membre.structure_id)
                directions = Direction_reg.objects.filter(
                    pk=membre.structure.direction_id
                ) if membre.structure.direction_id else Direction_reg.objects.none()
                return centres, directions, "centre"
        except MembreAdministration.DoesNotExist:
            pass

    # Fallback : rien
    return CentreFormation.objects.none(), Direction_reg.objects.none(), "none"


def _base_qs(user):
    """
    Retourne les querysets de base filtrés selon le scope de l'utilisateur.
    """
    centres_qs, directions_qs, scope = _get_scope(user)
    centre_ids = list(centres_qs.values_list("id", flat=True))

    inscriptions = Inscription.objects.filter(
        formation__centre_id__in=centre_ids
    )
    dettes = Dette.objects.filter(
        inscription__formation__centre_id__in=centre_ids
    )
    paiements = Paiement.objects.filter(
        dette__inscription__formation__centre_id__in=centre_ids
    )
    return inscriptions, dettes, paiements, centres_qs, directions_qs, scope


def _apply_stats_filters(request, inscriptions_qs, dettes_qs, paiements_qs, scope):
    """
    Applique aux 3 querysets (inscriptions/dettes/paiements) les filtres lus
    dans request.GET. Utilisée à la fois par statistiques_view (affichage
    écran) et par les exports (CSV/Excel/PDF), pour garantir que les exports
    reflètent TOUJOURS exactement ce qui est filtré à l'écran.
    """
    centre_id    = request.GET.get("centre")
    direction_id = request.GET.get("direction")
    filiere_id   = request.GET.get("filiere")
    annee_id     = request.GET.get("annee")
    statut_f     = request.GET.get("statut")
    region_id    = request.GET.get("region")
    genre        = request.GET.get("genre")
    date_debut   = request.GET.get("date_debut")
    date_fin     = request.GET.get("date_fin")

    if direction_id and scope == "global":
        inscriptions_qs = inscriptions_qs.filter(formation__centre__direction_id=direction_id)
        dettes_qs = dettes_qs.filter(inscription__formation__centre__direction_id=direction_id)
        paiements_qs = paiements_qs.filter(dette__inscription__formation__centre__direction_id=direction_id)

    if centre_id and scope in ("global", "direction"):
        inscriptions_qs = inscriptions_qs.filter(formation__centre_id=centre_id)
        dettes_qs = dettes_qs.filter(inscription__formation__centre_id=centre_id)
        paiements_qs = paiements_qs.filter(dette__inscription__formation__centre_id=centre_id)

    if filiere_id:
        inscriptions_qs = inscriptions_qs.filter(formation__filiere_id=filiere_id)
        dettes_qs = dettes_qs.filter(inscription__formation__filiere_id=filiere_id)
        paiements_qs = paiements_qs.filter(dette__inscription__formation__filiere_id=filiere_id)

    if annee_id:
        inscriptions_qs = inscriptions_qs.filter(annee_scolaire_id=annee_id)
        dettes_qs = dettes_qs.filter(inscription__annee_scolaire_id=annee_id)
        paiements_qs = paiements_qs.filter(dette__inscription__annee_scolaire_id=annee_id)

    if statut_f:
        inscriptions_qs = inscriptions_qs.filter(statut=statut_f)
        dettes_qs = dettes_qs.filter(inscription__statut=statut_f)
        paiements_qs = paiements_qs.filter(dette__inscription__statut=statut_f)

    if region_id:
        inscriptions_qs = inscriptions_qs.filter(formation__centre__province__region_id=region_id)
        dettes_qs = dettes_qs.filter(inscription__formation__centre__province__region_id=region_id)
        paiements_qs = paiements_qs.filter(dette__inscription__formation__centre__province__region_id=region_id)

    if genre:
        inscriptions_qs = inscriptions_qs.filter(eleve__sexe=genre)
        dettes_qs = dettes_qs.filter(inscription__eleve__sexe=genre)
        paiements_qs = paiements_qs.filter(dette__inscription__eleve__sexe=genre)

    if date_debut:
        inscriptions_qs = inscriptions_qs.filter(date_inscription__date__gte=date_debut)
        dettes_qs = dettes_qs.filter(inscription__date_inscription__date__gte=date_debut)
        paiements_qs = paiements_qs.filter(dette__inscription__date_inscription__date__gte=date_debut)

    if date_fin:
        inscriptions_qs = inscriptions_qs.filter(date_inscription__date__lte=date_fin)
        dettes_qs = dettes_qs.filter(inscription__date_inscription__date__lte=date_fin)
        paiements_qs = paiements_qs.filter(dette__inscription__date_inscription__date__lte=date_fin)

    filters = {
        "centre_id": centre_id, "direction_id": direction_id, "filiere_id": filiere_id,
        "annee_id": annee_id, "statut_f": statut_f, "region_id": region_id,
        "genre": genre, "date_debut": date_debut, "date_fin": date_fin,
    }
    return inscriptions_qs, dettes_qs, paiements_qs, filters


def _can_access_eleve_finances(user, eleve):
    """
    Contrôle d'accès pour les vues financières d'un élève (dettes/quittances) :
    l'élève lui-même, un superuser, ou un membre du personnel dont le périmètre
    (centre/direction/global) couvre au moins une des inscriptions de l'élève.
    """
    if user.is_superuser:
        return True
    if getattr(user, 'pk', None) == getattr(eleve, 'pk', None):
        return True
    if not user.has_perm('courses.voir_inscriptions'):
        return False
    centres_qs, _, scope = _get_scope(user)
    if scope == "none":
        return False
    if scope == "global":
        return True
    centre_ids = list(centres_qs.values_list("id", flat=True))
    return Inscription.objects.filter(eleve=eleve, formation__centre_id__in=centre_ids).exists()


def _can_access_dette_finances(user, dette):
    """Même contrôle que _can_access_eleve_finances, mais scopé à UNE dette précise."""
    if user.is_superuser:
        return True
    eleve = dette.inscription.eleve
    if getattr(user, 'pk', None) == getattr(eleve, 'pk', None):
        return True
    if not user.has_perm('courses.voir_inscriptions'):
        return False
    centres_qs, _, scope = _get_scope(user)
    if scope == "none":
        return False
    if scope == "global":
        return True
    centre_id = dette.inscription.formation.centre_id if dette.inscription.formation_id else None
    return centre_id is not None and centres_qs.filter(pk=centre_id).exists()


# ─── Vue principale ───────────────────────────────────────────────────────────

@login_required
def statistiques_view(request):
    user = request.user
    inscriptions_qs, dettes_qs, paiements_qs, centres_scope, directions_scope, scope = _base_qs(user)

    inscriptions_qs, dettes_qs, paiements_qs, filters = _apply_stats_filters(
        request, inscriptions_qs, dettes_qs, paiements_qs, scope
    )
    centre_id    = filters["centre_id"]
    direction_id = filters["direction_id"]
    filiere_id   = filters["filiere_id"]
    annee_id     = filters["annee_id"]
    statut_f     = filters["statut_f"]
    region_id    = filters["region_id"]
    genre        = filters["genre"]
    date_debut   = filters["date_debut"]
    date_fin     = filters["date_fin"]

    # Narrowing du dropdown "centre" affiché à l'écran quand une direction est sélectionnée.
    if direction_id and scope == "global":
        centres_scope = centres_scope.filter(direction_id=direction_id)

    # ── KPIs ─────────────────────────────────────────────────────────────────
    total_encaisse = paiements_qs.aggregate(s=Sum("montant_paiement"))["s"] or 0
    total_du       = dettes_qs.aggregate(s=Sum("montant_total"))["s"] or 0
    total_restant  = max(total_du - total_encaisse, 0)
    taux_global    = round(total_encaisse / total_du * 100, 1) if total_du > 0 else 0

    centre_ids_scope = list(centres_scope.values_list("id", flat=True))

    # Champ "Métier" : si un centre précis est sélectionné, ses métiers priment ;
    # sinon on retombe sur les métiers déjà lancés dans les centres du périmètre
    # (centres de la direction sélectionnée pour l'accès national, centres de la
    # direction/du centre de portée pour les accès directionnel/centre) ; en
    # accès national sans aucun filtre, tous les métiers actifs sont proposés.
    if centre_id and scope in ("global", "direction"):
        filieres_scope = Filiere.objects.filter(
            is_active=True, centreetfiliere__centre_id=centre_id
        ).distinct()
    elif scope == "global" and not direction_id:
        filieres_scope = Filiere.objects.filter(is_active=True)
    else:
        filieres_scope = Filiere.objects.filter(
            is_active=True, centreetfiliere__centre_id__in=centre_ids_scope
        ).distinct()

    stats = {
        "total_eleves":           Eleve.objects.filter(inscription__in=inscriptions_qs).distinct().count(),
        "inscriptions_validees":  inscriptions_qs.filter(statut__in=["valide", "valide_paye", "Valide"]).count(),
        "inscriptions_en_cours":  inscriptions_qs.filter(statut="en_cours").count(),
        "inscriptions_rejetees":  inscriptions_qs.filter(statut="rejete").count(),
        "total_encaisse":         total_encaisse,
        "total_restant":          total_restant,
        "total_du":               total_du,
        "taux_global":            taux_global,
        "total_centres":          centres_scope.count(),
        "total_filieres":         filieres_scope.count(),
        "total_directions":       directions_scope.count(),
    }

    # ── Top métiers ───────────────────────────────────────────────────────────
    top_filieres_qs = (
        inscriptions_qs
        .values("formation__filiere__nom_filiere")
        .annotate(count=Count("id"))
        .order_by("-count")[:8]
    )
    top_filieres = [
        {"nom": f["formation__filiere__nom_filiere"] or "—", "count": f["count"]}
        for f in top_filieres_qs
    ]

    # ── Taux de recouvrement par centre ───────────────────────────────────────
    recouvrement_centres = []
    for centre in centres_scope.order_by("nom_centre"):
        c_dettes    = dettes_qs.filter(inscription__formation__centre=centre)
        c_paiements = paiements_qs.filter(dette__inscription__formation__centre=centre)
        c_du  = c_dettes.aggregate(s=Sum("montant_total"))["s"] or 0
        c_enc = c_paiements.aggregate(s=Sum("montant_paiement"))["s"] or 0
        c_rest = max(c_du - c_enc, 0)
        taux = round(c_enc / c_du * 100, 1) if c_du > 0 else 0
        recouvrement_centres.append({
            "nom_centre":   centre.nom_centre,
            "direction":    centre.direction.nom_direction if centre.direction else "—",
            "total_du":     c_du,
            "encaisse":     c_enc,
            "restant":      c_rest,
            "taux":         taux,
            "inscrits":     inscriptions_qs.filter(formation__centre=centre).count(),
        })
    recouvrement_centres.sort(key=lambda x: x["taux"], reverse=True)

    # ── Évolution mensuelle inscriptions (12 derniers mois) ──────────────────
    from django.db.models.functions import TruncMonth
    evol_qs = (
        inscriptions_qs
        .annotate(mois=TruncMonth("date_inscription"))
        .values("mois")
        .annotate(count=Count("id"))
        .order_by("mois")
    )
    evol_labels = []
    evol_data   = []
    MOIS_FR = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]
    for e in evol_qs:
        if e["mois"]:
            evol_labels.append(f"{MOIS_FR[e['mois'].month-1]} {e['mois'].year}")
            evol_data.append(e["count"])

    # ── Paiements par mode ────────────────────────────────────────────────────
    modes = (
        paiements_qs
        .values("mode_paiement")
        .annotate(total=Sum("montant_paiement"))
        .order_by("-total")
    )
    mode_labels = [m["mode_paiement"].capitalize() for m in modes]
    mode_data   = [m["total"] or 0 for m in modes]

    # ── Dernières inscriptions ────────────────────────────────────────────────
    dernieres_inscriptions = (
        inscriptions_qs
        .select_related("eleve", "formation__filiere", "formation__centre", "annee_scolaire")
        .order_by("-date_inscription")[:20]
    )

    from .models import Region
    from accounts.models import Utilisateur

    def _direction_regions(direction_obj):
        """Régions couvertes par une direction (Direction_reg.region, texte
        séparé par virgules — voir DirectionRegForm)."""
        if not direction_obj or not direction_obj.region:
            return Region.objects.none()
        noms = [r.strip() for r in direction_obj.region.split(',') if r.strip()]
        return Region.objects.filter(nom_region__in=noms)

    if scope == "global":
        if direction_id:
            regions_scope = _direction_regions(Direction_reg.objects.filter(pk=direction_id).first())
        else:
            regions_scope = Region.objects.all()
    elif scope == "direction":
        regions_scope = _direction_regions(directions_scope.first())
    else:
        regions_scope = Region.objects.filter(
            provinces__centre_formations__id__in=centre_ids_scope
        ).distinct()

    context = {
        "stats":                  stats,
        "top_filieres":           top_filieres,
        "recouvrement_centres":   recouvrement_centres,
        "dernieres_inscriptions": dernieres_inscriptions,
        "scope":                  scope,
        # Filtres disponibles
        "centres":    centres_scope.order_by("nom_centre"),
        "directions": directions_scope.order_by("nom_direction"),
        "filieres":   filieres_scope.order_by("nom_filiere"),
        "annees":     AnneeScolaire.objects.all().order_by("-libelle_anne"),
        "regions":    regions_scope.order_by("nom_region"),
        "genres":     Utilisateur.SEXE_CHOICE,
        # Valeurs actives des filtres
        "f_centre":     centre_id,
        "f_direction":  direction_id,
        "f_filiere":    filiere_id,
        "f_annee":      annee_id,
        "f_statut":     statut_f,
        "f_region":     region_id,
        "f_genre":      genre,
        "f_date_debut": date_debut,
        "f_date_fin":   date_fin,
        # JSON pour charts
        "evol_labels_json": json.dumps(evol_labels),
        "evol_data_json":   json.dumps(evol_data),
        "mode_labels_json": json.dumps(mode_labels),
        "mode_data_json":   json.dumps(mode_data),
        "top_filieres_json": json.dumps([f["nom"] for f in top_filieres]),
        "top_filieres_count_json": json.dumps([f["count"] for f in top_filieres]),
    }
    return render(request, "member/statistiques/statistiques.html", context)


# ─── Export CSV ───────────────────────────────────────────────────────────────

@login_required
def export_csv(request):
    user = request.user
    inscriptions_qs, dettes_qs, paiements_qs, centres_scope, _, scope = _base_qs(user)
    inscriptions_qs, dettes_qs, paiements_qs, _ = _apply_stats_filters(
        request, inscriptions_qs, dettes_qs, paiements_qs, scope
    )

    export_type = request.GET.get("type", "inscriptions")

    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = f'attachment; filename="export_{export_type}.csv"'

    writer = csv.writer(response, delimiter=";")

    if export_type == "inscriptions":
        writer.writerow(["N°", "Apprenant", "Identifiant", "Sexe", "Téléphone", "Email", "Métier", "Centre", "Direction", "Année", "Statut", "Date inscription"])
        for i, insc in enumerate(
            inscriptions_qs.select_related(
                "eleve", "formation__filiere", "formation__centre__direction", "annee_scolaire"
            ).order_by("-date_inscription"), 1
        ):
            writer.writerow([
                i,
                f"{insc.eleve.nom} {insc.eleve.prenom}" if insc.eleve else "—",
                insc.eleve.numero_identifiant if insc.eleve else "—",
                insc.eleve.get_sexe_display() if insc.eleve else "—",
                insc.eleve.tel if insc.eleve else "—",
                insc.eleve.email if insc.eleve else "—",
                insc.formation.filiere.nom_filiere if insc.formation and insc.formation.filiere else "—",
                insc.formation.centre.nom_centre if insc.formation and insc.formation.centre else "—",
                insc.formation.centre.direction.nom_direction if insc.formation and insc.formation.centre and insc.formation.centre.direction else "—",
                insc.annee_scolaire.libelle_anne if insc.annee_scolaire else "—",
                insc.get_statut_display(),
                insc.date_inscription.strftime("%d/%m/%Y") if insc.date_inscription else "—",
            ])

    elif export_type == "paiements":
        writer.writerow(["N°", "Apprenant", "Quittance", "Montant (FCFA)", "Mode", "Date", "Centre"])
        for i, p in enumerate(
            paiements_qs.select_related(
                "dette__inscription__eleve",
                "dette__inscription__formation__centre",
            ).order_by("-date_paiement"), 1
        ):
            insc = p.dette.inscription if p.dette else None
            eleve = insc.eleve if insc else None
            centre = insc.formation.centre if insc and insc.formation else None
            writer.writerow([
                i,
                f"{eleve.nom} {eleve.prenom}" if eleve else "—",
                p.numero_quittance or "—",
                p.montant_paiement,
                p.mode_paiement,
                p.date_paiement.strftime("%d/%m/%Y") if p.date_paiement else "—",
                centre.nom_centre if centre else "—",
            ])

    elif export_type == "recouvrement":
        writer.writerow(["Centre", "Direction", "Total dû (FCFA)", "Encaissé (FCFA)", "Restant (FCFA)", "Taux (%)"])
        for centre in centres_scope.order_by("nom_centre"):
            c_dettes    = dettes_qs.filter(inscription__formation__centre=centre)
            c_paiements = paiements_qs.filter(dette__inscription__formation__centre=centre)
            c_du   = c_dettes.aggregate(s=Sum("montant_total"))["s"] or 0
            c_enc  = c_paiements.aggregate(s=Sum("montant_paiement"))["s"] or 0
            c_rest = max(c_du - c_enc, 0)
            taux   = round(c_enc / c_du * 100, 1) if c_du > 0 else 0
            writer.writerow([
                centre.nom_centre,
                centre.direction.nom_direction if centre.direction else "—",
                c_du, c_enc, c_rest, taux,
            ])

    return response


# ─── Export Excel ─────────────────────────────────────────────────────────────

@login_required
def export_excel(request):
    user = request.user
    inscriptions_qs, dettes_qs, paiements_qs, centres_scope, _, scope = _base_qs(user)
    inscriptions_qs, dettes_qs, paiements_qs, _ = _apply_stats_filters(
        request, inscriptions_qs, dettes_qs, paiements_qs, scope
    )
    export_type = request.GET.get("type", "inscriptions")

    wb = Workbook()
    ws = wb.active

    rouge_fill = PatternFill("solid", fgColor="C0392B")
    or_fill    = PatternFill("solid", fgColor="D4A017")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    center_align = Alignment(horizontal="center", vertical="center")

    def style_header(row_cells):
        for cell in row_cells:
            cell.fill = rouge_fill
            cell.font = header_font
            cell.alignment = center_align

    if export_type == "inscriptions":
        ws.title = "Inscriptions"
        headers = ["N°","Apprenant","Identifiant","Sexe","Téléphone","Email","Métier","Centre","Direction","Année","Statut","Date"]
        ws.append(headers)
        style_header(ws[1])
        for i, insc in enumerate(
            inscriptions_qs.select_related(
                "eleve","formation__filiere","formation__centre__direction","annee_scolaire"
            ).order_by("-date_inscription"), 1
        ):
            ws.append([
                i,
                f"{insc.eleve.nom} {insc.eleve.prenom}" if insc.eleve else "—",
                insc.eleve.numero_identifiant if insc.eleve else "—",
                insc.eleve.get_sexe_display() if insc.eleve else "—",
                insc.eleve.tel if insc.eleve else "—",
                insc.eleve.email if insc.eleve else "—",
                insc.formation.filiere.nom_filiere if insc.formation and insc.formation.filiere else "—",
                insc.formation.centre.nom_centre if insc.formation and insc.formation.centre else "—",
                insc.formation.centre.direction.nom_direction if insc.formation and insc.formation.centre and insc.formation.centre.direction else "—",
                insc.annee_scolaire.libelle_anne if insc.annee_scolaire else "—",
                insc.get_statut_display(),
                insc.date_inscription.strftime("%d/%m/%Y") if insc.date_inscription else "—",
            ])
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 18

    elif export_type == "recouvrement":
        ws.title = "Recouvrement"
        headers = ["Centre","Direction","Total dû (FCFA)","Encaissé (FCFA)","Restant (FCFA)","Taux (%)"]
        ws.append(headers)
        style_header(ws[1])
        for centre in centres_scope.order_by("nom_centre"):
            c_dettes    = dettes_qs.filter(inscription__formation__centre=centre)
            c_paiements = paiements_qs.filter(dette__inscription__formation__centre=centre)
            c_du   = c_dettes.aggregate(s=Sum("montant_total"))["s"] or 0
            c_enc  = c_paiements.aggregate(s=Sum("montant_paiement"))["s"] or 0
            c_rest = max(c_du - c_enc, 0)
            taux   = round(c_enc / c_du * 100, 1) if c_du > 0 else 0
            ws.append([
                centre.nom_centre,
                centre.direction.nom_direction if centre.direction else "—",
                c_du, c_enc, c_rest, taux,
            ])
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 20

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="export_{export_type}.xlsx"'
    wb.save(response)
    return response


# ─── Export PDF ───────────────────────────────────────────────────────────────

@login_required
def export_pdf(request):
    user = request.user
    inscriptions_qs, dettes_qs, paiements_qs, centres_scope, directions_scope, scope = _base_qs(user)
    inscriptions_qs, dettes_qs, paiements_qs, _ = _apply_stats_filters(
        request, inscriptions_qs, dettes_qs, paiements_qs, scope
    )
    export_type = request.GET.get("type", "inscriptions")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=2*cm, bottomMargin=1.5*cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title_bsb",
        parent=styles["Title"],
        fontSize=16,
        textColor=rl_colors.HexColor("#C0392B"),
        spaceAfter=12,
    )
    sub_style = ParagraphStyle(
        "sub_bsb",
        parent=styles["Normal"],
        fontSize=9,
        textColor=rl_colors.HexColor("#6B7280"),
        spaceAfter=16,
    )
    cell_style = ParagraphStyle(
        "cell_bsb", parent=styles["Normal"], fontSize=8, leading=10,
    )

    def cell(texte):
        """Cellule de tableau avec retour à la ligne au lieu d'une troncature."""
        return Paragraph(str(texte), cell_style)

    rouge = rl_colors.HexColor("#C0392B")
    or_cl = rl_colors.HexColor("#D4A017")
    gris  = rl_colors.HexColor("#F3F4F6")

    def base_table_style(header_rows=1):
        return TableStyle([
            ("BACKGROUND",  (0, 0), (-1, header_rows-1), rouge),
            ("TEXTCOLOR",   (0, 0), (-1, header_rows-1), rl_colors.white),
            ("FONTNAME",    (0, 0), (-1, header_rows-1), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, header_rows-1), 9),
            ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [rl_colors.white, gris]),
            ("FONTSIZE",    (0, header_rows), (-1, -1), 8),
            ("GRID",        (0, 0), (-1, -1), 0.4, rl_colors.HexColor("#E5E7EB")),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",  (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])

    story = []
    now = timezone.now().strftime("%d/%m/%Y %H:%M")

    header_left, header_right = _pdf_header_lines(
        centre=centres_scope.first() if scope == "centre" else None,
        direction=directions_scope.first() if scope == "direction" else None,
    )
    header_line_style = ParagraphStyle(
        "pdf_header_line", parent=styles["Normal"],
        fontSize=6, leading=8, alignment=1, fontName="Helvetica-Bold",
    )
    favicon_path = os.path.join(settings.BASE_DIR, 'static/images/favicon.png')
    header_table = Table(
        [[
            Paragraph("<br/>".join(header_left), header_line_style),
            Image(favicon_path, width=1.6*cm, height=1.6*cm),
            Paragraph("<br/>".join(header_right), header_line_style),
        ]],
        colWidths=[10*cm, 3*cm, 10*cm],
    )
    header_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 12))

    if export_type == "inscriptions":
        story.append(Paragraph("Rapport des Inscriptions — BSB", title_style))
        story.append(Paragraph(f"Généré le {now}  |  {inscriptions_qs.count()} inscription(s)", sub_style))

        data = [["N°", "Apprenant", "Identifiant", "Métier", "Centre", "Année", "Statut", "Date"]]
        for i, insc in enumerate(
            inscriptions_qs.select_related(
                "eleve","formation__filiere","formation__centre","annee_scolaire"
            ).order_by("-date_inscription")[:500], 1
        ):
            data.append([
                str(i),
                cell(f"{insc.eleve.nom} {insc.eleve.prenom}") if insc.eleve else "—",
                cell(insc.eleve.numero_identifiant) if insc.eleve and insc.eleve.numero_identifiant else "—",
                cell(insc.formation.filiere.nom_filiere) if insc.formation and insc.formation.filiere else "—",
                cell(insc.formation.centre.nom_centre) if insc.formation and insc.formation.centre else "—",
                insc.annee_scolaire.libelle_anne if insc.annee_scolaire else "—",
                cell(insc.get_statut_display()),
                insc.date_inscription.strftime("%d/%m/%Y") if insc.date_inscription else "—",
            ])

        col_widths = [1.2*cm, 4.5*cm, 3.5*cm, 4*cm, 4*cm, 2.5*cm, 4*cm, 2.5*cm]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(base_table_style())
        story.append(t)

    elif export_type == "recouvrement":
        story.append(Paragraph("Rapport de Recouvrement par Centre — BSB", title_style))
        story.append(Paragraph(f"Généré le {now}", sub_style))

        data = [["Centre", "Direction", "Total dû (FCFA)", "Encaissé (FCFA)", "Restant (FCFA)", "Taux (%)"]]
        for centre in centres_scope.order_by("nom_centre"):
            c_dettes    = dettes_qs.filter(inscription__formation__centre=centre)
            c_paiements = paiements_qs.filter(dette__inscription__formation__centre=centre)
            c_du   = c_dettes.aggregate(s=Sum("montant_total"))["s"] or 0
            c_enc  = c_paiements.aggregate(s=Sum("montant_paiement"))["s"] or 0
            c_rest = max(c_du - c_enc, 0)
            taux   = round(c_enc / c_du * 100, 1) if c_du > 0 else 0
            data.append([
                cell(centre.nom_centre),
                cell(centre.direction.nom_direction) if centre.direction else "—",
                f"{c_du:,.0f}".replace(",", " "),
                f"{c_enc:,.0f}".replace(",", " "),
                f"{c_rest:,.0f}".replace(",", " "),
                f"{taux}%",
            ])

        col_widths = [5*cm, 5*cm, 4.5*cm, 4.5*cm, 4.5*cm, 3*cm]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(base_table_style())
        story.append(t)

    signataire = {
        "centre": "Le Gestionnaire du centre",
        "direction": "Le Directeur Inter-Régional",
        "global": "Le Directeur Général",
    }.get(scope, "Le Directeur Général")
    signature_style = ParagraphStyle(
        "signature_bsb", parent=styles["Normal"], fontSize=10,
        alignment=2, spaceBefore=28,
    )
    story.append(Paragraph(signataire, signature_style))

    footer_style = ParagraphStyle(
        "footer_bsb", parent=styles["Normal"], fontSize=7,
        textColor=rl_colors.grey, alignment=1, spaceBefore=24,
    )
    story.append(Paragraph(f"BSB-DSI          généré sur YU-PAAN le : {now}", footer_style))

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="rapport_{export_type}.pdf"'
    return response


# ─────────────────────────────────────────────
# DETTES D'UN ÉLÈVE (groupées par inscription)
# ─────────────────────────────────────────────
@login_required
def stats_dettes_eleve_view(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)

    if not _can_access_eleve_finances(request.user, eleve):
        raise PermissionDenied("Vous n'avez pas accès aux informations financières de cet apprenant.")

    inscriptions = (
        Inscription.objects
        .filter(eleve=eleve)
        .exclude(statut='rejete')
        .select_related('formation__filiere', 'formation__centre', 'annee_scolaire')
        .prefetch_related('dettes__frais_formation__type_frais__tranches', 'dettes__paiements')
        .order_by('-date_inscription')
    )

    if not request.user.is_superuser and getattr(request.user, 'pk', None) != eleve.pk:
        centres_qs, _, scope = _get_scope(request.user)
        if scope != "global":
            centre_ids = list(centres_qs.values_list("id", flat=True))
            inscriptions = inscriptions.filter(formation__centre_id__in=centre_ids)

    inscription_id = request.GET.get('inscription')
    if inscription_id:
        inscriptions = inscriptions.filter(id=inscription_id)

    inscriptions_dettes = []
    total_restant_global = 0

    for insc in inscriptions:
        dettes_data = []
        insc_du = 0
        insc_paye = 0

        for dette in insc.dettes.all():
            paye = dette.montant_paye()
            reste = dette.reste_a_payer()
            taux = (paye / dette.montant_total * 100) if dette.montant_total > 0 else 0
            insc_du += dette.montant_total
            insc_paye += paye
            total_restant_global += max(reste, 0)

            dettes_data.append({
                'id': dette.id,
                'frais_formation': dette.frais_formation,
                'montant_total': dette.montant_total,
                'montant_paye': paye,
                'reste': max(reste, 0),
                'taux': min(round(taux, 1), 100),
                'etat_dette': dette.etat_dette,
                'tranches': dette.tranches_detail(),
                'bloquee': dette.bloquee_par_autre_dette(),
                'montant_a_payer': dette.montant_a_payer(),
            })

        inscriptions_dettes.append({
            'inscription': insc,
            'dettes': dettes_data,
            'total_du': insc_du,
            'total_paye': insc_paye,
        })

    return render(request, 'member/statistiques/stats_dettes_eleve.html', {
        'eleve': eleve,
        'inscriptions_dettes': inscriptions_dettes,
        'total_restant': total_restant_global,
    })


# ─────────────────────────────────────────────
# DÉTAIL D'UNE DETTE (tranches + modal paiement)
# ─────────────────────────────────────────────
@login_required
def stats_detail_dette_view(request, dette_id):
    dette = get_object_or_404(
        Dette.objects.select_related(
            'inscription__eleve',
            'inscription__formation__filiere',
            'inscription__formation__centre',
            'inscription__annee_scolaire',
            'frais_formation__type_frais',
        ).prefetch_related('paiements'),
        id=dette_id
    )
    eleve = dette.inscription.eleve

    if not _can_access_dette_finances(request.user, dette):
        raise PermissionDenied("Vous n'avez pas accès aux informations financières de cette dette.")

    if request.method == 'POST':
        if not (request.user.is_superuser or request.user.has_perm('courses.encaisser_paiement')):
            raise PermissionDenied("Vous n'avez pas la permission d'encaisser un paiement.")

        # Ordre de paiement : la tranche primordiale d'une autre dette de la
        # même inscription doit être intégralement réglée avant celle-ci.
        dette_bloquante, tranche_bloquante = dette.inscription.dette_et_tranche_bloquantes()
        if dette_bloquante and dette_bloquante.id != dette.id:
            messages.error(
                request,
                f"Il faut d'abord régler entièrement la tranche « {tranche_bloquante.libelle} » "
                f"de « {dette_bloquante.frais_formation.type_frais} »."
            )
            return redirect('courses:stats_detail_dette', dette_id=dette_id)

        montant_str = request.POST.get('montant_paiement', '').strip()
        mode = request.POST.get('mode_paiement', 'mobile')

        try:
            montant = float(montant_str)
        except (ValueError, TypeError):
            messages.error(request, "Montant invalide.")
            return redirect('courses:stats_detail_dette', dette_id=dette_id)

        tranche_cible = dette.tranche_a_payer()
        montant_cible = dette.montant_a_payer()

        if montant <= 0:
            messages.error(request, "Le montant doit être supérieur à 0.")
            return redirect('courses:stats_detail_dette', dette_id=dette_id)

        if montant > montant_cible:
            messages.error(request, f"Le montant saisi ({montant:,.0f} FCFA) dépasse le montant dû ({montant_cible:,.0f} FCFA).")
            return redirect('courses:stats_detail_dette', dette_id=dette_id)

        # Sous-paiement d'une tranche primordiale : motif + pièce jointe obligatoires.
        motif_derogation = None
        piece_jointe_derogation = None
        if tranche_cible and tranche_cible.est_primordiale and montant < montant_cible:
            motif_derogation = request.POST.get('motif_derogation', '').strip()
            piece_jointe_derogation = request.FILES.get('piece_jointe_derogation')
            if not motif_derogation or not piece_jointe_derogation:
                messages.error(
                    request,
                    "Un motif et une pièce jointe justificative sont obligatoires pour valider un "
                    "règlement inférieur au montant dû de la tranche primordiale."
                )
                return redirect('courses:stats_detail_dette', dette_id=dette_id)

        tranche_num = dette.paiements.count() + 1

        paiement = Paiement(
            dette=dette,
            montant_paiement=montant,
            mode_paiement=mode,
            tranche=tranche_num,
            tranche_frais=tranche_cible,
            date_paiement=timezone.now(),
            cree_par=request.user,  # ← ici
            motif_derogation=motif_derogation,
            piece_jointe_derogation=piece_jointe_derogation,
        )
        paiement.save()

        # Mettre à jour l'état de la dette si soldée. `dette.paiements` a été
        # préchargée (prefetch_related) avant la création du paiement ci-dessus ;
        # `dette.paiements.all()` réutiliserait ce cache obsolète (sans le
        # paiement qu'on vient de créer), d'où une requête indépendante ici.
        total_paye = Paiement.objects.filter(dette_id=dette.id).aggregate(s=Sum('montant_paiement'))['s'] or 0
        if dette.montant_total - total_paye <= 0:
            dette.etat_dette = 'soldé'
            dette.save()

        messages.success(request, f"Paiement de {montant:,.0f} FCFA enregistré — Tranche {tranche_num}.")
        return redirect('courses:stats_detail_dette', dette_id=dette_id)

    paiements = dette.paiements.order_by('-date_paiement', '-tranche')
    montant_paye = dette.montant_paye()
    reste = dette.reste_a_payer()
    taux = (montant_paye / dette.montant_total * 100) if dette.montant_total > 0 else 0

    tranche_cible = dette.tranche_a_payer()
    montant_cible = dette.montant_a_payer()
    bloquee = dette.bloquee_par_autre_dette()

    return render(request, 'member/statistiques/stats_detail_dette.html', {
        'dette': dette,
        'eleve': eleve,
        'paiements': paiements,
        'montant_paye': montant_paye,
        'reste': max(reste, 0),
        'taux': min(round(taux, 1), 100),
        'tranches_data': dette.tranches_detail(),
        'tranche_cible': tranche_cible,
        'montant_cible': montant_cible,
        'bloquee': bloquee,
    })


# ─────────────────────────────────────────────
# QUITTANCE D'UNE TRANCHE (liste des paiements)
# ─────────────────────────────────────────────
@login_required
def stats_quittance_tranche_view(request, dette_id, tranche):
    dette = get_object_or_404(
        Dette.objects.select_related(
            'inscription__eleve',
            'inscription__formation__filiere',
            'inscription__formation__centre',
            'inscription__annee_scolaire',
            'frais_formation__type_frais',
        ),
        id=dette_id
    )

    if not _can_access_dette_finances(request.user, dette):
        raise PermissionDenied("Vous n'avez pas accès aux informations financières de cette dette.")

    paiements = dette.paiements.filter(tranche=tranche).order_by('date_paiement')

    return render(request, 'member/statistiques/stats_quittance_tranche.html', {
        'dette': dette,
        'eleve': dette.inscription.eleve,
        'tranche': tranche,
        'paiements': paiements,
    })


# ─────────────────────────────────────────────
# TÉLÉCHARGER QUITTANCE PDF (réutilisable)
# ─────────────────────────────────────────────
@login_required
def stats_download_quittance_view(request, paiement_id):
    paiement = get_object_or_404(
        Paiement.objects.select_related(
            'dette__inscription__eleve',
            'dette__inscription__formation__filiere',
            'dette__inscription__formation__centre',
            'dette__inscription__annee_scolaire',
            'dette__frais_formation__type_frais',
        ),
        id=paiement_id
    )
    dette = paiement.dette
    inscription = dette.inscription
    eleve = inscription.eleve

    if not _can_access_dette_finances(request.user, dette):
        raise PermissionDenied("Vous n'avez pas accès à cette quittance.")

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A5)
    width, height = A5

    favicon_path = os.path.join(settings.BASE_DIR, 'static/images/favicon.png')
    header_left, header_right = _pdf_header_lines(inscription.formation.centre)
    line_h = 0.28*cm
    y_left = height - 0.6*cm
    p.setFont("Helvetica-Bold", 5.5)
    for line in header_left:
        p.drawString(0.6*cm, y_left, line)
        y_left -= line_h
    y_right = height - 0.6*cm
    for line in header_right:
        p.drawRightString(width-0.6*cm, y_right, line)
        y_right -= line_h
    try:
        p.drawImage(ImageReader(favicon_path), x=width/2-0.9*cm, y=height-2.2*cm,
                    width=1.8*cm, height=1.8*cm, preserveAspectRatio=True, mask='auto')
    except Exception:
        pass

    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width/2, height-3.8*cm, "QUITTANCE DE PAIEMENT")
    p.setFont("Helvetica", 9)
    p.drawCentredString(width/2, height-4.4*cm, "Burkina Suudu Bawdè")

    y = height - 5.2*cm
    p.setLineWidth(0.8)
    p.line(1.5*cm, y, width-1.5*cm, y)

    def ligne(label, valeur, y_pos):
        p.setFont("Helvetica-Bold", 10)
        p.drawString(1.5*cm, y_pos, label)
        p.setFont("Helvetica", 10)
        p.drawString(7*cm, y_pos, str(valeur))
        return y_pos - 0.5*cm   # <-- était 0.7*cm

    y -= 0.5*cm
    y = ligne("Numéro de quittance :", paiement.numero_quittance, y)
    y = ligne("Date de paiement :", paiement.date_paiement.strftime("%d/%m/%Y à %H:%M"), y)
    y -= 0.3*cm
    p.setDash(3, 3); p.line(1.5*cm, y, width-1.5*cm, y); p.setDash(); y -= 0.5*cm

    y = ligne("Apprenant :", f"{eleve.nom} {eleve.prenom}", y)
    y = ligne("Identifiant :", eleve.numero_identifiant or "—", y)
    y = ligne("Centre :", str(inscription.formation.centre), y)
    y = ligne("Métier :", str(inscription.formation.filiere), y)
    y = ligne("Année scolaire :", str(inscription.annee_scolaire or "—"), y)
    y -= 0.3*cm
    p.setDash(3, 3); p.line(1.5*cm, y, width-1.5*cm, y); p.setDash(); y -= 0.5*cm

    y = ligne("Type de frais :", str(dette.frais_formation.type_frais.libelle), y)
    y = ligne("Tranche :", f"Tranche {paiement.tranche}", y)
    y = ligne("Mode de paiement :", paiement.get_mode_paiement_display(), y)

    p.setFont("Helvetica-Bold", 12)
    p.drawString(1.5*cm, y, "Montant payé :")
    p.drawString(7*cm, y, f"{paiement.montant_paiement:,.0f} FCFA")
    y -= 0.7*cm; y -= 0.3*cm
    p.setDash(3, 3); p.line(1.5*cm, y, width-1.5*cm, y); p.setDash(); y -= 0.5*cm

    y = ligne("Total dû :", f"{dette.montant_total:,.0f} FCFA", y)
    y = ligne("Total payé :", f"{dette.montant_paye():,.0f} FCFA", y)
    y = ligne("Reste à payer :", f"{dette.reste_a_payer():,.0f} FCFA", y)
    y = ligne("État de la dette :", dette.get_etat_dette_display(), y)

    # QR Code
    qr_data = (
        f"Quittance : {paiement.numero_quittance}\n"
        f"Date : {paiement.date_paiement.strftime('%d/%m/%Y à %H:%M')}\n"
        f"Apprenant : {eleve.nom} {eleve.prenom}\n"
        f"Centre : {inscription.formation.centre}\n"
        f"Métier : {inscription.formation.filiere}\n"
        f"Montant payé : {paiement.montant_paiement:,.0f} FCFA\n"
        f"Reste à payer : {dette.reste_a_payer():,.0f} FCFA"
    )
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    qr_size = 3*cm
    p.drawImage(ImageReader(qr_buffer), x=(width-qr_size)/2, y=1.8*cm,
                width=qr_size, height=qr_size)
    p.setFont("Helvetica-Oblique", 7)
    p.setFillColor(colors.grey)
    p.drawCentredString(width/2, 1.6*cm, "Scannez pour vérifier")
    p.drawCentredString(width/2, 1*cm,
                        f"BSB-DSI          généré sur YU-PAAN le : {timezone.now().strftime('%d/%m/%Y à %H:%M')}")
    p.showPage()
    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="quittance_{paiement.numero_quittance}.pdf"'
    )
    return response

# courses/views/center_views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Q

from courses.models import CentreFormation, Filiere, CentreEtFiliere, Direction_reg
from courses.forms import CentreFormationForm


# ── LIST ──────────────────────────────────────────────────────────────────────
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views import View
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q

from courses.models import CentreFormation, Direction_reg


@method_decorator(login_required, name='dispatch')
@method_decorator(require_permission('courses.gerer_centres'), name='dispatch')
class CenterListView(View):
    template_name = 'admin/center/list.html'

    def get(self, request):
        q = request.GET.get('q', '').strip()
        direction_id = request.GET.get('direction', '').strip()
        niveau = request.GET.get('niveau', '').strip()

        qs = (
            CentreFormation.objects
            .filter(pk__in=_get_scope(request.user)[0])
            .select_related('direction', 'province')
            .order_by('nom_centre')
        )

        # 🔍 SEARCH GLOBAL
        if q:
            qs = qs.filter(
                Q(nom_centre__icontains=q) |
                Q(adresse__icontains=q) |
                Q(province__nom_province__icontains=q)  # ← adapter au nom exact du champ sur Province
            ).distinct()

        # 🏢 FILTER DIRECTION (SAFE)
        if direction_id and direction_id.isdigit():
            qs = qs.filter(direction_id=int(direction_id))

        # 🎯 FILTER NIVEAU (SAFE - IMPORTANT FIX)
        if niveau and niveau.isdigit():
            qs = qs.filter(niveau_centre=int(niveau))
        else:
            niveau = ''  # ← reset pour éviter qu'une valeur invalide soit renvoyée au template

        # 📄 PAGINATION SAFE
        try:
            page_number = int(request.GET.get('page', 1))
            if page_number < 1:
                page_number = 1
        except (ValueError, TypeError):
            page_number = 1

        paginator = Paginator(qs, 10)
        centers = paginator.get_page(page_number)

        # 📌 LISTE DIRECTIONS
        directions = Direction_reg.objects.all().order_by('nom_direction')

        # 📌 LISTE NIVEAUX PROPRES (sans NULL)
        niveaux = (
            CentreFormation.objects
            .exclude(niveau_centre__isnull=True)
            .values_list('niveau_centre', flat=True)
            .distinct()
            .order_by('niveau_centre')
        )

        return render(request, self.template_name, {
            'centers': centers,
            'q': q,
            'direction_id': direction_id,
            'niveau': niveau,
            'directions': directions,
            'niveaux': niveaux,
        })

# ── CREATE ────────────────────────────────────────────────────────────────────
@method_decorator(require_permission('courses.gerer_centres'), name='dispatch')
class CenterCreateView(View):
    template_name = 'admin/center/form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form':     CentreFormationForm(direction_queryset=_get_scope(request.user)[1]),
            #'filieres': Filiere.objects.all().order_by('nom_filiere'),
            'title':    'Créer un centre',
            'action':   'Créer',
        })

    def post(self, request):
        form = CentreFormationForm(request.POST, direction_queryset=_get_scope(request.user)[1])
        if form.is_valid():
            centre = form.save()
            messages.success(request, f'Le centre « {centre.nom_centre} » a été créé avec succès.')
            next_url = request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect('bsb_admin:center_list')
        return render(request, self.template_name, {
            'form': form, 'title': 'Créer un centre', 'action': 'Créer',
        })


# ── UPDATE ────────────────────────────────────────────────────────────────────
@method_decorator(require_permission('courses.gerer_centres'), name='dispatch')
class CenterUpdateView(View):
    template_name = 'admin/center/form.html'

    def get(self, request, pk):
        centre   = get_object_or_404(CentreFormation, pk=pk, pk__in=_get_scope(request.user)[0])
        filieres = Filiere.objects.all().order_by('nom_filiere')
        current_filieres = list(
            CentreEtFiliere.objects.filter(centre=centre).values_list('filiere_id', flat=True)
        )
        return render(request, self.template_name, {
            'form':   CentreFormationForm(instance=centre, direction_queryset=_get_scope(request.user)[1]),
            'title':  f'Modifier — {centre.nom_centre}',
            'action': 'Modifier',
        })

    def post(self, request, pk):
        centre   = get_object_or_404(CentreFormation, pk=pk, pk__in=_get_scope(request.user)[0])
        form     = CentreFormationForm(request.POST, instance=centre, direction_queryset=_get_scope(request.user)[1])
        filieres = Filiere.objects.all().order_by('nom_filiere')
        if form.is_valid():
            centre = form.save()
            messages.success(request, f'Le centre « {centre.nom_centre} » a été modifié avec succès.')
            next_url = request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect('bsb_admin:center_list')
        return render(request, self.template_name, {
            'form': form, 'title': f'Modifier — {centre.nom_centre}', 'action': 'Modifier',
        })


# ── DELETE ────────────────────────────────────────────────────────────────────
@method_decorator(require_permission('courses.gerer_centres'), name='dispatch')
class CenterDeleteView(View):
    template_name = 'admin/center/confirm_delete.html'

    def get(self, request, pk):
        centre = get_object_or_404(CentreFormation, pk=pk, pk__in=_get_scope(request.user)[0])
        return render(request, self.template_name, {'object': centre})

    def post(self, request, pk):
        centre = get_object_or_404(CentreFormation, pk=pk, pk__in=_get_scope(request.user)[0])
        nom    = centre.nom_centre
        centre.delete()
        messages.success(request, f'Le centre « {nom} » a été supprimé définitivement.')
        return redirect('bsb_admin:center_list')
    
    # ── CENTER FILIERES DETAIL ────────────────────────────────────────────────────
@method_decorator(login_required, name='dispatch')
class CenterFiliereListView(View):
    template_name = 'admin/center/filieres.html'

    def get(self, request, pk):
        centre = get_object_or_404(CentreFormation, pk=pk)
        centre_filieres = (
            CentreEtFiliere.objects
            .filter(centre=centre)
            .select_related('filiere', 'annee_prog')
            .order_by('filiere__nom_filiere')
        )
        paginator = Paginator(centre_filieres, 10)
        page_obj  = paginator.get_page(request.GET.get('page'))

        return render(request, self.template_name, {
            'centre':     centre,
            'page_obj':   page_obj,
        })
        
from django.http import HttpResponse
from django.db.models import Count, Sum, Q
import csv
import io

@require_role('formateur')
def formateur_dashboard(request):
    try:
        formateur = request.user.formateur
    except Exception:
        messages.error(request, "Profil formateur introuvable.")
        return redirect('accounts:login')

    centre = formateur.centre

    # Formations actives dans son centre pour son métier
    if formateur.filiere_id:
        formations = CentreEtFiliere.objects.filter(
            centre=centre,
            filiere_id=formateur.filiere_id,
            is_active=True
        ).select_related('filiere', 'annee_prog').prefetch_related('frais_set')
    else:
        formations = CentreEtFiliere.objects.none()

    # Stats globales
    total_inscrits = Inscription.objects.filter(
        formation__in=formations
    ).count()

    total_valides = Inscription.objects.filter(
        formation__in=formations,
        statut__in=['valide', 'valide_paye', 'Valide']
    ).count()

    # Vraiement inscrits = ont payé au moins quelque chose
    total_vrais = Inscription.objects.filter(
        formation__in=formations,
        dettes__paiements__isnull=False
    ).distinct().count()

    # Stats par filière
    stats_filieres = []
    for formation in formations:
        inscrits = Inscription.objects.filter(formation=formation)
        vrais = inscrits.filter(dettes__paiements__isnull=False).distinct()
        stats_filieres.append({
            'formation': formation,
            'total_inscrits': inscrits.count(),
            'total_valides': inscrits.filter(
                statut__in=['valide', 'valide_paye', 'Valide']
            ).count(),
            'vrais_inscrits': vrais.count(),
            'total_encaisse': Paiement.objects.filter(
                dette__inscription__formation=formation
            ).aggregate(s=Sum('montant_paiement'))['s'] or 0,
        })

    context = {
        'formateur': formateur,
        'centre': centre,
        'stats_filieres': stats_filieres,
        'total_inscrits': total_inscrits,
        'total_valides': total_valides,
        'total_vrais': total_vrais,
        'total_formations': formations.count(),
    }
    return render(request, 'teacher/dashboard/dashboard/dashboard.html', context)


@require_role('formateur')
def formateur_filieres(request):
    try:
        formateur = request.user.formateur
    except Exception:
        return redirect('accounts:login')

    if formateur.filiere_id:
        formations = CentreEtFiliere.objects.filter(
            centre=formateur.centre,
            filiere_id=formateur.filiere_id,
        ).select_related('filiere', 'annee_prog').order_by('filiere__nom_filiere')
    else:
        formations = CentreEtFiliere.objects.none()

    paginator = Paginator(formations, 10)
    page = request.GET.get('page')
    formations = paginator.get_page(page)

    return render(request, 'teacher/filieres/list.html', {
        'formations': formations,
        'formateur': formateur,
    })


@require_role('formateur')
def formateur_etudiants(request, formation_id):
    try:
        formateur = request.user.formateur
    except Exception:
        return redirect('accounts:login')

    formation = get_object_or_404(
        CentreEtFiliere,
        id=formation_id,
        centre=formateur.centre,
        filiere_id=formateur.filiere_id
    )

    # Filtres
    statut_filter = request.GET.get('statut', '')  # 'vrais' | 'valide' | '' (tous)
    q = request.GET.get('q', '').strip()

    inscriptions = Inscription.objects.filter(
        formation=formation
    ).select_related(
        'eleve', 'annee_scolaire'
    ).prefetch_related(
        'dettes__paiements'
    ).order_by('eleve__nom', 'eleve__prenom')

    if q:
        inscriptions = inscriptions.filter(
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q) |
            Q(eleve__numero_identifiant__icontains=q)
        )

    if statut_filter == 'vrais':
        inscriptions = inscriptions.filter(
            dettes__paiements__isnull=False
        ).distinct()
    elif statut_filter == 'valide':
        inscriptions = inscriptions.filter(
            statut__in=['valide', 'valide_paye', 'Valide']
        )

    # Enrichissement pour affichage
    inscrits_data = []
    for insc in inscriptions:
        total_du = sum(d.montant_total for d in insc.dettes.all())
        total_paye = sum(
            p.montant_paiement
            for d in insc.dettes.all()
            for p in d.paiements.all()
        )
        inscrits_data.append({
            'inscription': insc,
            'eleve': insc.eleve,
            'total_du': total_du,
            'total_paye': total_paye,
            'reste': total_du - total_paye,
            'a_paye': total_paye > 0,
        })

    paginator = Paginator(inscrits_data, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'formation': formation,
        'formateur': formateur,
        'page_obj': page_obj,
        'inscrits_data': inscrits_data,
        'statut_filter': statut_filter,
        'q': q,
        'total_tous': inscriptions.count(),
        'total_vrais': sum(1 for d in inscrits_data if d['a_paye']),
    }
    return render(request, 'teacher/filieres/etudiants.html', context)


@require_role('formateur')
def formateur_export(request, formation_id, format):
    try:
        formateur = request.user.formateur
    except Exception:
        return redirect('accounts:login')

    formation = get_object_or_404(
        CentreEtFiliere,
        id=formation_id,
        centre=formateur.centre,
        filiere_id=formateur.filiere_id
    )

    statut_filter = request.GET.get('statut', '')
    q = request.GET.get('q', '').strip()

    inscriptions = Inscription.objects.filter(
        formation=formation
    ).select_related('eleve', 'annee_scolaire').prefetch_related('dettes__paiements')

    if q:
        inscriptions = inscriptions.filter(
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q) |
            Q(eleve__numero_identifiant__icontains=q)
        )
    if statut_filter == 'vrais':
        inscriptions = inscriptions.filter(
            dettes__paiements__isnull=False
        ).distinct()
    elif statut_filter == 'valide':
        inscriptions = inscriptions.filter(
            statut__in=['valide', 'valide_paye', 'Valide']
        )

    # Préparer les données
    rows = []
    for i, insc in enumerate(inscriptions, 1):
        total_du = sum(d.montant_total for d in insc.dettes.all())
        total_paye = sum(
            p.montant_paiement for d in insc.dettes.all() for p in d.paiements.all()
        )
        rows.append({
            'N°': i,
            'Identifiant': insc.eleve.numero_identifiant or '—',
            'Nom': insc.eleve.nom,
            'Prénom': insc.eleve.prenom,
            'Sexe': insc.eleve.get_sexe_display() if hasattr(insc.eleve, 'get_sexe_display') else insc.eleve.sexe,
            'Téléphone': insc.eleve.tel or '—',
            'Email': insc.eleve.email,
            'Statut inscription': insc.get_statut_display(),
            'Total dû (FCFA)': total_du,
            'Total payé (FCFA)': total_paye,
            'Reste (FCFA)': total_du - total_paye,
            'A payé': 'Oui' if total_paye > 0 else 'Non',
        })

    label = f"{formation.filiere.nom_filiere}_{formation.centre.nom_centre}"

    # En-têtes fixes (mêmes noms de colonnes que les données), écrites
    # inconditionnellement — même logique que les exports de statistiques.
    headers = [
        'N°', 'Identifiant', 'Nom', 'Prénom', 'Sexe', 'Téléphone', 'Email',
        'Statut inscription', 'Total dû (FCFA)', 'Total payé (FCFA)', 'Reste (FCFA)', 'A payé',
    ]

    # ── CSV ──────────────────────────────────────────────────────────────────
    if format == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="etudiants_{label}.csv"'
        writer = csv.DictWriter(response, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        return response

    # ── XLSX ─────────────────────────────────────────────────────────────────
    elif format == 'xlsx':
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            messages.error(request, "openpyxl non installé. Lancez : pip install openpyxl")
            return redirect('courses:formateur_etudiants', formation_id=formation_id)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Étudiants"

        # En-tête titre
        titre = f"Liste des étudiants — {formation.filiere.nom_filiere} — {formation.centre.nom_centre}"
        ws.merge_cells('A1:L1')
        ws['A1'] = titre
        ws['A1'].font = Font(bold=True, size=13)
        ws['A1'].alignment = Alignment(horizontal='center')

        # En-têtes colonnes — écrites inconditionnellement, qu'il y ait ou non des lignes.
        header_fill = PatternFill("solid", fgColor="D4A017")
        thin = Side(style='thin')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        ws.append([])  # ligne vide après titre
        ws.append(headers)
        header_row = ws.max_row
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col_idx)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border

        # Données
        for row in rows:
            ws.append(list(row.values()))
            data_row = ws.max_row
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=data_row, column=col_idx)
                cell.border = border
                cell.alignment = Alignment(horizontal='left')
                # Colorier en vert si a payé
                if headers[col_idx - 1] == 'A payé' and cell.value == 'Oui':
                    cell.fill = PatternFill("solid", fgColor="C6EFCE")
                elif headers[col_idx - 1] == 'A payé' and cell.value == 'Non':
                    cell.fill = PatternFill("solid", fgColor="FFC7CE")

        # Largeur colonnes auto
        for col in ws.columns:
            max_len = max(
                (len(str(c.value or '')) for c in col),
                default=10
            )
            first_valid_cell = next(
                (cell for cell in col if not isinstance(cell, MergedCell)),
                None
            )
            if first_valid_cell:
                column_letter = get_column_letter(first_valid_cell.column)
                ws.column_dimensions[column_letter].width = min(max_len + 4, 40)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="etudiants_{label}.xlsx"'
        return response

    # ── PDF ──────────────────────────────────────────────────────────────────
    elif format == 'pdf':
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors as rl_colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=1.5*cm, rightMargin=1.5*cm,
            topMargin=1.5*cm, bottomMargin=1.5*cm
        )
        styles = getSampleStyleSheet()
        elements = []

        # Titre
        title_style = ParagraphStyle(
            'title', parent=styles['Heading1'],
            fontSize=14, spaceAfter=6, alignment=1
        )
        sub_style = ParagraphStyle(
            'sub', parent=styles['Normal'],
            fontSize=9, spaceAfter=12, alignment=1, textColor=rl_colors.grey
        )
        elements.append(Paragraph(
            f"Liste des étudiants — {formation.filiere.nom_filiere}", title_style
        ))
        elements.append(Paragraph(
            f"Centre : {formation.centre.nom_centre} | Filtre : {statut_filter or 'Tous'} | Total : {len(rows)}",
            sub_style
        ))
        elements.append(Spacer(1, 0.3*cm))

        data = [headers] + [list(r.values()) for r in rows]
        if not rows:
            elements.append(Paragraph("Aucun étudiant trouvé.", styles['Normal']))
        col_count = len(headers)
        page_w = landscape(A4)[0] - 3*cm
        col_w = page_w / col_count

        table = Table(data, colWidths=[col_w] * col_count, repeatRows=1)
        table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#D4A017')),
                ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor('#F9FAFB')]),
                ('GRID', (0, 0), (-1, -1), 0.4, rl_colors.HexColor('#E5E7EB')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)

        signature_style = ParagraphStyle(
            'signature', parent=styles['Normal'], fontSize=10,
            alignment=2, spaceBefore=28,
        )
        elements.append(Paragraph(f"Le Formateur — {formateur.nom} {formateur.prenom}", signature_style))

        footer_style = ParagraphStyle(
            'footer_bsb', parent=styles['Normal'], fontSize=7,
            textColor=rl_colors.grey, alignment=1, spaceBefore=24,
        )
        elements.append(Paragraph(
            f"BSB-DSI          généré sur YU-PAAN le : {timezone.now().strftime('%d/%m/%Y à %H:%M')}",
            footer_style
        ))

        doc.build(elements)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="etudiants_{label}.pdf"'
        return response

    return redirect('courses:formateur_etudiants', formation_id=formation_id)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count

# Adapte ces imports selon ton app
from .models import Region, Province


# ──────────────────────────────────────────────
#  RÉGION — Liste + filtres
# ──────────────────────────────────────────────

@login_required
def region_list(request):
    """Liste des régions avec leurs provinces, filtres et pagination."""
    q = request.GET.get("q", "").strip()
    chef_lieu_filter = request.GET.get("chef_lieu", "").strip()

    regions = Region.objects.annotate(nb_provinces=Count("provinces")).order_by("nom_region")

    if q:
        regions = regions.filter(
            Q(nom_region__icontains=q) | Q(chef_lieu__icontains=q)
        )
    if chef_lieu_filter:
        regions = regions.filter(chef_lieu__icontains=chef_lieu_filter)

    paginator = Paginator(regions, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Pour le filtre chef-lieu (valeurs distinctes)
    chefs_lieux = Region.objects.values_list("chef_lieu", flat=True).distinct().order_by("chef_lieu")

    return render(request, "admin/region/region_list.html", {
        "regions": page_obj,
        "q": q,
        "chef_lieu_filter": chef_lieu_filter,
        "chefs_lieux": chefs_lieux,
    })


# ──────────────────────────────────────────────
#  RÉGION — Créer / Modifier
# ──────────────────────────────────────────────

@require_permission('courses.gerer_regions')
def region_create(request):
    if request.method == "POST":
        nom = request.POST.get("nom_region", "").strip()
        chef_lieu = request.POST.get("chef_lieu", "").strip()
        errors = {}

        if not nom:
            errors["nom_region"] = "Le nom de la région est obligatoire."
        elif Region.objects.filter(nom_region__iexact=nom).exists():
            errors["nom_region"] = "Une région avec ce nom existe déjà."
        if not chef_lieu:
            errors["chef_lieu"] = "Le chef-lieu est obligatoire."

        if not errors:
            Region.objects.create(nom_region=nom, chef_lieu=chef_lieu)
            messages.success(request, f"Région « {nom} » créée avec succès.")
            return redirect("bsb_admin:region_list")

        return render(request, "admin/region/region_form.html", {
            "errors": errors,
            "values": request.POST,
            "action": "Créer",
            "title": "Nouvelle région",
        })

    return render(request, "admin/region/region_form.html", {
        "action": "Créer",
        "title": "Nouvelle région",
    })


@require_permission('courses.gerer_regions')
def region_update(request, pk):
    region = get_object_or_404(Region, pk=pk)

    if request.method == "POST":
        nom = request.POST.get("nom_region", "").strip()
        chef_lieu = request.POST.get("chef_lieu", "").strip()
        errors = {}

        if not nom:
            errors["nom_region"] = "Le nom de la région est obligatoire."
        elif Region.objects.filter(nom_region__iexact=nom).exclude(pk=pk).exists():
            errors["nom_region"] = "Une autre région porte déjà ce nom."
        if not chef_lieu:
            errors["chef_lieu"] = "Le chef-lieu est obligatoire."

        if not errors:
            region.nom_region = nom
            region.chef_lieu = chef_lieu
            region.save()
            messages.success(request, f"Région « {nom} » modifiée avec succès.")
            return redirect("bsb_admin:region_list")

        return render(request, "admin/region/region_form.html", {
            "errors": errors,
            "values": request.POST,
            "region": region,
            "action": "Modifier",
            "title": f"Modifier — {region.nom_region}",
        })

    return render(request, "admin/region/region_form.html", {
        "region": region,
        "action": "Modifier",
        "title": f"Modifier — {region.nom_region}",
    })


@require_permission('courses.gerer_regions')
def region_delete(request, pk):
    region = get_object_or_404(Region, pk=pk)
    if request.method == "POST":
        nom = region.nom_region
        region.delete()
        messages.success(request, f"Région « {nom} » supprimée.")
        return redirect("bsb_admin:region_list")
    return render(request, "admin/region/region_confirm_delete.html", {"region": region})


# ──────────────────────────────────────────────
#  PROVINCE — Créer / Modifier / Supprimer
# ──────────────────────────────────────────────

@require_permission('courses.gerer_regions')
def province_create(request):
    regions = Region.objects.order_by("nom_region")

    if request.method == "POST":
        nom = request.POST.get("nom_province", "").strip()
        chef_lieu = request.POST.get("chef_lieu", "").strip()
        region_id = request.POST.get("region", "").strip()
        errors = {}

        if not nom:
            errors["nom_province"] = "Le nom de la province est obligatoire."
        elif Province.objects.filter(nom_province__iexact=nom).exists():
            errors["nom_province"] = "Une province avec ce nom existe déjà."
        if not chef_lieu:
            errors["chef_lieu"] = "Le chef-lieu est obligatoire."
        if not region_id:
            errors["region"] = "Veuillez sélectionner une région."

        if not errors:
            region = get_object_or_404(Region, pk=region_id)
            Province.objects.create(nom_province=nom, chef_lieu=chef_lieu, region=region)
            messages.success(request, f"Province « {nom} » créée avec succès.")
            return redirect("bsb_admin:region_list")

        return render(request, "admin/region/province_form.html", {
            "errors": errors,
            "values": request.POST,
            "regions": regions,
            "action": "Créer",
            "title": "Nouvelle province",
        })

    # Pré-sélection région si passée en GET
    region_id = request.GET.get("region")
    return render(request, "admin/region/province_form.html", {
        "regions": regions,
        "preselected_region": region_id,
        "action": "Créer",
        "title": "Nouvelle province",
    })


# ─── Import Excel/CSV — Region et Province ─────────────────────────────────

@require_permission('courses.gerer_regions')
def region_import_template(request):
    from .bulk_import_registry import SPEC_REGION
    from .bulk_import.views_helpers import render_import_template
    return render_import_template(request, SPEC_REGION)


@require_permission('courses.gerer_regions')
def region_import(request):
    from .bulk_import_registry import SPEC_REGION
    from .bulk_import.views_helpers import handle_import_upload
    return handle_import_upload(request, SPEC_REGION)


@require_permission('courses.gerer_regions')
def province_import_template(request):
    from .bulk_import_registry import SPEC_PROVINCE
    from .bulk_import.views_helpers import render_import_template
    return render_import_template(request, SPEC_PROVINCE)


@require_permission('courses.gerer_regions')
def province_import(request):
    from .bulk_import_registry import SPEC_PROVINCE
    from .bulk_import.views_helpers import handle_import_upload
    return handle_import_upload(request, SPEC_PROVINCE)


@require_permission('courses.gerer_regions')
def province_update(request, pk):
    province = get_object_or_404(Province, pk=pk)
    regions = Region.objects.order_by("nom_region")

    if request.method == "POST":
        nom = request.POST.get("nom_province", "").strip()
        chef_lieu = request.POST.get("chef_lieu", "").strip()
        region_id = request.POST.get("region", "").strip()
        errors = {}

        if not nom:
            errors["nom_province"] = "Le nom de la province est obligatoire."
        elif Province.objects.filter(nom_province__iexact=nom).exclude(pk=pk).exists():
            errors["nom_province"] = "Une autre province porte déjà ce nom."
        if not chef_lieu:
            errors["chef_lieu"] = "Le chef-lieu est obligatoire."
        if not region_id:
            errors["region"] = "Veuillez sélectionner une région."

        if not errors:
            province.nom_province = nom
            province.chef_lieu = chef_lieu
            province.region = get_object_or_404(Region, pk=region_id)
            province.save()
            messages.success(request, f"Province « {nom} » modifiée avec succès.")
            return redirect("bsb_admin:region_list")

        return render(request, "admin/region/province_form.html", {
            "errors": errors,
            "values": request.POST,
            "province": province,
            "regions": regions,
            "action": "Modifier",
            "title": f"Modifier — {province.nom_province}",
        })

    return render(request, "admin/region/province_form.html", {
        "province": province,
        "regions": regions,
        "action": "Modifier",
        "title": f"Modifier — {province.nom_province}",
    })


@require_permission('courses.gerer_regions')
def province_delete(request, pk):
    province = get_object_or_404(Province, pk=pk)
    if request.method == "POST":
        nom = province.nom_province
        province.delete()
        messages.success(request, f"Province « {nom} » supprimée.")
        return redirect("bsb_admin:region_list")
    return render(request, "admin/region/province_confirm_delete.html", {"province": province})


@login_required
def page_notifications(request):
    inscriptions_notif = Inscription.objects.filter(
        eleve=request.user,
        statut__in=["valide", "rejete"]
    ).select_related('formation__filiere', 'formation').order_by('-date_validation')

    vues = request.session.get('notifs_vues', [])
    tous_ids = list(inscriptions_notif.values_list('id', flat=True))
    request.session['notifs_vues'] = list(set(vues + tous_ids))
    request.session.modified = True

    notifications = []
    for inscription in inscriptions_notif:
        if inscription.statut == "valide":
            total_frais = Frais.objects.filter(
                formation=inscription.formation
            ).aggregate(
                total=Sum("montant")
            )["total"] or 0

            if total_frais:
                montant_75 = total_frais * 0.75
                message = (
                    f"✅ Félicitations ! Votre dossier d'inscription à la formation "
                    f"<strong>{inscription.formation.filiere}</strong> a été <strong>validé</strong>. "
                    f"Pour finaliser votre inscription, vous devez payer <strong>75% du montant de la formation</strong>, "
                    f"soit <strong>{montant_75:,.0f} FCFA</strong>. "
                    f"Rendez-vous dans la section <em>Mes inscriptions</em> pour procéder au paiement."
                )
            else:
                message = (
                    f"✅ Félicitations ! Votre dossier d'inscription à la formation "
                    f"<strong>{inscription.formation.filiere}</strong> a été <strong>validé</strong>. "
                    f"Rendez-vous dans la section <em>Mes inscriptions</em> pour procéder au paiement (75% du montant dû)."
                )

        elif inscription.statut == "rejete":
            motif = inscription.motif_rejet or "Aucun motif précisé."
            message = (
                f"❌ Votre dossier d'inscription à la formation "
                f"<strong>{inscription.formation.filiere}</strong> a été <strong>rejeté</strong>. "
                f"<br><strong>Motif :</strong> {motif}"
            )

        notifications.append({
            "inscription": inscription,
            "message": message,
            "is_new": inscription.id not in vues,
        })

    return render(request, 'student/notifications.html', {
        'notifications': notifications,
    })
    
    
@login_required
def notifications_count(request):
    """Retourne le nombre de notifications non vues pour la cloche."""
    from django.http import JsonResponse
    
    vues = request.session.get('notifs_vues', [])
    count = Inscription.objects.filter(
        eleve=request.user,
        statut__in=["valide", "rejete"]
    ).exclude(id__in=vues).count()
    
    return JsonResponse({'count': count})