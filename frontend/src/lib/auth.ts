'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { User } from '@/types';
import { auth } from '@/lib/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; username: string; password: string; full_name?: string }) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<string | null>;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  refreshToken: null,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  refreshAccessToken: async () => null,
  loading: true,
});

function setCookie(name: string, value: string, days: number) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function deleteCookie(name: string) {
  document.cookie = `${name}=; path=/; max-age=0`;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const storedToken = localStorage.getItem('token');
      const storedRefresh = localStorage.getItem('refresh_token');
      const storedUser = localStorage.getItem('user');
      if (storedToken && storedUser) {
        setToken(storedToken);
        setRefreshToken(storedRefresh);
        setUser(JSON.parse(storedUser));
        setCookie('token', storedToken, 7);
      }
    } catch {
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
    }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const res = await auth.login({ email, password });
    const newToken = res.data.access_token;
    const newRefresh = res.data.refresh_token;
    const newUser = res.data.user;
    setToken(newToken);
    setRefreshToken(newRefresh);
    setUser(newUser);
    localStorage.setItem('token', newToken);
    localStorage.setItem('refresh_token', newRefresh);
    localStorage.setItem('user', JSON.stringify(newUser));
    setCookie('token', newToken, 7);
  };

  const register = async (data: { email: string; username: string; password: string; full_name?: string }) => {
    const res = await auth.register(data);
    const newToken = res.data.access_token;
    const newRefresh = res.data.refresh_token;
    const newUser = res.data.user;
    setToken(newToken);
    setRefreshToken(newRefresh);
    setUser(newUser);
    localStorage.setItem('token', newToken);
    localStorage.setItem('refresh_token', newRefresh);
    localStorage.setItem('user', JSON.stringify(newUser));
    setCookie('token', newToken, 7);
  };

  const refreshAccessToken = useCallback(async (): Promise<string | null> => {
    const storedRefresh = localStorage.getItem('refresh_token');
    if (!storedRefresh) return null;

    try {
      const res = await auth.refresh(storedRefresh);
      const newToken = res.data.access_token;
      const newRefresh = res.data.refresh_token;
      setToken(newToken);
      setRefreshToken(newRefresh);
      localStorage.setItem('token', newToken);
      localStorage.setItem('refresh_token', newRefresh);
      setCookie('token', newToken, 7);
      return newToken;
    } catch {
      logout();
      return null;
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setRefreshToken(null);
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    deleteCookie('token');
    router.push('/login');
  }, [router]);

  return React.createElement(
    AuthContext.Provider,
    { value: { user, token, refreshToken, login, register, logout, refreshAccessToken, loading } },
    children
  );
}

export const useAuth = () => useContext(AuthContext);
