from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from courses.permissions import require_permission

from .forms import ActualiteForm
from .models import AbonneNewsletter, Actualite
from .notifications import notifier_abonnes


@require_permission('actualites.gerer_actualites')
def actualite_list(request):
    toutes = Actualite.objects.select_related('auteur')
    q = request.GET.get('q', '').strip()
    statut = request.GET.get('statut', '').strip()

    actualites = toutes
    if q:
        actualites = actualites.filter(Q(titre__icontains=q) | Q(chapeau__icontains=q))
    if statut in ('publiee', 'brouillon'):
        actualites = actualites.filter(statut=statut)

    actualites = Paginator(actualites, 9).get_page(request.GET.get('page'))
    return render(request, 'admin/actualite/list.html', {
        'actualites': actualites,
        'q': q,
        'statut': statut,
        'total_publiees': toutes.filter(statut='publiee').count(),
        'total_brouillons': toutes.filter(statut='brouillon').count(),
        'total_abonnes_actifs': AbonneNewsletter.objects.filter(actif=True).count(),
    })


@require_permission('actualites.gerer_actualites')
def actualite_create(request):
    if request.method == 'POST':
        form = ActualiteForm(request.POST, request.FILES)
        if form.is_valid():
            actualite = form.save(commit=False)
            actualite.auteur = request.user
            if actualite.statut == 'publiee' and not actualite.date_publication:
                actualite.date_publication = timezone.now()
            actualite.save()
            messages.success(request, f'Actualité « {actualite.titre} » enregistrée.')
            return redirect('bsb_actualites:actualite_list')
    else:
        form = ActualiteForm()
    return render(request, 'admin/actualite/form.html', {'form': form, 'action': 'Créer'})


@require_permission('actualites.gerer_actualites')
def actualite_update(request, id):
    actualite = get_object_or_404(Actualite, id=id)
    if request.method == 'POST':
        form = ActualiteForm(request.POST, request.FILES, instance=actualite)
        if form.is_valid():
            actualite = form.save(commit=False)
            if actualite.statut == 'publiee' and not actualite.date_publication:
                actualite.date_publication = timezone.now()
            actualite.save()
            messages.success(request, f'Actualité « {actualite.titre} » mise à jour.')
            return redirect('bsb_actualites:actualite_list')
    else:
        form = ActualiteForm(instance=actualite)
    return render(request, 'admin/actualite/form.html',
                  {'form': form, 'action': 'Modifier', 'actualite': actualite})


@require_permission('actualites.gerer_actualites')
@require_POST
def actualite_delete(request, id):
    actualite = get_object_or_404(Actualite, id=id)
    titre = actualite.titre
    actualite.delete()
    messages.success(request, f'Actualité « {titre} » supprimée.')
    return redirect('bsb_actualites:actualite_list')


@require_permission('actualites.publier_actualite')
@require_POST
def actualite_publier(request, id):
    """Publie l'actualité puis prévient les abonnés. Un échec d'envoi ne doit
    jamais annuler la publication : elle est enregistrée avant l'e-mail."""
    actualite = get_object_or_404(Actualite, id=id)
    actualite.statut = 'publiee'
    if not actualite.date_publication:
        actualite.date_publication = timezone.now()
    actualite.save()
    messages.success(request, f'Actualité « {actualite.titre} » publiée.')

    try:
        envoyes = notifier_abonnes(actualite, request=request)
        if envoyes:
            messages.success(request, f'{envoyes} abonné(s) notifié(s) par e-mail.')
    except Exception as erreur:
        messages.warning(request, f"Publication faite, mais l'envoi aux abonnés a échoué : {erreur}")

    return redirect('bsb_actualites:actualite_list')


@require_permission('actualites.gerer_newsletter')
def abonne_list(request):
    abonnes = AbonneNewsletter.objects.all()
    q = request.GET.get('q', '').strip()
    if q:
        abonnes = abonnes.filter(email__icontains=q)
    total_actifs = AbonneNewsletter.objects.filter(actif=True).count()
    total_desabonnes = AbonneNewsletter.objects.filter(actif=False).count()
    abonnes = Paginator(abonnes, 25).get_page(request.GET.get('page'))
    return render(request, 'admin/actualite/abonnes.html', {
        'abonnes': abonnes, 'q': q,
        'total_actifs': total_actifs,
        'total_desabonnes': total_desabonnes,
    })
