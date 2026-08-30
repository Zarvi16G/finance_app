from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import (
    FinancialRecord, UserSetting, BankStatement, ExpectedGoal, ExtractedTransaction,
    Debt, Choice, CustomCategory, CustomType, CategorizationMemory,
)
from .crypto import decrypt_text
from .services.snapshot_service import compute_monthly_snapshot
from .services.categorization import record_memory
from .services.ai import key_validation
from .services.statement_detection import detect_statement_info

User = get_user_model()


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
        self.user = User.objects.get(username=self.username)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens['access']}")

    def _make_client_for(self, username, password='S3cure!Passw0rd-456'):
        """Register a second user and return an API client authenticated as them."""
        resp = APIClient().post(
            '/api/auth/register/',
            {'username': username, 'password': password, 'email': f'{username}@example.com'},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.json()['access']}")
        return client, User.objects.get(username=username)



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
            owner=self.user, type='expense', category='Food & Dining', amount=Decimal('100.00'), date=self.month
        )
        FinancialRecord.objects.create(
            owner=self.user, type='expense', category='Food & Dining', amount=Decimal('50.00'), date=self.month.replace(day=15)
        )
        FinancialRecord.objects.create(
            owner=self.user, type='expense', category='Utilities', amount=Decimal('75.00'), date=self.month.replace(day=10)
        )
        FinancialRecord.objects.create(
            owner=self.user, type='income', category='Salary', amount=Decimal('500.00'), date=self.month.replace(day=5)
        )

        compute_monthly_snapshot(self.user, self.month)

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
            owner=self.user, type='expense', category='Food & Dining', amount=Decimal('15.00'),
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


class OwnerIsolationTests(AuthTestCase):
    """Phase 0 multi-tenancy: user A must never see or touch user B's data.

    ``self.user`` / ``self.client`` are "user A" (from AuthTestCase). Each test
    creates a row owned by a second user B and asserts A gets an empty list and
    a 404 on every by-id route - never a 200, and never a 403 (a 403 would leak
    the fact that the object exists).
    """

    def setUp(self):
        super().setUp()
        self.other_client, self.other = self._make_client_for('user-b')

    # --- records ---------------------------------------------------------
    def test_records_are_isolated(self):
        rec = FinancialRecord.objects.create(
            owner=self.other, type='expense', category='Other',
            amount=Decimal('99.00'), date=date.today(),
        )
        self.assertEqual(self.client.get('/api/records/').json(), [])
        self.assertEqual(self.client.get(f'/api/records/{rec.id}/').status_code, 404)
        self.assertEqual(
            self.client.patch(f'/api/records/{rec.id}/', {'amount': '1.00'}, format='json').status_code,
            404,
        )
        self.assertEqual(self.client.delete(f'/api/records/{rec.id}/').status_code, 404)
        rec.refresh_from_db()
        self.assertEqual(rec.amount, Decimal('99.00'))

    def test_create_forces_owner_to_request_user(self):
        resp = self.client.post('/api/records/', {
            'type': 'income', 'category': 'Salary', 'amount': '10.00',
            'date': date.today().isoformat(), 'account_bank': 'cash',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(FinancialRecord.objects.get(id=resp.json()['id']).owner, self.user)

    # --- debts ---------------------------------------------------------
    def test_debts_are_isolated(self):
        debt = Debt.objects.create(
            owner=self.other, name='B loan', debt_type='personal_loan', creditor='Bank',
            original_amount=Decimal('1000'), current_balance=Decimal('1000'),
            interest_rate=Decimal('10'), minimum_payment=Decimal('50'),
            due_date=1, start_date=date.today(),
        )
        self.assertEqual(self.client.get('/api/debts/').json(), [])
        self.assertEqual(self.client.get(f'/api/debts/{debt.id}/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/debts/{debt.id}/').status_code, 404)

    # --- goals ---------------------------------------------------------
    def test_goals_are_isolated(self):
        goal = ExpectedGoal.objects.create(
            owner=self.other, title='B goal', target_amount=Decimal('100'),
            current_amount=Decimal('0'), start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        self.assertEqual(self.client.get('/api/goals/').json(), [])
        self.assertEqual(self.client.get(f'/api/goals/{goal.id}/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/goals/{goal.id}/').status_code, 404)

    # --- statements + extracted transactions --------------------------
    def test_statements_and_extracted_are_isolated(self):
        stmt = BankStatement.objects.create(
            owner=self.other,
            file=SimpleUploadedFile('b.pdf', b'%PDF-1.4', content_type='application/pdf'),
            original_filename='b.pdf', statement_type='other',
        )
        txn = ExtractedTransaction.objects.create(
            statement=stmt, date=date.today(), raw_description='x',
            cleaned_description='x', amount=Decimal('5.00'), transaction_type='expense',
        )
        self.assertEqual(self.client.get('/api/statements/').json(), [])
        self.assertEqual(self.client.get(f'/api/statements/{stmt.id}/').status_code, 404)
        self.assertEqual(self.client.get('/api/extracted/').json(), [])
        self.assertEqual(self.client.get(f'/api/extracted/{txn.id}/').status_code, 404)
        # confirming someone else's transaction must not create a record for A
        self.assertEqual(
            self.client.post(f'/api/extracted/{txn.id}/confirm/',
                             {'category': 'Other', 'type': 'expense'}, format='json').status_code,
            404,
        )

    # --- snapshots ---------------------------------------------------------
    def test_snapshots_are_isolated(self):
        FinancialRecord.objects.create(
            owner=self.other, type='income', category='Salary',
            amount=Decimal('500.00'), date=date.today().replace(day=1),
        )
        from .services.snapshot_service import compute_monthly_snapshot
        snap = compute_monthly_snapshot(self.other, date.today().replace(day=1))
        self.assertEqual(self.client.get('/api/snapshots/').json(), [])
        self.assertEqual(self.client.get(f'/api/snapshots/{snap.id}/').status_code, 404)

    # --- analytics / exports aggregate only the caller's data ---------
    def test_analytics_excludes_other_users_records(self):
        FinancialRecord.objects.create(
            owner=self.other, type='expense', category='Food & Dining',
            amount=Decimal('1234.00'), date=date.today(),
        )
        resp = self.client.get('/api/analytics/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['summary']['total_expenses'], 0)


class Phase0bIsolationTests(AuthTestCase):
    """Phase 0b: per-user AI settings, custom vocabulary and categorization memory.

    ``self.user`` / ``self.client`` = user A. Built-in choices (``owner=NULL``,
    ``builtin=True``) stay shared; everything a user creates is private.
    """

    def setUp(self):
        super().setUp()
        self.other_client, self.other = self._make_client_for('user-b')

    # --- AI provider keys --------------------------------------------------
    def test_ai_keys_are_per_user(self):
        with mock.patch.object(key_validation, 'validate_api_key', return_value={'valid': True}):
            resp = self.client.put(
                '/api/ai-settings/',
                {'provider': 'openai', 'api_key': 'sk-user-a-secret'},
                format='json',
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['keys']['openai'], '••••cret')

        # user B sees no key, and has a distinct UserSetting row
        b_config = self.other_client.get('/api/ai-settings/').json()
        self.assertIsNone(b_config['keys']['openai'])
        self.assertNotEqual(
            UserSetting.objects.get(owner=self.user).pk,
            UserSetting.objects.get(owner=self.other).pk,
        )
        self.assertNotIn('sk-user-a-secret', str(UserSetting.objects.get(owner=self.other).ai_keys))

    # --- custom categories / choices ------------------------------------
    def test_custom_category_is_private_but_builtins_are_shared(self):
        created = self.other_client.post(
            '/api/custom-categories/', {'name': 'B Secret Cat', 'type': 'expense'}, format='json'
        ).json()

        a_cats = [c['name'] for c in self.client.get('/api/custom-categories/').json()]
        self.assertNotIn('B Secret Cat', a_cats)
        # built-in vocabulary is still visible to A
        self.assertTrue(any(c['builtin'] for c in self.client.get('/api/choices/').json()))
        self.assertNotIn(
            'B Secret Cat',
            [c['name'] for c in self.client.get('/api/choices/').json()],
        )

        # A cannot delete B's custom category
        b_choice = Choice.objects.get(name='B Secret Cat', owner=self.other)
        self.assertEqual(
            self.client.delete(f'/api/custom-categories/{b_choice.custom_category_id}/').status_code,
            404,
        )
        self.assertTrue(CustomCategory.objects.filter(id=created['id']).exists())

    def test_two_users_can_have_a_category_with_the_same_name(self):
        r1 = self.client.post('/api/custom-categories/', {'name': 'Freelance', 'type': 'income'}, format='json')
        r2 = self.other_client.post('/api/custom-categories/', {'name': 'Freelance', 'type': 'income'}, format='json')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(CustomCategory.objects.filter(name='Freelance').count(), 2)

    def test_custom_type_is_private(self):
        self.other_client.post('/api/custom-types/', {'name': 'B Type'}, format='json')
        self.assertNotIn('B Type', [t['name'] for t in self.client.get('/api/custom-types/').json()])

    # --- categorization memory ------------------------------------------
    def test_categorization_memory_is_per_user(self):
        record_memory(self.user, 'starbucks reston town center', 'Food & Dining', 'expense')
        record_memory(self.other, 'starbucks reston town center', 'Entertainment & Leisure', 'expense')
        # same pattern, two owners -> two independent rows
        self.assertEqual(CategorizationMemory.objects.filter(pattern__startswith='starbucks').count(), 2)
        self.assertEqual(CategorizationMemory.objects.filter(owner=self.user).count(), 1)
        self.assertEqual(
            CategorizationMemory.objects.get(owner=self.user).category, 'Food & Dining'
        )