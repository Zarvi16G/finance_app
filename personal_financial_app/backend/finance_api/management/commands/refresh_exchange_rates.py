"""Refresh the cached exchange rates.

Rates are also fetched lazily on demand, but running this from cron once a day
keeps the first dashboard of the morning from paying for the network call —
and keeps working while the provider is briefly down, because the cache is
already warm.

    python manage.py refresh_exchange_rates              # every base in use
    python manage.py refresh_exchange_rates --base COP   # just one
"""
from django.core.management.base import BaseCommand

from finance_api.models import UserSetting
from finance_api.services import currency_service


class Command(BaseCommand):
    help = 'Fetch and cache exchange rates for the base currencies in use.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base', action='append', dest='bases',
            help='Base currency to refresh; repeatable. Defaults to every base currency users have chosen.',
        )

    def handle(self, *args, **options):
        bases = options.get('bases')
        if not bases:
            bases = sorted(
                {
                    currency_service.normalize(code)
                    for code in UserSetting.objects.values_list('currency', flat=True)
                    if code
                }
                or {currency_service.DEFAULT_BASE}
            )

        failures = 0
        for base in bases:
            base = currency_service.normalize(base)
            try:
                stored = currency_service.refresh_rates(base)
            except Exception as exc:  # provider down, bad key, network error
                failures += 1
                self.stderr.write(self.style.ERROR(f'{base}: {exc}'))
                continue
            self.stdout.write(self.style.SUCCESS(f'{base}: cached {stored} rates'))

        if failures:
            self.stderr.write(
                self.style.WARNING(f'{failures} of {len(bases)} base currencies failed.')
            )
