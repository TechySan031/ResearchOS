import { create } from 'zustand';
import { api } from '../lib/api';

// ── Types ────────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: string;
  created_at: string;
  updated_at: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<boolean>;
  fetchCurrentUser: () => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  initialize: () => void;
  clearError: () => void;
}

// ── Token Persistence ────────────────────────────────────────────────────────

const TOKEN_KEY = 'researchos_access_token';
const REFRESH_KEY = 'researchos_refresh_token';

function persistTokens(access: string, refresh: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  }
}

function clearTokens() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  }
}

function loadTokens(): { access: string | null; refresh: string | null } {
  if (typeof window === 'undefined') {
    return { access: null, refresh: null };
  }
  return {
    access: localStorage.getItem(TOKEN_KEY),
    refresh: localStorage.getItem(REFRESH_KEY),
  };
}

// ── Store ────────────────────────────────────────────────────────────────────

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  initialize: () => {
    const { access, refresh } = loadTokens();
    if (access && refresh) {
      set({
        accessToken: access,
        refreshToken: refresh,
        isAuthenticated: true,
      });
      // Fetch user profile in background
      get().fetchCurrentUser().catch(() => {
        // Token may be expired — try refresh
        get().refreshAccessToken().then((ok) => {
          if (ok) {
            get().fetchCurrentUser().catch(() => {
              // Give up
              clearTokens();
              set({ isAuthenticated: false, accessToken: null, refreshToken: null, user: null });
            });
          }
        });
      });
    }
  },

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.post<TokenResponse>('/api/v1/auth/login', {
        email,
        password,
      });
      persistTokens(data.access_token, data.refresh_token);
      set({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        isAuthenticated: true,
        isLoading: false,
      });
      // Fetch user profile
      await get().fetchCurrentUser();
    } catch (err: any) {
      set({
        error: err.info?.detail || err.message || 'Login failed',
        isLoading: false,
      });
      throw err;
    }
  },

  register: async (email: string, password: string, name: string) => {
    set({ isLoading: true, error: null });
    try {
      await api.post('/api/v1/auth/register', {
        email,
        password,
        name,
      });
      // Auto-login after registration
      await get().login(email, password);
    } catch (err: any) {
      set({
        error: err.info?.detail || err.message || 'Registration failed',
        isLoading: false,
      });
      throw err;
    }
  },

  logout: async () => {
    const { accessToken } = get();
    try {
      if (accessToken) {
        await api.post('/api/v1/auth/logout', undefined, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
      }
    } catch {
      // Ignore errors — we're logging out anyway
    }
    clearTokens();
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      error: null,
    });
  },

  refreshAccessToken: async () => {
    const { refreshToken } = get();
    if (!refreshToken) return false;

    try {
      const data = await api.post<TokenResponse>('/api/v1/auth/refresh', {
        refresh_token: refreshToken,
      });
      persistTokens(data.access_token, data.refresh_token);
      set({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        isAuthenticated: true,
      });
      return true;
    } catch {
      clearTokens();
      set({
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        user: null,
      });
      return false;
    }
  },

  fetchCurrentUser: async () => {
    const { accessToken } = get();
    if (!accessToken) return;

    try {
      const user = await api.get<AuthUser>('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      set({ user, isAuthenticated: true });
    } catch (err: any) {
      if (err.status === 401) {
        // Token expired — try refresh
        const refreshed = await get().refreshAccessToken();
        if (refreshed) {
          const token = get().accessToken;
          const user = await api.get<AuthUser>('/api/v1/auth/me', {
            headers: { Authorization: `Bearer ${token}` },
          });
          set({ user });
        }
      } else {
        throw err;
      }
    }
  },

  forgotPassword: async (email: string) => {
    await api.post('/api/v1/auth/forgot-password', { email });
  },

  clearError: () => set({ error: null }),
}));
