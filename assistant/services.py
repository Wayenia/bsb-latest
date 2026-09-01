import json
import threading
import urllib.error
import urllib.request

from django.conf import settings

from .models import ReglageAssistant

# Consigne systeme : l'assistant lit et explique, il n'agit jamais sur les donnees.
SYSTEME = (
    "Tu es l'assistant de la plateforme Yupaan (Burkina Suudu Bawdè). "
    "Tu aides à comprendre et analyser le fonctionnement et les données fournies. "
    "Tu es en LECTURE SEULE : tu ne modifies, ne crées ni ne supprimes jamais rien. "
    "Réponds en français, clairement, à partir du contexte donné."
)


def _appel(suffixe, charge, timeout=120):
    """POST JSON vers Ollama ; retourne le dict de reponse."""
    req = urllib.request.Request(
        settings.AI_OLLAMA_URL + suffixe,
        data=json.dumps(charge).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def modeles_installes():
    """Liste des modeles deja telecharges dans Ollama (vide si indisponible)."""
    try:
        req = urllib.request.Request(settings.AI_OLLAMA_URL + "/api/tags")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        return []


def telecharger_en_fond(nom):
    """Lance un pull Ollama en arriere-plan (la plateforme n'est pas bloquee)."""
    def _pull():
        try:
            _appel("/api/pull", {"name": nom, "stream": False}, timeout=1800)
        except Exception:
            pass
    threading.Thread(target=_pull, daemon=True).start()


def demander(question, contexte):
    """Interroge le modele actif avec un contexte deja calcule (lecture seule)."""
    modele = ReglageAssistant.actuel().modele_actif
    prompt = f"{SYSTEME}\n\nContexte:\n{contexte}\n\nQuestion: {question}\nRéponse:"
    try:
        data = _appel("/api/generate", {"model": modele, "prompt": prompt, "stream": False})
        return True, (data.get("response") or "").strip()
    except urllib.error.URLError:
        return False, "L'assistant est momentanément indisponible. Réessayez plus tard."
    except Exception:
        return False, "L'assistant n'a pas pu traiter la demande."


def contexte_lecture_seule(user, domaines):
    """Resume factuel des donnees autorisees, selon le perimetre de l'utilisateur."""
    from courses.views import _base_qs
    lignes = []
    try:
        inscr, dettes, paiements, centres, directions, scope = _base_qs(user)
    except Exception:
        return "Aucune donnée disponible."

    if "scolarite" in domaines:
        lignes.append(f"Inscriptions (périmètre): {inscr.count()}")
        lignes.append(f"Inscriptions validées: {inscr.filter(statut='valide').count()}")
        lignes.append(f"Centres visibles: {centres.count()}")
    if "finances" in domaines:
        from django.db.models import Sum
        encaisse = paiements.aggregate(s=Sum("montant_paiement"))["s"] or 0
        du = dettes.aggregate(s=Sum("montant_total"))["s"] or 0
        lignes.append(f"Total encaissé: {encaisse:.0f} FCFA")
        lignes.append(f"Total dû: {du:.0f} FCFA")
        lignes.append(f"Reste à recouvrer: {max(du - encaisse, 0):.0f} FCFA")
    if "facturation" in domaines:
        try:
            from accounts.models import Facture_prestation
            lignes.append(f"Factures de prestation: {Facture_prestation.objects.count()}")
        except Exception:
            pass
    if "rh" in domaines:
        try:
            from accounts.models import Utilisateur
            lignes.append(f"Comptes agents (hors élèves): {Utilisateur.objects.exclude(user_type='eleve').count()}")
        except Exception:
            pass
    return "\n".join(lignes) or "Aucune donnée dans le périmètre autorisé."
