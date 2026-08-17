"""App configuration. `ready()` is the single place that registers signals."""
from django.apps import AppConfig


class FinanceApiConfig(AppConfig):
    name = 'finance_api'

    def ready(self):
        import finance_api.signals
