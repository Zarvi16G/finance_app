/**
 * Shared axios instance for all API calls (baseURL `/api`, proxied to Django
 * in development via vite.config.ts).
 *
 * Request interceptor: attaches the Bearer access token to every call.
 * Response interceptor: transparently handles expired access tokens —
 * concurrent 401s are queued and replayed after a single POST /auth/refresh/,
 * and if refresh fails it clears both tokens and emits "auth:unauthorized"
 * so AuthContext can sign the user out.
 */
import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

let isRefreshing = false;
let queue: Array<(token: string | null) => void> = [];

const isAuthCall = (url?: string) => {
  if (!url) return false;
  return /\/auth\/(login|register|refresh|logout)\/?$/.test(url);
};

const flushQueue = (token: string | null) => {
  queue.forEach((cb) => cb(token));
  queue = [];
};

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !original?._retry && !isAuthCall(original?.url)) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          queue.push((token) => {
            if (token) {
              original._retry = true;
              original.headers.Authorization = `Bearer ${token}`;
              resolve(apiClient(original));
            } else {
              reject(error);
            }
          });
        });
      }

      isRefreshing = true;
      return apiClient
        .post('/auth/refresh/', { refresh: refreshToken })
        .then(({ data }) => {
          localStorage.setItem('access_token', data.access);
          flushQueue(data.access);
          original._retry = true;
          original.headers.Authorization = `Bearer ${data.access}`;
          return apiClient(original);
        })
        .catch((refreshError) => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          flushQueue(null);
          window.dispatchEvent(new CustomEvent('auth:unauthorized'));
          return Promise.reject(refreshError);
        })
        .finally(() => {
          isRefreshing = false;
        });
    }

    return Promise.reject(error);
  },
);

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | { error?: string; message?: string; detail?: string }
      | undefined;
    return data?.error || data?.message || data?.detail || error.message || 'An error occurred';
  }
  return error instanceof Error ? error.message : 'An error occurred';
}