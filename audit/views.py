"""Ecrans de parametrage de la diffusion du rapport d'inspection."""
from django.contrib import messages
from django.core.management import call_command
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from courses.bulk_import.views_helpers import handle_import_upload, render_import_template
from courses.permissions import require_permission
from courses.views_admin import _onglets_audit

from .bulk_import_registry import SPEC_DESTINATAIRE_AUDIT
from .forms import DestinataireRapportForm
from .models import DestinataireRapport

PERMISSION = 'audit.gerer_destinataires_audit'


@require_permission(PERMISSION)
def destinataire_list(request):
    if request.method == 'POST':
        form = DestinataireRapportForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Destinataire ajouté.")
            return redirect('bsb_admin:destinataire_audit_list')
        messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = DestinataireRapportForm()

    destinataires = DestinataireRapport.objects.all()
    return render(request, 'audit/destinataires.html', {
        'destinataires': destinataires,
        'form': form,
        'nb_actifs': destinataires.filter(actif=True).count(),
        'onglets': _onglets_audit(request.user, actif='reglage'),
    })


@require_permission(PERMISSION)
@require_POST
def destinataire_envoyer(request):
    """Declenche un envoi immediat depuis l'ecran.

    Evite d'avoir a expliquer une commande serveur dans la page : le geste se
    fait au clic, et le resultat s'affiche en message.
    """
    if not DestinataireRapport.adresses_actives():
        messages.error(request, "Aucun destinataire actif : rien n'a été envoyé.")
        return redirect('bsb_admin:destinataire_audit_list')
    try:
        call_command('envoyer_rapport_audit')
    except Exception as erreur:
        messages.error(request, f"L'envoi a échoué : {erreur}")
    else:
        nombre = len(DestinataireRapport.adresses_actives())
        messages.success(request, f"Rapport envoyé à {nombre} destinataire{'s' if nombre > 1 else ''}.")
    return redirect('bsb_admin:destinataire_audit_list')


@require_permission(PERMISSION)
@require_POST
def destinataire_basculer(request, pk):
    """Active ou suspend l'envoi, sans supprimer la fiche : on garde trace de
    qui recevait le rapport."""
    d = get_object_or_404(DestinataireRapport, pk=pk)
    d.actif = not d.actif
    d.save(update_fields=['actif'])
    messages.success(request, f"{d.email} : envoi {'activé' if d.actif else 'suspendu'}.")
    return redirect('bsb_admin:destinataire_audit_list')


@require_permission(PERMISSION)
@require_POST
def destinataire_supprimer(request, pk):
    d = get_object_or_404(DestinataireRapport, pk=pk)
    email = d.email
    d.delete()
    messages.success(request, f"{email} retiré de la liste.")
    return redirect('bsb_admin:destinataire_audit_list')


@require_permission(PERMISSION)
def destinataire_import_template(request):
    return render_import_template(request, SPEC_DESTINATAIRE_AUDIT)


@require_permission(PERMISSION)
def destinataire_import(request):
    return handle_import_upload(request, SPEC_DESTINATAIRE_AUDIT)
