/**
 * Детальная карточка объявления: фото, отзывы, избранное, чат, удаление для автора.
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardMedia,
  Button,
  Chip,
  Grid,
  IconButton,
  Divider,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Rating,
  Avatar,
  Paper,
} from '@mui/material';
import {
  ArrowBack,
  Favorite,
  FavoriteBorder,
  LocationOn,
  Phone,
  Email,
  Visibility,
  Edit,
  Delete,
  Message,
  Star,
} from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { Ad, Review, ReviewCreate } from '../types';
import { apiService } from '../services/api';
import { useAuth } from '../hooks/useAuth';

const AdDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const [ad, setAd] = useState<Ad | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
    reset,
  } = useForm<ReviewCreate>();

  useEffect(() => {
    if (id) {
      loadAd();
      loadReviews();
    }
  }, [id]);

  /** Загружает объявление по id из URL. */
  const loadAd = async () => {
    try {
      setLoading(true);
      setError(null);
      const adData = await apiService.getAd(Number(id));
      setAd(adData);
    } catch (err) {
      setError('Ошибка загрузки объявления');
      console.error('Error loading ad:', err);
    } finally {
      setLoading(false);
    }
  };

  /** Загружает отзывы, привязанные к текущему объявлению. */
  const loadReviews = async () => {
    try {
      const reviewsData = await apiService.getReviews(Number(id));
      // Убеждаемся, что это массив
      setReviews(Array.isArray(reviewsData) ? reviewsData : []);
    } catch (err) {
      console.error('Error loading reviews:', err);
      setReviews([]);
    }
  };

  /** Переключает признак избранного для текущего объявления. */
  const handleToggleFavorite = async () => {
    if (!ad) return;
    try {
      if (ad.is_favorite) {
        await apiService.removeFromFavorites(ad.id);
      } else {
        await apiService.addToFavorites(ad.id);
      }
      setAd({ ...ad, is_favorite: !ad.is_favorite });
    } catch (err) {
      console.error('Error toggling favorite:', err);
    }
  };

  /** Удаляет объявление и возвращает на главную. */
  const handleDelete = async () => {
    if (!ad) return;
    try {
      await apiService.deleteAd(ad.id);
      navigate('/');
    } catch (err) {
      setError('Ошибка удаления объявления');
    }
  };

  /** Создаёт отзыв через API и обновляет список отзывов. */
  const onSubmitReview = async (data: ReviewCreate) => {
    try {
      await apiService.createReview({ ...data, ad_id: Number(id) });
      setReviewDialogOpen(false);
      reset();
      loadReviews();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Ошибка создания отзыва');
    }
  };

  /** Переход к экрану переписки по этому объявлению. */
  const handleStartChat = () => {
    if (ad) {
      navigate(`/chat/${ad.id}`);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error && !ad) {
    return (
      <Box>
        <Alert severity="error">{error}</Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/')} sx={{ mt: 2 }}>
          Вернуться назад
        </Button>
      </Box>
    );
  }

  if (!ad) {
    return (
      <Box>
        <Alert severity="warning">Объявление не найдено</Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/')} sx={{ mt: 2 }}>
          Вернуться назад
        </Button>
      </Box>
    );
  }

  const primaryImage = ad.images.find(img => img.is_primary) || ad.images[0];
  const isOwner = user?.id === ad.author.id;
  const canEdit = isOwner || user?.role === 'admin';
  const statusColor = ad.status === 'approved' ? 'success' : 
                     ad.status === 'rejected' ? 'error' : 'warning';

  return (
    <Box>
      <Button
        startIcon={<ArrowBack />}
        onClick={() => navigate('/')}
        sx={{ mb: 2 }}
      >
        Назад
      </Button>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Typography variant="overline" color="primary" sx={{ letterSpacing: '0.18em' }}>
        Property Detail
      </Typography>

      <Grid container spacing={3} sx={{ mt: 0.5 }}>
        {/* Левая колонка - изображения и основная информация */}
        <Grid item xs={12} md={8}>
          <Card>
            {primaryImage && (
              <CardMedia
                component="img"
                height="400"
                image={primaryImage.image}
                alt={ad.title}
                sx={{ objectFit: 'cover' }}
              />
            )}
            
            {ad.images.length > 1 && (
              <Box sx={{ p: 2, display: 'flex', gap: 1, overflowX: 'auto' }}>
                {ad.images.map((image) => (
                  <CardMedia
                    key={image.id}
                    component="img"
                    sx={{ width: 100, height: 100, objectFit: 'cover', cursor: 'pointer' }}
                    image={image.image}
                    alt={ad.title}
                  />
                ))}
              </Box>
            )}

            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                <Typography variant="h4" component="h1" gutterBottom>
                  {ad.title}
                </Typography>
                {isAuthenticated && (
                  <IconButton onClick={handleToggleFavorite} color={ad.is_favorite ? 'error' : 'default'}>
                    {ad.is_favorite ? <Favorite /> : <FavoriteBorder />}
                  </IconButton>
                )}
              </Box>

              <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                <Chip label={ad.category.name} color="primary" variant="outlined" />
                <Chip 
                  label={ad.status === 'approved' ? 'Одобрено' : 
                         ad.status === 'rejected' ? 'Отклонено' : 'На модерации'} 
                  color={statusColor}
                />
                {ad.is_featured && <Chip label="Рекомендуемое" color="secondary" />}
              </Box>

              <Typography variant="h5" color="primary" fontWeight="bold" gutterBottom>
                {ad.price.toLocaleString()} ₽
              </Typography>

              <Divider sx={{ my: 2 }} />

              <Typography variant="h6" gutterBottom>
                Описание
              </Typography>
              <Typography variant="body1" paragraph>
                {ad.description}
              </Typography>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <LocationOn color="action" />
                <Typography variant="body2" color="text.secondary">
                  {ad.location || 'Местоположение не указано'}
                </Typography>
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Visibility color="action" />
                <Typography variant="body2" color="text.secondary">
                  Просмотров: {ad.views_count}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
                  Опубликовано: {new Date(ad.created_at).toLocaleDateString()}
                </Typography>
              </Box>

              {canEdit && (
                <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                  <Button
                    variant="outlined"
                    startIcon={<Edit />}
                    onClick={() => navigate(`/ads/${ad.id}/edit`)}
                  >
                    Редактировать
                  </Button>
                  <Button
                    variant="outlined"
                    color="error"
                    startIcon={<Delete />}
                    onClick={() => setDeleteDialogOpen(true)}
                  >
                    Удалить
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>

          {/* Отзывы */}
          <Card sx={{ mt: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Отзывы ({reviews.length})
                </Typography>
                {isAuthenticated && !isOwner && (
                  <Button
                    variant="outlined"
                    startIcon={<Star />}
                    onClick={() => setReviewDialogOpen(true)}
                  >
                    Оставить отзыв
                  </Button>
                )}
              </Box>

              {reviews.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Пока нет отзывов
                </Typography>
              ) : (
                <Box>
                  {reviews.map((review) => (
                    <Paper key={review.id} sx={{ p: 2, mb: 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <Avatar sx={{ mr: 1 }}>{review.author.username[0]}</Avatar>
                        <Box sx={{ flexGrow: 1 }}>
                          <Typography variant="subtitle2">{review.author.username}</Typography>
                          <Rating value={review.rating} readOnly size="small" />
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          {new Date(review.created_at).toLocaleDateString()}
                        </Typography>
                      </Box>
                      <Typography variant="body2">{review.text}</Typography>
                    </Paper>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Правая колонка - контакты и действия */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Контактная информация
              </Typography>

              {ad.contact_phone && (
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Phone color="action" sx={{ mr: 1 }} />
                  <Typography variant="body1">{ad.contact_phone}</Typography>
                </Box>
              )}

              {ad.contact_email && (
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Email color="action" sx={{ mr: 1 }} />
                  <Typography variant="body1">{ad.contact_email}</Typography>
                </Box>
              )}

              <Divider sx={{ my: 2 }} />

              <Typography variant="h6" gutterBottom>
                Автор объявления
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar sx={{ mr: 1 }}>{ad.author.username[0]}</Avatar>
                <Box>
                  <Typography variant="subtitle1">{ad.author.username}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {ad.author.role === 'tenant' ? 'Арендатор' : 
                     ad.author.role === 'landlord' ? 'Арендодатель' : 'Администратор'}
                  </Typography>
                </Box>
              </Box>

              {isAuthenticated && !isOwner && (
                <Button
                  fullWidth
                  variant="contained"
                  startIcon={<Message />}
                  onClick={handleStartChat}
                  sx={{ mt: 2 }}
                >
                  Написать автору
                </Button>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Диалог создания отзыва */}
      <Dialog open={reviewDialogOpen} onClose={() => setReviewDialogOpen(false)} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit(onSubmitReview)}>
          <DialogTitle>Оставить отзыв</DialogTitle>
          <DialogContent>
            <Box sx={{ mb: 2, mt: 1 }}>
              <Typography component="legend" gutterBottom>Рейтинг</Typography>
              <Controller
                name="rating"
                control={control}
                rules={{ required: 'Укажите рейтинг' }}
                defaultValue={5}
                render={({ field }) => (
                  <Rating
                    {...field}
                    size="large"
                    value={Number(field.value)}
                    onChange={(_, value) => field.onChange(value || 5)}
                  />
                )}
              />
              {errors.rating && (
                <Typography variant="caption" color="error" display="block">
                  {errors.rating.message}
                </Typography>
              )}
            </Box>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Текст отзыва"
              {...register('text', { required: 'Введите текст отзыва' })}
              error={!!errors.text}
              helperText={errors.text?.message}
              sx={{ mt: 2 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setReviewDialogOpen(false)}>Отмена</Button>
            <Button type="submit" variant="contained">Отправить</Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Диалог подтверждения удаления */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Подтверждение удаления</DialogTitle>
        <DialogContent>
          <Typography>Вы уверены, что хотите удалить это объявление?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Отмена</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Удалить
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AdDetailPage;
