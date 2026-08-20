from django.urls import path
from . import views
from . import views_stats_reel
from django.conf import settings
from django.conf.urls.static import static

app_name = "courses"

urlpatterns = [
    # ABOUT
    path('', views.home, name='home'),
    path('about', views.about_view, name='about'),

    # STUDENT
    path('student/dashboard', views.student_dashboard, name='student_dashboard'),
    path('student/my-subscriptions', views.my_subscriptions, name='my_subscriptions'),
    path('student/paiement/info-centre', views.paiement_info_centre, name='paiement_info_centre'),
    path('student/paiement/<int:id>', views.effectuer_paiment,name='paiement'),

    #Notifications 
     path('notifications/', views.page_notifications, name='notifications'),
     path('notifications/count/', views.notifications_count, name='notifications_count'),

    path('student/subscribe/choisir', views.subscribe_selection_view, name='subscribe_selection'),
    path('student/subscribe/career', views.available_career_view, name='available_career'),
    path('student/subscribe/career/<int:id>', views.get_career_by_id, name='get_career_by_id'),
    path('student/subscribe/career/documents', views.documents_view, name='documents'),
    path('student/subscribe/<int:career_id>/personal-info', views.personal_info_view, name='personal_info'),
    path('student/subscribe/recap', views.recap_view, name='recap'),
    path('student/suscribe/dette/<int:id>/',views.liste_dettes,name='liste_dettes'),
    path('student/paiement/',views.liste_paiement,name='mes_paiements'),
    path('student/paiement/quittance/<int:id>', views.telecharger_quittance , name='quittance'),
    path('student/paiement/reportlab-quitt/<int:id>',views.download_quittance,name='reportlab'),
    path('student/inscription/<int:id>/recepisse', views.telecharger_recepisse, name='telecharger_recepisse'),
    path('student/inscription/<int:id>/attestation', views.telecharger_attestation, name='telecharger_attestation'),
    # TEACHER
    path('teacher/dashboard', views.teacher_dashboard, name='teacher_dashboard'),
    
    
    #Member Of Center
    # urls.py
    path('membre/dashboard', views.member_dashboard, name='member_dashboard'),
    
    #Filière
    path('membre/centre/list-filiere',views.member_metier_list,name='member_field_list'),
    #Souscritpions
    path('membre/centre/souscriptions',views.member_inscriptions_list,name='subscription_list'),
    path('membre/dashboard/direction/<int:id>/', views.member_dashboard_direction, name='member_dashboard_direction'),
    path('membre/centre/souscriptions/inscriptions-a-valider', views.member_inscription_en_cours, name='valide_inscription'),
    path('membre/centre/souscriptions/<int:id>/detail',views.member_inscription_detail,name='inscription_detail'),
    path('membre/centre/souscriptions/gerer/<int:id>',views.gerer_inscription,name='gerer_inscription'),
    path('membre/centre/souscriptions/rejeter/<int:id>/',views.rejeter_inscription,name='rejeter_inscription'),
    path('membre/centre/filiere/ajouter',views.create_metier,name='create_field'),
    
    #Liste de paiement de membre en fait
    path('membre/centre/paiement/list-paiement',views.paiement_list,name='paiement_list'),
    path('membre/centre/paiement/historique',views.paiement_historique,name='paiement_historique'),
    #path('member/dashboard/center/<int:id>', views.member_dashboard, name='member_dashboard'),

    # HELPER
    path('redirect-dashboard', views.redirect_to_dashboard, name='redirect_to_dashboard'),
     # ── Statistiques ──────────────────────────────────────────────────────────
    path('statistiques/stat-globaux/',
         views.statistiques_view,
         name='statistiques'),
     path('statistiques/export-pdf/',
         views.export_pdf,
         name='export_pdf'),
     path('statistiques/export-csv/',
         views.export_csv,
         name='export_csv'),
     path('statistiques/export-excel/',
         views.export_excel,
         name='export_excel'),
    # ── Paiement : dettes d'un élève ──────────────────────────────────────────
    path('statistiques/paiement/eleve/<int:eleve_id>/',
         views.stats_dettes_eleve_view,
         name='stats_dettes_eleve'),
 
    # ── Paiement : détail d'une dette + enregistrement paiement ──────────────
    path('statistiques/paiement/dette/<int:dette_id>/',
         views.stats_detail_dette_view,
         name='stats_detail_dette'),
 
    # ── Encaisser le solde d'un type de frais (une dette) ─────────────────────
    path('statistiques/paiement/dette/<int:dette_id>/solder',
         views.stats_encaisser_solde_dette_view,
         name='stats_encaisser_solde_dette'),

    # ── Encaisser le solde de tous les types de frais d'une inscription ───────
    path('statistiques/paiement/inscription/<int:inscription_id>/solder',
         views.stats_encaisser_solde_inscription_view,
         name='stats_encaisser_solde_inscription'),

    # ── Quittance d'une tranche (liste des paiements) ─────────────────────────
    path('statistiques/paiement/dette/<int:dette_id>/tranche/<int:tranche>/',
         views.stats_quittance_tranche_view,
         name='stats_quittance_tranche'),
 
    # ── Téléchargement PDF d'une quittance ────────────────────────────────────
    path('statistiques/paiement/quittance/<int:paiement_id>/pdf/',
         views.stats_download_quittance_view,
         name='stats_download_quittance'),

    # ── Statistiques réelles (effectifs formés + liste nominative) ───────────
    path('statistiques-reelles/',
         views_stats_reel.stats_reel_dashboard,
         name='stats_reel_dashboard'),
    path('statistiques-reelles/<int:formation_id>/modele/',
         views_stats_reel.stats_reel_formation_template,
         name='stats_reel_formation_template'),
    path('statistiques-reelles/<int:formation_id>/upload/',
         views_stats_reel.stats_reel_formation_upload,
         name='stats_reel_formation_upload'),
    path('statistiques-reelles/export/nominatif/',
         views_stats_reel.stats_reel_export_nominatif,
         name='stats_reel_export_nominatif'),
    path('statistiques-reelles/export/agrege/',
         views_stats_reel.stats_reel_export_agrege,
         name='stats_reel_export_agrege'),
    path('statistiques-reelles/export/certification/',
         views_stats_reel.stats_reel_export_certification,
         name='stats_reel_export_certification'),
    path('statistiques-reelles/export/handicap/',
         views_stats_reel.stats_reel_export_handicap,
         name='stats_reel_export_handicap'),

    # ── Centres ──────────────────────────────────────────────────────────
    path('centres/',                   views.CenterListView.as_view(),   name='center_list'),
    path('centres/creer/',             views.CenterCreateView.as_view(), name='center_create'),
    path('centres/<int:pk>/modifier/', views.CenterUpdateView.as_view(), name='center_update'),
    path('centres/<int:pk>/supprimer/',views.CenterDeleteView.as_view(), name='center_delete'),
    path('centres/<int:pk>/filieres/', views.CenterFiliereListView.as_view(), name='center_filieres'),
    path('centres/<int:pk>/filieres/', views.CenterFiliereListView.as_view(), name='center_filieres'),
    # FORMATEUR
     path('formateur/dashboard', views.formateur_dashboard, name='formateur_dashboard'),
     path('formateur/mes-filieres', views.formateur_filieres, name='formateur_filieres'),
     path('formateur/filiere/<int:formation_id>/etudiants', views.formateur_etudiants, name='formateur_etudiants'),
     path('formateur/filiere/<int:formation_id>/export/<str:format>', views.formateur_export, name='formateur_export'),

    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)