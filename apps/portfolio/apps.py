from django.apps import AppConfig


class PortfolioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.portfolio'
    label = 'portfolio'
    verbose_name = 'Portfolio & Alerts'

    def ready(self):
        # Wire up the price-alert evaluation signal.
        from . import signals  # noqa: F401
