# Pages a rendre responsives — tableaux de plus de 3 colonnes

Releve **factuel** obtenu en comptant les balises `<th>` du premier `<thead>` de
chaque gabarit, commentaires retires. Sont exclus : l'espace apprenant (hors
perimetre demande), les gabarits PDF (`*_pdf.html`, qui ne sont pas des pages
web) et les replis de reversibilite (`*_classique.html`, qui ne sont pas des
ecrans distincts).

Le nombre de colonnes est le **maximum** du gabarit : certains tableaux ont des
colonnes conditionnelles selon le perimetre de l'utilisateur, elles sont
comptees.

Methode de reproduction : compter les `<th>` par `<thead>`, puis relier chaque
gabarit a sa vue (`render(...)` ou `template_name`) et sa vue a sa route
(`path(...)`).

## Ordre de traitement suggere

Les tableaux les plus larges sont les plus urgents : au telephone, onze
colonnes imposent un defilement horizontal qui rend la lecture impraticable.

**Mise a jour.** Ces pages recoivent desormais un repli automatique des colonnes
au-dela de la troisieme, dans une fiche depliable au telephone
(`static/js/bo-tableau.js`), et leur conteneur occupe toute la largeur
disponible sous la barre laterale (README 9.8). Le releve ci-dessous reste
valable : il compte les `<th>` presents dans le balisage, que ce repli n'enleve
pas mais masque selon la largeur de l'ecran. Il sert d'inventaire de suivi.

```
37 PAGES WEB avec un tableau de plus de 3 colonnes
(gabarits PDF et replis _classique exclus ; espace apprenant hors perimetre)

COL  ROLE                     ROUTE                                                GABARIT
-------------------------------------------------------------------------------------------------------------------------------------------------
 11  Caisse / centre          /membre/centre/paiement/historique                   member/paiement/historique.html
  9  Formateur                /formateur/filiere/<id>/etudiants                    teacher/filieres/etudiants.html
  8  Caisse / centre          /membre/centre/paiement/list-paiement                member/paiement/list.html
  8  DAF                      /accounts/encaissement/historique                    accounts/facturation/historique.html
  8  Direction / caisse       /bsb/payments                                        admin/payment/list.html
  8  Formateur                /formateur/dashboard                                 teacher/dashboard/dashboard/dashboard.html
  8  Tous agents              /statistiques/stat-globaux/                          member/statistiques/statistiques.html
  7  Caisse                   /statistiques/paiement/dette/<id>/                   member/statistiques/stats_detail_dette.html
  7  Direction                /bsb/courses                                         admin/course/list.html
  7  Formateur                /formateur/mes-filieres                              teacher/filieres/list.html
  6  Caisse                   /statistiques/paiement/dette/<id>/tranche/<n>/       member/statistiques/stats_quittance_tranche.html
  6  Centre                   /centres/<id>/filieres/                              admin/center/filieres.html
  6  Centre                   /membre/centre/souscriptions                         member/inscriptions/list.html
  6  Centre                   /membre/centre/souscriptions/inscriptions-a-valider  member/inscriptions/valide_inscription.html
  6  DAF                      /accounts/encaissement                               accounts/facturation/facture_list.html
  6  DAF                      /accounts/encaissement/<id>                          accounts/facturation/facture_detail.html
  6  Direction                /bsb/programmings                                    admin/programming/list.html
  6  Direction                /bsb/subscriptions                                   admin/subscription/list.html
  6  Direction                /bsb/subscriptions/incriptions-a-valide              admin/subscription/validate_inscription.html
  6  Direction / RH           /bsb/rh/agents                                       admin/rh/agent_list.html
  6  Supervision              /bsb/historique-connexions                           admin/historique_connexion/list.html
  5  Caisse                   /statistiques/paiement/recherche                     member/statistiques/stats_paiement_recherche.html
  5  Centre                   /membre/centre/list-filiere                          member/filiere/list.html
  5  DAF                      /accounts/facturation/prestations                    accounts/facturation/prestation_list.html
  5  DAF                      /accounts/facturation/proforma                       accounts/facturation/facture_proforma_list.html
  5  DEPS / centre            /statistiques-reelles/                               member/stats_reel/dashboard.html
  5  Direction                /bsb/directions                                      admin/direction/list.html
  5  Direction                /bsb/fees                                            admin/fees/list.html
  5  Direction                /bsb/filiere                                         admin/field/list.html
  5  Direction                /bsb/type-frais/<id>/tranches                        admin/fees/type_frais_tranches.html
  4  DAF                      /accounts/facturation/clients                        accounts/facturation/client_list.html
  4  Directeur inter-régional /membre/dashboard/direction/<id>/                    teacher/dashboard/dashboard.html
  4  Direction                /bsb/dashboard                                       admin/admin_dashboard/dashboard.html
  4  Direction                /bsb/modules                                         admin/module/list.html
  4  Direction                /bsb/regions/                                        admin/region/region_list.html
  4  Direction                /bsb/type-frais                                      admin/fees/type_frais_list.html
  4  Direction / RH           /bsb/eleves                                          admin/eleve/list.html
```
