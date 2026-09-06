/**
 * API call for the Wealthness dashboard.
 *
 * The backend clamps `months` to 2..60 rather than rejecting a nonsense
 * window, so the screen always renders something.
 */
import { apiClient } from './client';
import type { WealthnessOverview } from '../types';

export const wealthnessApi = {
  async overview(months = 12): Promise<WealthnessOverview> {
    const { data } = await apiClient.get<WealthnessOverview>('/wealthness/', {
      params: { months },
    });
    return data;
  },
};
