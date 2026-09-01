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
}


def guide_pour(user_type):
    return GUIDES.get(user_type)
