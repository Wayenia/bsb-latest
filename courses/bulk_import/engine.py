"""Moteur générique d'import : résolution des colonnes, appel du form/
validateur existant, sauvegarde ligne par ligne (atomique par ligne, jamais
globalement — une ligne invalide n'annule jamais les lignes déjà créées)."""

import datetime
from dataclasses import dataclass, field
from typing import Any, List, Optional

from django.db import transaction
from django.http import QueryDict

MULTI_KINDS = {"fk_pk_multi", "fk_name_value_multi"}


class RowValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass
class RowSuccess:
    row_number: int
    label: str
    extra: Optional[dict] = None


@dataclass
class RowError:
    row_number: int
    messages: List[str] = field(default_factory=list)


@dataclass
class ImportReport:
    created: List[RowSuccess] = field(default_factory=list)
    errors: List[RowError] = field(default_factory=list)


def _to_text(raw_value):
    if raw_value is None:
        return ""
    if isinstance(raw_value, (datetime.date, datetime.datetime)):
        return raw_value
    return str(raw_value).strip()


def resolve_column(col, raw_value):
    """Retourne (ok, valeur_resolue, message_erreur)."""
    text = _to_text(raw_value)
    is_empty = text == "" if isinstance(text, str) else False

    if is_empty:
        if col.required:
            return False, None, f"« {col.header} » est obligatoire."
        return True, (None if col.kind != "text" else ""), None

    kind = col.kind

    if kind == "text":
        return True, text, None

    if kind == "int":
        try:
            return True, int(float(str(text).replace(",", "."))), None
        except (ValueError, TypeError):
            return False, None, f"« {col.header} » doit être un nombre entier."

    if kind == "decimal":
        try:
            return True, str(text).replace(",", "."), None
        except Exception:
            return False, None, f"« {col.header} » doit être un nombre."

    if kind == "bool":
        s = str(text).strip().lower()
        if s in ("oui", "true", "vrai", "1", "yes"):
            return True, True, None
        if s in ("non", "false", "faux", "0", "no"):
            return True, False, None
        return False, None, f"« {col.header} » doit être Oui ou Non."

    if kind == "date":
        if isinstance(text, (datetime.date, datetime.datetime)):
            d = text.date() if isinstance(text, datetime.datetime) else text
            return True, d.strftime("%Y-%m-%d"), None
        s = str(text).strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return True, datetime.datetime.strptime(s, fmt).date().strftime("%Y-%m-%d"), None
            except ValueError:
                continue
        return False, None, f"« {col.header} » doit être une date au format JJ/MM/AAAA."

    if kind == "choice_static":
        s = str(text).strip().lower()
        for code, label in col.choices or []:
            if s == str(code).lower() or s == str(label).lower():
                return True, code, None
        valeurs = ", ".join(str(c) for c, _ in (col.choices or []))
        return False, None, f"« {col.header} » : valeur « {text} » non reconnue (attendu : {valeurs})."

    if kind == "fk_pk":
        obj = col.fk_model.objects.filter(
            **{f"{col.fk_lookup_field}__iexact": str(text).strip()}
        ).first()
        if not obj:
            return False, None, (
                f"« {col.header} » : aucun(e) {col.fk_model._meta.verbose_name} "
                f"nommé(e) « {text} » trouvé(e)."
            )
        return True, obj.pk, None

    if kind == "fk_pk_multi":
        noms = [n.strip() for n in str(text).split(col.separator) if n.strip()]
        pks, manquants = [], []
        for n in noms:
            obj = col.fk_model.objects.filter(**{f"{col.fk_lookup_field}__iexact": n}).first()
            (pks.append(obj.pk) if obj else manquants.append(n))
        if manquants:
            return False, None, f"« {col.header} » : introuvable(s) — {', '.join(manquants)}."
        return True, pks, None

    if kind == "fk_name_value":
        obj = col.fk_model.objects.filter(
            **{f"{col.fk_lookup_field}__iexact": str(text).strip()}
        ).first()
        if not obj:
            return False, None, (
                f"« {col.header} » : aucun(e) {col.fk_model._meta.verbose_name} avec "
                f"{col.fk_lookup_field} « {text} »."
            )
        return True, getattr(obj, col.fk_lookup_field), None

    if kind == "fk_name_value_multi":
        noms = [n.strip() for n in str(text).split(col.separator) if n.strip()]
        valeurs, manquants = [], []
        for n in noms:
            obj = col.fk_model.objects.filter(**{f"{col.fk_lookup_field}__iexact": n}).first()
            (valeurs.append(getattr(obj, col.fk_lookup_field)) if obj else manquants.append(n))
        if manquants:
            return False, None, f"« {col.header} » : introuvable(s) — {', '.join(manquants)}."
        return True, valeurs, None

    return False, None, f"Type de colonne non géré : {kind}."


def to_querydict(resolved, columns):
    """Construit un QueryDict mutable (supporte .getlist() pour les champs
    multi-select des ModelForm) à partir des valeurs déjà résolues."""
    qd = QueryDict(mutable=True)
    by_name = {c.field_name: c for c in columns}
    for field_name, value in resolved.items():
        col = by_name.get(field_name)
        if value is None:
            continue
        if col is not None and col.kind in MULTI_KINDS:
            qd.setlist(field_name, [str(v) for v in value])
        else:
            qd[field_name] = str(value)
    return qd


def run_import(spec, uploaded_file):
    from .readers import read_rows

    report = ImportReport()
    try:
        rows = read_rows(uploaded_file, spec)
    except ValueError as e:
        report.errors.append(RowError(0, [str(e)]))
        return report

    for row_number, raw_row in rows:
        resolved = {}
        col_errors = []
        for col in spec.columns:
            ok, value, err = resolve_column(col, raw_row.get(col.header))
            if ok:
                resolved[col.field_name] = value
            else:
                col_errors.append(err)

        if col_errors:
            report.errors.append(RowError(row_number, col_errors))
            continue

        try:
            with transaction.atomic():
                if spec.pre_validate_hook:
                    spec.pre_validate_hook(resolved)

                if spec.mode == "manual":
                    ok, obj, errs = spec.manual_validator(resolved)
                    if not ok:
                        raise RowValidationError(errs)
                else:
                    form = spec.form_class(data=to_querydict(resolved, spec.columns))
                    if not form.is_valid():
                        errs = []
                        for field_name, field_errors in form.errors.items():
                            label = form.fields[field_name].label if field_name in form.fields else field_name
                            errs.extend(f"{label} : {e}" for e in field_errors)
                        raise RowValidationError(errs)
                    obj = form.save()

                extra = spec.post_save_hook(obj, resolved) if spec.post_save_hook else None
                label = spec.label_fn(obj) if spec.label_fn else str(obj)
            report.created.append(RowSuccess(row_number, label, extra))
        except RowValidationError as e:
            report.errors.append(RowError(row_number, e.errors))
        except Exception as e:
            report.errors.append(RowError(row_number, [str(e)]))

    return report
