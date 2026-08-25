from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# L'admin Django (django.contrib.admin + jazzmin) a ete retire du projet : il
# n'avait servi qu'au debogage. Toute l'administration passe par le back-office
# maison sous /bsb/, gouverne par les permissions Django (courses/permissions.py).
# Effet de bord recherche : /admin/ n'est plus une porte d'entree exposee.

urlpatterns = [

    # ACCOUNTS
    path('accounts/', include('accounts.urls')),

    # COURSES
    path('', include('courses.urls')),
    path('bsb/', include('courses.urls_admin', namespace='bsb_admin')),
    path('actualites/', include('actualites.urls', namespace='actualites')),
    path('bsb/actualites/', include('actualites.urls_admin', namespace='bsb_actualites')),  # Correct namespace for bsb_admin
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)