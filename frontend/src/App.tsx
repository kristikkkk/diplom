/**
 * Корневой роутер: MUI-тема, React Query, провайдер авторизации и маршруты приложения.
 */
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Box, CircularProgress } from '@mui/material';

import Layout from './components/Layout/Layout';
import { AuthProvider, useAuth } from './hooks/useAuth';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AdDetailPage from './pages/AdDetailPage';
import AdCreatePage from './pages/AdCreatePage';
import AdEditPage from './pages/AdEditPage';
import FavoritesPage from './pages/FavoritesPage';
import ProfilePage from './pages/ProfilePage';
import ChatPage from './pages/ChatPage';
import ChatListPage from './pages/ChatListPage';
import ModerationPage from './pages/ModerationPage';
import { editorialTheme } from './theme';

// Создаем QueryClient для React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

/** Оборачивает дочерние страницы: доступ только для вошедших пользователей. */
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

/** Страницы входа/регистрации: редирект на главную, если уже авторизован. */
const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  return !isAuthenticated ? <>{children}</> : <Navigate to="/" />;
};

/** Сборка всех маршрутов и провайдеров верхнего уровня. */
const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={editorialTheme}>
        <CssBaseline />
        <AuthProvider>
          <Router>
            <Routes>
              {/* Публичные маршруты */}
              <Route
                path="/login"
                element={
                  <PublicRoute>
                    <LoginPage />
                  </PublicRoute>
                }
              />
              <Route
                path="/register"
                element={
                  <PublicRoute>
                    <RegisterPage />
                  </PublicRoute>
                }
              />

              {/* Защищенные маршруты */}
              <Route
                path="/"
                element={
                  <Layout>
                    <HomePage />
                  </Layout>
                }
              />

              {/* Страницы объявлений */}
              <Route
                path="/ads/:id"
                element={
                  <Layout>
                    <AdDetailPage />
                  </Layout>
                }
              />
              <Route
                path="/ads/:id/edit"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <AdEditPage />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/ads/new"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <AdCreatePage />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              
              {/* Избранное и профиль */}
              <Route
                path="/favorites"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <FavoritesPage />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <ProfilePage />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              
              {/* Чат */}
              <Route
                path="/chats"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <ChatListPage />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/chat/:id"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <ChatPage />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              
              {/* Модерация (только для админов) */}
              <Route
                path="/moderation"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <ModerationPage />
                    </Layout>
                  </ProtectedRoute>
                }
              />

              {/* 404 */}
              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </Router>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;

