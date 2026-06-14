/**
 * Профиль: редактирование контактов, таблица своих объявлений и своих отзывов.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Avatar,
  Grid,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
  Chip,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material';
import { Edit, Save, Cancel } from '@mui/icons-material';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';
import { User, MyReview } from '../types';
import { apiService } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import AdCard from '../components/AdCard';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

/** Контент вкладки профиля для MUI Tabs. */
function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`profile-tabpanel-${index}`}
      aria-labelledby={`profile-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

/** Локализованная подпись статуса модерации отзыва. */
const statusLabel = (s: MyReview['status']) => {
  if (s === 'approved') return 'Одобрено';
  if (s === 'rejected') return 'Отклонено';
  return 'На модерации';
};

const ProfilePage: React.FC = () => {
  const { logout, refreshUser } = useAuth();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [tabValue, setTabValue] = useState(0);
  const [userAds, setUserAds] = useState<any[]>([]);
  const [myReviews, setMyReviews] = useState<MyReview[]>([]);
  const [reviewsLoading, setReviewsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
  } = useForm<Partial<Pick<User, 'email' | 'phone_number'>>>();

  useEffect(() => {
    loadProfile();
  }, []);

  /** Объявления текущего пользователя из общего списка API. */
  const loadUserAds = useCallback(async () => {
    if (!user?.id) return;
    try {
      const adsData = await apiService.getAds();
      const filtered = adsData.results.filter((ad) => ad.author.id === user.id);
      setUserAds(filtered);
    } catch (err) {
      console.error('Error loading user ads:', err);
    }
  }, [user?.id]);

  /** Отзывы автора для вкладки «Мои отзывы». */
  const loadMyReviews = useCallback(async () => {
    try {
      setReviewsLoading(true);
      const data = await apiService.getMyReviews();
      setMyReviews(data);
    } catch (err) {
      console.error('Error loading my reviews:', err);
    } finally {
      setReviewsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tabValue === 1 && user) {
      loadUserAds();
    }
  }, [tabValue, user, loadUserAds]);

  useEffect(() => {
    if (tabValue === 2) {
      loadMyReviews();
    }
  }, [tabValue, loadMyReviews]);

  /** Первичная загрузка профиля и заполнение формы. */
  const loadProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      const userData = await apiService.getProfile();
      setUser(userData);
      reset({
        email: userData.email,
        phone_number: userData.phone_number ?? '',
      });
    } catch (err) {
      setError('Ошибка загрузки профиля');
      console.error('Error loading profile:', err);
    } finally {
      setLoading(false);
    }
  };

  /** Сохраняет email/телефон и синхронизирует контекст авторизации. */
  const onSubmit = async (data: Partial<Pick<User, 'email' | 'phone_number'>>) => {
    try {
      setLoading(true);
      setError(null);
      const phoneRaw = data.phone_number;
      const updated = await apiService.updateProfile({
        email: data.email?.trim(),
        phone_number:
          phoneRaw === undefined ? undefined : phoneRaw.trim() === '' ? null : phoneRaw.trim(),
      });
      setUser(updated);
      reset({
        email: updated.email,
        phone_number: updated.phone_number ?? '',
      });
      await refreshUser();
      setEditing(false);
    } catch (err: any) {
      const msg =
        err.response?.data?.email?.[0] ||
        err.response?.data?.detail ||
        (typeof err.response?.data === 'string' ? err.response.data : null) ||
        'Ошибка обновления профиля';
      setError(Array.isArray(msg) ? msg.join(' ') : String(msg));
    } finally {
      setLoading(false);
    }
  };

  /** Отмена редактирования: откат формы к значениям из state. */
  const handleCancel = () => {
    reset({
      email: user?.email,
      phone_number: user?.phone_number ?? '',
    });
    setEditing(false);
    setError(null);
  };

  if (loading && !user) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error && !user) {
    return (
      <Box>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <Box>
      <Typography variant="overline" color="primary" sx={{ letterSpacing: '0.18em' }}>
        Profile
      </Typography>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
        Профиль
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 2 }}>
                <Avatar
                  src={user.avatar}
                  sx={{ width: 120, height: 120, mb: 2 }}
                >
                  {user.username[0].toUpperCase()}
                </Avatar>
                <Typography variant="h6">{user.username}</Typography>
                <Chip
                  label={user.role === 'tenant' ? 'Арендатор' : 
                         user.role === 'landlord' ? 'Арендодатель' : 'Администратор'}
                  color="primary"
                  sx={{ mt: 1 }}
                />
                {user.is_verified && (
                  <Chip label="Верифицирован" color="success" size="small" sx={{ mt: 1 }} />
                )}
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Без нативного <form>: иначе любая кнопка без type в некоторых браузерах даёт submit (GET) и полную перезагрузку страницы */}
              <Box
                component="div"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && editing) {
                    e.preventDefault();
                    void handleSubmit(onSubmit)();
                  }
                }}
              >
                <TextField
                  fullWidth
                  label="Email"
                  type="email"
                  {...register('email', { required: 'Укажите email' })}
                  disabled={!editing}
                  margin="normal"
                />

                <TextField
                  fullWidth
                  label="Номер телефона"
                  {...register('phone_number')}
                  disabled={!editing}
                  margin="normal"
                />

                <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                  {editing ? (
                    <>
                      <Button
                        type="button"
                        variant="contained"
                        startIcon={<Save />}
                        disabled={loading}
                        fullWidth
                        onClick={handleSubmit(onSubmit)}
                      >
                        Сохранить
                      </Button>
                      <Button
                        type="button"
                        variant="outlined"
                        startIcon={<Cancel />}
                        onClick={handleCancel}
                        fullWidth
                      >
                        Отмена
                      </Button>
                    </>
                  ) : (
                    <Button
                      type="button"
                      variant="outlined"
                      startIcon={<Edit />}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setError(null);
                        setEditing(true);
                      }}
                      fullWidth
                    >
                      Редактировать
                    </Button>
                  )}
                </Box>
              </Box>

              <Divider sx={{ my: 2 }} />

              <Typography variant="body2" color="text.secondary">
                Дата регистрации: {new Date(user.date_joined).toLocaleDateString()}
              </Typography>
              {user.last_login && (
                <Typography variant="body2" color="text.secondary">
                  Последний вход: {new Date(user.last_login).toLocaleDateString()}
                </Typography>
              )}

              <Button
                variant="outlined"
                color="error"
                fullWidth
                onClick={logout}
                sx={{ mt: 2 }}
              >
                Выйти
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
                <Tab label="Информация" />
                <Tab label="Мои объявления" />
                <Tab label="Мои отзывы" />
              </Tabs>

              <TabPanel value={tabValue} index={0}>
                <Typography variant="h6" gutterBottom>
                  Информация о профиле
                </Typography>
                <Typography variant="body1" paragraph>
                  Здесь будет дополнительная информация о пользователе
                </Typography>
              </TabPanel>

              <TabPanel value={tabValue} index={1}>
                <Typography variant="h6" gutterBottom>
                  Мои объявления ({userAds.length})
                </Typography>
                {userAds.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    У вас пока нет объявлений
                  </Typography>
                ) : (
                  <Grid container spacing={2} sx={{ mt: 1 }}>
                    {userAds.map((ad) => (
                      <Grid item xs={12} sm={6} key={ad.id}>
                        <AdCard ad={ad} />
                      </Grid>
                    ))}
                  </Grid>
                )}
              </TabPanel>

              <TabPanel value={tabValue} index={2}>
                <Typography variant="h6" gutterBottom>
                  Мои отзывы ({myReviews.length})
                </Typography>
                {reviewsLoading ? (
                  <Box display="flex" justifyContent="center" py={4}>
                    <CircularProgress size={32} />
                  </Box>
                ) : myReviews.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    Вы ещё не оставляли отзывов
                  </Typography>
                ) : (
                  <TableContainer component={Paper} sx={{ mt: 2 }}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Текст</TableCell>
                          <TableCell>Объявление</TableCell>
                          <TableCell>Модерация</TableCell>
                          <TableCell sx={{ minWidth: 200 }}>Причина отклонения</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {myReviews.map((rev) => (
                          <TableRow key={rev.id}>
                            <TableCell sx={{ maxWidth: 280, verticalAlign: 'top' }}>
                              <Typography variant="body2">{rev.text}</Typography>
                              <Typography variant="caption" color="text.secondary">
                                Оценка: {rev.rating}/5
                              </Typography>
                            </TableCell>
                            <TableCell sx={{ verticalAlign: 'top' }}>
                              <Link to={`/ads/${rev.ad.id}`}>{rev.ad.title}</Link>
                            </TableCell>
                            <TableCell sx={{ verticalAlign: 'top' }}>
                              <Chip
                                size="small"
                                label={statusLabel(rev.status)}
                                color={
                                  rev.status === 'approved'
                                    ? 'success'
                                    : rev.status === 'rejected'
                                    ? 'error'
                                    : 'warning'
                                }
                              />
                            </TableCell>
                            <TableCell sx={{ verticalAlign: 'top', wordBreak: 'break-word' }}>
                              {rev.status === 'rejected' && rev.moderation_rejection_reason ? (
                                rev.moderation_rejection_reason
                              ) : (
                                <Typography variant="body2" color="text.secondary">
                                  —
                                </Typography>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </TabPanel>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ProfilePage;
