"""Limitation des tentatives de connexion (protection anti-force brute).

Deux compteurs independants, stockes dans le cache Redis partage par les trois
workers gunicorn (un compteur en memoire locale serait remis a zero a chaque
worker et donc trois fois plus permissif) :

  - par nom d'utilisateur : verrou principal. Non contournable, puisque c'est
    precisement le compte cible qui est compte. Seuil bas.
  - par adresse IP : verrou secondaire, contre un balayage de plusieurs comptes
    depuis une meme source. Seuil plus haut car l'IP est deduite d'un en-tete
    (voir `adresse_client`) et plusieurs agents d'un meme centre peuvent sortir
    derriere une seule IP publique.

Le comptage s'appuie sur le signal `user_login_failed` emis par
`authenticate()` : il couvre d'un seul tenant la page de connexion applicative,
l'admin Django et l'API DRF, sans avoir a decorer chaque vue.
"""

from django.core.cache import cache

MAX_ECHECS_UTILISATEUR = 5
MAX_ECHECS_IP = 25
# Duree du verrou ET fenetre de comptage : un compteur non reapprovisionne
# expire de lui-meme, il n'y a donc rien a purger.
DUREE_VERROU = 900  # 15 minutes

PREFIXE = "connexion:echecs"


def adresse_client(request):
    """Adresse IP du visiteur, deduite de X-Forwarded-For.

    Topologie : client -> proxy TLS amont -> nginx -> gunicorn. nginx utilise
    `$proxy_add_x_forwarded_for`, qui *ajoute* l'adresse qu'il voit (celle du
    proxy amont) a la fin de la chaine. Django recoit donc « client, proxy ».

    On prend l'avant-derniere entree et non la premiere : un client qui envoie
    un X-Forwarded-For falsifie voit sa valeur *prefixee* a la chaine, jamais
    inseree en avant-derniere position. Prendre la premiere entree rendrait le
    compteur trivialement contournable.

    S'il n'y a qu'une entree, le proxy amont ne transmet pas l'adresse
    d'origine : on ne peut pas distinguer les visiteurs, seul le compteur par
    nom d'utilisateur protege alors reellement.
    """
    transmis = request.META.get("HTTP_X_FORWARDED_FOR", "") if request else ""
    parties = [p.strip() for p in transmis.split(",") if p.strip()]
    if len(parties) >= 2:
        return parties[-2]
    if parties:
        return parties[-1]
    return (request.META.get("REMOTE_ADDR", "") if request else "") or "inconnu"


def _cle_utilisateur(username):
    return f"{PREFIXE}:u:{(username or '').strip().lower()[:150]}"


def _cle_ip(ip):
    return f"{PREFIXE}:ip:{ip}"


def _incrementer(cle):
    """Incremente un compteur a duree de vie fixe.

    `cache.add` ne fait rien si la cle existe deja : la duree de vie est donc
    posee une seule fois, a la premiere tentative. Le verrou expire 15 minutes
    apres le *premier* echec de la serie et non apres le dernier, ce qui evite
    qu'un attaquant patient prolonge indefiniment sa propre fenetre.
    """
    cache.add(cle, 0, DUREE_VERROU)
    try:
        return cache.incr(cle)
    except ValueError:
        # La cle a expire entre le `add` et l'`incr` : on repart de 1.
        cache.set(cle, 1, DUREE_VERROU)
        return 1


def enregistrer_echec(request, username):
    """Comptabilise une tentative de connexion echouee."""
    _incrementer(_cle_utilisateur(username))
    _incrementer(_cle_ip(adresse_client(request)))


def reinitialiser(request, username):
    """Efface les compteurs apres une connexion reussie."""
    cache.delete_many([_cle_utilisateur(username), _cle_ip(adresse_client(request))])


def motif_verrou(request, username=None):
    """Retourne le motif du verrou actif, ou None si la tentative est permise.

    `username` est absent lors du controle en amont (middleware) quand la
    requete n'a pas encore ete lue : seul le compteur IP est alors consulte.
    """
    if username and cache.get(_cle_utilisateur(username), 0) >= MAX_ECHECS_UTILISATEUR:
        return "utilisateur"
    if cache.get(_cle_ip(adresse_client(request)), 0) >= MAX_ECHECS_IP:
        return "ip"
    return None


def est_verrouille(request, username=None):
    return motif_verrou(request, username) is not None
