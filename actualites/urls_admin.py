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
    path("annonces", views_admin.annonce_list, name="annonce_list"),
    path("annonces/chemins", views_admin.chemins_internes, name="chemins_internes"),
    path("annonces/create", views_admin.annonce_create, name="annonce_create"),
    path("annonces/<int:id>/update", views_admin.annonce_update, name="annonce_update"),
    path("annonces/<int:id>/etat", views_admin.annonce_basculer, name="annonce_basculer"),
    path("annonces/<int:id>/delete", views_admin.annonce_delete, name="annonce_delete"),
]
