from django.utils.deprecation import MiddlewareMixin


class SecurityHeadersMiddleware(MiddlewareMixin):
    """En-têtes de sécurité posés sur toute réponse Django (pages proxyées par
    nginx). Les fichiers /static/ et /media/, servis directement par nginx sans
    passer par Django, reçoivent les mêmes en-têtes via nginx.conf."""

    def process_response(self, request, response):
        # Masque la bannière du serveur applicatif.
        response['Server'] = 'Custom-Server'
        if 'X-Powered-By' in response:
            del response['X-Powered-By']

        # Isolation cross-origin (findings V14/V15 du scan) : empêche qu'une page
        # tierce charge ou intègre nos ressources et nos fenêtres.
        response.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        response.setdefault('Cross-Origin-Embedder-Policy', 'require-corp')

        # Restreint les API navigateur sensibles ; aucune n'est utilisée par le site.
        response.setdefault(
            'Permissions-Policy',
            'geolocation=(), microphone=(), camera=(), payment=(), usb=()')

        # Pages authentifiées : jamais mises en cache par le navigateur.
        if request.path.startswith(('/admin', '/accounts', '/bsb')):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response
