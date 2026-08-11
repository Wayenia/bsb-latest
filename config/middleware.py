from django.utils.deprecation import MiddlewareMixin

class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # X-Content-Type-Options / X-Frame-Options / Referrer-Policy / X-XSS-Protection
        # sont deja poses par nginx (add_header) pour toutes les reponses -
        if 'Server' in response:
            response['Server'] = 'Custom-Server'

        if 'X-Powered-By' in response:
            del response['X-Powered-By']

        if request.path.startswith('/admin') or request.path.startswith('/accounts'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response
