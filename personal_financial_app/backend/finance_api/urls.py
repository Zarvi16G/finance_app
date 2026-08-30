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
    FinancialAnalyticsView, DebtViewSet, CurrencyRateViewSet, FinancialSnapshotViewSet,
    ChoiceView,
    RegisterView, LoginView, LogoutView, MeView,
)

router = DefaultRouter()
router.register(r'records', FinancialRecordViewSet, basename='financial-record')
router.register(r'goals', ExpectedGoalViewSet, basename='expected-goal')
router.register(r'statements', BankStatementViewSet, basename='bank-statement')
router.register(r'debts', DebtViewSet, basename='debt')
router.register(r'exchange-rates', CurrencyRateViewSet, basename='currency-rate')
router.register(r'snapshots', FinancialSnapshotViewSet, basename='financial-snapshot')
router.register(r'extracted', ExtractedTransactionViewSet, basename='extracted-transaction')

urlpatterns = [
    # Authentication (JWT session management)
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='auth-verify'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', MeView.as_view(), name='auth-me'),
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
    path('extracted-transactions/',
         BankStatementViewSet.as_view({'get': 'extracted_transactions'}),
         name='extracted-transactions'),
    path('', include(router.urls)),
]