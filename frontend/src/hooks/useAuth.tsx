/**
 * Контекст авторизации: JWT в localStorage, профиль пользователя и методы входа/выхода.
 */
import React, { useState, useEffect, createContext, useContext, ReactNode } from 'react';
import { User, LoginData, RegisterData } from '../types';
import { apiService } from '../services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (data: LoginData) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/** Хук доступа к AuthContext (только внутри AuthProvider). */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

/** Провайдер: при монтировании восстанавливает сессию по access_token и отдаёт API авторизации. */
export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  useEffect(() => {
    /** Загружает профиль при наличии токена или очищает просроченные ключи. */
    const initAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const userData = await apiService.getProfile();
          setUser(userData);
        } catch (error) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  /** Сохраняет токены и пользователя после успешного apiService.login. */
  const login = async (data: LoginData) => {
    const response = await apiService.login(data);
    localStorage.setItem('access_token', response.tokens.access);
    localStorage.setItem('refresh_token', response.tokens.refresh);
    setUser(response.user);
  };

  /** Регистрация и автоматический вход с сохранением JWT. */
  const register = async (data: RegisterData) => {
    const response = await apiService.register(data);
    localStorage.setItem('access_token', response.tokens.access);
    localStorage.setItem('refresh_token', response.tokens.refresh);
    setUser(response.user);
  };

  /** Удаляет токены и сбрасывает пользователя в состоянии. */
  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  /** Перезапрашивает профиль с сервера (например после смены данных). */
  const refreshUser = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setUser(null);
      return;
    }
    const userData = await apiService.getProfile();
    setUser(userData);
  };

  const value = {
    user,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
