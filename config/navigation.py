"""Description de la navigation du back-office.

Declaree en donnees plutot qu'en balisage : l'ordre, les regroupements et les
permissions se lisent et se modifient a un seul endroit, et le gabarit se
reduit a une boucle. C'est aussi ce qui rend l'ensemble verifiable par des
tests, ce qu'un balisage repete ne permet pas.

Ordre des groupes : du plus consulte au plus rare. Un agent de centre ouvre
les inscriptions et les encaissements plusieurs fois par jour, la decoupe
territoriale une fois par an. Les intitules restent ceux du tableau de bord
que le personnel connait deja.

Les couleurs sont celles de la charte Yupaan — rouge, or et vert — et non une
palette inventee : l'espace de travail doit se reconnaitre comme la partie
publique du site. Elles alternent d'un grand theme au suivant, ce qui donne un
repere stable : on retrouve un groupe a sa couleur avant d'en relire le titre.
"""
from django.urls import NoReverseMatch, reverse

# Les classes sont ecrites en toutes lettres : tailwind.config.js balaie
# ./**/*.py, une classe assemblee dynamiquement ne serait pas compilee.
COULEURS = {
    'rouge':  {'puce': 'bg-bsb-red/10 text-bsb-red',
               'bord': 'border-l-bsb-red',     'actif': 'bg-bsb-red/10 text-bsb-red'},
    'or':     {'puce': 'bg-bsb-gold/10 text-bsb-gold',
               'bord': 'border-l-bsb-gold',    'actif': 'bg-bsb-gold/10 text-bsb-gold'},
    'vert':   {'puce': 'bg-bsb-green/10 text-bsb-green',
               'bord': 'border-l-bsb-green',   'actif': 'bg-bsb-green/10 text-bsb-green'},
    'grenat': {'puce': 'bg-bsb-dark/10 text-bsb-dark',
               'bord': 'border-l-bsb-dark',    'actif': 'bg-bsb-dark/10 text-bsb-dark'},
}

# Traces d'icones (24x24, contour). Regroupees ici pour que le gabarit ne
# porte aucun balisage SVG.
ICONES = {
    'jauge':     'M3 13h2l2-5 3 10 3-13 2 8h6',
    'graphique': 'M4 19V5m0 14h16M8 17V9m4 8V6m4 11v-5',
    'dossier':   'M4 7a2 2 0 012-2h3l2 2h7a2 2 0 012 2v8a2 2 0 01-2 2H6a2 2 0 01-2-2V7z',
    'monnaie':   'M12 8c-2 0-3 .9-3 2s1 2 3 2 3 .9 3 2-1 2-3 2m0-8c1.5 0 2.5.5 3 1.5M12 8V6m0 12v-2m0 2c-1.5 0-2.5-.5-3-1.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
    'livre':     'M4 5a2 2 0 012-2h9a2 2 0 012 2v14l-5-3-5 3V5z',
    'personnes': 'M17 20h5v-2a3 3 0 00-5.4-1.8M17 20H7m10 0v-2c0-.7-.1-1.3-.4-1.8M7 20H2v-2a3 3 0 015.4-1.8M7 20v-2c0-.7.1-1.3.4-1.8m0 0a5 5 0 019.2 0M15 7a3 3 0 11-6 0 3 3 0 016 0z',
    'megaphone': 'M11 5.9L6 9H4a1 1 0 00-1 1v4a1 1 0 001 1h2l5 3.1V5.9zM15.5 8.5a5 5 0 010 7',
    'carte':     'M9 20l-5.4 2.7A1 1 0 013 21.8V6.2a1 1 0 01.6-.9L9 3m0 17l6-3m-6 3V3m6 14l5.4 2.7a1 1 0 001.6-.9V5.2a1 1 0 00-.6-.9L15 2m0 15V2M9 3l6-1',
    'reglages':  'M10.3 4.3a1 1 0 011-.8h1.4a1 1 0 011 .8l.2 1.3a7 7 0 011.6.9l1.2-.5a1 1 0 011.2.4l.7 1.2a1 1 0 01-.2 1.3l-1 .8a7 7 0 010 1.8l1 .8a1 1 0 01.2 1.3l-.7 1.2a1 1 0 01-1.2.4l-1.2-.5a7 7 0 01-1.6.9l-.2 1.3a1 1 0 01-1 .8h-1.4a1 1 0 01-1-.8l-.2-1.3a7 7 0 01-1.6-.9l-1.2.5a1 1 0 01-1.2-.4l-.7-1.2a1 1 0 01.2-1.3l1-.8a7 7 0 010-1.8l-1-.8a1 1 0 01-.2-1.3l.7-1.2a1 1 0 011.2-.4l1.2.5a7 7 0 011.6-.9l.2-1.3zM15 12a3 3 0 11-6 0 3 3 0 016 0z',
    'bouclier':  'M12 3l7 3v5c0 4.4-2.9 8.5-7 9.8-4.1-1.3-7-5.4-7-9.8V6l7-3z',
}


def _lien(nom_url, libelle, permission=None, prefixe_actif=None, args=None):
    return {
        'nom_url': nom_url, 'libelle': libelle, 'permission': permission,
        'prefixe_actif': prefixe_actif, 'args': args or [],
    }


GROUPES = [
    {
        'cle': 'pilotage', 'titre': 'Pilotage', 'couleur': 'rouge', 'icone': 'graphique',
        'liens': [
            _lien('courses:statistiques', 'Statistiques', 'courses.voir_statistiques', '/statistiques/stat-globaux'),
            _lien('courses:stats_reel_dashboard', 'Bilan des effectifs formés', 'courses.gerer_statistiques_reelles', '/statistiques-reelles'),
        ],
    },
    {
        'cle': 'scolarite', 'titre': 'Scolarité', 'couleur': 'or', 'icone': 'dossier',
        'liens': [
            _lien('bsb_admin:subscription_list', 'Inscriptions', 'courses.voir_inscriptions', '/bsb/subscriptions'),
            _lien('bsb_admin:eleve_list', 'Apprenants', 'accounts.gerer_eleves', '/bsb/eleves'),
        ],
    },
    {
        'cle': 'finances', 'titre': 'Encaissements et facturation', 'couleur': 'vert', 'icone': 'monnaie',
        'liens': [
            _lien('courses:paiement_list', 'Encaissements scolarité', 'courses.encaisser_paiement', '/membre/centre/paiement'),
            _lien('accounts:prestation_list', 'Prestations', 'accounts.gerer_facturation', '/accounts/facturation/prestations'),
            _lien('accounts:facture_proforma_list', 'Factures proforma', 'accounts.gerer_facturation', '/accounts/facturation/proforma'),
            _lien('accounts:facture_list', 'Encaissement prestations', 'accounts.encaisser_prestation', '/accounts/encaissement'),
        ],
    },
    {
        'cle': 'offre', 'titre': 'Offre de formation', 'couleur': 'grenat', 'icone': 'livre',
        'liens': [
            _lien('bsb_admin:programming_list', 'Programmations', 'courses.gerer_programmations', '/bsb/programmings'),
            _lien('bsb_admin:field_list', 'Métiers', 'courses.gerer_metiers', '/bsb/filiere'),
            _lien('bsb_admin:module_list', 'Modules et cours', 'courses.gerer_modules', '/bsb/modules'),
            _lien('courses:center_list', 'Centres', 'courses.gerer_centres', '/centres'),
        ],
    },
    {
        'cle': 'rh', 'titre': 'RH et Permissions', 'couleur': 'rouge', 'icone': 'personnes',
        'liens': [
            _lien('bsb_admin:agent_list', 'Agents et formateurs', 'accounts.gerer_agents', '/bsb/rh/agents'),
            _lien('bsb_admin:permissions_matrix', 'Permissions', 'accounts.gerer_permissions', '/bsb/rh/permissions'),
            _lien('bsb_admin:equipe_list', 'Équipe publique', 'courses.gerer_equipe', '/bsb/equipe'),
        ],
    },
    {
        'cle': 'communication', 'titre': 'Communication', 'couleur': 'or', 'icone': 'megaphone',
        'liens': [
            _lien('bsb_actualites:actualite_list', 'Actualités', 'actualites.gerer_actualites', '/bsb/actualites'),
            _lien('bsb_actualites:abonne_list', 'Abonnés à la lettre', 'actualites.gerer_newsletter', '/bsb/actualites/abonnes'),
        ],
    },
    {
        'cle': 'supervision', 'titre': 'Supervision', 'couleur': 'vert', 'icone': 'bouclier',
        'liens': [
            _lien('bsb_admin:historique_connexion_list', 'Historique des connexions', 'accounts.voir_historique_connexion', '/bsb/historique-connexions'),
        ],
    },
    {
        'cle': 'territoire', 'titre': 'Territoire', 'couleur': 'grenat', 'icone': 'carte',
        'liens': [
            _lien('bsb_admin:direction_list', 'Directions inter-régionales', 'courses.gerer_directions', '/bsb/directions'),
            _lien('bsb_admin:region_list', 'Régions et provinces', 'courses.gerer_regions', '/bsb/regions'),
        ],
    },
    {
        'cle': 'parametrage', 'titre': 'Paramétrage', 'couleur': 'rouge', 'icone': 'reglages',
        'liens': [
            _lien('bsb_admin:type_frais_list', 'Types de frais', 'courses.gerer_frais', '/bsb/type-frais'),
            _lien('bsb_admin:annee_list', 'Années de formation', 'courses.gerer_annees', '/bsb/annees'),
        ],
    },
]


def construire_menu(utilisateur, chemin):
    """Menu resolu pour cet utilisateur : liens autorises, URL calculees, et
    groupe courant marque afin que le gabarit le deplie d'emblee.

    Un lien dont la route n'existe pas est ignore silencieusement plutot que de
    faire echouer la page entiere : une navigation ne doit jamais empecher
    d'atteindre le reste de l'application.
    """
    menu = []
    for groupe in GROUPES:
        liens = []
        for lien in groupe['liens']:
            if lien['permission'] and not utilisateur.has_perm(lien['permission']):
                continue
            try:
                url = reverse(lien['nom_url'], args=lien['args'])
            except NoReverseMatch:
                continue
            prefixe = lien['prefixe_actif'] or url
            liens.append({'libelle': lien['libelle'], 'url': url,
                          'actif': chemin.startswith(prefixe)})
        if not liens:
            continue
        menu.append({
            'cle': groupe['cle'],
            'titre': groupe['titre'],
            'couleur': COULEURS[groupe['couleur']],
            'icone': ICONES[groupe['icone']],
            'liens': liens,
            'actif': any(l['actif'] for l in liens),
        })
    return menu
