/**
 * API calls for analytics (snapshot-cache dashboard) and AI features
(analysis, categorize, chat, settings). analyticsApi feeds the
dashboard; aiApi feeds pages/analysis and the statement review AI.
 */
import { apiClient } from './client';
import type { DashboardData, AIAnalysisResult, AIChatResponse, AIConfig, CategorySuggestion } from '../types';

export const analyticsApi = {
  async dashboard(params?: { start_date?: string; end_date?: string }): Promise<DashboardData> {
    const { data } = await apiClient.get<DashboardData>('/analytics/', { params });
    return data;
  },
};

export const aiApi = {
  async analyze(params?: Record<string, string | number | boolean>): Promise<AIAnalysisResult> {
    const { data } = await apiClient.post<AIAnalysisResult>('/analysis/', {}, { params });
    return data;
  },

  async chat(message: string, transactionIds: number[], history: Array<{ role: string; content: string }> = []) {
    const { data } = await apiClient.post<AIChatResponse>('/ai-chat/', {
      message,
      transaction_ids: transactionIds,
      history,
    });
    return data;
  },

  async categorize(
    transactionIds?: number[],
    descriptions?: string[],
  ): Promise<{ results: CategorySuggestion[] }> {
    const { data } = await apiClient.post<{ results: CategorySuggestion[] }>('/ai-categorize/', {
      transaction_ids: transactionIds || [],
      descriptions: descriptions || [],
    });
    return data;
  },

  async getSettings(): Promise<AIConfig> {
    const { data } = await apiClient.get<AIConfig>('/ai-settings/');
    return data;
  },

  async saveSettings(payload: { provider?: string; model?: string; api_key?: string }): Promise<AIConfig> {
    const { data } = await apiClient.put<AIConfig>('/ai-settings/', payload);
    return data;
  },
};