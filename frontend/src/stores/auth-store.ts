import { create } from 'zustand';
import { apiClient } from '@/lib/api-client';
import type { User, UserRole, LoginResponse } from '@/types/api';

interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: () => boolean;
  hasRole: (roles: UserRole[]) => boolean;
}

const storedToken = localStorage.getItem('auth_token');
const storedUser = localStorage.getItem('auth_user');

export const useAuthStore = create<AuthState>((set, get) => ({
  user: storedUser ? (JSON.parse(storedUser) as User) : null,
  token: storedToken,

  login: async (email: string, password: string) => {
    const response = await apiClient.post<LoginResponse>('/api/auth/login', {
      email,
      password,
    });
    const { access_token, user } = response.data;
    localStorage.setItem('auth_token', access_token);
    localStorage.setItem('auth_user', JSON.stringify(user));
    set({ token: access_token, user });
  },

  logout: () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    set({ token: null, user: null });
  },

  isAuthenticated: () => {
    return get().token !== null && get().user !== null;
  },

  hasRole: (roles: UserRole[]) => {
    const { user } = get();
    if (!user) return false;
    return roles.includes(user.role);
  },
}));
