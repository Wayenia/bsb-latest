from django.urls import path

from . import views_admin

app_name = "bsb_actualites"

urlpatterns = [
    path("", views_admin.actualite_list, name="actualite_list"),
    path("create", views_admin.actualite_create, name="actualite_create"),
    path("<int:id>/update", views_admin.actualite_update, name="actualite_update"),
    path("<int:id>/delete", views_admin.actualite_delete, name="actualite_delete"),
    path("<int:id>/publier", views_admin.actualite_publier, name="actualite_publier"),
    path("abonnes", views_admin.abonne_list, name="abonne_list"),
]
