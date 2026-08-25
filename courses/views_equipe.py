"""Back-office « Équipe » : Directeur Général et membres de l'administration.

Ces deux modèles alimentent la page publique « À propos »
(`courses.views.about_view`). Ils n'étaient éditables que par l'admin Django ;
ce module reprend cette fonction dans le back-office /bsb/, ce qui a permis de
retirer complètement `django.contrib.admin` du projet.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DGForm, MembreEquipeForm
from .models import DG, Membre
from .permissions import require_permission

PERMISSION = 'courses.gerer_equipe'


@require_permission(PERMISSION)
def equipe_list(request):
    """Une seule page : la fiche du DG actif et la liste des membres.

    Le modèle DG n'autorise qu'un seul actif à la fois (cf. `DG.save`), mais on
    affiche aussi les anciens : ils restent en base à titre d'historique.
    """
    return render(request, 'admin/equipe/list.html', {
        'dg_actif': DG.objects.filter(is_active=True).first(),
        'dgs': DG.objects.all(),
        'membres': Membre.objects.all(),
    })


# ─── Directeur Général ────────────────────────────────────────────────────────

@require_permission(PERMISSION)
def dg_create(request):
    return _enregistrer(request, DGForm, None,
                        titre='Ajouter un Directeur Général', action='Créer')


@require_permission(PERMISSION)
def dg_update(request, pk):
    return _enregistrer(request, DGForm, get_object_or_404(DG, pk=pk),
                        titre='Modifier le Directeur Général', action='Enregistrer')


@require_permission(PERMISSION)
def dg_delete(request, pk):
    return _supprimer(request, get_object_or_404(DG, pk=pk), 'Directeur Général')


# ─── Membres de l'équipe ──────────────────────────────────────────────────────

@require_permission(PERMISSION)
def membre_create(request):
    return _enregistrer(request, MembreEquipeForm, None,
                        titre="Ajouter un membre de l'équipe", action='Créer')


@require_permission(PERMISSION)
def membre_update(request, pk):
    return _enregistrer(request, MembreEquipeForm, get_object_or_404(Membre, pk=pk),
                        titre='Modifier le membre', action='Enregistrer')


@require_permission(PERMISSION)
def membre_delete(request, pk):
    return _supprimer(request, get_object_or_404(Membre, pk=pk), 'Membre')


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _enregistrer(request, form_class, instance, titre, action):
    """Création et modification partagent le même formulaire et le même gabarit.

    `request.FILES` est indispensable : les deux modèles portent une photo
    obligatoire à la création.
    """
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            objet = form.save()
            messages.success(request, f"« {objet.full_name} » enregistré avec succès.")
            return redirect('bsb_admin:equipe_list')
        messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = form_class(instance=instance)

    return render(request, 'admin/equipe/form.html', {
        'form': form, 'titre': titre, 'action': action, 'objet': instance,
    })


def _supprimer(request, objet, libelle):
    if request.method == 'POST':
        nom = objet.full_name
        objet.delete()
        messages.success(request, f"{libelle} « {nom} » supprimé avec succès.")
        return redirect('bsb_admin:equipe_list')
    return render(request, 'admin/equipe/confirm_delete.html', {
        'objet': objet, 'libelle': libelle,
    })
