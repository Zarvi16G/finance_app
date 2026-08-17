from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import FinancialRecord, UserSetting, BankStatement, ExpectedGoal, ExtractedTransaction
from .crypto import decrypt_text
from .services.snapshot_service import compute_monthly_snapshot
from .services.ai import key_validation
from .services.statement_detection import detect_statement_info


class AuthTestCase(TestCase):
    """Mixin that registers a user and exposes an authenticated API client."""

    username = 'tester'
    password = 'S3cure!Passw0rd-123'

    def setUp(self):
        self.anonymous = APIClient()
        response = self.anonymous.post(
            '/api/auth/register/',
            {'username': self.username, 'password': self.password, 'email': 'tester@example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.tokens = response.json()
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens['access']}")



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
            type='expense', category='Food & Dining', amount=Decimal('100.00'), date=self.month
        )
        FinancialRecord.objects.create(
            type='expense', category='Food & Dining', amount=Decimal('50.00'), date=self.month.replace(day=15)
        )
        FinancialRecord.objects.create(
            type='expense', category='Utilities', amount=Decimal('75.00'), date=self.month.replace(day=10)
        )
        FinancialRecord.objects.create(
            type='income', category='Salary', amount=Decimal('500.00'), date=self.month.replace(day=5)
        )

        compute_monthly_snapshot(self.month)

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
        setting = UserSetting.objects.get(pk=1)
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
            setting = UserSetting.objects.get(pk=1)
            self.assertNotIn(code, str(setting.ai_keys))

    def test_put_overwrites_key(self):
        with self._valid_key():
            self.client.put('/api/ai-settings/', {'provider': 'gemini', 'api_key': 'first-key'}, format='json')
            response = self.client.put('/api/ai-settings/', {'provider': 'gemini', 'api_key': 'second-key'}, format='json')
        self.assertEqual(response.status_code, 200)
        setting = UserSetting.objects.get(pk=1)
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