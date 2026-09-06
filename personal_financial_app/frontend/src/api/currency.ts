/**
 * API calls for the currency catalog and ad-hoc conversion.
 *
 * Conversion goes through the backend on purpose: rates live in a cache with
 * a TTL there, and the browser has no business holding a rate table.
 */
import { apiClient } from './client';
import type { CurrencyCatalog } from '../types';

export interface ConversionResult {
  amount: string;
  from: string;
  to: string;
  rate: string;
  converted: string;
}

export const currencyApi = {
  async catalog(): Promise<CurrencyCatalog> {
    const { data } = await apiClient.get<CurrencyCatalog>('/currencies/');
    return data;
  },

  async convert(amount: number | string, from: string, to?: string): Promise<ConversionResult> {
    const { data } = await apiClient.post<ConversionResult>('/currencies/convert/', {
      amount,
      from,
      to,
    });
    return data;
  },
};
