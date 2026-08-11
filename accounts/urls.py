from django.urls import path    
from . import views

app_name = "accounts"

urlpatterns = [
    path('register', views.user_register, name='register'),
    path('login', views.user_login, name='login'),
    path('logout', views.user_logout, name='logout'),

    # ── Profil (self-service, tous rôles) ──────────────────────────────────
    path('mon-profil', views.mon_profil, name='mon_profil'),
    path('mon-profil/mot-de-passe', views.changer_mot_de_passe, name='changer_mot_de_passe'),

    # ── Module Facturation et Prestation (DAF) ─────────────────────────────
    path('daf/dashboard', views.daf_dashboard, name='daf_dashboard'),
    path('facturation/client-lookup', views.client_lookup, name='client_lookup'),
    path('facturation/prestation/nouvelle', views.prestation_quick_create, name='prestation_quick_create'),
    path('facturation/prestations', views.prestation_list, name='prestation_list'),
    path('facturation/prestations/nouvelle', views.prestation_create, name='prestation_create'),
    path('facturation/prestations/import/modele', views.prestation_import_template, name='prestation_import_template'),
    path('facturation/prestations/import', views.prestation_import, name='prestation_import'),
    path('facturation/clients', views.client_list, name='client_list'),
    path('facturation/clients/import/modele', views.client_import_template, name='client_import_template'),
    path('facturation/clients/import', views.client_import, name='client_import'),
    path('facturation/nouvelle', views.facture_create, name='facture_create'),
    path('facturation/<int:id>/pdf', views.facture_pdf, name='facture_pdf'),
    path('facturation/<int:id>/valider', views.facture_valider, name='facture_valider'),
    path('encaissement', views.facture_list, name='facture_list'),
    path('encaissement/historique', views.prestation_historique, name='prestation_historique'),
    path('encaissement/<int:id>', views.facture_detail, name='facture_detail'),
    path('encaissement/<int:id>/encaisser', views.prestation_encaisser, name='prestation_encaisser'),
    path('encaissement/recu/<int:id>', views.prestation_recu_pdf, name='prestation_recu_pdf'),
]