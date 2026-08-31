"""Analyse des traces d'authentification.

Le parti pris est celui d'une surveillance defensive : on cherche les motifs
qui trahissent une attaque, pas seulement le volume d'activite. Chaque alerte
porte une severite et une phrase qui dit quoi faire — un rapport qui se
contente de compter n'est jamais lu deux fois.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from accounts.models import HistoriqueConnexion

CRITIQUE, ELEVE, MODERE = "critique", "eleve", "modere"
ORDRE_SEVERITE = {CRITIQUE: 0, ELEVE: 1, MODERE: 2}


def _param(nom, defaut):
    return int(getattr(settings, nom, defaut))


@dataclass
class Alerte:
    severite: str
    motif: str
    cible: str
    detail: str
    conduite: str


@dataclass
class Rapport:
    debut: object
    fin: object
    jours: int
    total: int = 0
    connexions: int = 0
    deconnexions: int = 0
    echecs: int = 0
    comptes_actifs: int = 0
    comptes_vises: int = 0
    sources_echec: int = 0
    echecs_compte_inconnu: int = 0
    par_jour: list = field(default_factory=list)
    par_heure: list = field(default_factory=list)
    top_comptes_vises: list = field(default_factory=list)
    top_sources: list = field(default_factory=list)
    alertes: list = field(default_factory=list)

    @property
    def taux_echec(self):
        tentatives = self.connexions + self.echecs
        return round(100 * self.echecs / tentatives, 1) if tentatives else 0.0

    @property
    def alertes_critiques(self):
        return [a for a in self.alertes if a.severite == CRITIQUE]


def _fenetre(jours):
    fin = timezone.now()
    return fin - timedelta(days=jours), fin


def construire_rapport(jours=None):
    jours = jours or _param('AUDIT_PERIODE_JOURS', 7)
    debut, fin = _fenetre(jours)
    qs = (HistoriqueConnexion.objects
          .filter(date_evenement__gte=debut, date_evenement__lte=fin)
          .order_by())          # cf. piege du GROUP BY : voir _indicateurs

    r = Rapport(debut=debut, fin=fin, jours=jours)
    par_type = dict(qs.values_list('type_evenement').annotate(n=Count('id')))
    r.total = sum(par_type.values())
    r.connexions = par_type.get('connexion', 0)
    r.deconnexions = par_type.get('deconnexion', 0)
    r.echecs = par_type.get('echec', 0)

    reussites = qs.filter(type_evenement='connexion')
    echecs = qs.filter(type_evenement='echec')

    r.comptes_actifs = reussites.values('username').distinct().count()
    r.comptes_vises = echecs.values('username').distinct().count()
    r.sources_echec = echecs.exclude(adresse_ip__isnull=True).values('adresse_ip').distinct().count()
    r.echecs_compte_inconnu = echecs.filter(utilisateur__isnull=True).count()

    r.par_jour = _serie_par_jour(qs, debut, jours)
    r.par_heure = _serie_par_heure(qs)
    r.top_comptes_vises = _top(echecs, 'username', 10)
    r.top_sources = _top(echecs.exclude(adresse_ip__isnull=True), 'adresse_ip', 10)
    r.alertes = detecter_anomalies(qs)
    return r


def _serie_par_jour(qs, debut, jours):
    """Une ligne par jour, y compris les jours sans activite : un graphique a
    trous laisse croire a une absence de donnees plutot qu'a une absence
    d'evenements."""
    brut = defaultdict(lambda: {'connexion': 0, 'echec': 0})
    for e in qs.filter(type_evenement__in=('connexion', 'echec')).values_list('date_evenement', 'type_evenement'):
        brut[timezone.localtime(e[0]).date()][e[1]] += 1
    base = timezone.localtime(debut).date()
    return [
        {
            'jour': base + timedelta(days=i),
            'connexions': brut[base + timedelta(days=i)]['connexion'],
            'echecs': brut[base + timedelta(days=i)]['echec'],
        }
        for i in range(jours + 1)
    ]


def _serie_par_heure(qs):
    """Repartition sur 24 heures. Une activite nocturne reguliere sur des
    comptes d'agents est un signal en soi."""
    compte = Counter()
    for (d,) in qs.filter(type_evenement='connexion').values_list('date_evenement'):
        compte[timezone.localtime(d).hour] += 1
    return [{'heure': h, 'connexions': compte.get(h, 0)} for h in range(24)]


def _top(qs, champ, limite):
    return [
        {'valeur': l[champ] or '(inconnu)', 'nombre': l['n']}
        for l in qs.values(champ).annotate(n=Count('id')).order_by('-n')[:limite]
    ]


# --------------------------------------------------------------------------
# Detection d'anomalies
# --------------------------------------------------------------------------
def detecter_anomalies(qs):
    alertes = []
    alertes += _compromissions_probables(qs)
    alertes += _sondage_de_comptes(qs)
    alertes += _acharnement_sur_compte(qs)
    alertes += _comptes_multi_sources(qs)
    alertes += _activite_hors_heures(qs)
    alertes.sort(key=lambda a: (ORDRE_SEVERITE[a.severite], a.cible))
    return alertes


def _compromissions_probables(qs):
    """Reussite precedee d'echecs repetes sur le meme compte, dans l'heure.

    C'est le motif le plus grave du rapport : une attaque par force brute qui
    aboutit ressemble exactement a cela. Il merite une verification meme quand
    l'explication est benigne (mot de passe oublie puis retrouve).
    """
    seuil = _param('AUDIT_SEUIL_ECHECS_COMPTE', 5)
    evenements = defaultdict(list)
    for u, t, d in qs.filter(type_evenement__in=('connexion', 'echec')) \
                     .values_list('username', 'type_evenement', 'date_evenement'):
        if u:
            evenements[u].append((d, t))

    alertes = []
    for compte, lignes in evenements.items():
        lignes.sort()
        echecs_recents = []
        for d, t in lignes:
            if t == 'echec':
                echecs_recents.append(d)
                continue
            fenetre = [x for x in echecs_recents if d - x <= timedelta(hours=1)]
            if len(fenetre) >= seuil:
                alertes.append(Alerte(
                    severite=CRITIQUE,
                    motif="Connexion reussie apres une serie d'echecs",
                    cible=compte,
                    detail=(f"{len(fenetre)} echecs dans l'heure precedant une connexion "
                            f"reussie le {timezone.localtime(d):%d/%m/%Y a %H:%M}"),
                    conduite="Confirmer avec le titulaire qu'il est bien a l'origine de cette connexion. "
                             "Dans le doute, reinitialiser le mot de passe et verifier les actions faites depuis.",
                ))
            echecs_recents = []
    return alertes


def _sondage_de_comptes(qs):
    """Une meme adresse qui vise plusieurs identifiants distincts.

    Le rapport distingue les identifiants inexistants : les viser en serie
    n'arrive pas par accident, c'est une enumeration de comptes.
    """
    seuil = _param('AUDIT_SEUIL_COMPTES_PAR_IP', 3)
    par_ip = defaultdict(lambda: {'comptes': set(), 'inconnus': set(), 'n': 0})
    for ip, u, lie in qs.filter(type_evenement='echec') \
                        .exclude(adresse_ip__isnull=True) \
                        .values_list('adresse_ip', 'username', 'utilisateur_id'):
        e = par_ip[ip]
        e['n'] += 1
        if u:
            e['comptes'].add(u)
            if lie is None:
                e['inconnus'].add(u)

    alertes = []
    for ip, e in par_ip.items():
        if len(e['comptes']) < seuil:
            continue
        inconnus = len(e['inconnus'])
        alertes.append(Alerte(
            severite=CRITIQUE if inconnus >= seuil else ELEVE,
            motif="Sondage de comptes depuis une meme adresse",
            cible=ip,
            detail=(f"{e['n']} echecs visant {len(e['comptes'])} identifiants distincts, "
                    f"dont {inconnus} inexistant(s)"),
            conduite="Bloquer l'adresse en amont si elle est externe. Si elle correspond a un centre, "
                     "verifier qu'aucun poste partage n'est compromis.",
        ))
    return alertes


def _acharnement_sur_compte(qs):
    seuil = _param('AUDIT_SEUIL_ECHECS_COMPTE', 5)
    alertes = []
    for l in qs.filter(type_evenement='echec').values('username') \
               .annotate(n=Count('id')).order_by('-n'):
        if l['n'] < seuil or not l['username']:
            continue
        alertes.append(Alerte(
            severite=ELEVE,
            motif="Echecs repetes sur un meme compte",
            cible=l['username'],
            detail=f"{l['n']} tentatives refusees sur la periode",
            conduite="Verifier aupres du titulaire. S'il n'est pas a l'origine des tentatives, "
                     "le compte est cible : imposer un nouveau mot de passe.",
        ))
    return alertes


def _comptes_multi_sources(qs):
    """Un identifiant utilise depuis plusieurs adresses : compte partage entre
    agents, ou identifiants circulant hors du titulaire."""
    seuil = _param('AUDIT_SEUIL_IP_PAR_COMPTE', 3)
    par_compte = defaultdict(set)
    for u, ip in qs.filter(type_evenement='connexion') \
                   .exclude(adresse_ip__isnull=True) \
                   .values_list('username', 'adresse_ip'):
        if u:
            par_compte[u].add(ip)
    return [
        Alerte(
            severite=MODERE,
            motif="Compte utilise depuis plusieurs adresses",
            cible=compte,
            detail=f"{len(ips)} adresses distinctes : {', '.join(sorted(ips)[:5])}"
                   + (" …" if len(ips) > 5 else ""),
            conduite="Verifier qu'il ne s'agit pas d'un compte partage entre plusieurs agents. "
                     "Chaque agent doit disposer de son propre identifiant, sans quoi le journal "
                     "ne permet plus d'imputer une action a une personne.",
        )
        for compte, ips in par_compte.items() if len(ips) >= seuil
    ]


def _activite_hors_heures(qs):
    """Connexions d'agents en dehors des heures ouvrees.

    Les apprenants sont exclus : ils consultent leur dossier a toute heure,
    c'est attendu. Un agent qui se connecte la nuit ne l'est pas.
    """
    debut = _param('AUDIT_HEURE_OUVREE_DEBUT', 7)
    fin = _param('AUDIT_HEURE_OUVREE_FIN', 19)
    hors = Counter()
    for u, d in qs.filter(type_evenement='connexion', est_apprenant=False) \
                  .values_list('username', 'date_evenement'):
        heure = timezone.localtime(d).hour
        if u and (heure < debut or heure >= fin):
            hors[u] += 1
    return [
        Alerte(
            severite=MODERE,
            motif="Connexions d'agent hors heures ouvrees",
            cible=compte,
            detail=f"{n} connexion(s) avant {debut}h ou apres {fin}h",
            conduite="Rapprocher de l'activite reelle du service. Une regularite nocturne "
                     "sans justification appelle une verification du compte.",
        )
        for compte, n in hors.most_common(10) if n >= 3
    ]
