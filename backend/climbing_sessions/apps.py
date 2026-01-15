from django.apps import AppConfig


class ClimbingSessionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'climbing_sessions'

    def ready(self):
        import climbing_sessions.signals
