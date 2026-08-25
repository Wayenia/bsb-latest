import logging

from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

from accounts import ratelimit

logger = logging.getLogger('django.security')

# Chemin de connexion surveille. `startswith` et non egalite : la route est
# declaree sans slash final (/accounts/login) mais CommonMiddleware peut
# rediriger depuis la variante avec slash.
# /admin/login a disparu de la liste : l'admin Django a ete retire du projet.
CHEMINS_CONNEXION = ('/accounts/login',)


class LimitationConnexionMiddleware(MiddlewareMixin):
    """Refuse les tentatives de connexion au-dela des seuils anti-force brute.

    Le comptage se fait dans `accounts.signals.on_user_login_failed` (branche
    sur le signal `user_login_failed`) ; ce middleware ne fait que *bloquer* en
    amont, avant que la vue ne verifie le mot de passe. Sans lui, un compte
    verrouille continuerait a etre teste : le compteur monterait, mais chaque
    tentative resterait evaluee.
    """

    def process_request(self, request):
        if request.method != 'POST':
            return None
        if not request.path.startswith(CHEMINS_CONNEXION):
            return None

        # Ne jamais toucher a request.POST sur un envoi multipart : cela
        # consommerait le flux avant les gestionnaires d'upload de Django. Les
        # formulaires de connexion sont urlencodes, jamais multipart.
        username = ''
        if not request.content_type.startswith('multipart/'):
            username = request.POST.get('username', '')

        motif = ratelimit.motif_verrou(request, username)
        if motif is None:
            return None

        logger.warning(
            'Connexion bloquee (verrou %s) pour "%s" depuis %s sur %s',
            motif, username[:150], ratelimit.adresse_client(request), request.path)
        reponse = render(request, '429.html', {
            'motif': motif,
            'minutes': ratelimit.DUREE_VERROU // 60,
        }, status=429)
        reponse['Retry-After'] = str(ratelimit.DUREE_VERROU)
        return reponse


class SecurityHeadersMiddleware(MiddlewareMixin):
    """En-têtes de sécurité posés sur toute réponse Django (pages proxyées par
    nginx). Les fichiers /static/ et /media/, servis directement par nginx sans
    passer par Django, reçoivent les mêmes en-têtes via nginx.conf."""

    def process_response(self, request, response):
        # Masque la bannière du serveur applicatif.
        response['Server'] = 'Custom-Server'
        if 'X-Powered-By' in response:
            del response['X-Powered-By']

        # La CSP n'est plus reecrite ici.
        # Ce middleware assouplissait auparavant script-src en 'unsafe-inline'
        # pour tout utilisateur authentifie, parce que le back-office reposait
        # sur des attributs onclick=/onsubmit=. Consequence : les pages qui
        # portent les donnees sensibles (dossiers, paiements, factures) etaient
        # les SEULES sans protection CSP contre le XSS, et le scan Acunetix ne
        # pouvait pas le voir puisqu'il travaillait sans profil authentifie.
        # Les 59 gestionnaires inline ont ete convertis en ecouteurs delegues
        # (attributs data-*), la politique stricte du middleware natif Django
        # — script-src 'self' 'nonce-...' — s'applique donc partout.

        # Isolation cross-origin (findings V14/V15 du scan) : empêche qu'une page
        # tierce charge ou intègre nos ressources et nos fenêtres.
        response.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        response.setdefault('Cross-Origin-Embedder-Policy', 'require-corp')

        # Restreint les API navigateur sensibles ; aucune n'est utilisée par le site.
        response.setdefault(
            'Permissions-Policy',
            'geolocation=(), microphone=(), camera=(), payment=(), usb=()')

        # Aucune page servie par Django n'est mise en cache. /static/ et
        # /media/ ne passent pas par ce middleware (nginx.conf les sert
        # directement avec leur propre Cache-Control) : restreindre cette
        # regle a une liste de prefixes "sensibles" a maintenir a la main
        # avait fini par en oublier - paiement, dette, inscription, stats -
        # des lors qu'ils sont montes a la racine par courses.urls plutot que
        # sous /accounts ou /bsb (cf. config/urls.py).
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'

        return response
