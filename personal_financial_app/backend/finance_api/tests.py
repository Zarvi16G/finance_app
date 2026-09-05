import time
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

import pyotp
import requests
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import (
    FinancialRecord, UserSetting, BankStatement, ExpectedGoal,
    ExtractedTransaction, Debt, Currency, ExchangeRate, Asset,
    ExperienceBudgetItem,
)
from .crypto import decrypt_text
from .services import currency_service, wealthness_service
from .services.snapshot_service import compute_monthly_snapshot
from .services.ai import key_validation
from .services.statement_detection import detect_statement_info


class AuthTestCase(TestCase):
    """Mixin that registers a user and exposes an authenticated API client."""

    username = 'tester'
    password = 'S3cure!Passw0rd-123'

    def register(self, username, password=None):
        """Register a user and return (api_client, user, tokens)."""
        password = password or self.password
        response = self.anonymous.post(
            '/api/auth/register/',
            {'username': username, 'password': password, 'email': f'{username}@example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        tokens = response.json()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        user = get_user_model().objects.get(username=username)
        return client, user, tokens

    def setUp(self):
        self.anonymous = APIClient()
        self.client, self.user, self.tokens = self.register(self.username)



class AuthViewsTests(AuthTestCase):
    """Tests for register / login / refresh / logout / me flows."""

    def test_register_returns_tokens_and_user(self):
        response = self.anonymous.post(
            '/api/auth/register/',
            {'username': 'new-user', 'password': 'Another!Secret-42'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertEqual(data['user']['username'], 'new-user')

    def test_register_rejects_duplicate_username(self):
        response = self.anonymous.post(
            '/api/auth/register/',
            {'username': self.username, 'password': 'Another!Secret-42'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_register_rejects_weak_password(self):
        response = self.anonymous.post(
            '/api/auth/register/',
            {'username': 'weak-user', 'password': '123'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_login_returns_tokens_and_user(self):
        response = self.anonymous.post(
            '/api/auth/login/',
            {'username': self.username, 'password': self.password},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertEqual(data['user']['username'], self.username)

    def test_login_rejects_bad_credentials(self):
        response = self.anonymous.post(
            '/api/auth/login/',
            {'username': self.username, 'password': 'wrong-password'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)

    def test_me_returns_profile(self):
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['username'], self.username)

    def test_protected_endpoint_rejects_anonymous(self):
        response = self.anonymous.get('/api/records/')
        self.assertEqual(response.status_code, 401)

    def test_refresh_rotates_tokens(self):
        response = self.anonymous.post(
            '/api/auth/refresh/',
            {'refresh': self.tokens['refresh']},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())
        self.assertIn('refresh', response.json())

    def test_logout_blacklists_refresh_token(self):
        logout = self.client.post(
            '/api/auth/logout/',
            {'refresh': self.tokens['refresh']},
            format='json',
        )
        self.assertEqual(logout.status_code, 200)

        # The blacklisted refresh token must be rejected afterwards
        refresh = self.anonymous.post(
            '/api/auth/refresh/',
            {'refresh': self.tokens['refresh']},
            format='json',
        )
        self.assertEqual(refresh.status_code, 401)



class AnalyticsSnapshotViewTests(AuthTestCase):
    """Tests for FinancialAnalyticsView snapshot path (expense_by_category counts)."""

    def setUp(self):
        super().setUp()
        ref = date.today().replace(day=1) - timedelta(days=1)
        self.month = ref.replace(day=1)
        self.end = (self.month.replace(day=28) + timedelta(days=7)).replace(day=1) - timedelta(days=1)

        FinancialRecord.objects.create(
            owner=self.user,
            type='expense', category='Food & Dining', amount=Decimal('100.00'), date=self.month
        )
        FinancialRecord.objects.create(
            owner=self.user,
            type='expense', category='Food & Dining', amount=Decimal('50.00'), date=self.month.replace(day=15)
        )
        FinancialRecord.objects.create(
            owner=self.user,
            type='expense', category='Utilities', amount=Decimal('75.00'), date=self.month.replace(day=10)
        )
        FinancialRecord.objects.create(
            owner=self.user,
            type='income', category='Salary', amount=Decimal('500.00'), date=self.month.replace(day=5)
        )

        compute_monthly_snapshot(self.month, self.user)

    def test_snapshot_path_returns_category_counts(self):
        url = f"/api/analytics/?start_date={self.month.isoformat()}&end_date={self.end.isoformat()}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        by_cat = {c['category']: c for c in data['expense_by_category']}
        self.assertEqual(set(by_cat), {'Food & Dining', 'Utilities'})
        self.assertEqual(by_cat['Food & Dining']['count'], 2)
        self.assertEqual(by_cat['Food & Dining']['total'], 150.0)
        self.assertEqual(by_cat['Utilities']['count'], 1)
        self.assertEqual(by_cat['Utilities']['total'], 75.0)
        self.assertEqual(data['expense_by_category'][0]['category'], 'Food & Dining')

    def test_live_fallback_path_returns_category_counts(self):
        url = f"/api/analytics/?start_date={self.month.isoformat()}&end_date={date.today().isoformat()}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        by_cat = {c['category']: c for c in data['expense_by_category']}
        self.assertEqual(by_cat['Food & Dining']['count'], 2)
        self.assertEqual(by_cat['Food & Dining']['total'], 150.0)
        self.assertEqual(by_cat['Utilities']['count'], 1)



class StatementDetectionTests(TestCase):
    """Unit tests for statement type/bank auto-detection."""

    def test_detects_savings_nu(self):
        info = detect_statement_info('BANCO NU COLOMBIA\nEstado de cuenta Ahorros Nº 123')
        self.assertEqual(info['statement_type'], 'savings')
        self.assertEqual(info['bank_name'], 'Nu Colombia')

    def test_detects_credit_card(self):
        info = detect_statement_info('Tarjeta de Crédito Visa\nEstado de cuenta. Cuota de manejo $ 12.000')
        self.assertEqual(info['statement_type'], 'credit_card')

    def test_detects_loan(self):
        info = detect_statement_info('Credito Hipotecario - Tabla de amortizacion')
        self.assertEqual(info['statement_type'], 'loan')

    def test_detects_investment(self):
        info = detect_statement_info('Portafolio de inversión y rendimientos')
        self.assertEqual(info['statement_type'], 'investment')

    def test_detects_checking(self):
        info = detect_statement_info('Cuenta corriente Nº 332-2211')
        self.assertEqual(info['statement_type'], 'checking')

    def test_detects_bank_without_type(self):
        info = detect_statement_info('Movimientos Nequi - extracto digital')
        self.assertEqual(info['statement_type'], 'other')
        self.assertEqual(info['bank_name'], 'Nequi')

    def test_savings_with_card_transaction_row_is_not_card(self):
        info = detect_statement_info(
            'Nu Colombia · Estado de cuenta Ahorros\n02 jul avance de tarjeta de crédito +$450.000,00'
        )
        self.assertEqual(info['statement_type'], 'savings')

    def test_unknown_statement(self):
        info = detect_statement_info('Lorem ipsum dolor sit amet, consectetuer adipiscing elit.')
        self.assertEqual(info, {'statement_type': 'other', 'bank_name': ''})


class StatementUpdateTests(AuthTestCase):
    """PATCH /api/statements/{id}/ accepts JSON and updates the type."""

    def setUp(self):
        super().setUp()
        self.statement = BankStatement.objects.create(
            owner=self.user,
            file=SimpleUploadedFile('test.pdf', b'%PDF-1.4 minimal', content_type='application/pdf'),
            original_filename='test.pdf',
            statement_type='other',
        )

    def test_patch_updates_statement_type(self):
        response = self.client.patch(
            f'/api/statements/{self.statement.id}/', {'statement_type': 'savings'}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['statement_type'], 'savings')
        self.statement.refresh_from_db()
        self.assertEqual(self.statement.statement_type, 'savings')

    def test_patch_rejects_invalid_type(self):
        response = self.client.patch(
            f'/api/statements/{self.statement.id}/', {'statement_type': 'crypto'}, format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_removes_statement_and_extracted_but_keeps_records(self):
        txn = ExtractedTransaction.objects.create(
            statement=self.statement, date=date.today(),
            raw_description='Coffee Shop', cleaned_description='Coffee Shop',
            amount=Decimal('15.00'), transaction_type='expense',
        )
        record = FinancialRecord.objects.create(
            owner=self.user,
            type='expense', category='Food & Dining', amount=Decimal('15.00'),
            date=date.today(), description='Coffee Shop',
        )
        response = self.client.delete(f'/api/statements/{self.statement.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(BankStatement.objects.filter(id=self.statement.id).exists())
        self.assertFalse(ExtractedTransaction.objects.filter(id=txn.id).exists())
        self.assertTrue(FinancialRecord.objects.filter(id=record.id).exists())


class GoalsApiTests(AuthTestCase):
    """Goals CRUD + analysis, including the Decimal*float regression."""

    def _make_goal(self, **kwargs):
        data = {
            'owner': self.user,
            'title': 'Emergency Fund',
            'target_amount': Decimal('5000000.00'),
            'current_amount': Decimal('1200000.50'),
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'category': 'Savings',
        }
        data.update(kwargs)
        return ExpectedGoal.objects.create(**data)

    def test_list_serializes_decimals_without_crashing(self):
        self._make_goal()
        response = self.client.get('/api/goals/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]['progress_percentage'], 24.0)

    def test_progress_capped_at_100(self):
        self._make_goal(current_amount=Decimal('9000000.00'))
        response = self.client.get('/api/goals/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['progress_percentage'], 100.0)

    def test_create_patch_delete_flow(self):
        response = self.client.post('/api/goals/', {
            'title': 'Vacation',
            'target_amount': 10000000,
            'current_amount': 2500000,
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'category': 'Travel',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        goal_id = response.json()['id']

        response = self.client.patch(f'/api/goals/{goal_id}/', {'current_amount': 8000000}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['progress_percentage'], 80.0)

        response = self.client.delete(f'/api/goals/{goal_id}/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(ExpectedGoal.objects.count(), 0)

    def test_analysis_groups_by_category(self):
        self._make_goal(title='Emergency Fund', category='Savings', current_amount=Decimal('500000.00'))
        self._make_goal(title='Graduation', category='Education', current_amount=Decimal('10000.00'),
                        target_amount=Decimal('10000.00'), status='achieved')
        self._make_goal(title='Vacation', category='Travel', current_amount=Decimal('0.00'),
                        target_amount=Decimal('9000000.00'))
        response = self.client.get('/api/goals/analysis/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['summary']['total_goals'], 3)
        self.assertEqual(body['summary']['achieved_goals'], 1)
        cats = {c['category']: c for c in body['categories']}
        self.assertEqual(set(cats), {'Savings', 'Education', 'Travel'})
        self.assertEqual(cats['Education']['overall_progress'], 100.0)
        self.assertEqual(cats['Savings']['overall_progress'], 10.0)


class AISettingsViewTests(AuthTestCase):
    """Security-focused tests for the AI settings endpoint (/api/ai-settings/)."""

    def _valid_key(self):
        return mock.patch.object(
            key_validation, 'validate_api_key',
            return_value={'valid': True},
        )

    def test_get_defaults_are_safe(self):
        response = self.client.get('/api/ai-settings/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['provider'], 'gemini')
        self.assertIn('keys', data)
        for provider in ('gemini', 'openai', 'anthropic'):
            self.assertIn(provider, data['keys'])

    def test_put_stores_key_encrypted_and_returns_masked(self):
        with self._valid_key():
            response = self.client.put(
                '/api/ai-settings/',
                {'provider': 'openai', 'api_key': 'sk-super-secret-1234'},
                format='json',
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Full key must never be returned
        self.assertNotIn('sk-super-secret-1234', response.content.decode())
        self.assertEqual(data['keys']['openai'], '••••1234')
        self.assertEqual(data['provider'], 'openai')

        # At rest, the stored value must be encrypted, not plaintext
        setting = UserSetting.objects.get(owner=self.user)
        self.assertNotIn('sk-super-secret-1234', setting.ai_keys['openai'])
        self.assertEqual(decrypt_text(setting.ai_keys['openai']), 'sk-super-secret-1234')

    def test_put_switches_provider_and_keeps_existing_key(self):
        # Save a key for anthropic first
        with self._valid_key():
            self.client.put(
                '/api/ai-settings/',
                {'provider': 'anthropic', 'api_key': 'ant-key-999', 'model': ''},
                format='json',
            )
        # Switch provider without sending a key -> key must be preserved
        response = self.client.put(
            '/api/ai-settings/',
            {'provider': 'anthropic', 'model': 'claude-3-7-sonnet'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['keys']['anthropic'], '••••-999')
        self.assertEqual(response.json()['model'], 'claude-3-7-sonnet')

    def test_put_rejects_unknown_provider(self):
        response = self.client.put(
            '/api/ai-settings/',
            {'provider': 'skynet', 'api_key': 'bad'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_put_rejects_empty_key(self):
        response = self.client.put(
            '/api/ai-settings/',
            {'provider': 'gemini', 'api_key': '   '},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_put_rejects_unverified_key_with_classified_error(self):
        for code in (
            key_validation.CODE_INVALID_KEY,
            key_validation.CODE_RATE_LIMIT,
            key_validation.CODE_BILLING,
            key_validation.CODE_PERMISSION,
            key_validation.CODE_NETWORK,
        ):
            with self.subTest(code=code), mock.patch.object(
                key_validation, 'validate_api_key',
                return_value={'valid': False, 'code': code, 'message': key_validation.CODE_MESSAGES[code]},
            ):
                response = self.client.put(
                    '/api/ai-settings/',
                    {'provider': 'openai', 'api_key': 'sk-rejected-000'},
                    format='json',
                )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error_code'], code)
            self.assertIn('error', response.json())
            # The rejected key must never be stored
            setting = UserSetting.objects.get(owner=self.user)
            self.assertNotIn(code, str(setting.ai_keys))

    def test_put_overwrites_key(self):
        with self._valid_key():
            self.client.put('/api/ai-settings/', {'provider': 'gemini', 'api_key': 'first-key'}, format='json')
            response = self.client.put('/api/ai-settings/', {'provider': 'gemini', 'api_key': 'second-key'}, format='json')
        self.assertEqual(response.status_code, 200)
        setting = UserSetting.objects.get(owner=self.user)
        self.assertEqual(decrypt_text(setting.ai_keys['gemini']), 'second-key')


class KeyValidationEngineTests(TestCase):
    """Unit tests for the provider error classification engine."""

    def test_classify_status_codes(self):
        self.assertEqual(key_validation.classify_error(401, ''), key_validation.CODE_INVALID_KEY)
        self.assertEqual(key_validation.classify_error(429, ''), key_validation.CODE_RATE_LIMIT)
        self.assertEqual(key_validation.classify_error(402, ''), key_validation.CODE_BILLING)
        self.assertEqual(key_validation.classify_error(500, ''), key_validation.CODE_UNKNOWN)

    def test_classify_403_uses_provider_hints(self):
        billing_body = '{"error": {"code": "insufficient_quota", "message": "You exceeded your current quota"}}'
        self.assertEqual(key_validation.classify_error(403, billing_body), key_validation.CODE_BILLING)
        permission_body = '{"error": {"code": "permission_error", "message": "The API key has no access"}}'
        self.assertEqual(key_validation.classify_error(403, permission_body), key_validation.CODE_PERMISSION)
        # Anonymous 403 without hints defaults to permission denied
        self.assertEqual(key_validation.classify_error(403, ''), key_validation.CODE_PERMISSION)

    def test_classify_gemini_invalid_key_message(self):
        body = '{"error": {"message": "API key not valid. Please pass a valid API key.", "status": "INVALID_ARGUMENT"}}'
        self.assertEqual(key_validation.classify_error(400, body), key_validation.CODE_INVALID_KEY)

    def test_validate_api_key_empty(self):
        verdict = key_validation.validate_api_key('gemini', '   ')
        self.assertFalse(verdict['valid'])
        self.assertEqual(verdict['code'], key_validation.CODE_INVALID_KEY)

    def test_validate_api_key_success_and_failure(self):
        with mock.patch('requests.get') as get:
            get.return_value.status_code = 200
            self.assertTrue(key_validation.validate_api_key('openai', 'sk-ok')['valid'])

            get.return_value.status_code = 401
            verdict = key_validation.validate_api_key('openai', 'sk-bad')
            self.assertFalse(verdict['valid'])
            self.assertEqual(verdict['code'], key_validation.CODE_INVALID_KEY)

    def test_validate_api_key_network_error(self):
        with mock.patch('requests.get', side_effect=key_validation.requests.RequestException('boom')):
            verdict = key_validation.validate_api_key('anthropic', 'ant-key')
            self.assertFalse(verdict['valid'])
            self.assertEqual(verdict['code'], key_validation.CODE_NETWORK)


@override_settings(EXCHANGERATE_API_KEY='test-key-not-a-real-one')
class LifeExperiencesTests(AuthTestCase):
    """Trip budgets: itemised costs against what the user set out to save."""

    def setUp(self):
        super().setUp()
        for code, name, decimals in (('COP', 'Colombian Peso', 0), ('USD', 'US Dollar', 2)):
            Currency.objects.update_or_create(
                code=code, defaults={'name': name, 'decimals': decimals}
            )
        ExchangeRate.objects.create(
            base='USD', target='COP', rate=Decimal('4000'), rate_date=date.today()
        )

        self.trip = ExpectedGoal.objects.create(
            owner=self.user, title='Japón 2027', goal_type='experience',
            location='Tokio', target_amount=Decimal('20000000'),
            current_amount=Decimal('5000000'), currency='COP',
            start_date=date.today(), end_date=date.today() + timedelta(days=400),
        )
        # A trip legitimately mixes currencies: the flight is priced in USD.
        self.flight = ExperienceBudgetItem.objects.create(
            goal=self.trip, label='Vuelos', category='transport',
            estimated_amount=Decimal('1500'), currency='USD', is_booked=True,
        )
        self.hotel = ExperienceBudgetItem.objects.create(
            goal=self.trip, label='Hotel', category='lodging',
            estimated_amount=Decimal('8000000'), currency='COP',
        )

    def test_budget_totals_convert_every_line(self):
        body = self.client.get('/api/life-experiences/').json()
        budget = body['experiences'][0]['budget']
        # 1500 USD * 4000 = 6M, plus 8M hotel = 14M COP
        self.assertEqual(budget['estimated_total'], 14000000.0)
        self.assertEqual(budget['booked_total'], 6000000.0)

    def test_target_and_budget_are_reported_separately(self):
        """The user owns the target; the line items are a separate opinion."""
        budget = self.client.get('/api/life-experiences/').json()['experiences'][0]['budget']
        self.assertEqual(budget['target_amount'], 20000000.0)
        self.assertEqual(budget['estimated_total'], 14000000.0)
        # Negative: the itemised plan costs less than the target set aside.
        self.assertEqual(budget['budget_vs_target'], -6000000.0)

    def test_saving_progress_and_remainder(self):
        budget = self.client.get('/api/life-experiences/').json()['experiences'][0]['budget']
        self.assertEqual(budget['saved_amount'], 5000000.0)
        self.assertEqual(budget['still_to_save'], 15000000.0)
        self.assertEqual(budget['progress_percentage'], 25.0)

    def test_category_breakdown_shares_add_up(self):
        by_category = self.client.get(
            '/api/life-experiences/'
        ).json()['experiences'][0]['budget']['by_category']
        shares = {row['category']: row['percentage'] for row in by_category}
        self.assertAlmostEqual(shares['lodging'], 57.14, places=1)
        self.assertAlmostEqual(shares['transport'], 42.86, places=1)
        self.assertAlmostEqual(sum(shares.values()), 100.0, places=1)

    def test_variance_appears_once_money_is_actually_spent(self):
        self.hotel.actual_amount = Decimal('8500000')
        self.hotel.save()
        items = self.client.get(f'/api/experience-budget/?goal={self.trip.id}').json()
        hotel = next(i for i in items if i['label'] == 'Hotel')
        self.assertEqual(hotel['variance'], 500000.0)
        flight = next(i for i in items if i['label'] == 'Vuelos')
        self.assertIsNone(flight['variance'])

    def test_only_experience_goals_are_listed(self):
        ExpectedGoal.objects.create(
            owner=self.user, title='Fondo de emergencia', goal_type='emergency_fund',
            target_amount=Decimal('10000000'), current_amount=Decimal('0'),
            currency='COP', start_date=date.today(),
            end_date=date.today() + timedelta(days=200),
        )
        body = self.client.get('/api/life-experiences/').json()
        self.assertEqual(body['count'], 1)
        self.assertEqual(body['experiences'][0]['title'], 'Japón 2027')

    def test_goals_default_to_savings(self):
        response = self.client.post('/api/goals/', {
            'title': 'Ahorro', 'target_amount': 1000, 'current_amount': 0,
            'start_date': date.today().isoformat(),
            'end_date': (date.today() + timedelta(days=30)).isoformat(),
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['goal_type'], 'savings')

    # --- Isolation -------------------------------------------------------

    def test_budget_items_are_isolated_between_users(self):
        other_client, _, _ = self.register('trip-intruder')
        self.assertEqual(other_client.get('/api/experience-budget/').json(), [])
        self.assertEqual(
            other_client.get(f'/api/experience-budget/{self.flight.id}/').status_code, 404
        )
        self.assertEqual(other_client.get('/api/life-experiences/').json()['count'], 0)

    def test_a_line_cannot_be_attached_to_someone_elses_trip(self):
        """The security hinge of this feature: `goal` decides the owner."""
        other_client, _, _ = self.register('trip-intruder')
        response = other_client.post('/api/experience-budget/', {
            'goal': self.trip.id, 'label': 'Colado', 'category': 'other',
            'estimated_amount': '1000',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('goal', response.json())
        self.assertEqual(self.trip.budget_items.count(), 2)

    def test_budget_lines_inherit_the_base_currency(self):
        response = self.client.post('/api/experience-budget/', {
            'goal': self.trip.id, 'label': 'Comida', 'category': 'food',
            'estimated_amount': '2000000',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['currency'], 'COP')

    def test_negative_lines_are_rejected(self):
        response = self.client.post('/api/experience-budget/', {
            'goal': self.trip.id, 'label': 'Descuento', 'category': 'other',
            'estimated_amount': '-500',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_deleting_a_trip_removes_its_budget(self):
        self.client.delete(f'/api/goals/{self.trip.id}/')
        self.assertEqual(ExperienceBudgetItem.objects.count(), 0)


class WealthnessServiceTests(TestCase):
    """The metric bands and the trend rule, isolated from the API."""

    def test_emergency_fund_bands(self):
        cases = [
            (Decimal('8'), 'strong'),
            (Decimal('6'), 'strong'),
            (Decimal('4'), 'adequate'),
            (Decimal('3'), 'adequate'),
            (Decimal('2'), 'low'),
            (Decimal('0.5'), 'critical'),
            (None, 'unknown'),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    wealthness_service._band(
                        value, wealthness_service.EMERGENCY_FUND_BANDS
                    )['status'],
                    expected,
                )

    def test_debt_to_income_bands_treat_high_as_bad(self):
        """Unlike the others, a bigger number here is worse."""
        for value, expected in [(50, 'critical'), (40, 'high'), (20, 'healthy')]:
            with self.subTest(value=value):
                self.assertEqual(
                    wealthness_service._band(
                        value, wealthness_service.DEBT_TO_INCOME_BANDS
                    )['status'],
                    expected,
                )

    def _series(self, net_worths, nets=None):
        nets = nets or [0] * len(net_worths)
        return [
            {'month': f'2026-{i + 1:02d}', 'income': 0, 'expenses': 0,
             'net': nets[i], 'net_worth': value}
            for i, value in enumerate(net_worths)
        ]

    def test_trend_needs_two_months(self):
        self.assertEqual(wealthness_service.trend(self._series([100]))['direction'], 'unknown')

    def test_trend_directions(self):
        self.assertEqual(
            wealthness_service.trend(self._series([100, 200]))['direction'], 'growing'
        )
        self.assertEqual(
            wealthness_service.trend(self._series([200, 100]))['direction'], 'declining'
        )

    def test_small_moves_are_noise_not_a_direction(self):
        # 1% either way stays inside the threshold.
        result = wealthness_service.trend(self._series([100, 101]))
        self.assertEqual(result['direction'], 'stable')
        self.assertEqual(result['change_pct'], 1.0)

    def test_trend_falls_back_to_net_flow_without_assets(self):
        """Someone who tracks spending but owns nothing still gets an answer."""
        result = wealthness_service.trend(self._series([0, 0, 0], nets=[10, 20, 30]))
        self.assertEqual(result['basis'], 'net_flow')
        self.assertEqual(result['direction'], 'growing')

    def test_months_back_crosses_year_boundaries(self):
        self.assertEqual(
            wealthness_service._months_back(date(2026, 2, 15), 3), date(2025, 11, 1)
        )


@override_settings(EXCHANGERATE_API_KEY='test-key-not-a-real-one')
class WealthnessApiTests(AuthTestCase):
    """The /api/wealthness/ dashboard over real records."""

    def setUp(self):
        super().setUp()
        Currency.objects.update_or_create(
            code='COP', defaults={'name': 'Colombian Peso', 'decimals': 0}
        )
        self.today = date.today().replace(day=1)

        # Six months of steady income and essential spending.
        for offset in range(6):
            month = wealthness_service._months_back(self.today, offset)
            FinancialRecord.objects.create(
                owner=self.user, type='income', category='Salary',
                amount=Decimal('5000000'), currency='COP', date=month,
            )
            FinancialRecord.objects.create(
                owner=self.user, type='expense', category='Rent & Housing',
                amount=Decimal('2000000'), currency='COP', date=month,
            )
            compute_monthly_snapshot(month, self.user)

    def test_returns_a_net_flow_series(self):
        response = self.client.get('/api/wealthness/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['base_currency'], 'COP')
        self.assertEqual(len(body['net_flow']['series']), 6)
        self.assertEqual(body['net_flow']['series'][-1]['net'], 3000000.0)

    def test_savings_rate_is_measured_over_the_window(self):
        body = self.client.get('/api/wealthness/').json()
        # Kept 3M of every 5M earned
        self.assertEqual(body['savings_rate']['value'], 60.0)
        self.assertEqual(body['savings_rate']['status'], 'strong')

    def test_emergency_fund_reports_unknown_without_liquid_assets(self):
        body = self.client.get('/api/wealthness/').json()
        self.assertEqual(body['emergency_fund']['liquid_assets'], 0.0)
        self.assertEqual(body['emergency_fund']['months_covered'], 0.0)
        self.assertEqual(body['emergency_fund']['status'], 'critical')

    def test_emergency_fund_counts_only_liquid_assets(self):
        Asset.objects.create(
            owner=self.user, name='Ahorros', asset_type='savings',
            current_value=Decimal('8000000'), currency='COP', is_liquid=True,
        )
        Asset.objects.create(
            owner=self.user, name='Apartamento', asset_type='property',
            current_value=Decimal('300000000'), currency='COP', is_liquid=False,
        )
        body = self.client.get('/api/wealthness/').json()
        # 8M liquid / 2M monthly essentials = 4 months. The flat is not counted.
        self.assertEqual(body['emergency_fund']['liquid_assets'], 8000000.0)
        self.assertEqual(body['emergency_fund']['months_covered'], 4.0)
        self.assertEqual(body['emergency_fund']['status'], 'adequate')

    def test_window_is_clamped_to_a_sane_range(self):
        for months in ('0', '-5', '9999', 'not-a-number'):
            with self.subTest(months=months):
                response = self.client.get(f'/api/wealthness/?months={months}')
                self.assertEqual(response.status_code, 200)

    def test_snapshot_stores_the_emergency_fund_metric(self):
        Asset.objects.create(
            owner=self.user, name='Ahorros', asset_type='savings',
            current_value=Decimal('6000000'), currency='COP', is_liquid=True,
        )
        snapshot = compute_monthly_snapshot(self.today, self.user)
        self.assertEqual(float(snapshot.liquid_assets), 6000000.0)
        self.assertEqual(float(snapshot.emergency_fund_months), 3.0)

    def test_wealthness_is_isolated_between_users(self):
        other_client, _, _ = self.register('wealthness-intruder')
        body = other_client.get('/api/wealthness/').json()
        self.assertEqual(body['net_flow']['series'], [])
        self.assertIsNone(body['savings_rate']['value'])
        self.assertEqual(body['net_worth']['current'], 0.0)


@override_settings(EXCHANGERATE_API_KEY='test-key-not-a-real-one')
class PatrimonyTests(AuthTestCase):
    """Net worth = what you own minus what you owe, in one currency."""

    def setUp(self):
        super().setUp()
        for code, name, decimals in (('COP', 'Colombian Peso', 0), ('USD', 'US Dollar', 2)):
            Currency.objects.update_or_create(
                code=code, defaults={'name': name, 'decimals': decimals}
            )
        ExchangeRate.objects.create(
            base='USD', target='COP', rate=Decimal('4000'), rate_date=date.today()
        )

        self.house = Asset.objects.create(
            owner=self.user, name='Apartamento', asset_type='property',
            current_value=Decimal('300000000'), currency='COP', is_liquid=False,
        )
        self.savings = Asset.objects.create(
            owner=self.user, name='Ahorros', asset_type='savings',
            current_value=Decimal('5000000'), currency='COP', is_liquid=True,
        )
        self.brokerage = Asset.objects.create(
            owner=self.user, name='Brokerage', asset_type='investment',
            current_value=Decimal('1000'), currency='USD', is_liquid=True,
        )
        self.mortgage = Debt.objects.create(
            owner=self.user, name='Hipoteca', debt_type='mortgage', creditor='Banco',
            original_amount=Decimal('200000000'), current_balance=Decimal('150000000'),
            currency='COP', interest_rate=Decimal('12.00'),
            minimum_payment=Decimal('2000000'), due_date=5, start_date=date.today(),
        )

    def test_net_worth_is_assets_minus_liabilities(self):
        response = self.client.get('/api/patrimony/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        # 300M + 5M + (1000 USD * 4000) = 309.000.000 COP
        self.assertEqual(body['total_assets'], 309000000.0)
        self.assertEqual(body['total_liabilities'], 150000000.0)
        self.assertEqual(body['net_worth'], 159000000.0)

    def test_liquid_and_illiquid_are_reported_separately(self):
        body = self.client.get('/api/patrimony/').json()
        # A house is wealth but will not cover next month's rent.
        self.assertEqual(body['liquid_assets'], 9000000.0)
        self.assertEqual(body['illiquid_assets'], 300000000.0)

    def test_debt_to_asset_ratio(self):
        body = self.client.get('/api/patrimony/').json()
        self.assertAlmostEqual(body['debt_to_asset'], 48.54, places=1)

    def test_breakdowns_group_by_type(self):
        body = self.client.get('/api/patrimony/').json()
        by_type = {row['type']: row for row in body['assets_by_type']}
        self.assertEqual(by_type['property']['total'], 300000000.0)
        self.assertEqual(by_type['investment']['total'], 4000000.0)
        self.assertEqual(body['liabilities_by_type'][0]['type'], 'mortgage')

    def test_paid_off_debts_do_not_count_against_net_worth(self):
        self.mortgage.status = 'paid_off'
        self.mortgage.save()
        body = self.client.get('/api/patrimony/').json()
        self.assertEqual(body['total_liabilities'], 0.0)
        self.assertEqual(body['net_worth'], 309000000.0)

    def test_snapshot_records_net_worth(self):
        snapshot = compute_monthly_snapshot(date.today().replace(day=1), self.user)
        self.assertEqual(float(snapshot.total_assets), 309000000.0)
        self.assertEqual(float(snapshot.net_worth), 159000000.0)
        # Previously hardcoded to None for want of an asset registry
        self.assertIsNotNone(snapshot.debt_to_asset)

    def test_liquidity_defaults_from_the_type(self):
        response = self.client.post('/api/assets/', {
            'name': 'Cuenta corriente', 'asset_type': 'cash', 'current_value': '100000',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['is_liquid'])

    def test_an_explicit_liquidity_choice_is_respected(self):
        """A locked-in savings account is savings, but not liquid."""
        response = self.client.post('/api/assets/', {
            'name': 'CDT a 5 años', 'asset_type': 'savings',
            'current_value': '10000000', 'is_liquid': False,
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()['is_liquid'])

    def test_assets_inherit_the_base_currency(self):
        response = self.client.post('/api/assets/', {
            'name': 'Carro', 'asset_type': 'vehicle', 'current_value': '40000000',
        }, format='json')
        self.assertEqual(response.json()['currency'], 'COP')

    def test_negative_values_are_rejected(self):
        response = self.client.post('/api/assets/', {
            'name': 'Deuda disfrazada', 'asset_type': 'other', 'current_value': '-500',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_assets_are_isolated_between_users(self):
        other_client, other, _ = self.register('patrimony-intruder')
        self.assertEqual(other_client.get('/api/assets/').json(), [])
        self.assertEqual(
            other_client.get(f'/api/assets/{self.house.id}/').status_code, 404
        )
        # And their net worth is their own, not mine
        self.assertEqual(other_client.get('/api/patrimony/').json()['net_worth'], 0.0)


@override_settings(EXCHANGERATE_API_KEY='test-key-not-a-real-one')
class CurrencyServiceTests(TestCase):
    """Rate caching, precision and rounding. The provider is always mocked."""

    def setUp(self):
        Currency.objects.update_or_create(
            code='COP', defaults={'name': 'Colombian Peso', 'decimals': 0}
        )
        Currency.objects.update_or_create(
            code='USD', defaults={'name': 'US Dollar', 'decimals': 2}
        )

    def _provider(self, rates=None):
        """Patch the HTTP call, not our own code, so the seam is exercised."""
        payload = {
            'result': 'success',
            'conversion_rates': rates or {'USD': 1, 'COP': 4000, 'EUR': 0.92},
        }
        response = mock.Mock(status_code=200)
        response.json.return_value = payload
        return mock.patch('requests.get', return_value=response)

    def test_rate_is_fetched_once_and_then_served_from_cache(self):
        with self._provider() as get:
            currency_service.get_rate('USD', 'COP')
            currency_service.get_rate('USD', 'COP')
            currency_service.get_rate('USD', 'COP')
        # Three lookups, one network call: the dashboard must not hammer the
        # metered free tier.
        self.assertEqual(get.call_count, 1)

    def test_same_currency_never_calls_the_provider(self):
        with mock.patch('requests.get', side_effect=AssertionError('must not be called')):
            self.assertEqual(currency_service.get_rate('COP', 'COP'), Decimal('1'))

    def test_conversion_uses_the_targets_decimals(self):
        with self._provider():
            # COP is written without cents
            self.assertEqual(currency_service.convert('10', 'USD', 'COP'), Decimal('40000'))
            # USD keeps two
            self.assertEqual(
                currency_service.convert('40000', 'COP', 'USD').as_tuple().exponent, -2
            )

    def test_rounding_is_half_even(self):
        """Half-up would bias every total upward; banker's rounding does not."""
        with self._provider(rates={'USD': 1, 'COP': 1}):
            self.assertEqual(currency_service.convert('0.125', 'USD', 'USD'), Decimal('0.12'))
            self.assertEqual(currency_service.convert('0.135', 'USD', 'USD'), Decimal('0.14'))

    def test_a_stale_rate_is_used_when_the_provider_is_down(self):
        with self._provider():
            currency_service.get_rate('USD', 'COP')

        stale = ExchangeRate.objects.get(base='USD', target='COP')
        stale.rate_date = date.today() - timedelta(days=3)
        stale.save()

        with mock.patch('requests.get', side_effect=requests.RequestException('down')):
            # An old rate beats a dashboard that refuses to render.
            self.assertEqual(currency_service.get_rate('USD', 'COP'), Decimal('4000'))

    def test_missing_rate_raises_rather_than_guessing(self):
        with mock.patch('requests.get', side_effect=requests.RequestException('down')):
            with self.assertRaises(currency_service.ExchangeRateUnavailable):
                currency_service.get_rate('USD', 'JPY')

    def test_convert_safe_leaves_the_amount_alone_when_no_rate_exists(self):
        with mock.patch('requests.get', side_effect=requests.RequestException('down')):
            self.assertEqual(
                currency_service.convert_safe(Decimal('50'), 'USD', 'JPY'), Decimal('50')
            )

    def test_refresh_only_caches_known_currencies(self):
        with self._provider(rates={'USD': 1, 'COP': 4000, 'XYZ': 7}):
            currency_service.refresh_rates('USD')
        self.assertFalse(ExchangeRate.objects.filter(target='XYZ').exists())
        self.assertTrue(ExchangeRate.objects.filter(target='COP').exists())


@override_settings(EXCHANGERATE_API_KEY='test-key-not-a-real-one')
class MultiCurrencyAggregationTests(AuthTestCase):
    """Totals must never add pesos to dollars."""

    def setUp(self):
        super().setUp()
        for code, name, decimals in (('COP', 'Colombian Peso', 0), ('USD', 'US Dollar', 2)):
            Currency.objects.update_or_create(
                code=code, defaults={'name': name, 'decimals': decimals}
            )
        setting, _ = UserSetting.objects.get_or_create(owner=self.user)
        setting.currency = 'COP'
        setting.save()

        # 1 USD = 4000 COP for the whole test.
        ExchangeRate.objects.create(
            base='USD', target='COP', rate=Decimal('4000'), rate_date=date.today()
        )
        ExchangeRate.objects.create(
            base='COP', target='COP', rate=Decimal('1'), rate_date=date.today()
        )

        self.month = date.today().replace(day=1)
        FinancialRecord.objects.create(
            owner=self.user, type='expense', category='Shopping',
            amount=Decimal('100000'), currency='COP', date=self.month,
        )
        FinancialRecord.objects.create(
            owner=self.user, type='expense', category='Shopping',
            amount=Decimal('10'), currency='USD', date=self.month,
        )

    def test_sum_in_converts_each_currency_before_adding(self):
        records = FinancialRecord.objects.filter(owner=self.user)
        # 100.000 COP + (10 USD * 4000) = 140.000 COP
        self.assertEqual(currency_service.sum_in(records, 'COP'), Decimal('140000'))

    def test_analytics_totals_are_in_the_base_currency(self):
        response = self.client.get('/api/analytics/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['base_currency'], 'COP')
        self.assertEqual(data['summary']['total_expenses'], 140000.0)

    def test_snapshot_totals_are_in_the_base_currency(self):
        snapshot = compute_monthly_snapshot(self.month, self.user)
        self.assertEqual(float(snapshot.total_expenses), 140000.0)

    def test_new_records_inherit_the_users_base_currency(self):
        response = self.client.post('/api/records/', {
            'type': 'income', 'category': 'Salary', 'amount': '500',
            'date': self.month.isoformat(),
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['currency'], 'COP')

    def test_an_explicit_currency_is_respected(self):
        response = self.client.post('/api/records/', {
            'type': 'income', 'category': 'Salary', 'amount': '500',
            'currency': 'USD', 'date': self.month.isoformat(),
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['currency'], 'USD')

    def test_currencies_endpoint_lists_the_catalog_and_base(self):
        response = self.client.get('/api/currencies/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['base_currency'], 'COP')
        self.assertIn('COP', [c['code'] for c in body['currencies']])

    def test_convert_endpoint_uses_the_cached_rate(self):
        with mock.patch('requests.get', side_effect=AssertionError('must not be called')):
            response = self.client.post('/api/currencies/convert/', {
                'amount': '10', 'from': 'USD', 'to': 'COP',
            }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['converted'], '40000')


class TwoFactorTests(AuthTestCase):
    """Enrollment, step-up login, replay protection and recovery codes."""

    def setUp(self):
        super().setUp()
        self.setting, _ = UserSetting.objects.get_or_create(owner=self.user)

    def _enroll(self):
        """Run the full enrollment flow; returns (secret, backup_codes)."""
        setup = self.client.post('/api/profile/2fa/setup/')
        self.assertEqual(setup.status_code, 200)
        secret = setup.json()['secret']

        enable = self.client.post(
            '/api/profile/2fa/enable/', {'code': pyotp.TOTP(secret).now()}, format='json'
        )
        self.assertEqual(enable.status_code, 200)
        return secret, enable.json()['backup_codes']

    @staticmethod
    def _next_code(secret):
        """A code from the following time step.

        The code that completed enrollment is spent, so signing in during that
        same 30-second window has to use the next one — which the server still
        accepts thanks to its one-step tolerance.
        """
        totp = pyotp.TOTP(secret)
        return totp.at(time.time() + totp.interval)

    # --- Enrollment ------------------------------------------------------

    def test_setup_returns_secret_uri_and_qr_without_enabling(self):
        response = self.client.post('/api/profile/2fa/setup/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('secret', data)
        self.assertTrue(data['otpauth_uri'].startswith('otpauth://totp/'))
        self.assertTrue(data['qr_code'].startswith('data:image/png;base64,'))

        # Scanning the QR is not enough: 2FA stays off until a code is proven.
        self.setting.refresh_from_db()
        self.assertFalse(self.setting.two_factor_enabled)

    def test_enable_requires_a_valid_code(self):
        self.client.post('/api/profile/2fa/setup/')
        response = self.client.post('/api/profile/2fa/enable/', {'code': '000000'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.setting.refresh_from_db()
        self.assertFalse(self.setting.two_factor_enabled)

    def test_enable_returns_backup_codes_and_turns_2fa_on(self):
        _, codes = self._enroll()
        self.assertEqual(len(codes), 10)
        self.setting.refresh_from_db()
        self.assertTrue(self.setting.two_factor_enabled)
        self.assertEqual(self.setting.two_factor_method, 'totp')

    def test_secret_is_encrypted_at_rest_and_never_returned_again(self):
        secret, _ = self._enroll()
        self.setting.refresh_from_db()
        self.assertNotIn(secret, self.setting.totp_secret)
        self.assertEqual(decrypt_text(self.setting.totp_secret), secret)

        status_body = self.client.get('/api/profile/2fa/').content.decode()
        self.assertNotIn(secret, status_body)
        profile_body = self.client.get('/api/profile/').content.decode()
        self.assertNotIn(secret, profile_body)

    def test_backup_codes_are_hashed_at_rest(self):
        _, codes = self._enroll()
        self.setting.refresh_from_db()
        self.assertNotIn(codes[0], str(self.setting.backup_codes))

    # --- Step-up login ---------------------------------------------------

    def test_login_with_2fa_withholds_tokens(self):
        self._enroll()
        response = self.anonymous.post(
            '/api/auth/login/',
            {'username': self.username, 'password': self.password},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['mfa_required'])
        self.assertIn('mfa_token', body)
        # The password alone must not hand out API credentials.
        self.assertNotIn('access', body)
        self.assertNotIn('refresh', body)

    def test_mfa_token_is_not_usable_as_an_access_token(self):
        self._enroll()
        login = self.anonymous.post(
            '/api/auth/login/',
            {'username': self.username, 'password': self.password},
            format='json',
        ).json()

        impostor = APIClient()
        impostor.credentials(HTTP_AUTHORIZATION=f"Bearer {login['mfa_token']}")
        self.assertEqual(impostor.get('/api/records/').status_code, 401)

    def test_verify_completes_the_login(self):
        secret, _ = self._enroll()
        login = self.anonymous.post(
            '/api/auth/login/',
            {'username': self.username, 'password': self.password},
            format='json',
        ).json()

        response = self.anonymous.post(
            '/api/auth/2fa/verify/',
            {'mfa_token': login['mfa_token'], 'code': self._next_code(secret)},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn('access', body)
        self.assertEqual(body['user']['username'], self.username)

        # And the issued token really works
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {body['access']}")
        self.assertEqual(client.get('/api/auth/me/').status_code, 200)

    def test_verify_rejects_a_wrong_code(self):
        self._enroll()
        login = self.anonymous.post(
            '/api/auth/login/',
            {'username': self.username, 'password': self.password},
            format='json',
        ).json()
        response = self.anonymous.post(
            '/api/auth/2fa/verify/',
            {'mfa_token': login['mfa_token'], 'code': '000000'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)

    def test_verify_rejects_a_forged_token(self):
        self._enroll()
        response = self.anonymous.post(
            '/api/auth/2fa/verify/',
            {'mfa_token': 'not-a-signed-token', 'code': '123456'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error_code'], 'mfa_token_invalid')

    def test_login_without_2fa_is_unchanged(self):
        response = self.anonymous.post(
            '/api/auth/login/',
            {'username': self.username, 'password': self.password},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())

    # --- Replay and recovery ---------------------------------------------

    def test_the_same_code_cannot_be_used_twice(self):
        secret, _ = self._enroll()
        code = self._next_code(secret)

        def attempt():
            login = self.anonymous.post(
                '/api/auth/login/',
                {'username': self.username, 'password': self.password},
                format='json',
            ).json()
            return self.anonymous.post(
                '/api/auth/2fa/verify/',
                {'mfa_token': login['mfa_token'], 'code': code},
                format='json',
            )

        self.assertEqual(attempt().status_code, 200)
        # Same code, still inside its 30-second window: must be refused.
        self.assertEqual(attempt().status_code, 401)

    def test_backup_code_works_once(self):
        _, codes = self._enroll()

        def attempt(code):
            login = self.anonymous.post(
                '/api/auth/login/',
                {'username': self.username, 'password': self.password},
                format='json',
            ).json()
            return self.anonymous.post(
                '/api/auth/2fa/verify/',
                {'mfa_token': login['mfa_token'], 'code': code},
                format='json',
            )

        self.assertEqual(attempt(codes[0]).status_code, 200)
        self.assertEqual(attempt(codes[0]).status_code, 401)
        # A different one still works
        self.assertEqual(attempt(codes[1]).status_code, 200)

        self.setting.refresh_from_db()
        self.assertEqual(len(self.setting.backup_codes), 8)

    def test_regenerating_backup_codes_invalidates_the_old_ones(self):
        _, old_codes = self._enroll()
        response = self.client.post(
            '/api/profile/2fa/backup-codes/', {'password': self.password}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        new_codes = response.json()['backup_codes']
        self.assertEqual(len(new_codes), 10)
        self.assertNotEqual(set(old_codes), set(new_codes))

    # --- Disabling -------------------------------------------------------

    def test_disable_requires_the_password(self):
        self._enroll()
        response = self.client.post(
            '/api/profile/2fa/disable/', {'password': 'wrong-password'}, format='json'
        )
        self.assertEqual(response.status_code, 403)
        self.setting.refresh_from_db()
        self.assertTrue(self.setting.two_factor_enabled)

    def test_disable_clears_the_secret(self):
        self._enroll()
        response = self.client.post(
            '/api/profile/2fa/disable/', {'password': self.password}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.setting.refresh_from_db()
        self.assertFalse(self.setting.two_factor_enabled)
        self.assertEqual(self.setting.totp_secret, '')
        self.assertEqual(self.setting.backup_codes, [])

    def test_2fa_endpoints_require_authentication(self):
        for path in ('/api/profile/2fa/', '/api/profile/2fa/setup/', '/api/profile/2fa/enable/'):
            with self.subTest(path=path):
                method = self.anonymous.get if path.endswith('/2fa/') else self.anonymous.post
                self.assertEqual(method(path).status_code, 401)


class ProfileDetailsTests(AuthTestCase):
    """Name, email and phone on the profile endpoint."""

    def test_put_updates_identity_fields(self):
        response = self.client.put('/api/profile/', {
            'first_name': 'Ada', 'last_name': 'Lovelace',
            'phone_number': '+573001234567', 'currency': 'COP',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['first_name'], 'Ada')
        self.assertEqual(body['last_name'], 'Lovelace')
        self.assertEqual(body['phone_number'], '+573001234567')
        self.assertEqual(body['currency'], 'COP')

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Ada')

    def test_changing_the_phone_clears_its_verified_flag(self):
        setting, _ = UserSetting.objects.get_or_create(owner=self.user)
        setting.phone_number = '+573001111111'
        setting.phone_verified = True
        setting.save()

        self.client.put('/api/profile/', {'phone_number': '+573002222222'}, format='json')
        setting.refresh_from_db()
        self.assertFalse(setting.phone_verified)

    def test_profile_reports_two_factor_status(self):
        response = self.client.get('/api/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['two_factor']['enabled'])


class MultiTenancyIsolationTests(AuthTestCase):
    """Every endpoint must expose one user's data only.

    Before the owner-scoping fix each ViewSet queried `Model.objects.all()`,
    so any authenticated account could read and mutate every other account's
    financial data (OWASP API1: Broken Object Level Authorization).

    Cross-user lookups must answer 404 rather than 403: a 403 would confirm
    that the id exists, which is itself a leak.
    """

    def setUp(self):
        super().setUp()
        # A second account with its own data, created straight through the ORM.
        self.other_client, self.other, _ = self.register('intruder')

        self.my_record = FinancialRecord.objects.create(
            owner=self.user, type='expense', category='Food & Dining',
            amount=Decimal('10.00'), date=date.today(), description='mine',
        )
        self.their_record = FinancialRecord.objects.create(
            owner=self.other, type='expense', category='Shopping',
            amount=Decimal('999.00'), date=date.today(), description='theirs',
        )
        self.their_goal = ExpectedGoal.objects.create(
            owner=self.other, title='Their goal', target_amount=Decimal('100.00'),
            current_amount=Decimal('10.00'), start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        self.their_debt = Debt.objects.create(
            owner=self.other, name='Their card', debt_type='credit_card',
            creditor='Bank', original_amount=Decimal('1000.00'),
            current_balance=Decimal('800.00'), interest_rate=Decimal('20.00'),
            minimum_payment=Decimal('50.00'), due_date=5, start_date=date.today(),
        )
        self.their_statement = BankStatement.objects.create(
            owner=self.other,
            file=SimpleUploadedFile('theirs.pdf', b'%PDF-1.4 theirs', content_type='application/pdf'),
            original_filename='theirs.pdf', content_hash='hash-of-their-file',
        )
        self.their_txn = ExtractedTransaction.objects.create(
            statement=self.their_statement, date=date.today(),
            raw_description='Their coffee', cleaned_description='Their coffee',
            amount=Decimal('5.00'), transaction_type='expense',
        )

    # --- Records ---------------------------------------------------------

    def test_record_list_excludes_other_users(self):
        response = self.client.get('/api/records/')
        self.assertEqual(response.status_code, 200)
        descriptions = [r['description'] for r in response.json()]
        self.assertEqual(descriptions, ['mine'])

    def test_record_detail_of_other_user_is_404(self):
        response = self.client.get(f'/api/records/{self.their_record.id}/')
        self.assertEqual(response.status_code, 404)

    def test_record_update_of_other_user_is_404(self):
        response = self.client.patch(
            f'/api/records/{self.their_record.id}/', {'amount': '1.00'}, format='json'
        )
        self.assertEqual(response.status_code, 404)
        self.their_record.refresh_from_db()
        self.assertEqual(self.their_record.amount, Decimal('999.00'))

    def test_record_delete_of_other_user_is_404(self):
        response = self.client.delete(f'/api/records/{self.their_record.id}/')
        self.assertEqual(response.status_code, 404)
        self.assertTrue(FinancialRecord.objects.filter(id=self.their_record.id).exists())

    def test_created_record_is_owned_by_requester(self):
        response = self.client.post('/api/records/', {
            'type': 'income', 'category': 'Salary', 'amount': '1500.00',
            'date': date.today().isoformat(), 'description': 'payday',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        record = FinancialRecord.objects.get(id=response.json()['id'])
        self.assertEqual(record.owner, self.user)

    # --- Goals / debts / statements --------------------------------------

    def test_goal_isolation(self):
        self.assertEqual(self.client.get('/api/goals/').json(), [])
        self.assertEqual(self.client.get(f'/api/goals/{self.their_goal.id}/').status_code, 404)

    def test_goals_analysis_excludes_other_users(self):
        response = self.client.get('/api/goals/analysis/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['summary']['total_goals'], 0)

    def test_debt_isolation(self):
        self.assertEqual(self.client.get('/api/debts/').json(), [])
        self.assertEqual(self.client.get(f'/api/debts/{self.their_debt.id}/').status_code, 404)

    def test_debt_payment_on_other_users_debt_is_404(self):
        response = self.client.post(
            f'/api/debts/{self.their_debt.id}/make_payment/', {'amount': '100'}, format='json'
        )
        self.assertEqual(response.status_code, 404)
        self.their_debt.refresh_from_db()
        self.assertEqual(self.their_debt.current_balance, Decimal('800.00'))

    def test_statement_isolation(self):
        self.assertEqual(self.client.get('/api/statements/').json(), [])
        self.assertEqual(self.client.get(f'/api/statements/{self.their_statement.id}/').status_code, 404)

    def test_statement_file_download_of_other_user_is_404(self):
        response = self.client.get(f'/api/statements/{self.their_statement.id}/file/')
        self.assertEqual(response.status_code, 404)

    def test_extracted_transactions_query_param_cannot_cross_users(self):
        response = self.client.get(
            f'/api/extracted-transactions/?statement_id={self.their_statement.id}'
        )
        self.assertEqual(response.status_code, 404)

    def test_same_file_can_be_uploaded_by_two_users(self):
        """Duplicate detection is per user, so it cannot leak another upload."""
        pdf = SimpleUploadedFile('shared.pdf', b'%PDF-1.4 shared', content_type='application/pdf')
        first = self.client.post('/api/statements/', {'file': pdf}, format='multipart')
        self.assertIn(first.status_code, (201, 200))

        same_pdf = SimpleUploadedFile('shared.pdf', b'%PDF-1.4 shared', content_type='application/pdf')
        second = self.other_client.post('/api/statements/', {'file': same_pdf}, format='multipart')
        self.assertNotEqual(second.status_code, 409)

    # --- Extracted transactions ------------------------------------------

    def test_extracted_transaction_isolation(self):
        self.assertEqual(self.client.get('/api/extracted/').json(), [])
        self.assertEqual(self.client.get(f'/api/extracted/{self.their_txn.id}/').status_code, 404)

    def test_confirming_other_users_transaction_is_404(self):
        response = self.client.post(
            f'/api/extracted/{self.their_txn.id}/confirm/',
            {'category': 'Food & Dining', 'type': 'expense'}, format='json',
        )
        self.assertEqual(response.status_code, 404)
        self.their_txn.refresh_from_db()
        self.assertFalse(self.their_txn.is_reviewed)

    def test_extracted_transactions_cannot_be_created_directly(self):
        """These rows only come from parsing a statement.

        A client-created one would carry no statement and therefore no owner,
        so the route is closed: 405, never a 500.
        """
        response = self.client.post('/api/extracted/', {
            'date': date.today().isoformat(), 'amount': '12.00',
            'transaction_type': 'expense',
        }, format='json')
        self.assertEqual(response.status_code, 405)

    def test_bulk_confirm_skips_other_users_transactions(self):
        response = self.client.post('/api/extracted/bulk_confirm/', {
            'transactions': [
                {'id': self.their_txn.id, 'category': 'Food & Dining', 'type': 'expense'}
            ]
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['created'], 0)
        self.their_txn.refresh_from_db()
        self.assertFalse(self.their_txn.is_reviewed)

    # --- Aggregates -------------------------------------------------------

    def test_analytics_totals_exclude_other_users(self):
        response = self.client.get('/api/analytics/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['summary']['total_expenses'], 10.0)

    def test_snapshots_are_per_user(self):
        """Both users can hold a snapshot for the same month without clashing."""
        month = date.today().replace(day=1)
        mine = self.client.post('/api/snapshots/generate/', {'date': month.isoformat()}, format='json')
        theirs = self.other_client.post('/api/snapshots/generate/', {'date': month.isoformat()}, format='json')
        self.assertEqual(mine.status_code, 200)
        self.assertEqual(theirs.status_code, 200)
        self.assertEqual(float(mine.json()['total_expenses']), 10.0)
        self.assertEqual(float(theirs.json()['total_expenses']), 999.0)
        self.assertEqual(len(self.client.get('/api/snapshots/').json()), 1)

    def test_csv_export_excludes_other_users(self):
        response = self.client.get('/api/export/csv/')
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('mine', body)
        self.assertNotIn('theirs', body)

    # --- Settings and vocabulary -----------------------------------------

    def test_ai_keys_are_per_user(self):
        with mock.patch.object(key_validation, 'validate_api_key', return_value={'valid': True}):
            self.client.put(
                '/api/ai-settings/',
                {'provider': 'openai', 'api_key': 'sk-mine-0001'},
                format='json',
            )
        # The other account must not see or inherit that key
        response = self.other_client.get('/api/ai-settings/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['keys']['openai'])
        self.assertEqual(
            decrypt_text(UserSetting.objects.get(owner=self.user).ai_keys['openai']),
            'sk-mine-0001',
        )

    def test_currency_setting_is_per_user(self):
        self.client.put('/api/profile/', {'currency': 'USD'}, format='json')
        self.assertEqual(self.client.get('/api/profile/').json()['currency'], 'USD')
        self.assertEqual(self.other_client.get('/api/profile/').json()['currency'], 'COP')

    def test_custom_categories_are_private_but_builtins_are_shared(self):
        created = self.client.post('/api/custom-categories/', {'name': 'Mis Viajes', 'type': 'expense'}, format='json')
        self.assertEqual(created.status_code, 200)

        mine = [c['name'] for c in self.client.get('/api/custom-categories/').json()]
        theirs = [c['name'] for c in self.other_client.get('/api/custom-categories/').json()]
        self.assertIn('Mis Viajes', mine)
        self.assertNotIn('Mis Viajes', theirs)
        # The seeded catalog stays visible to everyone
        self.assertIn('Food & Dining', theirs)