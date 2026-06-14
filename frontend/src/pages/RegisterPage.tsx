/**
 * Регистрация нового пользователя с выбором роли и подтверждением пароля.
 */
import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Link,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { useForm } from 'react-hook-form';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { RegisterData } from '../types';

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register: registerUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterData>();

  const password = watch('password');

  /** Регистрирует пользователя и выполняет автоматический вход. */
  const onSubmit = async (data: RegisterData) => {
    try {
      setLoading(true);
      setError(null);
      await registerUser(data);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка регистрации');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="85vh"
    >
      <Card sx={{ maxWidth: 460, width: '100%' }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="overline" color="primary" sx={{ letterSpacing: '0.18em', display: 'block', textAlign: 'center' }}>
            Architectural Curator
          </Typography>
          <Typography variant="h4" component="h1" gutterBottom align="center" sx={{ mt: 1 }}>
            Регистрация
          </Typography>
          
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 3 }}>
            Создайте новый аккаунт
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit(onSubmit)}>
            <TextField
              fullWidth
              label="Имя пользователя"
              margin="normal"
              {...register('username', {
                required: 'Имя пользователя обязательно',
                minLength: {
                  value: 3,
                  message: 'Минимум 3 символа',
                },
              })}
              error={!!errors.username}
              helperText={errors.username?.message}
            />

            <TextField
              fullWidth
              label="Email"
              type="email"
              margin="normal"
              {...register('email', {
                required: 'Email обязателен',
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: 'Неверный формат email',
                },
              })}
              error={!!errors.email}
              helperText={errors.email?.message}
            />

            <FormControl fullWidth margin="normal">
              <InputLabel>Роль</InputLabel>
              <Select
                {...register('role', { required: 'Роль обязательна' })}
                defaultValue="tenant"
                error={!!errors.role}
              >
                <MenuItem value="tenant">Арендатор</MenuItem>
                <MenuItem value="landlord">Арендодатель</MenuItem>
              </Select>
              {errors.role && (
                <Typography variant="caption" color="error" sx={{ mt: 0.5, ml: 1.75 }}>
                  {errors.role.message}
                </Typography>
              )}
            </FormControl>

            <TextField
              fullWidth
              label="Номер телефона"
              margin="normal"
              {...register('phone_number')}
              error={!!errors.phone_number}
              helperText={errors.phone_number?.message}
            />

            <TextField
              fullWidth
              label="Пароль"
              type="password"
              margin="normal"
              {...register('password', {
                required: 'Пароль обязателен',
                minLength: {
                  value: 8,
                  message: 'Пароль должен содержать минимум 8 символов',
                },
              })}
              error={!!errors.password}
              helperText={errors.password?.message}
            />

            <TextField
              fullWidth
              label="Подтверждение пароля"
              type="password"
              margin="normal"
              {...register('password_confirm', {
                required: 'Подтверждение пароля обязательно',
                validate: (value) =>
                  value === password || 'Пароли не совпадают',
              })}
              error={!!errors.password_confirm}
              helperText={errors.password_confirm?.message}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={loading}
              sx={{ mt: 3, mb: 2 }}
            >
              {loading ? <CircularProgress size={24} /> : 'Зарегистрироваться'}
            </Button>

            <Box textAlign="center">
              <Typography variant="body2">
                Уже есть аккаунт?{' '}
                <Link component={RouterLink} to="/login">
                  Войти
                </Link>
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default RegisterPage;


