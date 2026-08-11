from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Inscription, Dette, Frais

@receiver(post_save, sender=Inscription)
def creer_dettes_automatiquement(sender, instance, **kwargs):
    print(f"Signal déclenché — statut: {instance.statut}")
    print(f"Dettes existantes: {Dette.objects.filter(inscription=instance).exists()}")
    
    if instance.statut == 'valide':
        if not Dette.objects.filter(inscription=instance).exists():
            frais_formation = Frais.objects.filter(
                formation=instance.formation
            )
            #print(f"Frais trouvés: {frais_formation.count()}")  # frais_formation
            for frais in frais_formation:
                Dette.objects.create(
                    inscription=instance,
                    frais_formation=frais,
                    montant_total=frais.montant,
                    etat_dette='non_soldé'
                )