from django.urls import path

from courses import views
from . import views_admin
from . import views_equipe
from audit import views as vues_audit
from django.conf import settings
from django.conf.urls.static import static

app_name = "bsb_admin"

urlpatterns = [
    # DASHBOARD
    path('dashboard', views_admin.admin_dashboard, name='admin_dashboard'),
    
    # DIRECTION
    path('directions', views_admin.direction_list, name='direction_list'),
    path('directions/create', views_admin.direction_create, name='direction_create'),
    path('directions/import/modele', views_admin.direction_import_template, name='direction_import_template'),
    path('directions/import', views_admin.direction_import, name='direction_import'),
    path('directions/<int:id>/update', views_admin.direction_update, name='direction_update'),
    path('directions/<int:id>/delete', views_admin.direction_delete, name='direction_delete'),

    # FIELD
    path('filiere', views.member_metier_list, name='field_list'),
    path('filiere/create', views.create_metier, name='field_create'),
    path('filiere/import/modele', views.field_import_template, name='field_import_template'),
    path('filiere/import', views.field_import, name='field_import'),
    path('filiere/<int:id>/update', views_admin.field_update, name='field_update'),
    path('filiere/<int:id>/delete', views.metier_delete, name='metier_delete'),

    # CENTER
    path('centers', views_admin.center_list, name='center_list'),
    path('centers/create', views_admin.center_create, name='center_create'),
    path('centers/import/modele', views_admin.center_import_template, name='center_import_template'),
    path('centers/import', views_admin.center_import, name='center_import'),
    path('centers/<int:id>/update', views_admin.center_update, name='center_update'),
    path('centers/<int:id>/delete', views_admin.center_delete, name='center_delete'),

    # MODULES
    path('modules', views_admin.module_list, name='module_list'),
    path('modules/create', views_admin.module_create, name='module_create'),
    path('modules/import/modele', views_admin.module_import_template, name='module_import_template'),
    path('modules/import', views_admin.module_import, name='module_import'),
    path('modules/<int:id>/update', views_admin.module_update, name='module_update'),
    path('modules/<int:id>/delete', views_admin.module_delete, name='module_delete'),

    # FEES
    path('fees', views_admin.fees_list, name='fees_list'),
    path('fees/create', views_admin.fees_create, name='fees_create'),
    path('fees/<int:id>/update', views_admin.fees_update, name='fees_update'),
    path('fees/<int:id>/delete', views_admin.fees_delete, name='fees_delete'),

    # COURSES
    path('courses', views_admin.course_list, name='course_list'),
    path('courses/create', views_admin.course_create, name='course_create'),
    path('courses/import/modele', views_admin.course_import_template, name='course_import_template'),
    path('courses/import', views_admin.course_import, name='course_import'),
    path('courses/<int:id>/update', views_admin.course_update, name='course_update'),
    path('courses/<int:id>/delete', views_admin.course_delete, name='course_delete'),
    
    # SUBSCRIPTION
    path('subscriptions', views_admin.subscription_list, name='subscription_list'),
    path('subscriptions/create', views_admin.subscription_create, name='subscription_create'),
    path('subscriptions/<int:id>/update', views_admin.subscription_update, name='subscription_update'),
    path('subscriptions/<int:id>/delete', views_admin.subscription_delete, name='subscription_delete'),
    path('subscriptions/<int:id>/detail',views_admin.subscription_detail,name='subscription_detail'),
    path('subscriptions/incriptions-a-valide',views_admin.inscription__en_cours_view,name='subscription_en_cours'),
    path('subscriptions/<int:id>/action',views_admin.gerer_inscription,name='gerer_subscription'),
    path('subscriptions/rejeter/<int:id>',views_admin.rejeter_inscription,name='rejeter_inscription'),

    
    # PAYMENT
    path('payments', views_admin.payment_list, name='payment_list'),
    path('payments/create', views_admin.payment_create, name='payment_create'),
    path('payments/<int:id>/update', views_admin.payment_update, name='payment_update'),
    path('payments/<int:id>/delete', views_admin.payment_delete, name='payment_delete'),
    path('payment/list-paiement',views_admin.payment_list,name='payment_list'),

    # HISTORIQUE DES CONNEXIONS
    path('historique-connexions', views_admin.historique_connexion_list, name='historique_connexion_list'),
    # Export CSV retire : le classeur Excel porte l'en-tete et les filtres appliques,
    # un CSV brut circulait sans ce contexte.
    path('historique-connexions/export/<str:format>', views_admin.historique_connexion_export, name='historique_connexion_export'),
    # Diffusion du rapport d'inspection (application audit)
    path('historique-connexions/destinataires',                vues_audit.destinataire_list,            name='destinataire_audit_list'),
    path('historique-connexions/destinataires/<int:pk>/etat',  vues_audit.destinataire_basculer,        name='destinataire_audit_basculer'),
    path('historique-connexions/destinataires/<int:pk>/retirer', vues_audit.destinataire_supprimer,     name='destinataire_audit_supprimer'),
    path('historique-connexions/destinataires/import/modele',  vues_audit.destinataire_import_template, name='destinataire_audit_import_template'),
    path('historique-connexions/destinataires/import',         vues_audit.destinataire_import,          name='destinataire_audit_import'),
    path('historique-connexions/destinataires/envoyer',        vues_audit.destinataire_envoyer,         name='destinataire_audit_envoyer'),
    path('historique-connexions/destinataires/reglage',        vues_audit.reglage_diffusion,            name='destinataire_audit_reglage'),

    #PROGRAMMING
    path('programmings',views_admin.programming_list,name='programming_list'),
    path('programmings/create',views_admin.programming_create,name='program_create'),
    path('programmings/<int:id>/update',views_admin.update_pregramming,name='programming_update'),
    path('programmings/<int:id>/delete',views_admin.programming_delete,name='programming_delete'),
    path('programmings/import/modele', views_admin.programming_import_template, name='programming_import_template'),
    path('programmings/import', views_admin.programming_import, name='programming_import'),


    #Année scolaire
    path('annee/create',views_admin.annee_create,name='annee_create'),
    path('annees',views_admin.annee_list,name='annee_list'),
    # AGENTS (RH unifié)
    path('rh/agents', views_admin.agent_list, name='agent_list'),
    path('rh/agents/creer', views_admin.agent_create, name='agent_create'),
    path('rh/agents/import/modele', views_admin.agent_import_template, name='agent_import_template'),
    path('rh/agents/import', views_admin.agent_import, name='agent_import'),
    path('rh/agents/<int:id>/modifier', views_admin.agent_update, name='agent_update'),
    path('rh/agents/<int:id>/supprimer', views_admin.agent_delete, name='agent_delete'),
    path('rh/agents/<int:id>/suspendre', views_admin.agent_toggle_active, name='agent_toggle_active'),
    # APPRENANTS (modification complète, y compris mot de passe)
    path('eleves', views_admin.eleve_list, name='eleve_list'),
    path('eleves/<int:id>/modifier', views_admin.eleve_update, name='eleve_update'),
    # GESTION DES PERMISSIONS (matrice rôle x action)
    path('rh/permissions', views_admin.permissions_matrix_view, name='permissions_matrix'),
    # TYPE DE FRAIS
    path('type-frais',                       views_admin.type_frais_list,   name='type_frais_list'),
    path('type-frais/create',                views_admin.type_frais_create, name='type_frais_create'),
    path('type-frais/import/modele',         views_admin.type_frais_import_template, name='type_frais_import_template'),
    path('type-frais/import',                views_admin.type_frais_import, name='type_frais_import'),
    path('type-frais/<int:id>/update',       views_admin.type_frais_update, name='type_frais_update'),
    path('type-frais/<int:id>/delete',       views_admin.type_frais_delete, name='type_frais_delete'),
    path('type-frais/<int:id>/tranches',     views_admin.type_frais_tranches, name='type_frais_tranches'),

    # ANNÉE SCOLAIRE  (update + delete s'ajoutent aux 2 existants)
    path('annee/create',                     views_admin.annee_create,      name='annee_create'),
    path('annees',                           views_admin.annee_list,        name='annee_list'),
    path('annees/import/modele',             views_admin.annee_import_template, name='annee_import_template'),
    path('annees/import',                    views_admin.annee_import,      name='annee_import'),
    path('annees/<int:id>/update',           views_admin.annee_update,      name='annee_update'),
    path('annees/<int:id>/delete',           views_admin.annee_delete,      name='annee_delete'),
             # Régions
    path("regions/",                    views.region_list,    name="region_list"),
    path("regions/creer/",              views.region_create,  name="region_create"),
    path("regions/<int:pk>/modifier/",  views.region_update,  name="region_update"),
    path("regions/<int:pk>/supprimer/", views.region_delete,  name="region_delete"),
    path("regions/import/modele/",      views.region_import_template, name="region_import_template"),
    path("regions/import/",             views.region_import,  name="region_import"),

    # Provinces
    path("provinces/creer/",              views.province_create,  name="province_create"),
    path("provinces/<int:pk>/modifier/",  views.province_update,  name="province_update"),
    path("provinces/<int:pk>/supprimer/", views.province_delete,  name="province_delete"),
    path("provinces/import/modele/",      views.province_import_template, name="province_import_template"),
    path("provinces/import/",             views.province_import,  name="province_import"),

    # Équipe (Directeur Général et membres) — remplace l'admin Django, retiré
    # du projet. Alimente la page publique « À propos ».
    path("equipe/",                          views_equipe.equipe_list,    name="equipe_list"),
    path("equipe/dg/creer/",                 views_equipe.dg_create,      name="dg_create"),
    path("equipe/dg/<int:pk>/modifier/",     views_equipe.dg_update,      name="dg_update"),
    path("equipe/dg/<int:pk>/supprimer/",    views_equipe.dg_delete,      name="dg_delete"),
    path("equipe/membre/creer/",             views_equipe.membre_create,  name="membre_create"),
    path("equipe/membre/<int:pk>/modifier/", views_equipe.membre_update,  name="membre_update"),
    path("equipe/membre/<int:pk>/supprimer/", views_equipe.membre_delete, name="membre_delete"),
    path("equipe/membres/import/modele",     views_admin.membre_import_template, name="membre_import_template"),
    path("equipe/membres/import",            views_admin.membre_import,          name="membre_import"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)