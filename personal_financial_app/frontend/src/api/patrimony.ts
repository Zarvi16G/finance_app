/**
 * API calls for the patrimony domain: the asset register (CRUD) and the
 * net-worth summary that reads assets against debts.
 *
 * Every figure in the summary already arrives converted to the caller's base
 * currency — the conversion is the backend's job, because doing it here would
 * mean adding pesos to dollars in the browser.
 */
import i18n from '../i18n';
import { apiClient } from './client';
import type { Asset, PatrimonySummary } from '../types';

export const patrimonyApi = {
  async summary(): Promise<PatrimonySummary> {
    const { data } = await apiClient.get<PatrimonySummary>('/patrimony/');
    return data;
  },
};

export const assetsApi = {
  async list(params?: { asset_type?: string; is_liquid?: boolean }): Promise<Asset[]> {
    const { data } = await apiClient.get<Asset[]>('/assets/', { params });
    return data;
  },

  async create(payload: Partial<Asset>): Promise<Asset> {
    const { data } = await apiClient.post<Asset>('/assets/', payload);
    return data;
  },

  async update(id: number, payload: Partial<Asset>): Promise<Asset> {
    const { data } = await apiClient.patch<Asset>(`/assets/${id}/`, payload);
    return data;
  },

  async remove(id: number): Promise<void> {
    await apiClient.delete(`/assets/${id}/`);
  },
};

/** The asset types the backend accepts. Values are the API's; the words come
 *  from the dictionary, so they follow the interface language. */
export const ASSET_TYPES = [
  'cash', 'savings', 'investment', 'retirement', 'property',
  'vehicle', 'business', 'receivable', 'other',
] as const;

export const assetTypeLabel = (value: string): string =>
  i18n.t(`assetTypes.${value}`, { defaultValue: value });

/**
 * Which types the backend treats as liquid by default. Mirrors
 * `Asset.LIQUID_TYPES`; the user can always override it per asset, and that
 * override sticks — a five-year CD is savings but is not liquid.
 */
export const LIQUID_BY_DEFAULT = new Set(['cash', 'savings', 'investment', 'receivable']);
