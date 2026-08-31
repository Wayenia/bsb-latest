"""Import Excel des destinataires du rapport d'inspection.

Le modele telecharge est pre-rempli des destinataires deja enregistres : on
corrige et on complete une liste existante plutot que de la ressaisir, et le
format attendu se lit sur de vraies donnees. Une ligne portant une adresse
deja connue met la fiche a jour au lieu d'echouer sur l'unicite.
"""
from courses.bulk_import.specs import ColumnSpec, ImportSpec

from .forms import DestinataireRapportForm
from .models import DestinataireRapport


def _destinataires_existants():
    return [
        {'email': d.email, 'nom': d.nom, 'fonction': d.fonction, 'actif': d.actif}
        for d in DestinataireRapport.objects.all()
    ]


def _destinataire_existant(resolved):
    email = (resolved.get('email') or '').strip()
    return DestinataireRapport.objects.filter(email__iexact=email).first() if email else None


SPEC_DESTINATAIRE_AUDIT = ImportSpec(
    slug="destinataire_audit",
    verbose_name="Destinataire du rapport",
    model=DestinataireRapport,
    mode="form",
    form_class=DestinataireRapportForm,
    columns=[
        ColumnSpec("Adresse e-mail", "email", required=True, kind="text",
                   help_text="Une adresse deja presente met la fiche a jour."),
        ColumnSpec("Nom", "nom", required=False, kind="text"),
        ColumnSpec("Fonction", "fonction", required=False, kind="text"),
        ColumnSpec("Reçoit le rapport", "actif", required=False, kind="bool",
                   help_text="oui / non. Non : la fiche est conservee mais l'envoi cesse."),
    ],
    prefill_fn=_destinataires_existants,
    exemples=[
        {'email': 'inspection@mesfpt.gov.bf', 'nom': 'SANOU Boureima',
         'fonction': "Chargé de l'inspection", 'actif': True},
        {'email': 'dg@mesfpt.gov.bf', 'nom': 'OUEDRAOGO Awa',
         'fonction': 'Directrice générale', 'actif': True},
        {'email': 'ancien.auditeur@mesfpt.gov.bf', 'nom': 'KABORE Issa',
         'fonction': 'Auditeur (parti)', 'actif': False},
    ],
    instance_lookup_fn=_destinataire_existant,
    sheet_name="Destinataires",
    intro="Une ligne par personne recevant le rapport d'inspection des connexions.",
    url_namespace="bsb_admin",
    template_url_name="destinataire_audit_import_template",
    upload_url_name="destinataire_audit_import",
    list_url_name="destinataire_audit_list",
)
