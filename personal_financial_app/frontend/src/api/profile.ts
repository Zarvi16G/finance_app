/**
 * API calls for profile settings, the Choice vocabulary
(categories/types used across forms) and financial records
(the dashboard's live per-day/month series).
 */
import { apiClient } from './client';
import type { ProfileSettings, Choice, FinancialRecord } from '../types';

export const profileApi = {
  async get(): Promise<ProfileSettings> {
    const { data } = await apiClient.get<ProfileSettings>('/profile/');
    return data;
  },

  async update(payload: { currency?: string; new_type?: string; new_category?: string; new_category_type?: string }): Promise<ProfileSettings> {
    const { data } = await apiClient.put<ProfileSettings>('/profile/', payload);
    return data;
  },
};

export const choicesApi = {
  async list(): Promise<Choice[]> {
    const { data } = await apiClient.get<Choice[]>('/choices/');
    return data;
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/choices/${id}/`);
  },
};

export const recordsApi = {
  async list(params?: Record<string, string | number | boolean>): Promise<FinancialRecord[]> {
    const { data } = await apiClient.get<FinancialRecord[]>('/records/', { params });
    return data;
  },

  async create(payload: Partial<FinancialRecord>): Promise<FinancialRecord> {
    const { data } = await apiClient.post<FinancialRecord>('/records/', payload);
    return data;
  },

  async update(id: number, payload: Partial<FinancialRecord>): Promise<FinancialRecord> {
    const { data } = await apiClient.patch<FinancialRecord>(`/records/${id}/`, payload);
    return data;
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/records/${id}/`);
  },
};