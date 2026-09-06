/**
 * API calls for the patrimony domain: the asset register (CRUD) and the
 * net-worth summary that reads assets against debts.
 *
 * Every figure in the summary already arrives converted to the caller's base
 * currency — the conversion is the backend's job, because doing it here would
 * mean adding pesos to dollars in the browser.
 */
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

/** The asset types the backend accepts, with their Spanish labels. */
export const ASSET_TYPES: Array<{ value: string; label: string }> = [
  { value: 'cash', label: 'Efectivo' },
  { value: 'savings', label: 'Ahorros' },
  { value: 'investment', label: 'Inversión' },
  { value: 'retirement', label: 'Pensión' },
  { value: 'property', label: 'Propiedad' },
  { value: 'vehicle', label: 'Vehículo' },
  { value: 'business', label: 'Participación en negocio' },
  { value: 'receivable', label: 'Dinero que me deben' },
  { value: 'other', label: 'Otro' },
];

export const assetTypeLabel = (value: string): string =>
  ASSET_TYPES.find((t) => t.value === value)?.label ?? value;

/**
 * Which types the backend treats as liquid by default. Mirrors
 * `Asset.LIQUID_TYPES`; the user can always override it per asset, and that
 * override sticks — a five-year CD is savings but is not liquid.
 */
export const LIQUID_BY_DEFAULT = new Set(['cash', 'savings', 'investment', 'receivable']);
