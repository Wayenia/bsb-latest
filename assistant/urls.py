from django.urls import path

from . import views

app_name = "assistant"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("demander", views.demander, name="demander"),
    path("acces", views.acces, name="acces"),
    path("modeles", views.modeles, name="modeles"),
    path("journal", views.journal, name="journal"),
]
