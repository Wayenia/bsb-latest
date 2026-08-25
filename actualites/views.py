from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import AbonnementForm
from .models import AbonneNewsletter, Actualite


def _publiees():
    maintenant = timezone.now()
    return Actualite.objects.filter(statut="publiee", date_publication__lte=maintenant).filter(
        Q(date_fin_publication__isnull=True) | Q(date_fin_publication__gt=maintenant))


def liste(request):
    paginator = Paginator(_publiees(), 9)
    actualites = paginator.get_page(request.GET.get("page"))
    return render(request, "actualites/liste.html",
                  {"actualites": actualites, "form": AbonnementForm()})


def detail(request, slug):
    actualite = get_object_or_404(_publiees(), slug=slug)
    autres = _publiees().exclude(pk=actualite.pk)[:3]
    return render(request, "actualites/detail.html",
                  {"actualite": actualite, "autres": autres, "form": AbonnementForm()})


@require_POST
def abonnement(request):
    """Inscription à la newsletter. Le message de retour est volontairement le
    même que l'adresse soit nouvelle ou déjà inscrite : il ne permet pas de
    tester si une adresse figure dans la base."""
    form = AbonnementForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data["email"]
        abonne, cree = AbonneNewsletter.objects.get_or_create(email=email)
        if not cree and not abonne.actif:
            abonne.actif = True
            abonne.date_desinscription = None
            abonne.save(update_fields=["actif", "date_desinscription"])
        messages.success(request, "Votre inscription est enregistrée. "
                                  "Vous recevrez un e-mail à chaque nouvelle actualité.")
    else:
        messages.error(request, form.errors.get("email", ["Requête invalide."])[0])
    return redirect(_suivant_sur(request))


def _suivant_sur(request):
    """Destination de retour apres abonnement, validee contre l'hote courant.

    Le champ `suivant` est un champ cache du formulaire : sa valeur legitime est
    `request.path`, mais rien n'empeche un tiers de poster le formulaire avec
    une URL absolue. Sans ce controle, l'endpoint sert de tremplin de
    redirection (phishing) depuis un domaine gouvernemental - c'est le finding
    « Open Redirection » du scan Acunetix du 24/08/2026.

    Meme convention que les autres redirections pilotees par l'utilisateur du
    projet (courses/views.py, courses/views_admin.py).
    """
    suivant = request.POST.get("suivant")
    if suivant and url_has_allowed_host_and_scheme(
        suivant, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return suivant
    return "actualites:liste"


def desabonnement(request, token):
    abonne = get_object_or_404(AbonneNewsletter, token=token)
    if abonne.actif:
        abonne.actif = False
        abonne.date_desinscription = timezone.now()
        abonne.save(update_fields=["actif", "date_desinscription"])
    return render(request, "actualites/desabonnement.html", {"abonne": abonne})
