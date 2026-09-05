"""URL routing: DRF router for ViewSets plus explicit paths for the rest.

Every endpoint is versionless and lives under /api/ (added in config/urls.py).
The frontend mirrors these paths exactly in src/api/*.ts.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .views import (
    FinancialRecordViewSet, ExpectedGoalViewSet,
    ExportCSVView, ExportPDFView, AIAnalysisView, GoalsAnalysisView,
    BankStatementViewSet, ExtractedTransactionViewSet, AICategorizationView, AIChatView,
    AISettingsView, CustomCategoryView, CustomTypeView, ProfileSettingsView,
    FinancialAnalyticsView, DebtViewSet, FinancialSnapshotViewSet,
    ChoiceView,
    RegisterView, LoginView, LogoutView, MeView,
    TwoFactorLoginVerifyView, TwoFactorStatusView, TwoFactorSetupView,
    TwoFactorEnableView, TwoFactorDisableView, TwoFactorBackupCodesView,
    CurrencyListView, CurrencyConvertView,
    AssetViewSet, PatrimonyView, WealthnessView,
    ExperienceBudgetItemViewSet, LifeExperiencesView,
)

router = DefaultRouter()
router.register(r'records', FinancialRecordViewSet, basename='financial-record')
router.register(r'goals', ExpectedGoalViewSet, basename='expected-goal')
router.register(r'statements', BankStatementViewSet, basename='bank-statement')
router.register(r'debts', DebtViewSet, basename='debt')
router.register(r'snapshots', FinancialSnapshotViewSet, basename='financial-snapshot')
router.register(r'extracted', ExtractedTransactionViewSet, basename='extracted-transaction')
router.register(r'assets', AssetViewSet, basename='asset')
router.register(r'experience-budget', ExperienceBudgetItemViewSet, basename='experience-budget')

urlpatterns = [
    # Authentication (JWT session management)
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='auth-verify'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', MeView.as_view(), name='auth-me'),
    # Second step of login when the account has 2FA enabled
    path('auth/2fa/verify/', TwoFactorLoginVerifyView.as_view(), name='auth-2fa-verify'),
    # Second-factor management (from the profile screen)
    path('profile/2fa/', TwoFactorStatusView.as_view(), name='profile-2fa'),
    path('profile/2fa/setup/', TwoFactorSetupView.as_view(), name='profile-2fa-setup'),
    path('profile/2fa/enable/', TwoFactorEnableView.as_view(), name='profile-2fa-enable'),
    path('profile/2fa/disable/', TwoFactorDisableView.as_view(), name='profile-2fa-disable'),
    path('profile/2fa/backup-codes/', TwoFactorBackupCodesView.as_view(), name='profile-2fa-backup-codes'),
    path('export/csv/', ExportCSVView.as_view(), name='export-csv'),
    path('export/pdf/', ExportPDFView.as_view(), name='export-pdf'),
    path('analysis/', AIAnalysisView.as_view(), name='ai-analysis'),
    path('goals/analysis/', GoalsAnalysisView.as_view(), name='goals-analysis'),
    path('analytics/', FinancialAnalyticsView.as_view(), name='financial-analytics'),
    path('ai-categorize/', AICategorizationView.as_view(), name='ai-categorize'),
    path('ai-chat/', AIChatView.as_view(), name='ai-chat'),
    path('ai-settings/', AISettingsView.as_view(), name='ai-settings'),
    path('custom-categories/', CustomCategoryView.as_view(), name='custom-categories'),
    path('custom-categories/<int:pk>/', CustomCategoryView.as_view(), name='custom-category-detail'),
    path('custom-types/', CustomTypeView.as_view(), name='custom-types'),
    path('custom-types/<int:pk>/', CustomTypeView.as_view(), name='custom-type-detail'),
    path('choices/', ChoiceView.as_view(), name='choices'),
    path('choices/<int:pk>/', ChoiceView.as_view(), name='choice-detail'),
    path('profile/', ProfileSettingsView.as_view(), name='profile'),
    path('currencies/', CurrencyListView.as_view(), name='currencies'),
    path('currencies/convert/', CurrencyConvertView.as_view(), name='currencies-convert'),
    path('patrimony/', PatrimonyView.as_view(), name='patrimony'),
    path('wealthness/', WealthnessView.as_view(), name='wealthness'),
    path('life-experiences/', LifeExperiencesView.as_view(), name='life-experiences'),
    path('extracted-transactions/',
         BankStatementViewSet.as_view({'get': 'extracted_transactions'}),
         name='extracted-transactions'),
    path('', include(router.urls)),
]