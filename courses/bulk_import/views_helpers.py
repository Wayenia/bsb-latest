"""Fonctions génériques appelées par les vues fines de chaque modèle
(une paire de vues par modèle : téléchargement du modèle + upload).

L'upload se fait en deux temps : un aperçu, puis une confirmation. L'aperçu
rejoue l'import dans une transaction annulée, ce qui donne le compte exact des
créations, des mises à jour et des refus sans rien écrire en base. Un fichier
de plusieurs centaines de lignes se corrige ainsi avant d'être appliqué, au
lieu d'être découvert après coup.

Le fichier déposé est conservé le temps de la confirmation dans un répertoire
temporaire ; son chemin, jamais transmis au navigateur, vit en session sous un
jeton aléatoire.
"""

import os
import secrets
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

from .engine import ImportReport, RowError, run_import
from .xlsx_template import build_template_workbook

CLE_SESSION = "bulk_import_en_attente"


class _Annuler(Exception):
    """Interrompt la transaction de l'aperçu sans rien conserver."""


def _apercu(spec, contenu, nom):
    """Rejoue l'import et annule tout : rien n'est écrit, le rapport est réel."""
    rapport = {}
    try:
        with transaction.atomic():
            rapport['r'] = run_import(spec, SimpleUploadedFile(nom, contenu))
            raise _Annuler
    except _Annuler:
        pass
    return rapport['r']


def _deposer(request, contenu, nom):
    _purger(request)
    jeton = secrets.token_urlsafe(16)
    dossier = tempfile.mkdtemp(prefix="import_")
    chemin = os.path.join(dossier, "depot.bin")
    with open(chemin, "wb") as f:
        f.write(contenu)
    request.session[CLE_SESSION] = {'jeton': jeton, 'chemin': chemin, 'nom': nom}
    return jeton


def _reprendre(request, jeton):
    depot = request.session.get(CLE_SESSION)
    if not depot or depot.get('jeton') != jeton:
        return None, None
    try:
        with open(depot['chemin'], "rb") as f:
            return f.read(), depot['nom']
    except OSError:
        return None, None


def _purger(request):
    depot = request.session.pop(CLE_SESSION, None)
    if not depot:
        return
    try:
        os.remove(depot['chemin'])
        os.rmdir(os.path.dirname(depot['chemin']))
    except OSError:
        pass


def spec_url(spec, name):
    if not name:
        return None
    ns = f"{spec.url_namespace}:" if spec.url_namespace else ""
    return reverse(f"{ns}{name}")


def render_import_template(request, spec):
    wb = build_template_workbook(spec)
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="modele_import_{spec.slug}.xlsx"'
    wb.save(response)
    return response


def handle_import_upload(request, spec):
    """GET → formulaire. POST avec fichier → aperçu. POST avec jeton → import."""
    contexte = {
        "spec": spec,
        "template_url": spec_url(spec, spec.template_url_name),
        "upload_url": spec_url(spec, spec.upload_url_name),
        "list_url": spec_url(spec, spec.list_url_name),
    }

    if request.method != "POST":
        _purger(request)
        return render(request, "bulk_import/upload_form.html", contexte)

    # Deuxième temps : l'utilisateur confirme l'aperçu qu'il vient de lire.
    jeton = request.POST.get("confirmer")
    if jeton:
        contenu, nom = _reprendre(request, jeton)
        if contenu is None:
            rapport = ImportReport()
            rapport.errors.append(RowError(0, [
                "Le fichier n'est plus disponible : la session a expiré. "
                "Déposez-le à nouveau."]))
            return render(request, "bulk_import/import_result.html",
                          dict(contexte, report=rapport))
        rapport = run_import(spec, SimpleUploadedFile(nom, contenu))
        _purger(request)
        return render(request, "bulk_import/import_result.html",
                      dict(contexte, report=rapport))

    # Premier temps : on montre ce que le fichier ferait, sans rien écrire.
    fichier = request.FILES.get("fichier")
    if not fichier:
        rapport = ImportReport()
        rapport.errors.append(RowError(0, ["Aucun fichier n'a été sélectionné."]))
        return render(request, "bulk_import/import_result.html",
                      dict(contexte, report=rapport))

    contenu = fichier.read()
    rapport = _apercu(spec, contenu, fichier.name)
    jeton = _deposer(request, contenu, fichier.name)
    creations = [l for l in rapport.created if not (l.extra or {}).get("mise_a_jour")]
    majs = [l for l in rapport.created if (l.extra or {}).get("mise_a_jour")]
    return render(request, "bulk_import/import_apercu.html", dict(
        contexte, report=rapport, jeton=jeton, nom_fichier=fichier.name,
        creations=creations, majs=majs))
