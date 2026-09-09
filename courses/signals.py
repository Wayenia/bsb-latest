import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Inscription, Dette, Frais

logger = logging.getLogger(__name__)

# Statuts « validé » (workflow) : une inscription passée à l'un d'eux a ses
# dettes générées. Le champ `statut` reste au niveau workflow ; l'état de
# paiement réel est calculé (voir Inscription.libelle_statut_paiement).
STATUTS_VALIDES = ('valide', 'valide_paye', 'Valide')


@receiver(post_save, sender=Inscription)
def creer_dettes_automatiquement(sender, instance, **kwargs):
    if instance.statut in STATUTS_VALIDES:
        if not Dette.objects.filter(inscription=instance).exists():
            for frais in Frais.objects.filter(formation=instance.formation):
                Dette.objects.create(
                    inscription=instance,
                    frais_formation=frais,
                    montant_total=frais.montant,
                    etat_dette='non_soldé',
                )
            logger.info("Dettes générées pour l'inscription %s.", instance.pk)
