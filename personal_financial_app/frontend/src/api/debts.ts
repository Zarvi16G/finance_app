/**
 * API calls for the debt registry (CRUD). debt_type values and
display labels mirror backend models/debts.py exactly.
 */
import { apiClient } from './client';
import type { Debt } from '../types';

export interface DebtInput {
  name: string;
  debt_type: string;
  creditor: string;
  original_amount: number | string;
  current_balance: number | string;
  interest_rate: number | string;
  minimum_payment: number | string;
  due_date: number;
  start_date: string;
  end_date?: string | null;
  status?: string;
  notes?: string;
}

export const debtsApi = {
  async list(): Promise<Debt[]> {
    const { data } = await apiClient.get<Debt[]>('/debts/');
    return data;
  },

  async get(id: string): Promise<Debt> {
    const { data } = await apiClient.get<Debt>(`/debts/${id}/`);
    return data;
  },

  async create(payload: DebtInput): Promise<Debt> {
    const { data } = await apiClient.post<Debt>('/debts/', payload);
    return data;
  },

  async update(id: string, payload: Partial<DebtInput>): Promise<Debt> {
    const { data } = await apiClient.patch<Debt>(`/debts/${id}/`, payload);
    return data;
  },

  async remove(id: string): Promise<void> {
    await apiClient.delete(`/debts/${id}/`);
  },
};
/** Spanish labels for the fixed debt enums. These are closed sets defined in
 *  the backend model, so mapping them here is safe — unlike user-created
 *  categories, which stay in whatever words the user typed. */
export const DEBT_TYPE_LABELS: Record<string, string> = {
  credit_card: 'Tarjeta de crédito',
  personal_loan: 'Préstamo personal',
  mortgage: 'Hipotecario',
  auto_loan: 'Crédito de vehículo',
  student_loan: 'Crédito educativo',
  medical_debt: 'Deuda médica',
  other: 'Otra',
};

export const DEBT_STATUS_LABELS: Record<string, string> = {
  active: 'Activa',
  paid_off: 'Pagada',
  defaulted: 'En mora',
  in_grace: 'En periodo de gracia',
};

export const debtTypeLabel = (value: string, fallback = ''): string =>
  DEBT_TYPE_LABELS[value] ?? fallback ?? value;

export const debtStatusLabel = (value: string, fallback = ''): string =>
  DEBT_STATUS_LABELS[value] ?? fallback ?? value;
