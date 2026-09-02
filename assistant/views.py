import json

from django.conf import settings
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render

from courses.permissions import require_permission
from accounts.models import Utilisateur

from . import services
from .models import (DOMAINES, DOMAINES_GROUPES, LIBELLES_DOMAINES, AccesAssistant,
                     EchangeAssistant, ReglageAssistant)

# Modeles conseilles : petit en dev (<=380 Mo), avance et stable en prod (<=1 Go).
MODELES_CONSEILLES = [
    ("qwen2:0.5b", "Léger — tests locaux (~0,35 Go)"),
    ("qwen2.5:1.5b", "Avancé et stable — production (~1 Go)"),
    ("deepseek-r1:1.5b", "DeepSeek avancé (~1,1 Go)"),
]


def _garde():
    """Interrompt si le module IA est desactive : reversibilite totale."""
    if getattr(settings, "AI_MODULE", "off") != "on":
        raise Http404()


def _est_gestionnaire_ia(user):
    return user.is_superuser or user.has_perm("assistant.gerer_assistant_ia")


def domaines_autorises(user):
    """Domaines consultables : tout pour un gestionnaire, sinon le perimetre delegue."""
    if _est_gestionnaire_ia(user):
        return [code for code, _ in DOMAINES]
    acces = getattr(user, "acces_assistant", None)
    if acces and acces.actif:
        return list(acces.domaines or [])
    return []


@require_permission("assistant.utiliser_assistant_ia")
def accueil(request):
    _garde()
    reglage = ReglageAssistant.actuel()
    return render(request, "assistant/accueil.html", {
        "modele_actif": reglage.modele_actif,
        "domaines": [lib for code, lib in DOMAINES if code in domaines_autorises(request.user)],
        "peut_gerer": _est_gestionnaire_ia(request.user),
    })


@require_permission("assistant.utiliser_assistant_ia")
def demander(request):
    _garde()
    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "Méthode non autorisée."}, status=405)
    question = (request.POST.get("question") or "").strip()
    if not question:
        return JsonResponse({"ok": False, "message": "Posez une question."}, status=400)
    domaines = domaines_autorises(request.user)
    # Aucun domaine autorise : refus professionnel, sans solliciter le modele.
    if not domaines:
        EchangeAssistant.journaliser(request.user, question, services.REFUS, [], refuse=True)
        return JsonResponse({"ok": True, "message": services.REFUS})
    contexte = services.contexte_lecture_seule(request.user, domaines)
    ok, reponse = services.demander(question, contexte)
    EchangeAssistant.journaliser(request.user, question, reponse, domaines, refuse=not ok)
    return JsonResponse({"ok": ok, "message": reponse})


@require_permission("assistant.gerer_assistant_ia")
def acces(request):
    _garde()
    if request.method == "POST":
        uid = request.POST.get("utilisateur")
        domaines = request.POST.getlist("domaines")
        cible = Utilisateur.objects.filter(pk=uid).first()
        if not cible:
            messages.error(request, "Agent introuvable.")
            return redirect("assistant:acces")
        if request.POST.get("action") == "retirer":
            AccesAssistant.objects.filter(utilisateur=cible).delete()
            _permission_utiliser(cible, accorder=False)
            messages.success(request, f"Accès retiré à {cible}.")
        else:
            AccesAssistant.objects.update_or_create(
                utilisateur=cible, defaults={"domaines": domaines, "actif": True})
            _permission_utiliser(cible, accorder=True)
            messages.success(request, f"Accès accordé à {cible}.")
        return redirect("assistant:acces")

    delegues = AccesAssistant.objects.select_related("utilisateur").order_by("-cree_le")
    for d in delegues:
        d.libelles = [LIBELLES_DOMAINES.get(c, c) for c in (d.domaines or [])]
    agents = Utilisateur.objects.exclude(user_type="eleve").order_by("nom", "prenom")
    groupes = [(theme, [(c, LIBELLES_DOMAINES[c]) for c in codes]) for theme, codes in DOMAINES_GROUPES]
    return render(request, "assistant/acces.html", {
        "delegues": delegues, "agents": agents, "groupes_domaines": groupes})


@require_permission("assistant.gerer_assistant_ia")
def modeles(request):
    _garde()
    reglage = ReglageAssistant.actuel()
    if request.method == "POST":
        nom = (request.POST.get("modele") or "").strip()
        if nom:
            reglage.modele_actif = nom
            reglage.save()
            if nom not in services.modeles_installes():
                services.telecharger_en_fond(nom)
                messages.info(request, f"Téléchargement de « {nom} » lancé en arrière-plan.")
            else:
                messages.success(request, f"Modèle actif : « {nom} ».")
        return redirect("assistant:modeles")

    return render(request, "assistant/modeles.html", {
        "modele_actif": reglage.modele_actif,
        "installes": services.modeles_installes(),
        "conseilles": MODELES_CONSEILLES})


@require_permission("assistant.gerer_assistant_ia")
def journal(request):
    _garde()
    echanges = list(EchangeAssistant.objects.select_related("utilisateur")[:200])
    for e in echanges:
        e.libelles = [LIBELLES_DOMAINES.get(c, c) for c in (e.domaines or [])]
    return render(request, "assistant/journal.html", {
        "echanges": echanges,
        "total": EchangeAssistant.objects.count(),
        "retention": EchangeAssistant.RETENTION_JOURS})


def _permission_utiliser(user, accorder):
    """Octroie ou retire la permission d'utiliser l'assistant, par utilisateur."""
    from django.contrib.auth.models import Permission
    perm = Permission.objects.filter(codename="utiliser_assistant_ia").first()
    if not perm:
        return
    if accorder:
        user.user_permissions.add(perm)
    else:
        user.user_permissions.remove(perm)
