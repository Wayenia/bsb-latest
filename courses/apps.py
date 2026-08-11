from django.apps import AppConfig


class CoursesConfig(AppConfig):
    name = 'courses'
    verbose_name = "GESTION DES COURS"

class DetteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'courses'

    def ready(self):
        import courses.signals