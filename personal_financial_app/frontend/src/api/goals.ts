/**
 * API calls for savings goals: CRUD plus the /goals/analysis/
aggregation endpoint rendered by components/goals/GoalsList.
 */
import { apiClient } from './client';
import type { ExpectedGoal, GoalsAnalysis } from '../types';

export interface GoalInput {
  title: string;
  target_amount: number | string;
  current_amount: number | string;
  start_date: string;
  end_date: string;
  category: string;
  status?: string;
  description?: string;
}

export const goalsApi = {
  async list(): Promise<ExpectedGoal[]> {
    const { data } = await apiClient.get<ExpectedGoal[]>('/goals/');
    return data;
  },

  async create(payload: GoalInput): Promise<ExpectedGoal> {
    const { data } = await apiClient.post<ExpectedGoal>('/goals/', payload);
    return data;
  },

  async update(id: number, payload: Partial<GoalInput>): Promise<ExpectedGoal> {
    const { data } = await apiClient.patch<ExpectedGoal>(`/goals/${id}/`, payload);
    return data;
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/goals/${id}/`);
  },

  async analysis(): Promise<GoalsAnalysis> {
    const { data } = await apiClient.get<GoalsAnalysis>('/goals/analysis/');
    return data;
  },
};