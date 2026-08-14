from django.urls import path

from . import views

app_name = "actualites"

urlpatterns = [
    path("", views.liste, name="liste"),
    path("abonnement", views.abonnement, name="abonnement"),
    path("desabonnement/<str:token>", views.desabonnement, name="desabonnement"),
    path("<slug:slug>", views.detail, name="detail"),
]
