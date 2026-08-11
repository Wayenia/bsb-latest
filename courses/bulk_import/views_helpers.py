"""Deux fonctions génériques appelées par les vues fines de chaque modèle
(une paire de vues par modèle : téléchargement du modèle + upload)."""

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

from .engine import ImportReport, RowError, run_import
from .xlsx_template import build_template_workbook


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
    """GET → formulaire d'upload. POST → traite le fichier et affiche le
    rapport (créés / erreurs)."""
    if request.method == "POST":
        uploaded_file = request.FILES.get("fichier")
        if not uploaded_file:
            report = ImportReport()
            report.errors.append(RowError(0, ["Aucun fichier n'a été sélectionné."]))
        else:
            report = run_import(spec, uploaded_file)
        return render(request, "bulk_import/import_result.html", {
            "spec": spec,
            "report": report,
            "template_url": spec_url(spec, spec.template_url_name),
            "upload_url": spec_url(spec, spec.upload_url_name),
            "list_url": spec_url(spec, spec.list_url_name),
        })

    return render(request, "bulk_import/upload_form.html", {
        "spec": spec,
        "template_url": spec_url(spec, spec.template_url_name),
        "list_url": spec_url(spec, spec.list_url_name),
    })
