"""Model layer: one module per domain.

Mirrors the services/ organization — each module owns the models for a
single business domain (records, goals, statements, debts, snapshots, settings).
"""
from .records import FinancialRecord
from .goals import ExpectedGoal
from .statements import BankStatement, ExtractedTransaction, CategorizationMemory
from .debts import Debt
from .snapshots import FinancialSnapshot
from .settings import UserSetting, CustomType, CustomCategory, Choice
from .currency_rates import CurrencyRate

__all__ = [
    'FinancialRecord',
    'ExpectedGoal',
    'BankStatement',
    'ExtractedTransaction',
    'CategorizationMemory',
    'Debt',
    'FinancialSnapshot',
    'UserSetting',
    'CustomType',
    'CustomCategory',
    'Choice',
    'CurrencyRate',
]