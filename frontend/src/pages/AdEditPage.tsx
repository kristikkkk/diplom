/**
 * Редактирование объявления автором: форма, новые фото, удаление карточки.
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  IconButton,
  Paper,
  Chip,
} from '@mui/material';
import { Save, Delete, CloudUpload, Cancel } from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { Ad, AdCreate, Category } from '../types';
import { apiService } from '../services/api';
import { useAuth } from '../hooks/useAuth';

const AdEditPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [ad, setAd] = useState<Ad | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [images, setImages] = useState<File[]>([]);
  const [imagePreviews, setImagePreviews] = useState<string[]>([]);
  const [existingImages, setExistingImages] = useState<any[]>([]);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
    reset,
  } = useForm<AdCreate & { category_id: number }>();

  useEffect(() => {
    if (id) {
      loadAd();
      loadCategories();
    }
  }, [id]);

  /** Загружает объявление и заполняет форму и список уже загруженных изображений. */
  const loadAd = async () => {
    try {
      setLoading(true);
      setError(null);
      const adData = await apiService.getAd(Number(id));
      setAd(adData);
      setExistingImages(adData.images || []);
      reset({
        title: adData.title,
        description: adData.description,
        price: adData.price,
        category_id: adData.category.id,
        location: adData.location || '',
        contact_phone: adData.contact_phone || '',
        contact_email: adData.contact_email || '',
      });
    } catch (err) {
      setError('Ошибка загрузки объявления');
      console.error('Error loading ad:', err);
    } finally {
      setLoading(false);
    }
  };

  /** Справочник категорий для выпадающего списка. */
  const loadCategories = async () => {
    try {
      const categoriesData = await apiService.getCategories();
      setCategories(categoriesData);
    } catch (err) {
      console.error('Error loading categories:', err);
    }
  };

  /** Добавляет локальные файлы для последующей отправки multipart PATCH. */
  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const files = Array.from(event.target.files);
      const newImages = [...images, ...files];
      setImages(newImages);

      const newPreviews = files.map(file => URL.createObjectURL(file));
      setImagePreviews([...imagePreviews, ...newPreviews]);
    }
  };

  /** Удаляет новый файл из очереди загрузки по индексу. */
  const removeImage = (index: number) => {
    const newImages = images.filter((_, i) => i !== index);
    const newPreviews = imagePreviews.filter((_, i) => i !== index);
    setImages(newImages);
    setImagePreviews(newPreviews);
  };

  /** Помечает уже сохранённое изображение к удалению на клиенте до сохранения формы. */
  const removeExistingImage = (imageId: number) => {
    setExistingImages(existingImages.filter(img => img.id !== imageId));
  };

  /** PATCH объявления через FormData и редирект на страницу объявления. */
  const onSubmit = async (data: AdCreate & { category_id: number }) => {
    try {
      setSaving(true);
      setError(null);

      if (!data.category_id) {
        setError('Необходимо выбрать категорию');
        setSaving(false);
        return;
      }

      const formData = new FormData();
      formData.append('title', data.title);
      formData.append('description', data.description);
      formData.append('price', data.price.toString());
      formData.append('category_id', data.category_id.toString());
      
      if (data.location) {
        formData.append('location', data.location);
      }
      if (data.contact_phone) {
        formData.append('contact_phone', data.contact_phone);
      }
      if (data.contact_email) {
        formData.append('contact_email', data.contact_email);
      }

      // Добавляем новые изображения
      images.forEach((image, index) => {
        formData.append('images', image);
        if (index === 0 && existingImages.length === 0) {
          formData.append('is_primary', 'true');
        }
      });

      const response = await fetch(`/api/ads/${id}/`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Ошибка обновления объявления');
      }

      const updatedAd = await response.json();
      navigate(`/ads/${updatedAd.id}`);
    } catch (err: any) {
      setError(err.message || 'Ошибка обновления объявления');
    } finally {
      setSaving(false);
    }
  };

  /** Удаление объявления по подтверждению пользователя. */
  const handleDelete = async () => {
    if (!ad) return;
    if (!window.confirm('Вы уверены, что хотите удалить это объявление?')) {
      return;
    }
    try {
      await apiService.deleteAd(ad.id);
      navigate('/');
    } catch (err) {
      setError('Ошибка удаления объявления');
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
        <Button onClick={() => navigate('/')} sx={{ mt: 2 }}>
          Вернуться назад
        </Button>
      </Box>
    );
  }

  if (!ad) {
    return (
      <Box>
        <Alert severity="warning">Объявление не найдено</Alert>
        <Button onClick={() => navigate('/')} sx={{ mt: 2 }}>
          Вернуться назад
        </Button>
      </Box>
    );
  }

  if (user?.id !== ad.author.id && user?.role !== 'admin') {
    return (
      <Box>
        <Alert severity="error">У вас нет прав на редактирование этого объявления</Alert>
        <Button onClick={() => navigate(`/ads/${ad.id}`)} sx={{ mt: 2 }}>
          Вернуться к объявлению
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="overline" color="primary" sx={{ letterSpacing: '0.18em' }}>
        Edit Listing
      </Typography>
      <Typography variant="h4" component="h1" gutterBottom>
        Редактировать объявление
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <TextField
                  fullWidth
                  label="Заголовок"
                  {...register('title', { required: 'Заголовок обязателен' })}
                  error={!!errors.title}
                  helperText={errors.title?.message}
                  margin="normal"
                />

                <TextField
                  fullWidth
                  multiline
                  rows={6}
                  label="Описание"
                  {...register('description', { required: 'Описание обязательно' })}
                  error={!!errors.description}
                  helperText={errors.description?.message}
                  margin="normal"
                />

                <Grid container spacing={2} sx={{ mt: 1 }}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Цена (₽)"
                      {...register('price', {
                        required: 'Цена обязательна',
                        min: { value: 0, message: 'Цена должна быть положительной' },
                        valueAsNumber: true,
                      })}
                      error={!!errors.price}
                      helperText={errors.price?.message}
                      margin="normal"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth margin="normal">
                      <InputLabel>Категория</InputLabel>
                      <Controller
                        name="category_id"
                        control={control}
                        rules={{ required: 'Категория обязательна' }}
                        render={({ field }) => (
                          <Select
                            {...field}
                            label="Категория"
                            error={!!errors.category_id}
                          >
                            {categories.map((category) => (
                              <MenuItem key={category.id} value={category.id}>
                                {category.name}
                              </MenuItem>
                            ))}
                          </Select>
                        )}
                      />
                    </FormControl>
                  </Grid>
                </Grid>

                <TextField
                  fullWidth
                  label="Местоположение"
                  {...register('location')}
                  margin="normal"
                />
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Контактная информация
                </Typography>

                <TextField
                  fullWidth
                  label="Телефон"
                  {...register('contact_phone')}
                  margin="normal"
                />

                <TextField
                  fullWidth
                  type="email"
                  label="Email"
                  {...register('contact_email')}
                  margin="normal"
                />
              </CardContent>
            </Card>

            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Изображения
                </Typography>

                {existingImages.length > 0 && (
                  <Grid container spacing={1} sx={{ mb: 2 }}>
                    {existingImages.map((image) => (
                      <Grid item xs={6} key={image.id}>
                        <Paper
                          sx={{
                            position: 'relative',
                            paddingTop: '100%',
                            backgroundImage: `url(${image.image})`,
                            backgroundSize: 'cover',
                            backgroundPosition: 'center',
                          }}
                        >
                          <IconButton
                            size="small"
                            onClick={() => removeExistingImage(image.id)}
                            sx={{
                              position: 'absolute',
                              top: 4,
                              right: 4,
                              bgcolor: 'rgba(255, 255, 255, 0.8)',
                            }}
                          >
                            <Delete fontSize="small" />
                          </IconButton>
                          {image.is_primary && (
                            <Chip
                              label="Основное"
                              size="small"
                              color="primary"
                              sx={{
                                position: 'absolute',
                                bottom: 4,
                                left: 4,
                              }}
                            />
                          )}
                        </Paper>
                      </Grid>
                    ))}
                  </Grid>
                )}

                <input
                  accept="image/*"
                  style={{ display: 'none' }}
                  id="image-upload"
                  type="file"
                  multiple
                  onChange={handleImageChange}
                />
                <label htmlFor="image-upload">
                  <Button
                    variant="outlined"
                    component="span"
                    startIcon={<CloudUpload />}
                    fullWidth
                    sx={{ mb: 2 }}
                  >
                    Добавить изображения
                  </Button>
                </label>

                {imagePreviews.length > 0 && (
                  <Grid container spacing={1}>
                    {imagePreviews.map((preview, index) => (
                      <Grid item xs={6} key={index}>
                        <Paper
                          sx={{
                            position: 'relative',
                            paddingTop: '100%',
                            backgroundImage: `url(${preview})`,
                            backgroundSize: 'cover',
                            backgroundPosition: 'center',
                          }}
                        >
                          <IconButton
                            size="small"
                            onClick={() => removeImage(index)}
                            sx={{
                              position: 'absolute',
                              top: 4,
                              right: 4,
                              bgcolor: 'rgba(255, 255, 255, 0.8)',
                            }}
                          >
                            <Delete fontSize="small" />
                          </IconButton>
                        </Paper>
                      </Grid>
                    ))}
                  </Grid>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Cancel />}
            onClick={() => navigate(`/ads/${ad.id}`)}
            disabled={saving}
          >
            Отмена
          </Button>
          <Button
            variant="outlined"
            color="error"
            startIcon={<Delete />}
            onClick={handleDelete}
            disabled={saving}
          >
            Удалить
          </Button>
          <Button
            type="submit"
            variant="contained"
            startIcon={saving ? <CircularProgress size={20} /> : <Save />}
            disabled={saving}
            sx={{ ml: 'auto' }}
          >
            {saving ? 'Сохранение...' : 'Сохранить'}
          </Button>
        </Box>
      </form>
    </Box>
  );
};

export default AdEditPage;
