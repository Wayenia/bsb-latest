from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ADMIN
    path('admin/', admin.site.urls),

    # ACCOUNTS
    path('accounts/', include('accounts.urls')),

    # COURSES
    path('', include('courses.urls')),
    path('bsb/', include('courses.urls_admin', namespace='bsb_admin')),  # Correct namespace for bsb_admin
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)