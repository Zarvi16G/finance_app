/**
 * API calls for the auth endpoints (register/login/refresh/logout/me).
Used by pages/Login, pages/Register and auth/AuthContext.
 */
import { apiClient } from './client';
import type { AuthResponse, User } from '../types';

export const authApi = {
  async register(username: string, password: string, email?: string): Promise<AuthResponse> {
    const { data } = await apiClient.post<AuthResponse>('/auth/register/', {
      username,
      password,
      email: email || '',
    });
    return data;
  },

  async login(username: string, password: string): Promise<AuthResponse> {
    const { data } = await apiClient.post<AuthResponse>('/auth/login/', { username, password });
    return data;
  },

  async logout(refresh: string): Promise<void> {
    await apiClient.post('/auth/logout/', { refresh });
  },

  async me(): Promise<User> {
    const { data } = await apiClient.get<User>('/auth/me/');
    return data;
  },
};