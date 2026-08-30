/**
 * API calls for currency exchange rates (foreign → COP table).
 */
import { apiClient } from './client';
import type { CurrencyRate } from '../types';

export const exchangeRatesApi = {
    async list(): Promise<CurrencyRate[]> {
        const { data } = await apiClient.get<CurrencyRate[]>('/exchange-rates/');
        return data;
    },

    async create(payload: { currency_code: string; rate_to_cop: number }): Promise<CurrencyRate> {
        const { data } = await apiClient.post<CurrencyRate>('/exchange-rates/', payload);
        return data;
    },

    async update(currencyCode: string, payload: { rate_to_cop: number }): Promise<CurrencyRate> {
        const { data } = await apiClient.patch<CurrencyRate>(`/exchange-rates/${currencyCode}/`, payload);
        return data;
    },

    async remove(currencyCode: string): Promise<void> {
        await apiClient.delete(`/exchange-rates/${currencyCode}/`);
    },
};
