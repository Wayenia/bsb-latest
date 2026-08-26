import logging

from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

from accounts import ratelimit

logger = logging.getLogger('django.security')

# startswith et non egalite : CommonMiddleware peut rediriger depuis la
# variante avec slash final.
CHEMINS_CONNEXION = ('/accounts/login',)


class LimitationConnexionMiddleware(MiddlewareMixin):
    """Bloque les connexions au-dela des seuils anti-force brute, avant que la
    vue ne verifie le mot de passe. Le comptage est fait par
    `accounts.signals.on_user_login_failed`."""

    def process_request(self, request):
        if request.method != 'POST':
            return None
        if not request.path.startswith(CHEMINS_CONNEXION):
            return None

        # Lire request.POST sur un multipart consommerait le flux avant les
        # gestionnaires d'upload de Django.
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
    """En-tetes de securite sur toute reponse Django. /static/ et /media/, servis
    directement par nginx, les recoivent via nginx.conf."""

    def process_response(self, request, response):
        # Masque la banniere du serveur applicatif.
        response['Server'] = 'Custom-Server'
        if 'X-Powered-By' in response:
            del response['X-Powered-By']

        # La CSP n'est plus reecrite ici : elle est posee par le middleware natif
        # de Django et s'applique aussi aux pages authentifiees (README 9).

        # Isolation cross-origin : empeche une page tierce de charger ou
        # d'integrer nos ressources et nos fenetres.
        response.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        response.setdefault('Cross-Origin-Embedder-Policy', 'require-corp')

        # Restreint les API navigateur sensibles, aucune n'etant utilisee.
        response.setdefault(
            'Permissions-Policy',
            'geolocation=(), microphone=(), camera=(), payment=(), usb=()')

        # Aucune page Django n'est mise en cache : une liste de prefixes
        # sensibles a maintenir a la main finissait par en oublier.
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'

        return response
