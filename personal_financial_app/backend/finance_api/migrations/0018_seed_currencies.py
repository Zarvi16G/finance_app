"""Seed the currency catalog.

A starting set rather than all ~160 ISO 4217 codes: the three the app is built
around (COP, USD, EUR), the rest of the majors, and the Latin American
neighbours most likely to show up on a Colombian statement. Anything missing
can be added later — the catalog is data, not code.

`decimals` follows ISO 4217: COP, CLP, JPY and KRW are conventionally written
without cents.
"""

from django.db import migrations

CURRENCIES = [
    # code, name, symbol, decimals
    ('COP', 'Colombian Peso', '$', 0),
    ('USD', 'US Dollar', '$', 2),
    ('EUR', 'Euro', '€', 2),
    ('GBP', 'British Pound', '£', 2),
    ('JPY', 'Japanese Yen', '¥', 0),
    ('CHF', 'Swiss Franc', 'CHF', 2),
    ('CAD', 'Canadian Dollar', '$', 2),
    ('AUD', 'Australian Dollar', '$', 2),
    ('CNY', 'Chinese Yuan', '¥', 2),
    ('MXN', 'Mexican Peso', '$', 2),
    ('BRL', 'Brazilian Real', 'R$', 2),
    ('ARS', 'Argentine Peso', '$', 2),
    ('CLP', 'Chilean Peso', '$', 0),
    ('PEN', 'Peruvian Sol', 'S/', 2),
    ('UYU', 'Uruguayan Peso', '$U', 2),
    ('BOB', 'Bolivian Boliviano', 'Bs', 2),
    ('CRC', 'Costa Rican Colón', '₡', 2),
    ('PAB', 'Panamanian Balboa', 'B/.', 2),
    ('DOP', 'Dominican Peso', 'RD$', 2),
    ('GTQ', 'Guatemalan Quetzal', 'Q', 2),
    ('VES', 'Venezuelan Bolívar', 'Bs.', 2),
]


def seed(apps, schema_editor):
    Currency = apps.get_model('finance_api', 'Currency')
    for code, name, symbol, decimals in CURRENCIES:
        Currency.objects.update_or_create(
            code=code,
            defaults={'name': name, 'symbol': symbol, 'decimals': decimals},
        )


def unseed(apps, schema_editor):
    Currency = apps.get_model('finance_api', 'Currency')
    Currency.objects.filter(code__in=[row[0] for row in CURRENCIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('finance_api', '0017_currency_support'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
