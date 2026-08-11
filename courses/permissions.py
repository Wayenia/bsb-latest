# permissions.py
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def require_permission(*codenames):
    """
    Décorateur de vue : exige au moins une des permissions Django `codenames`
    (format 'app_label.codename', ex. 'courses.gerer_metiers'). Plusieurs
    codenames sont acceptés quand une même page peut être ouverte par
    différentes permissions (ex. lister les paiements avec soit
    'encaisser_paiement' soit 'gerer_paiements').

    Contrairement à l'ancien système par rôle en dur, la permission est
    résolue via les groupes/permissions Django (voir Utilisateur.ROLE_GROUPS
    et l'écran "Gestion des permissions") — révoquer/accorder une permission
    change immédiatement ce qu'un utilisateur peut faire, quel que soit son rôle.

    En cas de refus, on lève PermissionDenied (page 403) plutôt que de
    rediriger vers la connexion : un utilisateur déjà connecté qui échoue
    ce contrôle ne doit jamais être renvoyé vers le login, ce qui créerait
    une boucle de redirection (login → redirect_to_dashboard → login → ...).
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser or any(request.user.has_perm(c) for c in codenames):
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("Vous n'avez pas la permission d'effectuer cette action.")
        return _wrapped
    return decorator


def require_role(*user_types):
    """
    Décorateur pour les vues d'identité (ex. le tableau de bord propre à un
    formateur) qui ne correspondent pas à une permission accordable à un
    autre rôle. Refuse via une page 403 (jamais de redirection vers le
    login), pour la même raison anti-boucle que `require_permission`.
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser or request.user.user_type in user_types:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("Cette page est réservée à un autre rôle.")
        return _wrapped
    return decorator
