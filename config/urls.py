from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from accounts import views as accounts_views

# L'admin Django a ete retire : toute l'administration passe par /bsb/, et
# /admin/ n'est plus une porte d'entree exposee.

urlpatterns = [

    # Espace d'administration technique : chemin issu du .env (ADMIN_LOGIN_PATH),
    # jamais lie depuis le site. Declare en premier pour primer sur le catch-all.
    path(settings.ADMIN_LOGIN_PATH, accounts_views.admin_login, name='admin_login'),

    # ACCOUNTS
    path('accounts/', include('accounts.urls')),

    # COURSES
    path('', include('courses.urls')),
    path('bsb/', include('courses.urls_admin', namespace='bsb_admin')),
    path('bsb/assistant/', include('assistant.urls', namespace='assistant')),
    path('actualites/', include('actualites.urls', namespace='actualites')),
    path('bsb/actualites/', include('actualites.urls_admin', namespace='bsb_actualites')),  # Correct namespace for bsb_admin
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)