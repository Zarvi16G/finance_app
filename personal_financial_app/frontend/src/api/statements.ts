/**
 * API calls for bank statements: upload, list, detail,
reprocess, type/bank PATCH, PDF download and the extracted
transactions review/confirm flow.
 */
import { apiClient } from './client';
import type { BankStatement, ExtractedTransaction } from '../types';

export const statementsApi = {
  async list(): Promise<BankStatement[]> {
    const { data } = await apiClient.get<BankStatement[]>('/statements/');
    return data;
  },

  async upload(file: File, statementType?: string, password?: string): Promise<BankStatement> {
    const formData = new FormData();
    formData.append('file', file);
    if (statementType) formData.append('statement_type', statementType);
    if (password) formData.append('password', password);
    const { data } = await apiClient.post<BankStatement>('/statements/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  async get(id: number | string): Promise<BankStatement> {
    const { data } = await apiClient.get<BankStatement>(`/statements/${id}/`);
    return data;
  },

  async reprocess(id: number | string): Promise<BankStatement> {
    const { data } = await apiClient.post<BankStatement>(`/statements/${id}/reprocess/`);
    return data;
  },

  async update(id: number | string, data: Partial<Pick<BankStatement, 'statement_type' | 'bank_name'>>): Promise<BankStatement> {
    const { data: updated } = await apiClient.patch<BankStatement>(`/statements/${id}/`, data);
    return updated;
  },

  async remove(id: number | string): Promise<void> {
    await apiClient.delete(`/statements/${id}/`);
  },

  async extracted(statementId: number | string): Promise<ExtractedTransaction[]> {
    const { data } = await apiClient.get<ExtractedTransaction[] | { message: string }>(
      '/extracted-transactions/',
      { params: { statement_id: statementId } },
    );
    return Array.isArray(data) ? data : [];
  },

  fileUrl(id: number | string): string {
    return `${apiClient.defaults.baseURL}/statements/${id}/file/`;
  },
};

export const extractedApi = {
  async list(params?: { statement_id?: number | string; needs_review?: boolean }): Promise<ExtractedTransaction[]> {
    const { data } = await apiClient.get<ExtractedTransaction[]>('/extracted/', { params });
    return data;
  },

  async confirm(
    id: number | string,
    payload: { category: string; type: string; description?: string; account_bank?: string },
  ) {
    const { data } = await apiClient.post(`/extracted/${id}/confirm/`, payload);
    return data;
  },

  async bulkConfirm(
    transactions: Array<{ id: number; category: string; type: string; description?: string; account_bank?: string }>,
  ) {
    const { data } = await apiClient.post('/extracted/bulk_confirm/', { transactions });
    return data;
  },
};