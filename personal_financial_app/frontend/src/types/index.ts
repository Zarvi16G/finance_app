/**
 * Shared TypeScript contracts for the whole app. Field names
mirror the Django serializer output 1:1 — keep in sync when
the backend contract changes.
 */
export interface User {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
  is_active: boolean;
  date_joined: string;
}

export interface TokenPair {
  access: string;
  refresh: string;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface FinancialRecord {
    id: number;
    type: 'income' | 'expense' | 'other';
    category: string;
    amount: number | string;
    currency: string;
    date: string;
    description: string;
    account_bank: string;
    account_bank_other?: string;
    created_at: string;
}

export interface BankStatement {
    id: number;
    file: string;
    original_filename: string;
    file_size_mb: number;
    content_hash: string;
    statement_type: string;
    statement_type_display: string;
    currency: string;
    bank_name: string;
    password: string;
    account_number: string;
    statement_period_start: string | null;
    statement_period_end: string | null;
    uploaded_at: string;
    processed_at: string | null;
    status: 'processing' | 'completed' | 'failed';
    status_display: string;
    total_transactions_extracted: number;
    total_transactions_imported: number;
    error_message: string | null;
    total_income_usd: number;
    total_expense_usd: number;
    net_usd: number;
    totals_stale: boolean;
    totals_updated_at: string | null;
}

export interface ExtractedTransaction {
    id: number;
    statement: number;
    date: string;
    raw_description: string;
    cleaned_description: string;
    amount: number | string;
    currency: string;
    transaction_type: string;
    transaction_type_display: string;
    suggested_category: string | null;
    suggested_category_display: string;
    confidence_score: number;
    needs_review: boolean;
    is_reviewed: boolean;
    user_confirmed_category: string | null;
    user_confirmed_type: string | null;
    created_at: string;
    reviewed_at: string | null;
}

export interface Debt {
    id: string;
    name: string;
    debt_type: string;
    debt_type_display: string;
    currency: string;
    original_amount: number | string;
    current_balance: number | string;
    interest_rate: number | string;
    minimum_payment: number | string;
    due_date: number;
    start_date: string;
    end_date: string | null;
    status: string;
    status_display: string;
    creditor: string;
    notes: string | null;
    progress_percentage: number;
    remaining_balance: number;
    months_remaining: number | null;
    monthly_interest: number;
    created_at: string;
    updated_at: string;
}

export interface ExpectedGoal {
  id: number;
  title: string;
  target_amount: number | string;
  current_amount: number | string;
  start_date: string;
  end_date: string;
  category: string;
  status: string;
  description: string;
  progress_percentage: number;
  created_at: string;
}

export interface GoalsAnalysis {
  summary: {
    total_target: number;
    total_current: number;
    overall_progress: number;
    total_goals: number;
    achieved_goals: number;
  };
  categories: Array<{
    category: string;
    total_target: number;
    total_current: number;
    goals_count: number;
    achieved_count: number;
    goals: Array<{
      id: number;
      title: string;
      target_amount: number;
      current_amount: number;
      progress_percentage: number;
      status: string;
      start_date: string;
      end_date: string;
      description: string;
    }>;
    overall_progress: number;
  }>;
}

export interface DashboardData {
  period: { start: string; end: string };
  income_vs_expenses: Array<{ month: string; income: number; expenses: number; net: number }>;
  expense_by_category: Array<{ category: string; total: number; count: number }>;
  income_by_category: Array<{ category: string; total: number; count: number }>;
  monthly_trends: Array<{ month: string; income: number; expenses: number; net: number }>;
  financial_ratios: {
    liquidity: { current_ratio: number | null; quick_ratio: number | null; cash_ratio: number | null };
    profitability: { net_profit_margin: number; savings_rate: number; expense_ratio: number };
    solvency: { debt_to_income: number | null; debt_to_asset: number | null };
    growth: { income_growth_yoy: number; expense_growth_yoy: number; net_worth_growth: number };
    operational_efficiency: {
      expenses_per_category: Record<string, { total: number; average: number; count: number; percentage: number }>;
    };
  };
  debt_summary: {
    total_debts: number;
    total_balance: number;
    total_monthly_payment: number;
    total_monthly_interest: number;
    has_multiple_currencies: boolean;
    active_currencies: string[];
    exchange_rates: Record<string, number>;
    by_currency: Record<string, {
      count: number;
      total_balance: number;
      total_monthly_payment: number;
      total_monthly_interest: number;
    }>;
    by_currency_cop: Record<string, {
      total_balance: number;
      total_monthly_payment: number;
      total_monthly_interest: number;
    }>;
    by_type: Record<string, {
      count: number;
      total_balance: number;
      currency: string;
    }>;
    payoff_timeline: Array<{
      debt_id: string;
      name: string;
      type: string;
      currency: string;
      balance: number;
      interest_rate: number;
      minimum_payment: number;
      estimated_months: number | null;
      total_interest: number | null;
    }>;
  };
  summary: {
    total_income: number;
    total_expenses: number;
    total_other: number;
    net_cash_flow: number;
    savings_rate: number;
  };
}

export interface AIAnalysisResult {
  analysis: string;
  used_fallback: boolean;
}

export interface AIChatResponse {
  reply: string;
  actions: Array<Record<string, unknown>>;
}

export interface AIConfig {
  provider: string;
  model: string;
  keys: Record<string, string | null>;
  default_models: Record<string, string>;
}

export interface Choice {
  id: number;
  name: string;
  choice_type: 'category' | 'type';
  transaction_type: 'income' | 'expense' | null;
  builtin: boolean;
}

export interface ProfileSettings {
    currency: string;
    exchange_rates: Record<string, number>;
    types: Array<{ id: number; name: string; builtin: boolean }>;
    categories: Array<{ id: number; name: string; type: string; builtin: boolean }>;
}

export interface CurrencyRate {
    id: number;
    currency_code: string;
    rate_to_cop: number;
    created_at: string;
    updated_at: string;
}

export interface CategorySuggestion {
  id: number | null;
  description: string;
  amount: number;
  suggested_category: string;
  suggested_type: string;
  confidence_score: number;
}