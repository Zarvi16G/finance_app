"""API views package: one module per domain.

For backwards compatibility this package re-exports every public view class
so `from .views import FinancialRecordViewSet` keeps working.
"""
from .records import FinancialRecordViewSet
from .goals import ExpectedGoalViewSet, GoalsAnalysisView
from .exports import ExportCSVView, ExportPDFView
from .analysis import AIAnalysisView
from .statements import BankStatementViewSet
from .extracted import ExtractedTransactionViewSet
from .ai import AICategorizationView, AIChatView, AISettingsView
from .choices import ChoiceView, CustomCategoryView, CustomTypeView
from .profile import ProfileSettingsView
from .analytics import FinancialAnalyticsView
from .debts import DebtViewSet
from .snapshots import FinancialSnapshotViewSet
from .auth import RegisterView, LoginView, LogoutView, MeView

__all__ = [
    'FinancialRecordViewSet',
    'ExpectedGoalViewSet',
    'GoalsAnalysisView',
    'ExportCSVView',
    'ExportPDFView',
    'AIAnalysisView',
    'BankStatementViewSet',
    'ExtractedTransactionViewSet',
    'AICategorizationView',
    'AIChatView',
    'AISettingsView',
    'ChoiceView',
    'CustomCategoryView',
    'CustomTypeView',
    'ProfileSettingsView',
    'FinancialAnalyticsView',
    'DebtViewSet',
    'FinancialSnapshotViewSet',
    'RegisterView',
    'LoginView',
    'LogoutView',
    'MeView',
]