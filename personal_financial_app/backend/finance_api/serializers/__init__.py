"""Serializer layer: one module per domain, mirroring models/ and services/.

For backwards compatibility this package re-exports every public serializer
so `from .serializers import FinancialRecordSerializer` keeps working.
"""
from .records import FinancialRecordSerializer
from .goals import ExpectedGoalSerializer
from .statements import BankStatementSerializer, ExtractedTransactionSerializer, CategorizationReviewSerializer
from .debts import DebtSerializer
from .snapshots import FinancialSnapshotSerializer
from .auth import RegisterSerializer
from .patrimony import AssetSerializer

__all__ = [
    'FinancialRecordSerializer',
    'ExpectedGoalSerializer',
    'BankStatementSerializer',
    'ExtractedTransactionSerializer',
    'CategorizationReviewSerializer',
    'DebtSerializer',
    'FinancialSnapshotSerializer',
    'RegisterSerializer',
    'AssetSerializer',
]