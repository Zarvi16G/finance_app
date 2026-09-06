/**
 * API calls for life experiences: the goals themselves come from the
 * aggregate endpoint (with their budgets already totalled and converted),
 * while individual budget lines are edited through their own ViewSet.
 */
import i18n from '../i18n';
import { apiClient } from './client';
import type { ExperienceBudgetItem, LifeExperiences } from '../types';

export const experiencesApi = {
  async overview(): Promise<LifeExperiences> {
    const { data } = await apiClient.get<LifeExperiences>('/life-experiences/');
    return data;
  },
};

export const budgetItemsApi = {
  async list(goalId?: number): Promise<ExperienceBudgetItem[]> {
    const { data } = await apiClient.get<ExperienceBudgetItem[]>('/experience-budget/', {
      params: goalId ? { goal: goalId } : undefined,
    });
    return data;
  },

  async create(payload: Partial<ExperienceBudgetItem>): Promise<ExperienceBudgetItem> {
    const { data } = await apiClient.post<ExperienceBudgetItem>('/experience-budget/', payload);
    return data;
  },

  async update(id: number, payload: Partial<ExperienceBudgetItem>): Promise<ExperienceBudgetItem> {
    const { data } = await apiClient.patch<ExperienceBudgetItem>(
      `/experience-budget/${id}/`,
      payload,
    );
    return data;
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/experience-budget/${id}/`);
  },
};

export const BUDGET_CATEGORIES = [
  'transport', 'lodging', 'food', 'activities',
  'insurance', 'shopping', 'buffer', 'other',
] as const;

export const budgetCategoryLabel = (value: string): string =>
  i18n.t(`budgetCategories.${value}`, { defaultValue: value });
