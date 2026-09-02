"""Contenu du guide d'aide, par role.

Le texte pas-a-pas est tire des vrais parcours (memes vues, memes intitules que
l'application), pour que le guide ne s'ecarte jamais de ce que l'agent voit a
l'ecran. Chaque etape reserve un emplacement d'image : la vraie capture, une
fois deposee sous static/aides/<role>/, s'affiche automatiquement ; en son
absence, un repli soigne indique « capture a venir ».

Un role dont le guide n'est pas encore redige renvoie None : la page affiche
alors un etat « en preparation » et la section contacts reste disponible.
"""

# Coordonnees du support : a completer par l'administration (valeurs reelles).
SUPPORT = {
    'organisation': "Plateforme Yupaan — Burkina Suudu Bawdè",
    'email': "",
    'telephone': "",
    'horaires': "Du lundi au vendredi, de 7 h 30 à 16 h 30",
    'a_completer': True,
}


def _etape(titre, texte, image=None, astuce=None):
    return {'titre': titre, 'texte': texte, 'image': image, 'astuce': astuce}


# Niveaux de sensibilité d'un thème (libellé + classe de couleur du badge).
SENSIBILITES = {
    'faible': ("Sensibilité faible", "bg-green-50 text-green-700 border-green-200"),
    'moyen': ("Sensibilité moyenne", "bg-amber-50 text-amber-700 border-amber-200"),
    'eleve': ("Sensibilité élevée", "bg-red-50 text-red-700 border-red-200"),
}


def _section(theme, sensibilite, intro, etapes):
    return {'theme': theme, 'sensibilite': sensibilite, 'intro': intro, 'etapes': etapes}


GUIDES = {
    'caissier': {
        'titre': "Encaisser la scolarité d'un apprenant",
        'resume': "De l'ouverture du site jusqu'à la quittance remise à l'apprenant, "
                  "chaque étape est décrite dans l'ordre, sans rien omettre.",
        'etapes': [
            _etape(
                "Ouvrir le site de la plateforme",
                "Sur l'ordinateur du centre, ouvrez le navigateur et saisissez l'adresse "
                "de la plateforme Yupaan. La page d'accueil du site s'affiche.",
                image='caissier/01-accueil.png',
                astuce="Ajoutez l'adresse aux favoris du navigateur pour la retrouver d'un clic."),
            _etape(
                "Cliquer sur « Se connecter »",
                "En haut à droite de la page, cliquez sur le bouton rouge « Se connecter ».",
                image='caissier/02-bouton-connexion.png'),
            _etape(
                "Saisir votre identifiant et votre mot de passe",
                "Renseignez votre nom d'utilisateur (ou votre e-mail) et votre mot de passe, "
                "puis validez.",
                image='caissier/03-identifiants.png',
                astuce="Ne communiquez votre mot de passe à personne : aucun agent Yupaan ne vous le demandera."),
            _etape(
                "Entrer le code reçu par e-mail",
                "Pour votre sécurité, un code à quatre chiffres est envoyé sur votre boîte "
                "e-mail. Ouvrez votre messagerie, recopiez le code dans la page, puis validez. "
                "Le code n'est valable que quelques minutes.",
                image='caissier/04-code-verification.png',
                astuce="Si le code tarde, vérifiez le dossier « indésirables » de votre messagerie."),
            _etape(
                "Vous êtes dans « Mon espace »",
                "Après le code, vous arrivez sur votre espace de travail : le tableau de bord "
                "de votre centre. La barre latérale, à gauche, regroupe toutes vos rubriques.",
                image='caissier/05-mon-espace.png'),
            _etape(
                "Ouvrir « Encaissements scolarité »",
                "Dans la barre latérale, dépliez le thème « Scolarité » puis cliquez sur "
                "« Encaissements scolarité ». La liste des paiements de votre centre s'affiche.",
                image='caissier/06-encaissements.png'),
            _etape(
                "Rechercher l'apprenant",
                "Utilisez la recherche pour retrouver l'apprenant par son nom ou son "
                "identifiant, puis ouvrez sa situation de paiement.",
                image='caissier/07-recherche.png'),
            _etape(
                "Choisir la tranche à encaisser",
                "La situation de l'apprenant montre ce qui reste à payer, tranche par tranche. "
                "Sélectionnez la tranche à encaisser. Une tranche marquée « primordiale » doit "
                "être réglée avant les autres.",
                image='caissier/08-tranche.png'),
            _etape(
                "Enregistrer le paiement",
                "Saisissez le montant reçu, vérifiez les informations, puis validez "
                "l'encaissement. Le montant restant se met à jour automatiquement.",
                image='caissier/09-enregistrer.png',
                astuce="Vérifiez le montant à l'écran avant de valider : l'annulation d'un paiement laisse une trace."),
            _etape(
                "Éditer et remettre la quittance",
                "Après validation, éditez la quittance au format PDF (elle porte un code de "
                "vérification) et imprimez-la ou remettez-la à l'apprenant.",
                image='caissier/10-quittance.png'),
            _etape(
                "Se déconnecter en fin de service",
                "Quand vous avez terminé, cliquez sur « Quitter » en bas de la barre latérale. "
                "Sur un poste partagé, déconnectez-vous systématiquement.",
                image='caissier/11-quitter.png'),
        ],
    },

    'admin': {
        'titre': "Piloter la plateforme en tant qu'administrateur",
        'resume': "Le guide est organisé par thème d'action, du plus courant au plus "
                  "sensible. Chaque thème porte un niveau de sensibilité : plus il est "
                  "élevé, plus l'action engage la sécurité ou les données de la plateforme.",
        'sections': [
            _section(
                "Connexion sécurisée", 'eleve',
                "Votre compte ouvre des accès étendus. Traitez sa connexion avec le plus grand soin.",
                [
                    _etape("Ouvrir la plateforme",
                           "Sur votre navigateur, saisissez l'adresse de la plateforme Yupaan. "
                           "La page d'accueil s'affiche.",
                           image='admin/01-accueil.png'),
                    _etape("Se connecter et valider le code",
                           "Cliquez sur « Se connecter », saisissez votre identifiant et votre "
                           "mot de passe, puis entrez le code à quatre chiffres reçu par e-mail.",
                           image='admin/02-code-verification.png',
                           astuce="Ne communiquez jamais votre mot de passe : aucun agent Yupaan ne vous le demandera."),
                    _etape("Arriver sur le tableau de bord d'administration",
                           "Après le code, vous atteignez votre espace : le tableau de bord "
                           "d'administration, avec la barre latérale à gauche.",
                           image='admin/03-dashboard.png'),
                ]),
            _section(
                "Se repérer dans l'espace", 'faible',
                "La barre latérale regroupe tous les volets ; chaque volet ouvre ses rubriques.",
                [
                    _etape("Lire le tableau de bord",
                           "Le tableau de bord donne une vue d'ensemble : effectifs, paiements, "
                           "activité récente. C'est votre point de départ."),
                    _etape("Utiliser la barre latérale",
                           "Dépliez un volet (Scolarité, RH et Permissions, Offre de formation, "
                           "Communication, Supervision…) pour accéder à ses écrans.",
                           image='admin/04-sidebar.png'),
                ]),
            _section(
                "Ressources humaines et permissions", 'eleve',
                "C'est le volet le plus sensible : il décide qui peut faire quoi. Accordez "
                "toujours le minimum nécessaire à chaque agent.",
                [
                    _etape("Créer un compte d'agent",
                           "Dans « RH et Permissions », ajoutez un agent en renseignant son "
                           "rôle : le compte est automatiquement rattaché au bon groupe.",
                           image='admin/05-rh-agents.png'),
                    _etape("Attribuer les permissions",
                           "Écran « RH → Permissions » : cochez les accès accordés à l'agent. "
                           "Un accès retiré ici disparaît immédiatement pour lui.",
                           image='admin/06-permissions.png',
                           astuce="Principe du moindre privilège : n'accordez que ce dont l'agent a réellement besoin."),
                    _etape("Retirer un accès ou désactiver un compte",
                           "Décochez une permission pour la retirer, ou désactivez le compte "
                           "d'un agent qui quitte ses fonctions."),
                ]),
            _section(
                "Offre de formation", 'moyen',
                "La structure sur laquelle repose toute la scolarité : territoire, centres, "
                "filières et programmations.",
                [
                    _etape("Découpage territorial",
                           "Gérez les régions, provinces et directions régionales dans le volet "
                           "« Offre de formation »."),
                    _etape("Centres et filières",
                           "Créez et mettez à jour les centres de formation et les filières "
                           "(métiers) proposées.",
                           image='admin/07-centres-filieres.png'),
                    _etape("Programmations et années",
                           "Reliez un centre et une filière pour une année : c'est la "
                           "« programmation » qui ouvre les inscriptions.",
                           astuce="Depuis « Années », le bouton « Lancer une formation » mène directement à la programmation."),
                ]),
            _section(
                "Scolarité : inscriptions et suivi", 'moyen',
                "Le suivi des dossiers d'apprenants, de la demande jusqu'au paiement.",
                [
                    _etape("Suivre les inscriptions",
                           "Consultez les demandes d'inscription. Valider un dossier crée "
                           "automatiquement les dettes (échéances) de l'apprenant.",
                           image='admin/08-inscriptions.png',
                           astuce="La validation est un acte engageant : elle déclenche les échéances de paiement."),
                    _etape("Suivre les paiements par tranches",
                           "Chaque dette se règle par tranches. Une tranche « primordiale » "
                           "bloque les autres tant qu'elle n'est pas soldée."),
                ]),
            _section(
                "Finances et statistiques", 'eleve',
                "Vue d'argent et chiffres officiels : à manipuler avec rigueur.",
                [
                    _etape("Consulter les encaissements",
                           "Suivez les paiements de tous les centres de votre périmètre et leur "
                           "état de recouvrement.",
                           image='admin/09-finances.png'),
                    _etape("Statistiques réelles",
                           "Les effectifs réels alimentent les chiffres officiels : vérifiez "
                           "toujours une source avant de la diffuser."),
                ]),
            _section(
                "Facturation DAF", 'moyen',
                "Le module de facturation de prestations, indépendant de la scolarité.",
                [
                    _etape("Suivre le cycle d'une facture",
                           "Client → prestations → facture proforma → validation (elle devient "
                           "définitive et reçoit un numéro officiel) → encaissement → reçu.",
                           image='admin/10-facturation.png',
                           astuce="Seule une facture définitive est encaissable : la validation est irréversible."),
                ]),
            _section(
                "Communication", 'faible',
                "Informer le public et les abonnés.",
                [
                    _etape("Publier une actualité",
                           "Dans « Communication », rédigez une actualité puis « Publier et "
                           "notifier » pour prévenir les abonnés par e-mail.",
                           image='admin/11-actualites.png'),
                    _etape("Gérer les annonces défilantes",
                           "Créez de courtes annonces (avec lien facultatif et date "
                           "d'expiration) affichées dans le bandeau en haut du site."),
                    _etape("Consulter les abonnés",
                           "Suivez la liste des abonnés à la lettre d'information."),
                ]),
            _section(
                "Supervision et sécurité", 'eleve',
                "Surveiller les accès et régler la diffusion des rapports.",
                [
                    _etape("Historique des connexions",
                           "Consultez le journal des connexions et des tentatives échouées "
                           "dans le volet « Supervision ».",
                           image='admin/12-historique.png'),
                    _etape("Réglage d'envoi du rapport d'inspection",
                           "Écran « Supervision → Réglage d'envoi » : réglez la fréquence "
                           "(quotidien, hebdomadaire, mensuel) et les destinataires du rapport.",
                           image='admin/13-reglage-envoi.png'),
                    _etape("Yupaan-IA : accès et journal",
                           "Si l'assistant est activé, déléguez des accès par domaine et "
                           "consultez le journal d'audit des échanges.",
                           astuce="L'IA est en lecture seule : elle ne modifie jamais les données."),
                ]),
            _section(
                "Réglages réversibles et environnements", 'eleve',
                "Des bascules puissantes : à utiliser en connaissance de cause.",
                [
                    _etape("Basculer un rendu sans redéploiement",
                           "Le format des documents, l'interface et l'assistant se basculent "
                           "par commande dédiée (bascule_doc, bascule_ui, bascule_ai)."),
                    _etape("Séparer les tests des données réelles",
                           "L'environnement de staging permet aux agents de tester sans toucher "
                           "aux données de production (voir README_STAGING).",
                           astuce="Ne testez jamais des manipulations risquées directement en production."),
                ]),
            _section(
                "Fin de service", 'moyen',
                "Une bonne hygiène de session protège la plateforme.",
                [
                    _etape("Se déconnecter",
                           "En fin de session, cliquez sur « Quitter ». Sur un poste partagé, "
                           "déconnectez-vous systématiquement.",
                           image='admin/14-quitter.png'),
                ]),
        ],
    },

    'gestionnaire': {
        'titre': "Gérer la scolarité de votre centre",
        'resume': "Le guide suit votre travail quotidien : suivre les dossiers "
                  "d'inscription et les paiements de votre centre, en toute clarté.",
        'sections': [
            _section(
                "Connexion sécurisée", 'eleve',
                "Protégez votre accès : il ouvre les données de votre centre.",
                [
                    _etape("Se connecter à la plateforme",
                           "Ouvrez le site, cliquez sur « Se connecter », saisissez vos "
                           "identifiants puis le code à quatre chiffres reçu par e-mail.",
                           image='gestionnaire/01-connexion.png',
                           astuce="Ne communiquez jamais votre mot de passe."),
                    _etape("Arriver sur le tableau de bord de votre centre",
                           "Vous atteignez votre espace : le tableau de bord de votre centre, "
                           "avec la barre latérale à gauche.",
                           image='gestionnaire/02-dashboard.png'),
                ]),
            _section(
                "Suivre les inscriptions", 'moyen',
                "Les demandes d'inscription de votre centre, de la réception à la validation.",
                [
                    _etape("Ouvrir la liste des inscriptions",
                           "Dans le volet « Scolarité », ouvrez les inscriptions. Vous ne "
                           "voyez que les dossiers de votre centre.",
                           image='gestionnaire/03-inscriptions.png'),
                    _etape("Vérifier et valider un dossier",
                           "Contrôlez les informations et les pièces jointes, puis validez. "
                           "La validation crée automatiquement les échéances de paiement.",
                           astuce="La validation est engageante : vérifiez les pièces avant de valider."),
                ]),
            _section(
                "Suivre les paiements", 'moyen',
                "L'état de recouvrement de votre centre, tranche par tranche.",
                [
                    _etape("Consulter les encaissements",
                           "Le volet « Scolarité » donne l'état des paiements. Chaque dette se "
                           "règle par tranches ; une tranche « primordiale » passe avant les autres.",
                           image='gestionnaire/04-paiements.png'),
                ]),
            _section(
                "Fin de service", 'moyen',
                "Refermez votre session proprement.",
                [
                    _etape("Se déconnecter",
                           "Cliquez sur « Quitter » en bas de la barre latérale, surtout sur "
                           "un poste partagé.",
                           image='gestionnaire/05-quitter.png'),
                ]),
        ],
    },

    'dir': {
        'titre': "Piloter votre direction régionale",
        'resume': "Vous supervisez les centres de votre région : vue d'ensemble, "
                  "statistiques et suivi financier.",
        'sections': [
            _section(
                "Connexion sécurisée", 'eleve',
                "Votre accès couvre plusieurs centres : protégez-le.",
                [
                    _etape("Se connecter",
                           "Ouvrez le site, connectez-vous et validez le code reçu par e-mail.",
                           image='dir/01-connexion.png',
                           astuce="Ne partagez jamais votre mot de passe."),
                    _etape("Arriver sur le tableau de bord régional",
                           "Votre espace affiche la vue d'ensemble de votre région.",
                           image='dir/02-dashboard.png'),
                ]),
            _section(
                "Suivre l'activité de la région", 'moyen',
                "Les chiffres consolidés de vos centres.",
                [
                    _etape("Consulter les statistiques",
                           "Le volet « Statistiques » donne effectifs et recouvrement pour "
                           "l'ensemble de votre région.",
                           image='dir/03-statistiques.png'),
                ]),
            _section(
                "Suivi financier", 'eleve',
                "Une vue d'argent : à lire avec rigueur avant toute diffusion.",
                [
                    _etape("Suivre le recouvrement",
                           "Consultez l'état des paiements de vos centres et les montants "
                           "restant à recouvrer."),
                    _etape("Se déconnecter en fin de session",
                           "Cliquez sur « Quitter ». Déconnectez-vous toujours sur un poste partagé.",
                           image='dir/04-quitter.png'),
                ]),
        ],
    },

    'dg': {
        'titre': "Superviser la plateforme (Direction générale)",
        'resume': "Vous avez une vue d'ensemble : pilotage, statistiques officielles "
                  "et supervision de la sécurité.",
        'sections': [
            _section(
                "Connexion sécurisée", 'eleve',
                "Votre compte a une portée large : traitez sa connexion avec soin.",
                [
                    _etape("Se connecter",
                           "Ouvrez le site, connectez-vous et validez le code reçu par e-mail.",
                           image='dg/01-connexion.png',
                           astuce="Ne partagez jamais votre mot de passe."),
                    _etape("Arriver sur le tableau de bord",
                           "Votre espace donne la vue d'ensemble de toute la plateforme.",
                           image='dg/02-dashboard.png'),
                ]),
            _section(
                "Piloter et lire les chiffres", 'moyen',
                "Les statistiques consolidées de l'ensemble des centres.",
                [
                    _etape("Consulter les statistiques",
                           "Le volet « Statistiques » agrège effectifs, inscriptions et "
                           "recouvrement au niveau national.",
                           image='dg/03-statistiques.png',
                           astuce="Vérifiez toujours une source avant de la diffuser publiquement."),
                ]),
            _section(
                "Supervision et sécurité", 'eleve',
                "Garder un œil sur les accès et la diffusion des rapports.",
                [
                    _etape("Historique et rapport d'inspection",
                           "Le volet « Supervision » donne le journal des connexions et le "
                           "réglage d'envoi du rapport d'inspection."),
                    _etape("Se déconnecter",
                           "Cliquez sur « Quitter » en fin de session.",
                           image='dg/04-quitter.png'),
                ]),
        ],
    },

    'daf': {
        'titre': "Facturer des prestations (DAF)",
        'resume': "Le cycle complet d'une facture de prestation, du client jusqu'au "
                  "reçu, indépendamment de la scolarité.",
        'sections': [
            _section(
                "Connexion sécurisée", 'eleve',
                "Votre accès touche à la facturation : protégez-le.",
                [
                    _etape("Se connecter",
                           "Ouvrez le site, connectez-vous et validez le code reçu par e-mail.",
                           image='daf/01-connexion.png',
                           astuce="Ne partagez jamais votre mot de passe."),
                ]),
            _section(
                "Client et prestations", 'moyen',
                "La base de toute facture : un client et les prestations à facturer.",
                [
                    _etape("Créer le client et ses prestations",
                           "Dans « Prestation et facturation », enregistrez le client puis "
                           "les prestations à lui facturer.",
                           image='daf/02-prestations.png'),
                ]),
            _section(
                "De la proforma à la facture définitive", 'moyen',
                "La validation transforme la proforma en facture officielle.",
                [
                    _etape("Établir une facture proforma",
                           "Regroupez les prestations dans une facture proforma, modifiable "
                           "tant qu'elle n'est pas validée.",
                           image='daf/03-proforma.png'),
                    _etape("Valider la facture",
                           "La validation attribue un numéro officiel et rend la facture "
                           "définitive.",
                           astuce="Seule une facture définitive est encaissable : la validation est irréversible."),
                ]),
            _section(
                "Encaissement et reçu", 'eleve',
                "Enregistrer le paiement et remettre le reçu.",
                [
                    _etape("Encaisser et éditer le reçu",
                           "Enregistrez l'encaissement (total ou ligne par ligne), puis éditez "
                           "le reçu à remettre au client.",
                           image='daf/04-encaissement.png'),
                    _etape("Se déconnecter",
                           "Cliquez sur « Quitter » en fin de session.",
                           image='daf/05-quitter.png'),
                ]),
        ],
    },

    'agent_comptable': {
        'titre': "Suivre les encaissements (Agent comptable)",
        'resume': "Votre rôle est le suivi financier d'ensemble : recouvrement et "
                  "statistiques, sur tout le périmètre.",
        'etapes': [
            _etape("Se connecter",
                   "Ouvrez le site, connectez-vous et validez le code à quatre chiffres "
                   "reçu par e-mail.",
                   image='agent_comptable/01-connexion.png',
                   astuce="Ne partagez jamais votre mot de passe."),
            _etape("Consulter le recouvrement",
                   "Le tableau de bord et le volet « Statistiques » donnent l'état des "
                   "encaissements et des montants restant à recouvrer.",
                   image='agent_comptable/02-statistiques.png'),
            _etape("Exporter les chiffres",
                   "Depuis les statistiques, exportez les données (CSV, Excel, PDF) pour "
                   "vos rapports."),
            _etape("Se déconnecter",
                   "Cliquez sur « Quitter » en fin de session.",
                   image='agent_comptable/03-quitter.png'),
        ],
    },

    'deps': {
        'titre': "Consulter l'activité (DESP)",
        'resume': "Votre rôle est la consultation d'ensemble : effectifs et "
                  "statistiques, sans intervention sur les dossiers.",
        'etapes': [
            _etape("Se connecter",
                   "Ouvrez le site, connectez-vous et validez le code reçu par e-mail.",
                   image='deps/01-connexion.png',
                   astuce="Ne partagez jamais votre mot de passe."),
            _etape("Lire les statistiques",
                   "Le volet « Statistiques » donne la vue d'ensemble : effectifs, "
                   "inscriptions et recouvrement.",
                   image='deps/02-statistiques.png'),
            _etape("Se déconnecter",
                   "Cliquez sur « Quitter » en fin de session.",
                   image='deps/03-quitter.png'),
        ],
    },

    'formateur': {
        'titre': "Consulter vos filières (Formateur)",
        'resume': "Retrouvez les filières qui vous sont rattachées et votre tableau "
                  "de bord.",
        'etapes': [
            _etape("Se connecter",
                   "Ouvrez le site, cliquez sur « Se connecter », saisissez vos identifiants "
                   "puis le code à quatre chiffres reçu par e-mail.",
                   image='formateur/01-connexion.png',
                   astuce="Ne communiquez jamais votre mot de passe."),
            _etape("Ouvrir « Mes métiers »",
                   "Dans le menu, ouvrez « Mes métiers » pour voir les filières qui vous "
                   "sont rattachées.",
                   image='formateur/02-mes-metiers.png'),
            _etape("Consulter votre tableau de bord",
                   "Le tableau de bord regroupe les informations utiles à votre suivi.",
                   image='formateur/03-dashboard.png'),
            _etape("Se déconnecter",
                   "En fin de session, déconnectez-vous, surtout sur un poste partagé.",
                   image='formateur/04-quitter.png'),
        ],
    },

    'eleve': {
        'titre': "S'inscrire et suivre sa scolarité (Apprenant)",
        'resume': "De la création de votre compte au suivi de vos paiements, chaque "
                  "étape est décrite dans l'ordre.",
        'etapes': [
            _etape("Créer votre compte ou vous connecter",
                   "Sur la page d'accueil, cliquez sur « S'inscrire » pour créer votre "
                   "compte, ou « Se connecter » si vous en avez déjà un.",
                   image='eleve/01-connexion.png'),
            _etape("Choisir un métier de formation",
                   "Ouvrez « Métiers de formation » et parcourez les filières proposées "
                   "par les centres.",
                   image='eleve/02-metiers.png'),
            _etape("Déposer une demande d'inscription",
                   "Choisissez la formation qui vous intéresse et remplissez votre demande "
                   "d'inscription en suivant les étapes.",
                   image='eleve/03-inscription.png',
                   astuce="Préparez vos pièces (pièce d'identité, documents demandés) avant de commencer."),
            _etape("Suivre vos demandes",
                   "Dans « Mes demandes d'inscription », suivez l'état de chaque dossier "
                   "(en cours, validé, rejeté).",
                   image='eleve/04-mes-demandes.png'),
            _etape("Régler la scolarité par tranches",
                   "Une fois votre inscription validée, votre scolarité se règle par "
                   "tranches auprès du caissier de votre centre. Votre espace montre ce "
                   "qui reste à payer.",
                   image='eleve/05-paiements.png'),
            _etape("Se déconnecter",
                   "En fin de session, déconnectez-vous, surtout sur un poste partagé.",
                   image='eleve/06-quitter.png'),
        ],
    },

    'membre': {
        'titre': "Accéder à votre espace (Membre)",
        'resume': "Votre espace personnel et les informations utiles à votre rôle.",
        'etapes': [
            _etape("Se connecter",
                   "Ouvrez le site, connectez-vous et validez le code reçu par e-mail.",
                   image='membre/01-connexion.png',
                   astuce="Ne partagez jamais votre mot de passe."),
            _etape("Ouvrir votre espace",
                   "Après connexion, vous accédez à votre tableau de bord.",
                   image='membre/02-dashboard.png'),
            _etape("Se déconnecter",
                   "Cliquez sur « Quitter » en fin de session.",
                   image='membre/03-quitter.png'),
        ],
    },
}


def guide_pour(user_type):
    return GUIDES.get(user_type)
